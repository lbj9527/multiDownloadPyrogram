"""
MultiDownloadPyrogram 主程序
Telegram频道历史消息批量下载工具
"""

import asyncio
import os
import sys
from typing import Optional, List
from pyrogram import Client
from pyrogram.types import Message

from .utils.config import init_config, get_config
from .utils.logger import get_logger, get_download_logger, setup_pyrogram_logging
from .utils.exceptions import MultiDownloadError
from .client.client_manager import ClientManager
from .downloader.media_downloader import MediaDownloader


class MultiDownloadApp:
    """多客户端下载应用程序"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = init_config(config_path)
        self.logger = get_logger()
        self.download_logger = get_download_logger()
        self.client_manager = ClientManager(self.config)
        self.downloader = MediaDownloader(self.config)
        
        # 设置Pyrogram日志
        setup_pyrogram_logging()
    
    async def download_channel_history(self) -> dict:
        """
        根据配置文件下载频道历史消息
        
        Returns:
            dict: 下载结果统计
        """
        # 从配置获取任务参数
        channel_username = self.config.task.channel_username
        start_message_id = self.config.task.start_message_id
        end_message_id = self.config.task.end_message_id
        limit = self.config.task.limit
        
        self.logger.info(f"开始下载频道 {channel_username} 的历史消息")
        self.logger.info(f"消息范围: {start_message_id} - {end_message_id}, 限制: {limit}")
        
        # 验证参数
        if not channel_username:
            raise ValidationError("频道用户名不能为空", "channel_username", channel_username)
        
        # 初始化统计信息
        stats = {
            'channel': channel_username,
            'total_messages': 0,
            'media_messages': 0,
            'downloaded_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'start_message_id': start_message_id,
            'end_message_id': end_message_id,
            'limit': limit
        }
        
        try:
            # 使用客户端管理器
            async with self.client_manager.managed_clients() as clients:
                if not clients:
                    raise MultiDownloadError("没有可用的客户端")
                
                self.logger.info(f"使用 {len(clients)} 个客户端进行下载")
                
                # 获取消息列表
                messages = await self._get_channel_messages(
                    clients[0],  # 使用第一个客户端获取消息列表
                    channel_username,
                    start_message_id,
                    end_message_id,
                    limit
                )
                
                stats['total_messages'] = len(messages)
                self.logger.info(f"获取到 {len(messages)} 条消息")
                
                # 过滤包含媒体的消息
                media_messages = [msg for msg in messages if self._has_media(msg)]
                stats['media_messages'] = len(media_messages)
                self.logger.info(f"其中包含媒体的消息: {len(media_messages)} 条")
                
                if not media_messages:
                    self.logger.warning("没有找到包含媒体的消息")
                    return stats
                
                # 开始下载会话
                self.download_logger.start_download_session(len(media_messages))
                
                # 分配任务给多个客户端
                download_results = await self._download_with_multiple_clients(
                    clients,
                    media_messages
                )
                
                # 统计结果
                for result in download_results:
                    if result['success']:
                        stats['downloaded_files'] += result['downloaded_count']
                    else:
                        stats['failed_files'] += result['failed_count']
                        stats['skipped_files'] += result['skipped_count']
                
                # 记录会话总结
                self.download_logger.log_session_summary()
                
                self.logger.info(
                    f"下载完成: 成功 {stats['downloaded_files']}, "
                    f"失败 {stats['failed_files']}, "
                    f"跳过 {stats['skipped_files']}"
                )
                
                return stats
                
        except Exception as e:
            self.logger.error(f"下载频道历史消息失败: {str(e)}")
            raise
    
    async def _get_channel_messages(
        self,
        client: Client,
        channel_username: str,
        start_message_id: Optional[int],
        end_message_id: Optional[int],
        limit: Optional[int]
    ) -> List[Message]:
        """
        获取频道消息列表
        
        Args:
            client: Pyrogram客户端
            channel_username: 频道用户名
            start_message_id: 起始消息ID
            end_message_id: 结束消息ID
            limit: 消息数量限制
            
        Returns:
            List[Message]: 消息列表
        """
        messages = []
        
        try:
            # 获取频道信息
            chat = await client.get_chat(channel_username)
            self.logger.info(f"频道信息: {chat.title} (ID: {chat.id})")
            
            # 设置获取参数
            offset_id = end_message_id or 0
            collected_count = 0
            max_limit = limit or 1000  # 默认最多1000条
            
            self.logger.info(f"开始获取消息，范围: {start_message_id} - {end_message_id}, 限制: {max_limit}")
            
            async for message in client.get_chat_history(
                chat_id=channel_username,
                offset_id=offset_id,
                limit=None  # 不限制单次获取数量
            ):
                # 检查消息ID范围
                if start_message_id and message.id < start_message_id:
                    break
                
                if end_message_id and message.id > end_message_id:
                    continue
                
                messages.append(message)
                collected_count += 1
                
                # 检查数量限制
                if collected_count >= max_limit:
                    break
                
                # 定期报告进度
                if collected_count % 100 == 0:
                    self.logger.info(f"已获取 {collected_count} 条消息")
            
            # 按消息ID排序（从旧到新）
            messages.sort(key=lambda x: x.id)
            
            self.logger.info(f"消息获取完成，共 {len(messages)} 条")
            return messages
            
        except Exception as e:
            self.logger.error(f"获取频道消息失败: {str(e)}")
            raise
    
    async def _download_with_multiple_clients(
        self,
        clients: List[Client],
        messages: List[Message]
    ) -> List[dict]:
        """
        使用多个客户端并发下载
        
        Args:
            clients: 客户端列表
            messages: 消息列表
            
        Returns:
            List[dict]: 每个客户端的下载结果
        """
        # 确保消息按ID排序，避免重复处理
        messages = sorted(messages, key=lambda x: x.id)
        
        # 去重处理：对于媒体组消息，只保留第一个
        unique_messages = []
        processed_group_ids = set()
        
        for message in messages:
            if message.media_group_id:
                if message.media_group_id not in processed_group_ids:
                    unique_messages.append(message)
                    processed_group_ids.add(message.media_group_id)
            else:
                unique_messages.append(message)
        
        self.logger.info(f"去重后消息数量: {len(unique_messages)} (原始: {len(messages)})")
        
        # 将消息平均分配给不同的客户端
        client_count = len(clients)
        message_chunks = []
        
        # 使用更均匀的分配策略
        chunk_size = len(unique_messages) // client_count
        remainder = len(unique_messages) % client_count
        
        start_idx = 0
        for i in range(client_count):
            # 如果有余数，前面的客户端多分配一个
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end_idx = start_idx + current_chunk_size
            
            chunk = unique_messages[start_idx:end_idx]
            message_chunks.append(chunk)
            start_idx = end_idx
        
        self.logger.info(f"消息分配: {[len(chunk) for chunk in message_chunks]}")
        
        # 为每个客户端创建下载任务
        download_tasks = []
        for i, (client, message_chunk) in enumerate(zip(clients, message_chunks)):
            task = self._download_client_messages(client, i, message_chunk)
            download_tasks.append(task)
        
        # 并发执行所有下载任务
        self.logger.info(f"开始并发执行 {len(download_tasks)} 个下载任务")
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"客户端 {i} 下载任务失败: {str(result)}")
                processed_results.append({
                    'client_index': i,
                    'success': False,
                    'error': str(result),
                    'downloaded_count': 0,
                    'failed_count': 0,
                    'skipped_count': 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _download_client_messages(
        self,
        client: Client,
        client_index: int,
        messages: List[Message]
    ) -> dict:
        """
        单个客户端下载消息
        
        Args:
            client: Pyrogram客户端
            client_index: 客户端索引
            messages: 分配给该客户端的消息列表
            
        Returns:
            dict: 下载结果
        """
        result = {
            'client_index': client_index,
            'success': True,
            'downloaded_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'errors': []
        }
        
        self.logger.info(f"客户端 {client_index} 开始下载 {len(messages)} 条消息")
        
        for message in messages:
            if not self._has_media(message):
                result['skipped_count'] += 1
                continue
            
            # 为每个客户端创建独立的下载目录，避免文件冲突
            client_download_dir = os.path.join(
                self.config.download.download_dir,
                f"client_{client_index}"
            )
            os.makedirs(client_download_dir, exist_ok=True)
            
            # 下载媒体文件
            try:
                if message.media_group_id:
                    # 媒体组下载
                    downloaded_paths = await self.downloader.download_media_group(
                        client,
                        message,
                        custom_dir=os.path.join(client_download_dir, f"media_group_{message.media_group_id}")
                    )
                    if downloaded_paths:
                        result['downloaded_count'] += len(downloaded_paths)
                        self.logger.debug(f"客户端 {client_index} 媒体组下载成功: {len(downloaded_paths)} 个文件")
                    else:
                        result['failed_count'] += 1
                        self.logger.warning(f"客户端 {client_index} 媒体组下载失败: 消息 {message.id}")
                else:
                    # 单个媒体文件下载
                    downloaded_path = await self.downloader.download_with_retry(
                        client,
                        message,
                        max_retries=self.config.download.max_retries,
                        custom_dir=client_download_dir
                    )
                    
                    if downloaded_path:
                        result['downloaded_count'] += 1
                        self.logger.debug(f"客户端 {client_index} 下载成功: {downloaded_path}")
                    else:
                        result['failed_count'] += 1
                        self.logger.warning(f"客户端 {client_index} 下载失败: 消息 {message.id}")
                        
            except Exception as e:
                result['failed_count'] += 1
                error_msg = f"消息 {message.id}: {str(e)}"
                result['errors'].append(error_msg)
                self.logger.error(f"客户端 {client_index} 下载异常: {error_msg}")
        
        self.logger.info(
            f"客户端 {client_index} 下载完成: "
            f"成功 {result['downloaded_count']}, "
            f"失败 {result['failed_count']}, "
            f"跳过 {result['skipped_count']}"
        )
        
        return result
    
    def _has_media(self, message: Message) -> bool:
        """检查消息是否包含媒体"""
        return bool(
            message.photo or
            message.video or
            message.audio or
            message.voice or
            message.video_note or
            message.sticker or
            message.animation or
            message.document
        )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            return await self.client_manager.health_check()
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        try:
            await self.client_manager.cleanup()
            self.logger.info("应用程序清理完成")
        except Exception as e:
            self.logger.error(f"清理资源失败: {str(e)}")


async def main():
    """主函数"""
    try:
        # 检查配置文件是否存在
        config_path = "config.json"
        if not os.path.exists(config_path):
            print(f"错误: 配置文件 {config_path} 不存在")
            print("请复制 config.example.json 为 config.json 并填写配置")
            sys.exit(1)
        
        # 创建应用程序实例
        app = MultiDownloadApp(config_path)
        logger = app.logger
        
        logger.info("MultiDownloadPyrogram 启动")
        logger.info(f"配置文件: {config_path}")
        logger.info(f"目标频道: {app.config.task.channel_username}")
        logger.info(f"客户端数量: {app.config.download.client_count}")
        logger.info(f"下载目录: {app.config.download.download_dir}")
        
        try:
            # 执行下载任务
            stats = await app.download_channel_history()
            
            # 输出最终统计
            logger.info("=" * 50)
            logger.info("下载统计:")
            logger.info(f"  频道: {stats['channel']}")
            logger.info(f"  总消息数: {stats['total_messages']}")
            logger.info(f"  媒体消息数: {stats['media_messages']}")
            logger.info(f"  下载成功: {stats['downloaded_files']}")
            logger.info(f"  下载失败: {stats['failed_files']}")
            logger.info(f"  跳过文件: {stats['skipped_files']}")
            
            success_rate = (
                stats['downloaded_files'] / max(stats['media_messages'], 1) * 100
            )
            logger.info(f"  成功率: {success_rate:.1f}%")
            logger.info("=" * 50)
            
            # 根据成功率决定退出码
            if success_rate >= 95:
                sys.exit(0)
            elif success_rate >= 80:
                sys.exit(1)
            else:
                sys.exit(2)
                
        finally:
            # 清理资源
            await app.cleanup()
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
        sys.exit(130)
    except MultiDownloadError as e:
        print(f"应用程序错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 