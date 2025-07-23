"""
下载接口
为UI、API等提供统一的下载接口
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from models import DownloadTask, TaskRange, TaskStatus
from services import ClientManager
from core import TelegramDownloader
from utils import get_logger

logger = get_logger(__name__)


class DownloadInterface:
    """下载接口类"""
    
    def __init__(self, client_manager: ClientManager, downloader: TelegramDownloader):
        self.client_manager = client_manager
        self.downloader = downloader
        self.active_tasks: Dict[str, DownloadTask] = {}
        self.progress_callbacks: List[Callable] = []
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加进度回调函数
        
        Args:
            callback: 进度回调函数
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """
        移除进度回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_progress(self, progress_data: Dict[str, Any]):
        """
        通知进度更新
        
        Args:
            progress_data: 进度数据
        """
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                logger.error(f"进度回调函数执行失败: {e}")
    
    async def download_messages(
        self,
        channel: str,
        start_message_id: int,
        end_message_id: int,
        batch_size: int = 200,
        storage_mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        下载消息范围
        
        Args:
            channel: 频道名称
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            batch_size: 批次大小
            storage_mode: 存储模式
            
        Returns:
            下载结果列表
        """
        logger.info(f"开始下载任务: {channel} ({start_message_id}-{end_message_id})")
        
        # 获取可用客户端
        available_clients = self.client_manager.get_available_clients()
        if not available_clients:
            raise ValueError("没有可用的客户端")
        
        # 创建任务范围
        task_ranges = self.downloader.create_task_ranges(
            start_message_id, end_message_id, len(available_clients)
        )
        
        # 创建下载任务
        tasks = []
        for i, (client_name, task_range) in enumerate(zip(available_clients, task_ranges)):
            task = DownloadTask(
                client_name=client_name,
                channel=channel,
                message_range=task_range,
                batch_size=batch_size,
                storage_mode=storage_mode
            )
            
            # 启动任务
            task.start(client_name)
            
            # 存储活动任务
            self.active_tasks[task.task_id] = task
            
            # 更新客户端任务信息
            self.client_manager.update_client_task(client_name, task.task_id)
            
            tasks.append(task)
            
            logger.info(f"创建任务 {i+1}: {client_name} -> {task_range}")
        
        # 并发执行所有任务
        download_tasks = []
        for task in tasks:
            client = self.client_manager.get_client(task.client_name)
            if client:
                download_task = self._execute_task_with_progress(client, task)
                download_tasks.append(download_task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"任务 {task.task_id} 执行失败: {result}")
                task.fail(str(result))
                processed_results.append({
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": "failed",
                    "error": str(result),
                    "downloaded": 0,
                    "failed": task.message_range.total_messages if task.message_range else 0
                })
            else:
                task.complete(result)
                processed_results.append({
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": "completed",
                    "downloaded": result.downloaded,
                    "failed": result.failed,
                    "duration": result.duration
                })
            
            # 清理任务信息
            self.client_manager.update_client_task(task.client_name, None)
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
        
        logger.info("所有下载任务完成")
        return processed_results
    
    async def _execute_task_with_progress(self, client, task: DownloadTask):
        """
        执行任务并报告进度
        
        Args:
            client: Pyrogram客户端
            task: 下载任务
            
        Returns:
            任务结果
        """
        try:
            # 创建进度监控任务
            progress_task = asyncio.create_task(
                self._monitor_task_progress(task)
            )
            
            # 执行下载任务
            result = await self.downloader.download_range(client, task)
            
            # 取消进度监控
            progress_task.cancel()
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            raise
    
    async def _monitor_task_progress(self, task: DownloadTask):
        """
        监控任务进度
        
        Args:
            task: 下载任务
        """
        try:
            while not task.is_completed:
                # 发送进度更新
                progress_data = {
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": task.status.value,
                    "progress_percentage": task.progress_percentage,
                    "processed_messages": task.processed_messages,
                    "total_messages": task.total_messages,
                    "downloaded_files": task.downloaded_files,
                    "failed_downloads": task.failed_downloads,
                    "duration": task.duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                self._notify_progress(progress_data)
                
                # 等待一段时间再次检查
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass
        except Exception as e:
            logger.error(f"监控任务进度失败: {e}")
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        获取活动任务列表
        
        Returns:
            活动任务信息列表
        """
        return [task.to_dict() for task in self.active_tasks.values()]
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        task = self.active_tasks.get(task_id)
        return task.to_dict() if task else None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        try:
            # 标记任务为取消状态
            task.cancel()
            
            # 更新客户端状态
            self.client_manager.update_client_task(task.client_name, None)
            
            # 从活动任务中移除
            del self.active_tasks[task_id]
            
            logger.info(f"任务 {task_id} 已取消")
            return True
            
        except Exception as e:
            logger.error(f"取消任务 {task_id} 失败: {e}")
            return False
    
    async def cancel_all_tasks(self) -> int:
        """
        取消所有活动任务
        
        Returns:
            取消的任务数量
        """
        cancelled_count = 0
        task_ids = list(self.active_tasks.keys())
        
        for task_id in task_ids:
            if await self.cancel_task(task_id):
                cancelled_count += 1
        
        logger.info(f"已取消 {cancelled_count} 个任务")
        return cancelled_count
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """
        获取下载统计信息
        
        Returns:
            统计信息字典
        """
        # 获取客户端统计
        client_stats = self.client_manager.get_client_stats()
        
        # 获取下载器统计
        download_stats = self.downloader.get_download_stats()
        
        # 获取活动任务统计
        active_tasks_count = len(self.active_tasks)
        running_tasks = sum(1 for task in self.active_tasks.values() if task.is_running)
        
        return {
            "client_stats": client_stats,
            "download_stats": download_stats,
            "active_tasks": active_tasks_count,
            "running_tasks": running_tasks,
            "task_details": self.get_active_tasks()
        }
