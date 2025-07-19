"""
任务管理模块

提供下载任务的队列管理和并发控制功能
"""

from .task_manager import TaskManager
from .task_queue import TaskQueue

__all__ = [
    'TaskManager',
    'TaskQueue'
] 