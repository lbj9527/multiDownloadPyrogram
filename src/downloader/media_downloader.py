"""
媒体下载器模块
支持单文件下载、大文件分片下载、媒体组下载等功能
"""

import os
import asyncio
import time
from typing import Optional, List, Callable, Any, Union
from pathlib import Path
from pyrogram import Client
from pyrogram.types import Message

from ..utils.config import AppConfig, get_config
from ..utils.logger import get_logger, get_download_logger
from ..utils.exceptions import (
    DownloadError, FileNotFoundError, FileSizeError, MediaGroupError,
    handle_pyrogram_exception, is_retryable_error, get_retry_delay,
    FileError, NetworkError, RateLimitError
)


class ProgressTracker:
    """
    下载进度跟踪器（修复版）
    """
    
    def __init__(self, filename: str, total_size: int, update_interval: float = 1.0):
        self.filename = filename
        self.total_size = total_size
        self.update_interval = update_interval
        self.last_update_time = 0
        self.start_time = time.time()
        self.logger = get_logger()
    
    def __call__(self, current: int, total: int) -> None:
        """
        进度回调函数（同步版本）
        注意：这里不使用async，避免协程未await的问题
        """
        now = time.time()
        if now - self.last_update_time >= self.update_interval:
            percentage = (current / total) * 100 if total > 0 else 0
            elapsed = now - self.start_time
            speed = current / elapsed if elapsed > 0 else 0
            
            # 格式化显示
            size_mb = total / (1024 * 1024)
            current_mb = current / (1024 * 1024)
            speed_mbps = speed / (1024 * 1024)
            
            self.logger.info(
                f"下载进度 {self.filename}: {percentage:.1f}% "
                f"({current_mb:.1f}MB/{size_mb:.1f}MB) "
                f"速度: {speed_mbps:.1f}MB/s"
            )
            
            self.last_update_time = now


class MediaDownloader:
    """媒体文件下载器"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger()
        self.download_logger = get_download_logger()
        
        # 添加并发控制信号量
        self._download_semaphore = asyncio.Semaphore(self.config.download.max_concurrent_downloads)
        self.logger.info(f"初始化下载器，最大并发下载数: {self.config.download.max_concurrent_downloads}")
    
    async def download_media(
        self,
        client: Client,
        message: Message,
        custom_filename: Optional[str] = None,
        custom_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        下载单个媒体文件（带并发控制）
        
        Args:
            client: Pyrogram客户端
            message: 包含媒体的消息
            custom_filename: 自定义文件名
            custom_dir: 自定义下载目录
            
        Returns:
            Optional[str]: 下载的文件路径，失败返回None
            
        Raises:
            DownloadError: 下载失败
        """
        # 使用信号量控制并发下载数量
        async with self._download_semaphore:
            return await self._download_media_internal(client, message, custom_filename, custom_dir)
    
    async def _download_media_internal(
        self,
        client: Client,
        message: Message,
        custom_filename: Optional[str] = None,
        custom_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        内部下载实现（不带并发控制）
        """
        if not self._has_media(message):
            raise DownloadError("消息不包含媒体文件", message_id=message.id)
        
        try:
            # 获取文件信息
            file_info = self._get_file_info(message)
            filename = custom_filename or file_info['filename']
            download_dir = custom_dir or self.config.download.download_dir
            
            # 确保下载目录存在
            os.makedirs(download_dir, exist_ok=True)
            file_path = os.path.join(download_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                self.logger.warning(f"文件已存在，跳过下载: {filename}")
                return file_path
            
            # 记录开始下载
            self.download_logger.log_file_start(filename, file_info['size'])
            start_time = time.time()
            
            # 选择下载方式
            if file_info['size'] > self.config.download.large_file_threshold:
                # 大文件使用流式下载
                self.logger.info(f"使用流式下载大文件: {filename} ({file_info['size']} bytes)")
                downloaded_path = await self._download_large_file(
                    client, message, file_path, file_info
                )
            else:
                # 小文件使用标准下载
                downloaded_path = await self._download_standard_file(
                    client, message, file_path, file_info
                )
            
            # 验证下载结果
            if downloaded_path and os.path.exists(downloaded_path):
                actual_size = os.path.getsize(downloaded_path)
                if actual_size != file_info['size']:
                    self.logger.warning(f"文件大小不匹配: 期望 {file_info['size']}, 实际 {actual_size}")
                
                # 记录下载完成
                duration = time.time() - start_time
                speed = actual_size / duration if duration > 0 else 0
                
                self.download_logger.log_file_success(filename, actual_size, duration)
                self.logger.info(
                    f"下载完成: {filename} ({actual_size/(1024*1024):.1f}MB, {duration:.1f}s, {speed/(1024*1024):.1f}MB/s)"
                )
                
                return downloaded_path
            else:
                raise DownloadError(f"下载失败，文件不存在: {file_path}")
                
        except Exception as e:
            self.download_logger.log_file_error(filename if 'filename' in locals() else "unknown", str(e))
            if isinstance(e, DownloadError):
                raise
            else:
                raise DownloadError(f"下载媒体文件失败: {str(e)}", message_id=message.id)
    
    async def _download_standard_file(
        self,
        client: Client,
        message: Message,
        file_path: str,
        file_info: dict
    ) -> str:
        """
        标准下载方式
        """
        temp_file_path = file_path + '.temp'
        
        try:
            # 创建进度跟踪器
            progress = ProgressTracker(
                file_info['filename'],
                file_info['size'],
                self.config.download.progress_update_interval
            )
            
            self.logger.info(f"开始下载文件: {file_info['filename']} ({file_info['size']/(1024*1024):.1f}MB)")
            
            # 下载到临时文件
            await client.download_media(
                message,
                file_name=temp_file_path,
                progress=progress
            )
            
            # 移动到最终位置
            if os.path.exists(temp_file_path):
                os.rename(temp_file_path, file_path)
                return file_path
            else:
                raise DownloadError(f"临时文件不存在: {temp_file_path}")
                
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            raise
    
    async def _download_large_file(
        self,
        client: Client,
        message: Message,
        file_path: str,
        file_info: dict
    ) -> str:
        """
        大文件流式下载
        """
        temp_file_path = file_path + '.temp'
        
        try:
            # 创建进度跟踪器
            progress = ProgressTracker(
                file_info['filename'],
                file_info['size'],
                self.config.download.progress_update_interval
            )
            
            downloaded_size = 0
            
            with open(temp_file_path, 'wb') as f:
                async for chunk in client.stream_media(message, limit=self.config.download.chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 更新进度
                    progress(downloaded_size, file_info['size'])
                    
                    # 定期刷新缓冲区
                    if downloaded_size % (self.config.download.chunk_size * 10) == 0:
                        f.flush()
            
            # 移动到最终位置
            if os.path.exists(temp_file_path):
                os.rename(temp_file_path, file_path)
                return file_path
            else:
                raise DownloadError(f"临时文件不存在: {temp_file_path}")
                
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            raise
    
    def _has_media(self, message: Message) -> bool:
        """检查消息是否包含媒体"""
        return bool(
            message.photo or
            message.video or
            message.audio or
            message.voice or
            message.video_note or
            message.sticker or
            message.animation or
            message.document
        )
    
    def _get_file_info(self, message: Message) -> dict:
        """获取文件信息"""
        if message.photo:
            # 获取最大尺寸的图片 - 修复API兼容性
            # 新版Pyrogram使用thumbs而不是sizes
            if hasattr(message.photo, 'thumbs') and message.photo.thumbs:
                photo = max(message.photo.thumbs, key=lambda x: x.width * x.height)
                return {
                    'filename': f"photo_{message.id}_{photo.width}x{photo.height}.jpg",
                    'size': photo.file_size or 0,
                    'mime_type': 'image/jpeg'
                }
            elif hasattr(message.photo, 'sizes') and message.photo.sizes:
                # 兼容旧版API
                photo = max(message.photo.sizes, key=lambda x: x.width * x.height)
                return {
                    'filename': f"photo_{message.id}_{photo.width}x{photo.height}.jpg",
                    'size': photo.file_size or 0,
                    'mime_type': 'image/jpeg'
                }
            else:
                # 如果没有thumbs或sizes，使用基本信息
                return {
                    'filename': f"photo_{message.id}.jpg",
                    'size': getattr(message.photo, 'file_size', 0),
                    'mime_type': 'image/jpeg'
                }
        elif message.video:
            return {
                'filename': getattr(message.video, 'file_name', None) or f"video_{message.id}.mp4",
                'size': message.video.file_size or 0,
                'mime_type': message.video.mime_type or 'video/mp4'
            }
        elif message.document:
            return {
                'filename': getattr(message.document, 'file_name', None) or f"document_{message.id}",
                'size': message.document.file_size or 0,
                'mime_type': message.document.mime_type or 'application/octet-stream'
            }
        elif message.audio:
            return {
                'filename': getattr(message.audio, 'file_name', None) or f"audio_{message.id}.mp3",
                'size': message.audio.file_size or 0,
                'mime_type': message.audio.mime_type or 'audio/mpeg'
            }
        elif message.voice:
            return {
                'filename': f"voice_{message.id}.ogg",
                'size': message.voice.file_size or 0,
                'mime_type': message.voice.mime_type or 'audio/ogg'
            }
        elif message.video_note:
            return {
                'filename': f"video_note_{message.id}.mp4",
                'size': message.video_note.file_size or 0,
                'mime_type': 'video/mp4'
            }
        elif message.sticker:
            ext = '.webp' if message.sticker.is_animated else '.webp'
            return {
                'filename': f"sticker_{message.id}{ext}",
                'size': message.sticker.file_size or 0,
                'mime_type': 'image/webp'
            }
        elif message.animation:
            return {
                'filename': getattr(message.animation, 'file_name', None) or f"animation_{message.id}.gif",
                'size': message.animation.file_size or 0,
                'mime_type': message.animation.mime_type or 'image/gif'
            }
        else:
            raise DownloadError("未知的媒体类型", message_id=message.id)
    
    async def download_media_group(
        self,
        client: Client,
        message: Message,
        custom_dir: Optional[str] = None
    ) -> List[str]:
        """
        下载媒体组中的所有文件（带并发控制）
        
        Args:
            client: Pyrogram客户端
            message: 媒体组中的任一消息
            custom_dir: 自定义下载目录
            
        Returns:
            List[str]: 下载的文件路径列表
            
        Raises:
            MediaGroupError: 媒体组下载失败
        """
        if not message.media_group_id:
            raise MediaGroupError("消息不属于媒体组", message_id=message.id)
        
        try:
            # 获取媒体组中的所有消息
            media_group = await client.get_media_group(
                message.chat.id,
                message.id
            )
            
            if not media_group:
                raise MediaGroupError("无法获取媒体组消息", message.media_group_id, message.id)
            
            self.logger.info(f"开始下载媒体组 {message.media_group_id}，包含 {len(media_group)} 个文件")
            
            # 创建媒体组专用目录
            group_dir = custom_dir or os.path.join(
                self.config.download.download_dir,
                f"media_group_{message.media_group_id}"
            )
            os.makedirs(group_dir, exist_ok=True)
            
            # 并发下载所有文件（每个文件都会受到信号量控制）
            download_tasks = []
            for i, media_message in enumerate(media_group):
                if self._has_media(media_message):
                    # 为媒体组文件添加序号前缀
                    file_info = self._get_file_info(media_message)
                    filename = f"{i+1:02d}_{file_info['filename']}"
                    
                    # 注意：这里调用download_media会自动应用并发控制
                    task = self.download_media(
                        client,
                        media_message,
                        custom_filename=filename,
                        custom_dir=group_dir
                    )
                    download_tasks.append(task)
            
            # 等待所有下载完成
            results = await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # 处理结果
            downloaded_files = []
            failed_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"媒体组文件下载失败: {str(result)}")
                    failed_count += 1
                elif result:
                    downloaded_files.append(result)
            
            success_count = len(downloaded_files)
            total_count = len(download_tasks)
            
            self.logger.info(
                f"媒体组 {message.media_group_id} 下载完成: "
                f"成功 {success_count}/{total_count}, 失败 {failed_count}"
            )
            
            if failed_count > 0 and success_count == 0:
                raise MediaGroupError(
                    f"媒体组下载完全失败",
                    message.media_group_id,
                    message.id
                )
            
            return downloaded_files
            
        except MediaGroupError:
            raise
        except Exception as e:
            error_msg = f"媒体组下载失败: {str(e)}"
            self.logger.error(error_msg)
            raise MediaGroupError(error_msg, message.media_group_id, message.id)
    
    async def download_with_retry(
        self,
        client: Client,
        message: Message,
        max_retries: int = 3,
        custom_filename: Optional[str] = None,
        custom_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        带重试机制的媒体下载
        
        Args:
            client: Pyrogram客户端
            message: 包含媒体的消息
            max_retries: 最大重试次数
            custom_filename: 自定义文件名
            custom_dir: 自定义下载目录
            
        Returns:
            Optional[str]: 下载的文件路径，失败返回None
        """
        for attempt in range(max_retries + 1):
            try:
                result = await self.download_media(client, message, custom_filename, custom_dir)
                if result:
                    return result
                    
            except RateLimitError as e:
                if attempt < max_retries:
                    self.logger.warning(f"下载限流，等待 {e.wait_time} 秒后重试...")
                    await asyncio.sleep(e.wait_time)
                    continue
                else:
                    self.logger.error(f"下载限流，重试 {max_retries} 次后仍然失败")
                    return None
                    
            except (NetworkError, FileError) as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.warning(f"下载失败，{wait_time} 秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"下载失败，重试 {max_retries} 次后仍然失败: {str(e)}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"下载出现未知错误: {str(e)}")
                return None
        
        return None
    
    def get_download_stats(self) -> dict:
        """获取下载统计信息"""
        stats = self.download_logger.download_stats.copy()
        stats['max_concurrent_downloads'] = self.config.download.max_concurrent_downloads
        stats['available_download_slots'] = self._download_semaphore._value
        return stats 