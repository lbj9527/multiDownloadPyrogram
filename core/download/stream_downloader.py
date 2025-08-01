"""
流式下载器
从test_downloader_stream.py提取的stream_media下载逻辑
"""
from pathlib import Path
from typing import Optional, Any
from pyrogram.client import Client
from .base import BaseDownloader

class StreamDownloader(BaseDownloader):
    """流式下载器 - 使用stream_media方法"""
    
    async def download(self, client: Client, message: Any, folder_name: str) -> Optional[Path]:
        """
        使用stream_media方法下载媒体文件
        从test_downloader_stream.py提取的逻辑
        """
        try:
            # 验证消息
            if not self.validate_message(message):
                self.log_error(f"消息 {message.id} 无有效媒体")
                return None
            
            # 生成文件路径
            file_path = self.generate_file_path(message, folder_name)
            
            # 获取文件大小信息
            size_info = self.get_file_size_info(message)
            expected_size = size_info["size_bytes"]
            
            # 记录下载开始
            self.log_download_start(message, file_path, "Stream")
            
            # 使用stream_media进行流式下载
            downloaded_bytes = 0
            with open(file_path, 'wb') as f:
                async for chunk in client.stream_media(message):
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    
                    # 显示下载进度（每10MB显示一次）
                    if downloaded_bytes % (10 * 1024 * 1024) == 0:
                        progress_mb = downloaded_bytes / (1024 * 1024)
                        self.log_info(f"消息 {message.id} 已下载: {progress_mb:.1f} MB")
            
            # 验证下载完整性
            actual_size = file_path.stat().st_size
            if not self.verify_download(file_path, expected_size):
                self.log_warning(
                    f"消息 {message.id} 文件大小不匹配: "
                    f"期望 {expected_size}, 实际 {actual_size}"
                )
            
            # 记录下载成功
            self.log_download_success(file_path, actual_size)
            return file_path
            
        except Exception as e:
            self.log_download_error(message, e, "Stream")
            # 清理失败的文件
            if 'file_path' in locals() and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            return None
