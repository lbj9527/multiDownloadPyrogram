"""
任务队列管理模块

负责管理和调度下载任务，支持优先级、并发控制和任务状态跟踪
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from pyrogram.types import Message

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import TaskError, TaskQueueError


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(Enum):
    """任务优先级枚举"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class DownloadTask:
    """下载任务"""
    task_id: str
    message: Message
    chat_title: Optional[str] = None
    custom_path: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    file_path: Optional[str] = None
    file_size: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # 任务类型
    task_type: str = "download"  # download, group_download, chunk_download
    
    # 额外参数
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """任务初始化后处理"""
        if self.message.media_group_id:
            self.task_type = "group_download"
        elif hasattr(self.message, 'document') and self.message.document:
            if self.message.document.file_size > 50 * 1024 * 1024:  # 50MB
                self.task_type = "chunk_download"
    
    @property
    def duration(self) -> float:
        """获取任务执行时间"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return 0.0
    
    @property
    def age(self) -> float:
        """获取任务年龄（创建到现在的时间）"""
        return time.time() - self.created_at
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "age": self.age,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "chat_title": self.chat_title,
            "message_id": self.message.id if self.message else None,
            "media_group_id": self.message.media_group_id if self.message else None
        }


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, config: Config):
        """
        初始化任务队列
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.TaskQueue")
        
        # 任务队列 - 按优先级分组
        self.pending_tasks: Dict[TaskPriority, deque] = {
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque()
        }
        
        # 任务存储
        self.tasks: Dict[str, DownloadTask] = {}
        self.running_tasks: Dict[str, DownloadTask] = {}
        self.completed_tasks: Dict[str, DownloadTask] = {}
        self.failed_tasks: Dict[str, DownloadTask] = {}
        
        # 配置
        self.max_queue_size = 10000
        self.max_concurrent_tasks = config.download.max_concurrent_downloads
        self.task_timeout = config.download.timeout
        self.cleanup_interval = 3600  # 1小时清理一次
        
        # 统计信息
        self.total_tasks_added = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
        self.total_tasks_cancelled = 0
        
        # 回调函数
        self.task_added_callback: Optional[Callable] = None
        self.task_started_callback: Optional[Callable] = None
        self.task_completed_callback: Optional[Callable] = None
        self.task_failed_callback: Optional[Callable] = None
        
        # 控制标志
        self._is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def set_callbacks(self, 
                     task_added: Optional[Callable] = None,
                     task_started: Optional[Callable] = None,
                     task_completed: Optional[Callable] = None,
                     task_failed: Optional[Callable] = None):
        """
        设置回调函数
        
        Args:
            task_added: 任务添加回调
            task_started: 任务开始回调
            task_completed: 任务完成回调
            task_failed: 任务失败回调
        """
        self.task_added_callback = task_added
        self.task_started_callback = task_started
        self.task_completed_callback = task_completed
        self.task_failed_callback = task_failed
    
    def add_task(self, task: DownloadTask) -> bool:
        """
        添加任务到队列
        
        Args:
            task: 下载任务
            
        Returns:
            是否添加成功
        """
        if len(self.tasks) >= self.max_queue_size:
            self.logger.warning("任务队列已满，无法添加新任务")
            return False
        
        if task.task_id in self.tasks:
            self.logger.warning(f"任务已存在: {task.task_id}")
            return False
        
        # 添加到任务存储
        self.tasks[task.task_id] = task
        
        # 添加到对应优先级的队列
        self.pending_tasks[task.priority].append(task)
        task.status = TaskStatus.QUEUED
        
        self.total_tasks_added += 1
        self.logger.debug(f"任务已添加: {task.task_id} (优先级: {task.priority.name})")
        
        # 触发回调
        if self.task_added_callback:
            try:
                self.task_added_callback(task)
            except Exception as e:
                self.logger.error(f"任务添加回调失败: {e}")
        
        return True
    
    def get_next_task(self) -> Optional[DownloadTask]:
        """
        获取下一个待执行的任务（按优先级）
        
        Returns:
            下一个任务，如果没有则返回None
        """
        # 按优先级顺序检查队列
        for priority in [TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            if self.pending_tasks[priority]:
                task = self.pending_tasks[priority].popleft()
                return task
        
        return None
    
    def start_task(self, task: DownloadTask) -> bool:
        """
        开始执行任务
        
        Args:
            task: 下载任务
            
        Returns:
            是否开始成功
        """
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            self.logger.warning("并发任务数已达上限")
            return False
        
        if task.task_id in self.running_tasks:
            self.logger.warning(f"任务已在运行: {task.task_id}")
            return False
        
        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        # 添加到运行任务列表
        self.running_tasks[task.task_id] = task
        
        self.logger.debug(f"任务开始执行: {task.task_id}")
        
        # 触发回调
        if self.task_started_callback:
            try:
                self.task_started_callback(task)
            except Exception as e:
                self.logger.error(f"任务开始回调失败: {e}")
        
        return True
    
    def complete_task(self, task_id: str, file_path: Optional[str] = None, 
                     file_size: int = 0) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            file_path: 文件路径
            file_size: 文件大小
            
        Returns:
            是否完成成功
        """
        if task_id not in self.running_tasks:
            self.logger.warning(f"任务不在运行列表中: {task_id}")
            return False
        
        task = self.running_tasks.pop(task_id)
        
        # 更新任务状态
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.file_path = file_path
        task.file_size = file_size
        
        # 移动到完成列表
        self.completed_tasks[task_id] = task
        
        self.total_tasks_completed += 1
        self.logger.info(f"任务完成: {task_id} (用时: {task.duration:.2f}s)")
        
        # 触发回调
        if self.task_completed_callback:
            try:
                self.task_completed_callback(task)
            except Exception as e:
                self.logger.error(f"任务完成回调失败: {e}")
        
        return True
    
    def fail_task(self, task_id: str, error_message: str) -> bool:
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error_message: 错误消息
            
        Returns:
            是否标记成功
        """
        if task_id not in self.running_tasks:
            self.logger.warning(f"任务不在运行列表中: {task_id}")
            return False
        
        task = self.running_tasks.pop(task_id)
        
        # 更新任务状态
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        task.error_message = error_message
        task.retry_count += 1
        
        # 检查是否可以重试
        if task.can_retry():
            self.logger.info(f"任务失败，将重试: {task_id} (重试次数: {task.retry_count}/{task.max_retries})")
            # 重新添加到队列
            task.status = TaskStatus.QUEUED
            self.pending_tasks[task.priority].append(task)
        else:
            # 移动到失败列表
            self.failed_tasks[task_id] = task
            self.total_tasks_failed += 1
            self.logger.error(f"任务失败: {task_id} - {error_message}")
        
        # 触发回调
        if self.task_failed_callback:
            try:
                self.task_failed_callback(task)
            except Exception as e:
                self.logger.error(f"任务失败回调失败: {e}")
        
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        if task_id not in self.tasks:
            self.logger.warning(f"任务不存在: {task_id}")
            return False
        
        task = self.tasks[task_id]
        
        # 从对应队列中移除
        if task.status == TaskStatus.QUEUED:
            try:
                self.pending_tasks[task.priority].remove(task)
            except ValueError:
                pass
        elif task.status == TaskStatus.RUNNING:
            self.running_tasks.pop(task_id, None)
        
        # 更新任务状态
        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        
        self.total_tasks_cancelled += 1
        self.logger.info(f"任务已取消: {task_id}")
        
        return True
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[DownloadTask]:
        """按状态获取任务"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return sum(len(queue) for queue in self.pending_tasks.values())
    
    def get_running_count(self) -> int:
        """获取正在运行的任务数"""
        return len(self.running_tasks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            "total_tasks": len(self.tasks),
            "queue_size": self.get_queue_size(),
            "running_count": self.get_running_count(),
            "completed_count": len(self.completed_tasks),
            "failed_count": len(self.failed_tasks),
            "cancelled_count": self.total_tasks_cancelled,
            "total_added": self.total_tasks_added,
            "total_completed": self.total_tasks_completed,
            "total_failed": self.total_tasks_failed,
            "success_rate": (self.total_tasks_completed / self.total_tasks_added) * 100
            if self.total_tasks_added > 0 else 0,
            "priority_distribution": {
                priority.name: len(queue) for priority, queue in self.pending_tasks.items()
            }
        }
    
    def clear_completed_tasks(self, older_than: Optional[float] = None):
        """
        清理完成的任务
        
        Args:
            older_than: 清理多久之前的任务（秒）
        """
        if older_than is None:
            older_than = 3600  # 1小时
        
        cutoff_time = time.time() - older_than
        
        # 清理完成的任务
        to_remove = []
        for task_id, task in self.completed_tasks.items():
            if task.completed_at and task.completed_at < cutoff_time:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            self.completed_tasks.pop(task_id, None)
            self.tasks.pop(task_id, None)
        
        # 清理失败的任务
        to_remove = []
        for task_id, task in self.failed_tasks.items():
            if task.completed_at and task.completed_at < cutoff_time:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            self.failed_tasks.pop(task_id, None)
            self.tasks.pop(task_id, None)
        
        if to_remove:
            self.logger.info(f"清理了 {len(to_remove)} 个旧任务")
    
    def clear_all_tasks(self):
        """清理所有任务"""
        self.tasks.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        
        for queue in self.pending_tasks.values():
            queue.clear()
        
        self.logger.info("所有任务已清理")
    
    def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("清理任务已启动")
    
    def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        self.logger.info("清理任务已停止")
    
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self.clear_completed_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理任务异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟 