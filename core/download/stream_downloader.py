"""
流式下载器
使用stream_media方法进行下载
"""
from pathlib import Path
from typing import Optional, Any
from pyrogram.client import Client
from .base import BaseDownloader
from models.download_result import DownloadResult
from utils.message_utils import MessageUtils

class StreamDownloader(BaseDownloader):
    """流式下载器 - 使用stream_media方法"""
    
    async def download(self, client: Client, message: Any, folder_name: str) -> Optional[Path]:
        """本地下载方法（保持向后兼容）"""
        return await self._download_to_file(client, message, folder_name)

    async def download_to_memory(self, client: Client, message: Any) -> Optional[DownloadResult]:
        """内存下载方法"""
        return await self._download_to_memory(client, message)

    async def _download_to_file(self, client: Client, message: Any, folder_name: str) -> Optional[Path]:
        """
        使用stream_media方法下载媒体文件到本地
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

    async def _download_to_memory(self, client: Client, message: Any) -> Optional[DownloadResult]:
        """
        使用stream_media方法下载媒体文件到内存
        """
        try:
            # 验证消息
            if not self.validate_message(message):
                self.log_error(f"消息 {message.id} 无有效媒体")
                return None

            # 获取文件信息
            file_info = MessageUtils.get_file_info(message)
            file_name = file_info['file_name']
            file_size = file_info['file_size']
            mime_type = file_info.get('mime_type')

            # 记录下载开始
            self.log_info(f"开始Stream内存下载消息 {message.id}: {file_name}")

            # 使用stream_media进行流式下载到内存
            file_data = bytearray()
            downloaded_bytes = 0

            async for chunk in client.stream_media(message):
                file_data.extend(chunk)
                downloaded_bytes += len(chunk)

                # 显示下载进度（每10MB显示一次）
                if downloaded_bytes % (10 * 1024 * 1024) == 0:
                    progress_mb = downloaded_bytes / (1024 * 1024)
                    self.log_info(f"消息 {message.id} 已下载到内存: {progress_mb:.1f} MB")

            # 转换为bytes
            file_bytes = bytes(file_data)
            actual_size = len(file_bytes)

            # 验证下载完整性
            if file_size > 0 and actual_size != file_size:
                self.log_warning(
                    f"消息 {message.id} 文件大小不匹配: "
                    f"期望 {file_size}, 实际 {actual_size}"
                )

            # 创建下载结果
            result = MessageUtils.create_memory_download_result(message, file_bytes, client.name, file_info)

            # 记录下载成功
            self.log_info(f"Stream内存下载完成: {file_name} ({result.get_size_formatted()})")
            return result

        except Exception as e:
            self.log_error(f"Stream内存下载消息 {message.id} 失败: {e}")
            return None


