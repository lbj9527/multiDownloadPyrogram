"""
下载结果数据模型
支持本地文件和内存数据两种模式
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import time

@dataclass
class DownloadResult:
    """下载结果数据模型"""
    
    # 基础信息
    message_id: int
    file_name: str
    file_size: int
    download_mode: str  # "local" 或 "memory"
    
    # 文件数据 (二选一)
    file_path: Optional[str] = None      # 本地文件路径
    file_data: Optional[bytes] = None    # 内存数据
    
    # 元数据
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None
    download_time: Optional[float] = None
    client_name: Optional[str] = None
    
    # 原始消息信息
    original_caption: Optional[str] = None
    original_text: Optional[str] = None
    media_group_id: Optional[str] = None
    
    # 额外属性
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 验证下载模式
        if self.download_mode not in ["local", "memory"]:
            raise ValueError("download_mode must be 'local' or 'memory'")

        # 验证数据完整性 (仅在创建新实例时验证，反序列化时可能缺少数据)
        if self.download_mode == "local" and not self.file_path:
            raise ValueError("Local download mode requires file_path")

        # 对于内存模式，如果没有 file_data，可能是从序列化数据恢复的
        # 这种情况下不强制要求 file_data（通过检查调用栈判断）
        import inspect
        is_from_serialization = any('from_dict' in frame.function for frame in inspect.stack())

        if (self.download_mode == "memory" and not self.file_data and
            not is_from_serialization):
            raise ValueError("Memory download mode requires file_data")

        # 设置下载时间
        if self.download_time is None:
            self.download_time = time.time()

        # 计算文件哈希
        if not self.file_hash:
            self.file_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> Optional[str]:
        """计算文件哈希值"""
        try:
            if self.download_mode == "memory" and self.file_data:
                return hashlib.md5(self.file_data).hexdigest()
            elif self.download_mode == "local" and self.file_path:
                path = Path(self.file_path)
                if path.exists():
                    with open(path, 'rb') as f:
                        return hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass
        return None
    
    def get_data(self) -> Optional[bytes]:
        """获取文件数据"""
        if self.download_mode == "memory":
            return self.file_data
        elif self.download_mode == "local" and self.file_path:
            try:
                with open(self.file_path, 'rb') as f:
                    return f.read()
            except Exception:
                return None
        return None
    
    def get_size_mb(self) -> float:
        """获取文件大小(MB)"""
        return self.file_size / (1024 * 1024)
    
    def get_size_formatted(self) -> str:
        """获取格式化的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def is_valid(self) -> bool:
        """检查下载结果是否有效"""
        if self.download_mode == "local":
            return self.file_path and Path(self.file_path).exists()
        elif self.download_mode == "memory":
            return self.file_data is not None and len(self.file_data) > 0
        return False
    
    def get_content_text(self) -> str:
        """获取消息文本内容"""
        if self.original_text:
            return self.original_text
        elif self.original_caption:
            return self.original_caption
        return ""
    
    def has_media_group(self) -> bool:
        """是否属于媒体组"""
        return self.media_group_id is not None
    
    def to_dict(self, include_file_data: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式(用于API)

        Args:
            include_file_data: 是否包含文件数据 (默认不包含，避免序列化问题)
        """
        result = {
            "message_id": self.message_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_size_formatted": self.get_size_formatted(),
            "download_mode": self.download_mode,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "file_hash": self.file_hash,
            "download_time": self.download_time,
            "client_name": self.client_name,
            "original_caption": self.original_caption,
            "original_text": self.original_text,
            "content_text": self.get_content_text(),
            "media_group_id": self.media_group_id,
            "has_media_group": self.has_media_group(),
            "metadata": self.metadata,
            "size_mb": self.get_size_mb(),
            "is_valid": self.is_valid()
        }

        # 只在明确要求时包含文件数据
        if include_file_data and self.file_data:
            result["file_data"] = self.file_data

        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadResult':
        """从字典创建实例"""
        # 复制数据避免修改原始字典
        data_copy = data.copy()

        # 移除计算字段
        computed_fields = [
            "size_mb", "is_valid", "file_size_formatted",
            "content_text", "has_media_group"
        ]
        for field in computed_fields:
            data_copy.pop(field, None)

        # 直接创建实例，__post_init__ 会通过调用栈检测是否来自序列化
        return cls(**data_copy)
    
    @classmethod
    def create_local_result(cls, message_id: int, file_path: str, 
                          file_name: str, file_size: int, 
                          client_name: str = None, **kwargs) -> 'DownloadResult':
        """创建本地下载结果"""
        return cls(
            message_id=message_id,
            file_name=file_name,
            file_size=file_size,
            download_mode="local",
            file_path=file_path,
            client_name=client_name,
            **kwargs
        )
    
    @classmethod
    def create_memory_result(cls, message_id: int, file_data: bytes,
                           file_name: str, client_name: str = None, 
                           **kwargs) -> 'DownloadResult':
        """创建内存下载结果"""
        return cls(
            message_id=message_id,
            file_name=file_name,
            file_size=len(file_data),
            download_mode="memory",
            file_data=file_data,
            client_name=client_name,
            **kwargs
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        mode_str = "本地" if self.download_mode == "local" else "内存"
        return (f"DownloadResult(消息ID={self.message_id}, "
                f"文件={self.file_name}, "
                f"大小={self.get_size_formatted()}, "
                f"模式={mode_str})")
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"DownloadResult(message_id={self.message_id}, "
                f"file_name='{self.file_name}', "
                f"file_size={self.file_size}, "
                f"download_mode='{self.download_mode}', "
                f"is_valid={self.is_valid()})")
