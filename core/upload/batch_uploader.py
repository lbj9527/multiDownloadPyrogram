"""
批量上传器
支持多文件并发上传和进度管理
"""
import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from pyrogram.client import Client
from models.upload_task import UploadTask, UploadStatus, BatchUploadResult
from .upload_manager import UploadManager
from utils.logging_utils import LoggerMixin


class BatchUploader(LoggerMixin):
    """批量上传器"""
    
    def __init__(self, max_concurrent: int = 3):
        """
        初始化批量上传器
        
        Args:
            max_concurrent: 最大并发上传数
        """
        self.max_concurrent = max_concurrent
        self.upload_manager = UploadManager()
        self.active_uploads = {}  # 活跃的上传任务
        self.upload_semaphore = asyncio.Semaphore(max_concurrent)
    
    async def upload_batch(self, client: Client, tasks: List[UploadTask],
                          progress_callback: Optional[Callable] = None) -> BatchUploadResult:
        """
        批量上传文件
        
        Args:
            client: Pyrogram客户端
            tasks: 上传任务列表
            progress_callback: 进度回调函数
            
        Returns:
            BatchUploadResult: 批量上传结果
        """
        if not tasks:
            self.log_warning("没有要上传的任务")
            return BatchUploadResult()
        
        # 创建批量结果
        batch_result = BatchUploadResult(
            total_tasks=len(tasks),
            start_time=time.time(),
            tasks=tasks.copy()
        )
        
        self.log_info(f"开始批量上传 {len(tasks)} 个文件，最大并发: {self.max_concurrent}")
        
        try:
            # 创建上传任务
            upload_coroutines = [
                self._upload_single_task(client, task, batch_result, progress_callback)
                for task in tasks
            ]
            
            # 并发执行上传
            await asyncio.gather(*upload_coroutines, return_exceptions=True)
            
        except Exception as e:
            self.log_error(f"批量上传异常: {e}")
        
        finally:
            batch_result.end_time = time.time()
            self._finalize_batch_result(batch_result)
        
        return batch_result
    
    async def _upload_single_task(self, client: Client, task: UploadTask,
                                 batch_result: BatchUploadResult,
                                 progress_callback: Optional[Callable] = None):
        """
        上传单个任务（带并发控制）
        
        Args:
            client: Pyrogram客户端
            task: 上传任务
            batch_result: 批量结果
            progress_callback: 进度回调
        """
        async with self.upload_semaphore:
            try:
                # 记录活跃上传
                self.active_uploads[task.task_id] = task
                
                # 创建任务级别的进度回调
                def task_progress_callback(current_task: UploadTask, current: int, total: int):
                    if progress_callback:
                        progress_callback(batch_result, current_task, current, total)
                
                # 执行上传
                success = await self.upload_manager.upload_task(
                    client, task, task_progress_callback
                )
                
                # 更新批量结果
                if success:
                    batch_result.completed_tasks += 1
                elif task.status == UploadStatus.CANCELLED:
                    batch_result.cancelled_tasks += 1
                else:
                    batch_result.failed_tasks += 1
                
            except Exception as e:
                self.log_error(f"任务 {task.task_id} 上传异常: {e}")
                task.fail_upload(str(e))
                batch_result.failed_tasks += 1
            
            finally:
                # 移除活跃上传记录
                self.active_uploads.pop(task.task_id, None)
    
    async def upload_with_retry(self, client: Client, tasks: List[UploadTask],
                               max_retries: int = 3,
                               progress_callback: Optional[Callable] = None) -> BatchUploadResult:
        """
        带重试的批量上传
        
        Args:
            client: Pyrogram客户端
            tasks: 上传任务列表
            max_retries: 最大重试次数
            progress_callback: 进度回调函数
            
        Returns:
            BatchUploadResult: 批量上传结果
        """
        # 设置任务的最大重试次数
        for task in tasks:
            task.max_retries = max_retries
        
        # 执行初始上传
        result = await self.upload_batch(client, tasks, progress_callback)
        
        # 重试失败的任务
        retry_round = 1
        while retry_round <= max_retries:
            failed_tasks = [task for task in result.tasks if task.can_retry()]
            
            if not failed_tasks:
                break
            
            self.log_info(f"第 {retry_round} 轮重试，重试 {len(failed_tasks)} 个失败任务")
            
            # 重试失败的任务
            retry_result = await self.upload_batch(client, failed_tasks, progress_callback)
            
            # 更新总体结果
            result.completed_tasks += retry_result.completed_tasks
            result.failed_tasks = len([task for task in result.tasks 
                                     if task.status == UploadStatus.FAILED])
            
            retry_round += 1
        
        return result
    
    def _finalize_batch_result(self, batch_result: BatchUploadResult):
        """
        完善批量结果统计
        
        Args:
            batch_result: 批量结果
        """
        # 统计各种状态的任务数量
        batch_result.completed_tasks = len([
            task for task in batch_result.tasks 
            if task.status == UploadStatus.COMPLETED
        ])
        
        batch_result.failed_tasks = len([
            task for task in batch_result.tasks 
            if task.status == UploadStatus.FAILED
        ])
        
        batch_result.cancelled_tasks = len([
            task for task in batch_result.tasks 
            if task.status == UploadStatus.CANCELLED
        ])
        
        # 记录统计信息
        success_rate = batch_result.get_success_rate()
        duration = batch_result.get_duration()
        
        self.log_info(f"批量上传完成: {batch_result.completed_tasks}/{batch_result.total_tasks} 成功 "
                     f"(成功率: {success_rate:.1f}%, 耗时: {duration:.1f}秒)")
    
    async def cancel_batch(self, batch_id: str):
        """
        取消批量上传
        
        Args:
            batch_id: 批量上传ID
        """
        cancelled_count = 0
        
        for task in self.active_uploads.values():
            if task.status == UploadStatus.UPLOADING:
                task.cancel_upload()
                cancelled_count += 1
        
        self.log_info(f"已取消 {cancelled_count} 个正在上传的任务")
    
    def get_active_uploads(self) -> List[UploadTask]:
        """
        获取当前活跃的上传任务
        
        Returns:
            List[UploadTask]: 活跃任务列表
        """
        return list(self.active_uploads.values())
    
    def get_upload_progress(self) -> Dict[str, Any]:
        """
        获取整体上传进度
        
        Returns:
            Dict[str, Any]: 进度信息
        """
        active_tasks = self.get_active_uploads()
        
        if not active_tasks:
            return {
                "active_uploads": 0,
                "total_progress": 0.0,
                "average_speed": 0.0,
                "estimated_time": 0.0
            }
        
        total_progress = sum(task.progress.progress_percent for task in active_tasks)
        average_progress = total_progress / len(active_tasks)
        
        total_speed = sum(task.progress.upload_speed for task in active_tasks)
        average_speed = total_speed / len(active_tasks)
        
        # 估算剩余时间
        remaining_tasks = len([task for task in active_tasks 
                             if task.progress.progress_percent < 100])
        estimated_time = 0.0
        if remaining_tasks > 0 and average_speed > 0:
            avg_remaining_bytes = sum(
                task.file_size - task.progress.uploaded_bytes 
                for task in active_tasks 
                if task.progress.progress_percent < 100
            ) / remaining_tasks
            estimated_time = avg_remaining_bytes / average_speed
        
        return {
            "active_uploads": len(active_tasks),
            "total_progress": average_progress,
            "average_speed": average_speed,
            "estimated_time": estimated_time,
            "tasks": [task.to_dict() for task in active_tasks]
        }
    
    async def upload_to_multiple_channels(self, client: Client, task: UploadTask,
                                        target_channels: List[str],
                                        progress_callback: Optional[Callable] = None) -> List[UploadTask]:
        """
        上传到多个频道
        
        Args:
            client: Pyrogram客户端
            task: 原始上传任务
            target_channels: 目标频道列表
            progress_callback: 进度回调函数
            
        Returns:
            List[UploadTask]: 每个频道的上传任务
        """
        if not target_channels:
            self.log_warning("没有指定目标频道")
            return []
        
        # 为每个频道创建独立的上传任务
        tasks = []
        for channel in target_channels:
            # 复制原任务
            channel_task = UploadTask(
                source_message_id=task.source_message_id,
                target_channel=channel,
                file_name=task.file_name,
                file_size=task.file_size,
                file_data=task.file_data,  # 共享文件数据
                upload_type=task.upload_type,
                mime_type=task.mime_type,
                caption=task.caption,
                formatted_content=task.formatted_content,
                max_retries=task.max_retries,
                metadata=task.metadata.copy()
            )
            tasks.append(channel_task)
        
        self.log_info(f"开始上传到 {len(target_channels)} 个频道: {', '.join(target_channels)}")
        
        # 批量上传
        batch_result = await self.upload_batch(client, tasks, progress_callback)
        
        self.log_info(f"多频道上传完成: {batch_result.completed_tasks}/{len(tasks)} 成功")
        
        return tasks
    
    def create_upload_summary(self, batch_result: BatchUploadResult) -> Dict[str, Any]:
        """
        创建上传摘要
        
        Args:
            batch_result: 批量上传结果
            
        Returns:
            Dict[str, Any]: 上传摘要
        """
        total_size = sum(task.file_size for task in batch_result.tasks)
        successful_size = sum(
            task.file_size for task in batch_result.tasks 
            if task.status == UploadStatus.COMPLETED
        )
        
        return {
            "batch_id": batch_result.batch_id,
            "total_tasks": batch_result.total_tasks,
            "completed_tasks": batch_result.completed_tasks,
            "failed_tasks": batch_result.failed_tasks,
            "cancelled_tasks": batch_result.cancelled_tasks,
            "success_rate": batch_result.get_success_rate(),
            "duration": batch_result.get_duration(),
            "total_size_mb": total_size / (1024 * 1024),
            "successful_size_mb": successful_size / (1024 * 1024),
            "average_speed_mbps": (successful_size / batch_result.get_duration() / (1024 * 1024)) 
                                 if batch_result.get_duration() > 0 else 0,
            "failed_tasks_details": [
                {
                    "task_id": task.task_id,
                    "file_name": task.file_name,
                    "target_channel": task.target_channel,
                    "error": task.error_message
                }
                for task in batch_result.tasks 
                if task.status == UploadStatus.FAILED
            ]
        }
