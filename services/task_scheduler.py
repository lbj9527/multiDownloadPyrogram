"""
任务调度服务
负责任务的创建、分配、监控
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from models import DownloadTask, TaskRange, TaskStatus
from utils import get_logger, TaskManager

logger = get_logger(__name__)


class ScheduleType(Enum):
    """调度类型"""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    RECURRING = "recurring"


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_manager = TaskManager(max_concurrent_tasks)
        self.scheduled_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue: List[DownloadTask] = []
        self.running_tasks: Dict[str, DownloadTask] = {}
        self.completed_tasks: List[DownloadTask] = []
        self.failed_tasks: List[DownloadTask] = []
        
        # 调度器状态
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
    
    async def start_scheduler(self):
        """启动任务调度器"""
        if self.is_running:
            logger.warning("任务调度器已在运行")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("任务调度器已启动")
    
    async def stop_scheduler(self):
        """停止任务调度器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 取消所有运行中的任务
        await self.task_manager.cancel_all()
        
        logger.info("任务调度器已停止")
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        try:
            while self.is_running:
                # 处理队列中的任务
                await self._process_task_queue()
                
                # 检查调度任务
                await self._check_scheduled_tasks()
                
                # 清理完成的任务
                self._cleanup_completed_tasks()
                
                # 等待一段时间
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.info("调度器循环被取消")
        except Exception as e:
            logger.error(f"调度器循环异常: {e}")
    
    async def _process_task_queue(self):
        """处理任务队列"""
        while (self.task_queue and 
               len(self.running_tasks) < self.max_concurrent_tasks):
            
            task = self.task_queue.pop(0)
            await self._start_task(task)
    
    async def _start_task(self, task: DownloadTask):
        """启动任务"""
        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # 添加到运行任务列表
            self.running_tasks[task.task_id] = task
            
            logger.info(f"启动任务: {task.task_id}")
            
            # 这里应该调用实际的下载逻辑
            # 由于这是调度器，实际执行由其他组件负责
            
        except Exception as e:
            logger.error(f"启动任务失败: {e}")
            task.fail(str(e))
            self.failed_tasks.append(task)
    
    async def _check_scheduled_tasks(self):
        """检查调度任务"""
        current_time = datetime.now()
        
        for task_id, schedule_info in list(self.scheduled_tasks.items()):
            schedule_time = schedule_info["schedule_time"]
            
            if current_time >= schedule_time:
                task = schedule_info["task"]
                schedule_type = schedule_info["type"]
                
                # 添加到任务队列
                self.add_task_to_queue(task)
                
                # 处理不同类型的调度
                if schedule_type == ScheduleType.RECURRING:
                    # 重复任务，重新调度
                    interval = schedule_info.get("interval", timedelta(hours=1))
                    self.schedule_task(task, schedule_time + interval, ScheduleType.RECURRING, interval)
                else:
                    # 一次性任务，移除调度
                    del self.scheduled_tasks[task_id]
    
    def _cleanup_completed_tasks(self):
        """清理完成的任务"""
        completed_task_ids = []
        
        for task_id, task in self.running_tasks.items():
            if task.is_completed:
                completed_task_ids.append(task_id)
                
                if task.status == TaskStatus.COMPLETED:
                    self.completed_tasks.append(task)
                else:
                    self.failed_tasks.append(task)
        
        # 从运行任务中移除
        for task_id in completed_task_ids:
            del self.running_tasks[task_id]
    
    def add_task_to_queue(self, task: DownloadTask) -> str:
        """
        添加任务到队列
        
        Args:
            task: 下载任务
            
        Returns:
            任务ID
        """
        task.status = TaskStatus.PENDING
        self.task_queue.append(task)
        
        logger.info(f"任务已添加到队列: {task.task_id}")
        return task.task_id
    
    def schedule_task(
        self,
        task: DownloadTask,
        schedule_time: datetime,
        schedule_type: ScheduleType = ScheduleType.IMMEDIATE,
        interval: Optional[timedelta] = None
    ) -> str:
        """
        调度任务
        
        Args:
            task: 下载任务
            schedule_time: 调度时间
            schedule_type: 调度类型
            interval: 重复间隔（仅用于重复任务）
            
        Returns:
            任务ID
        """
        schedule_info = {
            "task": task,
            "schedule_time": schedule_time,
            "type": schedule_type,
            "created_at": datetime.now()
        }
        
        if interval:
            schedule_info["interval"] = interval
        
        self.scheduled_tasks[task.task_id] = schedule_info
        
        logger.info(f"任务已调度: {task.task_id} at {schedule_time}")
        return task.task_id
    
    def create_download_task(
        self,
        channel: str,
        start_message_id: int,
        end_message_id: int,
        client_name: str = "",
        batch_size: int = 200,
        storage_mode: str = "hybrid"
    ) -> DownloadTask:
        """
        创建下载任务
        
        Args:
            channel: 频道名称
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            client_name: 客户端名称
            batch_size: 批次大小
            storage_mode: 存储模式
            
        Returns:
            下载任务
        """
        task_range = TaskRange(start_message_id, end_message_id)
        
        task = DownloadTask(
            client_name=client_name,
            channel=channel,
            message_range=task_range,
            batch_size=batch_size,
            storage_mode=storage_mode
        )
        
        return task
    
    def get_task_by_id(self, task_id: str) -> Optional[DownloadTask]:
        """
        根据ID获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象
        """
        # 检查运行中的任务
        if task_id in self.running_tasks:
            return self.running_tasks[task_id]
        
        # 检查队列中的任务
        for task in self.task_queue:
            if task.task_id == task_id:
                return task
        
        # 检查已完成的任务
        for task in self.completed_tasks + self.failed_tasks:
            if task.task_id == task_id:
                return task
        
        # 检查调度任务
        if task_id in self.scheduled_tasks:
            return self.scheduled_tasks[task_id]["task"]
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        # 从队列中移除
        for i, task in enumerate(self.task_queue):
            if task.task_id == task_id:
                task.cancel()
                self.task_queue.pop(i)
                logger.info(f"任务已从队列中取消: {task_id}")
                return True
        
        # 从运行任务中取消
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            logger.info(f"运行中的任务已取消: {task_id}")
            return True
        
        # 从调度任务中移除
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            logger.info(f"调度任务已取消: {task_id}")
            return True
        
        return False
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        获取调度器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "is_running": self.is_running,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "queued_tasks": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "scheduled_tasks": len(self.scheduled_tasks),
            "task_manager_stats": self.task_manager.get_stats()
        }
    
    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有任务信息
        
        Returns:
            任务信息字典
        """
        return {
            "queued": [task.to_dict() for task in self.task_queue],
            "running": [task.to_dict() for task in self.running_tasks.values()],
            "completed": [task.to_dict() for task in self.completed_tasks],
            "failed": [task.to_dict() for task in self.failed_tasks],
            "scheduled": [
                {
                    **info["task"].to_dict(),
                    "schedule_time": info["schedule_time"].isoformat(),
                    "schedule_type": info["type"].value
                }
                for info in self.scheduled_tasks.values()
            ]
        }
