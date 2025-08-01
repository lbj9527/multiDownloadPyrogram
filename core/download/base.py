"""
下载器基类
定义下载器的通用接口和功能
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any
from pyrogram.client import Client
from utils.logging_utils import LoggerMixin
from utils.file_utils import FileUtils

class BaseDownloader(LoggerMixin, ABC):
    """下载器基类"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    async def download(self, client: Client, message: Any) -> Optional[Path]:
        """
        下载媒体文件
        
        Args:
            client: Pyrogram客户端
            message: 消息对象
            
        Returns:
            下载文件的路径，失败返回None
        """
        pass
    
    def get_channel_directory(self, folder_name: str) -> Path:
        """获取频道下载目录"""
        return FileUtils.get_channel_directory(self.download_dir, folder_name)

    def generate_file_path(self, message: Any, folder_name: str) -> Path:
        """生成文件保存路径"""
        channel_dir = self.get_channel_directory(folder_name)
        filename = FileUtils.generate_filename_by_type(message)
        return channel_dir / filename
    
    def get_file_size_info(self, message: Any) -> dict:
        """获取文件大小信息"""
        return {
            "size_bytes": FileUtils.get_file_size_bytes(message),
            "size_mb": FileUtils.get_file_size_mb(message),
            "is_video": FileUtils.is_video_file(message),
            "is_image": FileUtils.is_image_file(message)
        }
    
    def validate_message(self, message: Any) -> bool:
        """验证消息是否有效 - 与原程序保持一致，只判断empty属性"""
        if not message:
            return False

        # 只判断empty属性，不判断是否有媒体文件（与原程序一致）
        return not getattr(message, 'empty', True)
    
    def log_download_start(self, message: Any, file_path: Path, method: str):
        """记录下载开始"""
        size_info = self.get_file_size_info(message)
        self.log_info(
            f"{method}下载消息 {message.id} "
            f"(大小: {size_info['size_mb']:.2f} MB) -> {file_path.name}"
        )
    
    def log_download_success(self, file_path: Path, actual_size: int):
        """记录下载成功"""
        actual_mb = actual_size / (1024 * 1024)
        self.log_info(f"✅ 下载完成: {file_path.name} ({actual_mb:.2f} MB)")
    
    def log_download_error(self, message: Any, error: Exception, method: str):
        """记录下载错误"""
        self.log_error(f"❌ {method}下载消息 {message.id} 失败: {error}")
    
    def verify_download(self, file_path: Path, expected_size: int) -> bool:
        """验证下载文件的完整性"""
        if not file_path.exists():
            return False
        
        actual_size = file_path.stat().st_size
        
        # 如果期望大小为0或未知，只检查文件是否存在且不为空
        if expected_size <= 0:
            return actual_size > 0
        
        # 检查大小是否匹配（允许小幅差异）
        size_diff = abs(actual_size - expected_size)
        tolerance = max(1024, expected_size * 0.01)  # 1KB或1%的容差
        
        if size_diff > tolerance:
            self.log_warning(
                f"文件大小不匹配: 期望 {expected_size}, 实际 {actual_size}, "
                f"差异 {size_diff} 字节"
            )
            return False
        
        return True
