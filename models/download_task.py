"""
下载任务相关数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskRange:
    """任务消息范围"""
    start_id: int
    end_id: int
    
    @property
    def total_messages(self) -> int:
        return self.end_id - self.start_id + 1
    
    def __str__(self) -> str:
        return f"{self.start_id}-{self.end_id}"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    client_name: str
    status: TaskStatus
    downloaded: int = 0
    failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    file_paths: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """任务执行时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.downloaded + self.failed
        return (self.downloaded / total * 100) if total > 0 else 0.0


@dataclass
class DownloadTask:
    """下载任务模型"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str = ""
    channel: str = ""
    message_range: Optional[TaskRange] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 进度信息
    total_messages: int = 0
    processed_messages: int = 0
    downloaded_files: int = 0
    failed_downloads: int = 0
    
    # 配置信息
    batch_size: int = 200
    storage_mode: str = "hybrid"
    
    # 结果信息
    result: Optional[TaskResult] = None
    error_details: Optional[str] = None
    
    def start(self, client_name: str):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.client_name = client_name
        self.started_at = datetime.now()
        
        if self.message_range:
            self.total_messages = self.message_range.total_messages
    
    def complete(self, result: 'TaskResult'):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        self.downloaded_files = result.downloaded
        self.failed_downloads = result.failed
    
    def fail(self, error_message: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_details = error_message
    
    def cancel(self):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def update_progress(self, processed: int, downloaded: int, failed: int):
        """更新进度"""
        self.processed_messages = processed
        self.downloaded_files = downloaded
        self.failed_downloads = failed
    
    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_messages == 0:
            return 0.0
        return (self.processed_messages / self.total_messages) * 100
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == TaskStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    @property
    def duration(self) -> Optional[float]:
        """任务持续时间（秒）"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'client_name': self.client_name,
            'channel': self.channel,
            'message_range': str(self.message_range) if self.message_range else None,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_messages': self.total_messages,
            'processed_messages': self.processed_messages,
            'downloaded_files': self.downloaded_files,
            'failed_downloads': self.failed_downloads,
            'progress_percentage': self.progress_percentage,
            'duration': self.duration,
            'error_details': self.error_details
        }
