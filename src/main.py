"""
MultiDownloadPyrogram 主应用程序

基于Pyrogram的高性能Telegram媒体下载工具
"""

import asyncio
import sys
import argparse
from typing import Optional, List
from pathlib import Path

from utils.config import get_config, setup_config
from utils.logger import setup_logging, get_logger
from task.task_manager import TaskManager, TaskPriority
from client.client_pool import ClientPool


class MultiDownloadPyrogram:
    """主应用程序类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化应用程序
        
        Args:
            config_file: 配置文件路径
        """
        # 设置配置
        self.config = setup_config(config_file)
        
        # 设置日志
        self.logger = setup_logging(
            log_level=self.config.logging.level,
            log_file=self.config.logging.log_file,
            log_dir=self.config.logging.log_dir,
            console_output=self.config.logging.console_output,
            json_format=self.config.logging.json_format
        )
        
        # 初始化任务管理器
        self.task_manager = TaskManager(self.config)
        
        # 设置进度回调
        self.task_manager.set_progress_callback(self._on_progress)
        self.task_manager.set_task_status_callback(self._on_task_status)
        
        self.logger.info("MultiDownloadPyrogram 应用程序初始化完成")
    
    async def initialize(self, session_strings: Optional[List[str]] = None) -> bool:
        """
        初始化应用程序
        
        Args:
            session_strings: 会话字符串列表
            
        Returns:
            是否初始化成功
        """
        self.logger.info("正在初始化应用程序...")
        
        try:
            # 初始化任务管理器
            if not await self.task_manager.initialize(session_strings):
                self.logger.error("任务管理器初始化失败")
                return False
            
            self.logger.info("应用程序初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"应用程序初始化失败: {e}")
            return False
    
    async def start(self):
        """启动应用程序"""
        self.logger.info("启动 MultiDownloadPyrogram...")
        
        # 启动任务管理器
        await self.task_manager.start()
        
        self.logger.info("应用程序已启动")
    
    async def stop(self):
        """停止应用程序"""
        self.logger.info("正在停止应用程序...")
        
        # 停止任务管理器
        await self.task_manager.shutdown()
        
        self.logger.info("应用程序已停止")
    
    async def download_channel_history(self, channel_username: str, 
                                     limit: Optional[int] = None,
                                     start_message_id: Optional[int] = None,
                                     end_message_id: Optional[int] = None) -> List[str]:
        """
        下载频道历史消息
        
        Args:
            channel_username: 频道用户名
            limit: 消息限制数量
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            
        Returns:
            任务ID列表
        """
        self.logger.info(f"开始下载频道历史消息: {channel_username}")
        
        # 检查客户端池状态
        pool_info = self.task_manager.client_pool.get_pool_info()
        available_clients = pool_info["available_clients"]
        
        if available_clients == 0:
            # 尝试重连所有客户端
            self.logger.warning("没有可用客户端，尝试重连...")
            for manager in self.task_manager.client_pool.client_managers:
                if manager.can_retry():
                    try:
                        await manager.reconnect()
                        if manager.is_available():
                            self.logger.info(f"客户端重连成功: {manager.client_id}")
                            break
                    except Exception as e:
                        self.logger.error(f"客户端重连失败: {manager.client_id}, {e}")
            
            # 再次检查
            pool_info = self.task_manager.client_pool.get_pool_info()
            available_clients = pool_info["available_clients"]
            
            if available_clients == 0:
                raise RuntimeError("没有可用的客户端，请检查网络连接和配置")
        
        # 获取一个可用的客户端
        client_manager = self.task_manager.client_pool.select_client()
        if not client_manager:
            raise RuntimeError("没有可用的客户端")
        
        # 获取消息
        messages = []
        try:
            async for message in client_manager.client.get_chat_history(
                channel_username, 
                limit=limit,
                offset_id=start_message_id,
                reverse=True
            ):
                if end_message_id and message.id > end_message_id:
                    break
                
                if message.media:
                    messages.append(message)
        except Exception as e:
            self.logger.error(f"获取频道消息失败: {e}")
            raise RuntimeError(f"获取频道消息失败: {e}")
        
        self.logger.info(f"找到 {len(messages)} 条媒体消息")
        
        # 获取频道标题
        try:
            chat = await client_manager.client.get_chat(channel_username)
            chat_title = chat.title
        except:
            chat_title = channel_username
        
        # 批量添加下载任务
        task_ids = self.task_manager.add_batch_download_tasks(
            messages,
            chat_title=chat_title,
            priority=TaskPriority.NORMAL
        )
        
        self.logger.info(f"已添加 {len(task_ids)} 个下载任务")
        return task_ids
    
    async def download_messages(self, channel_username: str, 
                              message_ids: List[int]) -> List[str]:
        """
        下载指定消息
        
        Args:
            channel_username: 频道用户名
            message_ids: 消息ID列表
            
        Returns:
            任务ID列表
        """
        self.logger.info(f"开始下载指定消息: {channel_username}, 消息数: {len(message_ids)}")
        
        # 获取一个可用的客户端
        client_manager = self.task_manager.client_pool.select_client()
        if not client_manager:
            raise RuntimeError("没有可用的客户端")
        
        # 获取消息
        messages = []
        for message_id in message_ids:
            try:
                message = await client_manager.client.get_messages(channel_username, message_id)
                if message and message.media:
                    messages.append(message)
            except Exception as e:
                self.logger.error(f"获取消息失败: {message_id}, {e}")
        
        self.logger.info(f"找到 {len(messages)} 条有效媒体消息")
        
        # 获取频道标题
        try:
            chat = await client_manager.client.get_chat(channel_username)
            chat_title = chat.title
        except:
            chat_title = channel_username
        
        # 批量添加下载任务
        task_ids = self.task_manager.add_batch_download_tasks(
            messages,
            chat_title=chat_title,
            priority=TaskPriority.NORMAL
        )
        
        self.logger.info(f"已添加 {len(task_ids)} 个下载任务")
        return task_ids
    
    def get_statistics(self):
        """获取统计信息"""
        return self.task_manager.get_statistics()
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        
        print("\n=== MultiDownloadPyrogram 统计信息 ===")
        print(f"队列大小: {stats['queue_size']}")
        print(f"运行中任务: {stats['running_count']}")
        print(f"已完成任务: {stats['completed_count']}")
        print(f"失败任务: {stats['failed_count']}")
        print(f"总任务数: {stats['total_tasks']}")
        print(f"成功率: {stats['success_rate']:.2f}%")
        
        print(f"\n客户端池状态:")
        print(f"总客户端数: {stats['client_pool']['total_clients']}")
        print(f"可用客户端数: {stats['client_pool']['available_clients']}")
        print(f"客户端可用率: {stats['client_pool']['client_availability']:.2f}%")
        
        print(f"\n下载器统计:")
        media_stats = stats['downloader_stats']['media_downloader']
        print(f"媒体下载完成: {media_stats['downloads_completed']}")
        print(f"媒体下载失败: {media_stats['downloads_failed']}")
        print(f"媒体下载字节数: {media_stats['bytes_downloaded']}")
        
        chunk_stats = stats['downloader_stats']['chunk_downloader']
        print(f"分片下载完成: {chunk_stats['total_chunks_downloaded']}")
        print(f"分片下载失败: {chunk_stats['total_chunks_failed']}")
        
        group_stats = stats['downloader_stats']['group_downloader']
        print(f"媒体组下载完成: {group_stats['groups_downloaded']}")
        print(f"媒体组下载失败: {group_stats['groups_failed']}")
        
        print("=" * 40)
    
    async def _on_progress(self, progress_type: str, progress_data: dict):
        """进度回调"""
        if self.config.logging.level == "DEBUG":
            self.logger.debug(f"进度更新 [{progress_type}]: {progress_data}")
    
    def _on_task_status(self, status_type: str, task_data: dict):
        """任务状态回调"""
        if status_type == "task_completed":
            self.logger.info(f"任务完成: {task_data['task_id']} - {task_data['file_path']}")
        elif status_type == "task_failed":
            self.logger.error(f"任务失败: {task_data['task_id']} - {task_data['error_message']}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="MultiDownloadPyrogram - 高性能Telegram媒体下载工具"
    )
    
    parser.add_argument(
        "--config", "-c",
        help="配置文件路径",
        default="config.json"
    )
    
    parser.add_argument(
        "--channel", "-ch",
        help="频道用户名",
        required=True
    )
    
    parser.add_argument(
        "--limit", "-l",
        help="下载消息数量限制",
        type=int,
        default=None
    )
    
    parser.add_argument(
        "--start-id",
        help="开始消息ID",
        type=int,
        default=None
    )
    
    parser.add_argument(
        "--end-id",
        help="结束消息ID",
        type=int,
        default=None
    )
    
    parser.add_argument(
        "--message-ids",
        help="指定消息ID列表（逗号分隔）",
        default=None
    )
    
    parser.add_argument(
        "--dry-run",
        help="仅模拟运行，不实际下载",
        action="store_true"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        help="详细输出",
        action="store_true"
    )
    
    return parser


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # 创建应用程序实例
        app = MultiDownloadPyrogram(args.config)
        
        # 设置详细输出
        if args.verbose:
            app.config.logging.level = "DEBUG"
        
        # 设置模拟运行
        if args.dry_run:
            app.config.dry_run = True
            print("模拟运行模式")
        
        async with app:
            if args.message_ids:
                # 下载指定消息
                message_ids = [int(mid.strip()) for mid in args.message_ids.split(",")]
                task_ids = await app.download_messages(args.channel, message_ids)
            else:
                # 下载频道历史消息
                task_ids = await app.download_channel_history(
                    args.channel,
                    limit=args.limit,
                    start_message_id=args.start_id,
                    end_message_id=args.end_id
                )
            
            print(f"已添加 {len(task_ids)} 个下载任务")
            
            # 等待任务完成
            while True:
                stats = app.get_statistics()
                
                if stats['running_count'] == 0 and stats['queue_size'] == 0:
                    break
                
                # 每10秒打印一次统计信息
                app.print_statistics()
                await asyncio.sleep(10)
            
            # 打印最终统计
            print("\n=== 下载完成 ===")
            app.print_statistics()
            
    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 