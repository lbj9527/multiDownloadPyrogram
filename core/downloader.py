"""
Telegram下载器核心逻辑
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pyrogram.client import Client
from pyrogram.errors import FloodWait

from models import DownloadTask, TaskRange, TaskResult, TaskStatus
from utils import get_logger, log_performance, retry_async
from .message_handler import MessageHandler
from .file_processor import FileProcessor

logger = get_logger(__name__)


class TelegramDownloader:
    """Telegram下载器"""
    
    def __init__(self, file_processor: FileProcessor):
        self.file_processor = file_processor
        self.message_handler = MessageHandler(file_processor)
        self.stats = {
            "start_time": 0,
            "total_downloaded": 0,
            "total_failed": 0,
            "total_processed": 0
        }
    
    @log_performance
    async def download_range(
        self,
        client: Client,
        task: DownloadTask
    ) -> TaskResult:
        """
        下载指定范围的消息
        
        Args:
            client: Pyrogram客户端
            task: 下载任务
            
        Returns:
            任务结果
        """
        if not task.message_range:
            raise ValueError("任务缺少消息范围信息")
        
        client_name = task.client_name
        start_id = task.message_range.start_id
        end_id = task.message_range.end_id
        
        logger.info(f"{client_name} 开始下载消息范围: {start_id}-{end_id}")

        # 获取频道信息（只需要一次）
        try:
            channel_info = await self._get_channel_info(client, task.channel)
            logger.info(f"频道信息: {channel_info['username']} - {channel_info['title']}")
        except Exception as e:
            logger.warning(f"获取频道信息失败: {e}")

        # 初始化结果
        result = TaskResult(
            task_id=task.task_id,
            client_name=client_name,
            status=TaskStatus.RUNNING,
            start_time=datetime.now()
        )
        
        downloaded = 0
        failed = 0
        
        try:
            # 获取消息范围内的所有消息ID
            message_ids = list(range(start_id, end_id + 1))
            
            # 批量获取消息
            batch_size = task.batch_size
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                
                try:
                    # 获取消息批次
                    messages = await self._get_messages_with_retry(
                        client, task.channel, batch_ids
                    )
                    
                    # 处理每条消息
                    batch_downloaded, batch_failed = await self._process_message_batch(
                        client, messages, task
                    )
                    
                    downloaded += batch_downloaded
                    failed += batch_failed
                    
                    # 更新任务进度
                    processed = i + len(batch_ids)
                    task.update_progress(processed, downloaded, failed)
                    
                    # 显示进度
                    progress = processed / len(message_ids) * 100
                    logger.info(
                        f"{client_name} 进度: {progress:.1f}% "
                        f"({downloaded} 成功, {failed} 失败)"
                    )
                    
                except FloodWait as e:
                    logger.warning(f"{client_name} 遇到限流，等待 {e.value} 秒")
                    await asyncio.sleep(float(e.value))
                except Exception as e:
                    logger.error(f"{client_name} 批量获取消息失败: {e}")
                    failed += len(batch_ids)
                
                # 小延迟避免过于频繁的请求
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"{client_name} 下载任务失败: {e}")
            result.status = TaskStatus.FAILED
            result.error_message = str(e)
        
        # 完成结果
        result.downloaded = downloaded
        result.failed = failed
        result.end_time = datetime.now()
        result.status = TaskStatus.COMPLETED if result.status != TaskStatus.FAILED else TaskStatus.FAILED
        
        logger.info(f"{client_name} 完成下载: {downloaded} 成功, {failed} 失败")
        return result
    
    @retry_async(max_retries=3, delay=1.0)
    async def _get_messages_with_retry(
        self,
        client: Client,
        channel: str,
        message_ids: List[int]
    ) -> List[Any]:
        """
        带重试的消息获取
        
        Args:
            client: Pyrogram客户端
            channel: 频道名称
            message_ids: 消息ID列表
            
        Returns:
            消息列表
        """
        return await client.get_messages(channel, message_ids)
    
    async def _process_message_batch(
        self,
        client: Client,
        messages: List[Any],
        task: DownloadTask
    ) -> tuple[int, int]:
        """
        处理消息批次
        
        Args:
            client: Pyrogram客户端
            messages: 消息列表
            task: 下载任务
            
        Returns:
            (成功数量, 失败数量)
        """
        downloaded = 0
        failed = 0
        
        for message in messages:
            if message:
                try:
                    success = await self.message_handler.process_message(
                        client, message, task.channel
                    )
                    if success:
                        downloaded += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"处理消息 {message.id} 失败: {e}")
        
        return downloaded, failed

    async def _get_channel_info(self, client: Client, channel: str) -> dict:
        """
        获取频道信息

        Args:
            client: Pyrogram客户端
            channel: 频道名称

        Returns:
            频道信息字典
        """
        try:
            chat = await client.get_chat(channel)
            username = f"@{chat.username}" if chat.username else f"id_{chat.id}"
            title = chat.title or "Unknown"

            # 清理文件名中的非法字符
            from utils import sanitize_filename
            safe_title = sanitize_filename(title)
            folder_name = f"{username}-{safe_title}"

            return {
                "username": username,
                "title": title,
                "folder_name": folder_name,
                "chat_id": chat.id
            }
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")
            # 失败时返回默认信息
            safe_channel_name = channel.replace('@', '').replace('/', '_')
            return {
                "username": f"@{safe_channel_name}",
                "title": "Unknown",
                "folder_name": f"@{safe_channel_name}-Unknown",
                "chat_id": None
            }

    def create_task_ranges(
        self,
        start_id: int,
        end_id: int,
        num_clients: int
    ) -> List[TaskRange]:
        """
        创建任务范围分片
        
        Args:
            start_id: 开始消息ID
            end_id: 结束消息ID
            num_clients: 客户端数量
            
        Returns:
            任务范围列表
        """
        total_messages = end_id - start_id + 1
        messages_per_client = total_messages // num_clients
        remainder = total_messages % num_clients
        
        ranges = []
        current_start = start_id
        
        for i in range(num_clients):
            # 分配消息数量（余数分配给前几个客户端）
            messages_for_this_client = messages_per_client + (1 if i < remainder else 0)
            current_end = current_start + messages_for_this_client - 1
            
            ranges.append(TaskRange(current_start, current_end))
            current_start = current_end + 1
        
        return ranges
    
    def get_download_stats(self) -> Dict[str, Any]:
        """
        获取下载统计信息
        
        Returns:
            统计信息字典
        """
        elapsed_time = time.time() - self.stats["start_time"] if self.stats["start_time"] > 0 else 0
        total_processed = self.stats["total_downloaded"] + self.stats["total_failed"]
        
        return {
            "total_downloaded": self.stats["total_downloaded"],
            "total_failed": self.stats["total_failed"],
            "total_processed": total_processed,
            "success_rate": (
                self.stats["total_downloaded"] / total_processed * 100 
                if total_processed > 0 else 0
            ),
            "elapsed_time": elapsed_time,
            "download_rate": (
                self.stats["total_downloaded"] / elapsed_time 
                if elapsed_time > 0 else 0
            )
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "start_time": time.time(),
            "total_downloaded": 0,
            "total_failed": 0,
            "total_processed": 0
        }
    
    def update_stats(self, downloaded: int, failed: int):
        """
        更新统计信息
        
        Args:
            downloaded: 成功下载数量
            failed: 失败数量
        """
        self.stats["total_downloaded"] += downloaded
        self.stats["total_failed"] += failed
        self.stats["total_processed"] += downloaded + failed
