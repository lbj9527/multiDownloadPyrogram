"""
文件信息数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum


class FileType(Enum):
    """文件类型枚举"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    OTHER = "other"


class CompressionType(Enum):
    """压缩类型枚举"""
    NONE = "none"
    ZIP = "zip"
    GZIP = "gzip"
    SEVENZ = "7z"


@dataclass
class MediaInfo:
    """媒体文件信息"""
    message_id: int
    media_type: str  # photo, video, audio, etc.
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[int] = None  # 音视频时长（秒）
    width: Optional[int] = None     # 图片/视频宽度
    height: Optional[int] = None    # 图片/视频高度
    media_group_id: Optional[str] = None  # 媒体组ID
    
    @property
    def file_size_mb(self) -> float:
        """文件大小（MB）"""
        return (self.file_size / (1024 * 1024)) if self.file_size else 0.0
    
    @property
    def is_media_group(self) -> bool:
        """是否为媒体组"""
        return self.media_group_id is not None


@dataclass
class CompressionInfo:
    """压缩信息"""
    compression_type: CompressionType = CompressionType.NONE
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    compression_time: float = 0.0  # 压缩耗时（秒）
    
    @property
    def space_saved(self) -> int:
        """节省的空间（字节）"""
        return max(0, self.original_size - self.compressed_size)
    
    @property
    def space_saved_mb(self) -> float:
        """节省的空间（MB）"""
        return self.space_saved / (1024 * 1024)
    
    @property
    def compression_percentage(self) -> float:
        """压缩百分比"""
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100


@dataclass
class FileInfo:
    """文件信息模型"""
    file_path: Path
    original_name: str
    file_type: FileType
    created_at: datetime = field(default_factory=datetime.now)
    
    # 文件基本信息
    file_size: int = 0
    file_hash: Optional[str] = None  # MD5哈希
    
    # 媒体信息
    media_info: Optional[MediaInfo] = None
    
    # 压缩信息
    compression_info: Optional[CompressionInfo] = None
    
    # 下载信息
    download_time: Optional[datetime] = None
    download_duration: float = 0.0  # 下载耗时（秒）
    download_speed: float = 0.0     # 下载速度（MB/s）
    
    # 状态信息
    is_downloaded: bool = False
    is_compressed: bool = False
    is_duplicate: bool = False
    
    @property
    def file_size_mb(self) -> float:
        """文件大小（MB）"""
        return self.file_size / (1024 * 1024)
    
    @property
    def file_extension(self) -> str:
        """文件扩展名"""
        return self.file_path.suffix.lower()
    
    @property
    def relative_path(self) -> str:
        """相对路径"""
        return str(self.file_path)
    
    def mark_downloaded(self, download_duration: float = 0.0):
        """标记为已下载"""
        self.is_downloaded = True
        self.download_time = datetime.now()
        self.download_duration = download_duration
        
        # 计算下载速度
        if download_duration > 0 and self.file_size > 0:
            self.download_speed = self.file_size_mb / download_duration
    
    def mark_compressed(self, compression_info: CompressionInfo):
        """标记为已压缩"""
        self.is_compressed = True
        self.compression_info = compression_info
    
    def mark_duplicate(self, original_file_hash: str):
        """标记为重复文件"""
        self.is_duplicate = True
        self.file_hash = original_file_hash
    
    def calculate_hash(self) -> str:
        """计算文件哈希值"""
        import hashlib
        
        if not self.file_path.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        self.file_hash = hash_md5.hexdigest()
        return self.file_hash
    
    def get_file_type_from_extension(self) -> FileType:
        """根据扩展名确定文件类型"""
        from config.constants import FILE_TYPE_CATEGORIES
        
        ext = self.file_extension
        
        for category, extensions in FILE_TYPE_CATEGORIES.items():
            if ext in extensions:
                return FileType(category.rstrip('s'))  # images -> image
        
        return FileType.OTHER
    
    def should_compress(self, threshold_mb: int = 50) -> bool:
        """判断是否应该压缩"""
        # 已经压缩过的不再压缩
        if self.is_compressed:
            return False
        
        # 根据文件类型和大小决定
        if self.file_type in [FileType.DOCUMENT, FileType.ARCHIVE]:
            return True
        
        if self.file_size_mb > threshold_mb:
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'file_path': str(self.file_path),
            'original_name': self.original_name,
            'file_type': self.file_type.value,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'file_hash': self.file_hash,
            'is_downloaded': self.is_downloaded,
            'is_compressed': self.is_compressed,
            'is_duplicate': self.is_duplicate,
            'download_time': self.download_time.isoformat() if self.download_time else None,
            'download_duration': self.download_duration,
            'download_speed': self.download_speed,
            'created_at': self.created_at.isoformat(),
            'media_info': self.media_info.__dict__ if self.media_info else None,
            'compression_info': self.compression_info.__dict__ if self.compression_info else None
        }
