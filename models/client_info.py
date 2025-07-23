"""
客户端信息数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ClientStatus(Enum):
    """客户端状态枚举"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DOWNLOADING = "downloading"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class ClientInfo:
    """客户端信息模型"""
    name: str
    session_file: str
    status: ClientStatus = ClientStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None
    
    # 连接信息
    is_connected: bool = False
    connection_time: Optional[datetime] = None
    disconnection_time: Optional[datetime] = None
    
    # 任务信息
    current_task_id: Optional[str] = None
    total_tasks_completed: int = 0
    total_files_downloaded: int = 0
    total_download_failures: int = 0
    
    # 性能统计
    average_download_speed: float = 0.0  # MB/s
    total_bytes_downloaded: int = 0
    
    # 错误信息
    last_error: Optional[str] = None
    error_count: int = 0
    
    def connect(self):
        """标记客户端已连接"""
        self.status = ClientStatus.CONNECTED
        self.is_connected = True
        self.connection_time = datetime.now()
        self.last_activity = datetime.now()
    
    def disconnect(self):
        """标记客户端已断开"""
        self.status = ClientStatus.DISCONNECTED
        self.is_connected = False
        self.disconnection_time = datetime.now()
        self.current_task_id = None
    
    def start_task(self, task_id: str):
        """开始执行任务"""
        self.status = ClientStatus.DOWNLOADING
        self.current_task_id = task_id
        self.last_activity = datetime.now()
    
    def complete_task(self, downloaded: int, failed: int, bytes_downloaded: int):
        """完成任务"""
        self.status = ClientStatus.CONNECTED
        self.current_task_id = None
        self.total_tasks_completed += 1
        self.total_files_downloaded += downloaded
        self.total_download_failures += failed
        self.total_bytes_downloaded += bytes_downloaded
        self.last_activity = datetime.now()
        
        # 更新平均下载速度
        self._update_average_speed()
    
    def report_error(self, error_message: str):
        """报告错误"""
        self.status = ClientStatus.ERROR
        self.last_error = error_message
        self.error_count += 1
        self.last_activity = datetime.now()
    
    def recover_from_error(self):
        """从错误中恢复"""
        if self.is_connected:
            self.status = ClientStatus.CONNECTED
        else:
            self.status = ClientStatus.DISCONNECTED
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = datetime.now()
    
    def _update_average_speed(self):
        """更新平均下载速度"""
        if self.connection_time and self.total_bytes_downloaded > 0:
            duration = (datetime.now() - self.connection_time).total_seconds()
            if duration > 0:
                # 转换为 MB/s
                self.average_download_speed = (self.total_bytes_downloaded / (1024 * 1024)) / duration
    
    @property
    def is_available(self) -> bool:
        """是否可用于新任务"""
        return self.status in [ClientStatus.IDLE, ClientStatus.CONNECTED] and self.is_connected
    
    @property
    def is_busy(self) -> bool:
        """是否正在忙碌"""
        return self.status == ClientStatus.DOWNLOADING
    
    @property
    def connection_duration(self) -> Optional[float]:
        """连接持续时间（秒）"""
        if not self.connection_time:
            return None
        
        end_time = self.disconnection_time or datetime.now()
        return (end_time - self.connection_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """下载成功率"""
        total = self.total_files_downloaded + self.total_download_failures
        return (self.total_files_downloaded / total * 100) if total > 0 else 0.0
    
    @property
    def total_downloads(self) -> int:
        """总下载尝试次数"""
        return self.total_files_downloaded + self.total_download_failures
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'session_file': self.session_file,
            'status': self.status.value,
            'is_connected': self.is_connected,
            'current_task_id': self.current_task_id,
            'total_tasks_completed': self.total_tasks_completed,
            'total_files_downloaded': self.total_files_downloaded,
            'total_download_failures': self.total_download_failures,
            'success_rate': self.success_rate,
            'average_download_speed': self.average_download_speed,
            'total_bytes_downloaded': self.total_bytes_downloaded,
            'connection_duration': self.connection_duration,
            'last_error': self.last_error,
            'error_count': self.error_count,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }
