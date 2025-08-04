"""
上传任务数据模型
定义上传任务的结构和状态管理
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time
import uuid

class UploadStatus(Enum):
    """上传状态枚举"""
    PENDING = "pending"         # 等待上传
    UPLOADING = "uploading"     # 正在上传
    COMPLETED = "completed"     # 上传完成
    FAILED = "failed"          # 上传失败
    CANCELLED = "cancelled"     # 已取消

class UploadType(Enum):
    """上传类型枚举"""
    PHOTO = "photo"            # 图片
    VIDEO = "video"            # 视频
    DOCUMENT = "document"      # 文档
    AUDIO = "audio"           # 音频
    VOICE = "voice"           # 语音
    VIDEO_NOTE = "video_note"  # 视频消息
    STICKER = "sticker"       # 贴纸

@dataclass
class UploadProgress:
    """上传进度信息"""
    uploaded_bytes: int = 0     # 已上传字节数
    total_bytes: int = 0        # 总字节数
    progress_percent: float = 0.0  # 进度百分比
    upload_speed: float = 0.0   # 上传速度 (bytes/s)
    estimated_time: float = 0.0 # 预计剩余时间 (seconds)
    
    def update_progress(self, uploaded: int, total: int, speed: float = 0.0):
        """更新进度信息"""
        self.uploaded_bytes = uploaded
        self.total_bytes = total
        self.progress_percent = (uploaded / total * 100) if total > 0 else 0.0
        self.upload_speed = speed
        
        if speed > 0 and total > uploaded:
            self.estimated_time = (total - uploaded) / speed
        else:
            self.estimated_time = 0.0

@dataclass
class UploadTask:
    """上传任务"""
    
    # 基础信息
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_message_id: int = 0
    target_channel: str = ""
    
    # 文件信息
    file_name: str = ""
    file_size: int = 0
    file_data: Optional[bytes] = None
    upload_type: UploadType = UploadType.DOCUMENT
    mime_type: Optional[str] = None
    
    # 内容信息
    caption: str = ""           # 上传时的说明文字
    formatted_content: str = "" # 模板处理后的内容
    
    # 状态信息
    status: UploadStatus = UploadStatus.PENDING
    progress: UploadProgress = field(default_factory=UploadProgress)
    
    # 结果信息
    uploaded_message_id: Optional[int] = None
    error_message: Optional[str] = None
    
    # 时间信息
    created_time: Optional[float] = None
    started_time: Optional[float] = None
    completed_time: Optional[float] = None
    
    # 重试信息
    retry_count: int = 0
    max_retries: int = 3
    
    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.upload_type, str):
            self.upload_type = UploadType(self.upload_type)
        
        if isinstance(self.status, str):
            self.status = UploadStatus(self.status)
        
        if self.created_time is None:
            self.created_time = time.time()
    
    def start_upload(self):
        """开始上传"""
        self.status = UploadStatus.UPLOADING
        self.started_time = time.time()
    
    def complete_upload(self, message_id: int):
        """完成上传"""
        self.status = UploadStatus.COMPLETED
        self.uploaded_message_id = message_id
        self.completed_time = time.time()
        self.progress.progress_percent = 100.0
    
    def fail_upload(self, error: str):
        """上传失败"""
        self.status = UploadStatus.FAILED
        self.error_message = error
        self.completed_time = time.time()
    
    def cancel_upload(self):
        """取消上传"""
        self.status = UploadStatus.CANCELLED
        self.completed_time = time.time()
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return (self.status == UploadStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        self.status = UploadStatus.PENDING
        self.error_message = None
    
    def get_duration(self) -> float:
        """获取上传耗时"""
        if self.started_time and self.completed_time:
            return self.completed_time - self.started_time
        elif self.started_time:
            return time.time() - self.started_time
        return 0.0
    
    def get_upload_speed_formatted(self) -> str:
        """获取格式化的上传速度"""
        speed = self.progress.upload_speed
        if speed == 0:
            return "0 B/s"
        
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024.0:
                return f"{speed:.1f} {unit}"
            speed /= 1024.0
        return f"{speed:.1f} TB/s"
    
    def get_file_size_formatted(self) -> str:
        """获取格式化的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_estimated_time_formatted(self) -> str:
        """获取格式化的预计剩余时间"""
        seconds = self.progress.estimated_time
        if seconds <= 0:
            return "未知"
        
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "source_message_id": self.source_message_id,
            "target_channel": self.target_channel,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_size_formatted": self.get_file_size_formatted(),
            "upload_type": self.upload_type.value,
            "mime_type": self.mime_type,
            "caption": self.caption,
            "formatted_content": self.formatted_content,
            "status": self.status.value,
            "progress": {
                "uploaded_bytes": self.progress.uploaded_bytes,
                "total_bytes": self.progress.total_bytes,
                "progress_percent": self.progress.progress_percent,
                "upload_speed": self.progress.upload_speed,
                "upload_speed_formatted": self.get_upload_speed_formatted(),
                "estimated_time": self.progress.estimated_time,
                "estimated_time_formatted": self.get_estimated_time_formatted()
            },
            "uploaded_message_id": self.uploaded_message_id,
            "error_message": self.error_message,
            "created_time": self.created_time,
            "started_time": self.started_time,
            "completed_time": self.completed_time,
            "duration": self.get_duration(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UploadTask':
        """从字典创建实例"""
        # 处理进度信息
        progress_data = data.pop("progress", {})
        progress = UploadProgress(
            uploaded_bytes=progress_data.get("uploaded_bytes", 0),
            total_bytes=progress_data.get("total_bytes", 0),
            progress_percent=progress_data.get("progress_percent", 0.0),
            upload_speed=progress_data.get("upload_speed", 0.0),
            estimated_time=progress_data.get("estimated_time", 0.0)
        )
        
        # 移除计算字段
        computed_fields = [
            "file_size_formatted", "upload_speed_formatted", 
            "estimated_time_formatted", "duration", "can_retry"
        ]
        for field in computed_fields:
            data.pop(field, None)
        
        # 创建实例
        task = cls(**data)
        task.progress = progress
        return task
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"UploadTask(任务ID={self.task_id[:8]}..., "
                f"文件={self.file_name}, "
                f"目标={self.target_channel}, "
                f"状态={self.status.value}, "
                f"进度={self.progress.progress_percent:.1f}%)")
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"UploadTask(task_id='{self.task_id}', "
                f"file_name='{self.file_name}', "
                f"target_channel='{self.target_channel}', "
                f"status='{self.status.value}', "
                f"progress={self.progress.progress_percent:.1f}%)")

@dataclass
class BatchUploadResult:
    """批量上传结果"""
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    tasks: List[UploadTask] = field(default_factory=list)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    def get_duration(self) -> float:
        """获取总耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0
    
    def is_completed(self) -> bool:
        """是否全部完成"""
        return (self.completed_tasks + self.failed_tasks + 
                self.cancelled_tasks) >= self.total_tasks
