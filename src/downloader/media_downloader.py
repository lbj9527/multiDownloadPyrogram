"""
媒体下载器模块

实现基础的媒体文件下载功能，支持多种媒体类型和下载策略
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Union
from dataclasses import dataclass
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, FileReferenceExpired

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import DownloadError, DownloadTimeoutError, handle_pyrogram_exception
from client.client_manager import ClientManager


@dataclass
class DownloadProgress:
    """下载进度信息"""
    current: int = 0
    total: int = 0
    speed: float = 0.0
    eta: float = 0.0
    percentage: float = 0.0
    start_time: float = 0.0
    file_name: str = ""
    
    def update(self, current: int, total: int):
        """更新进度"""
        self.current = current
        self.total = total
        self.percentage = (current / total) * 100 if total > 0 else 0
        
        # 计算速度和ETA
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.speed = current / elapsed_time
            if self.speed > 0:
                self.eta = (total - current) / self.speed
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current": self.current,
            "total": self.total,
            "speed": self.speed,
            "eta": self.eta,
            "percentage": self.percentage,
            "file_name": self.file_name
        }


class MediaDownloader:
    """媒体下载器"""
    
    def __init__(self, config: Config, client_manager: Optional[ClientManager] = None):
        """
        初始化媒体下载器
        
        Args:
            config: 配置对象
            client_manager: 客户端管理器
        """
        self.config = config
        self.client_manager = client_manager
        self.logger = get_logger(f"{__name__}.MediaDownloader")
        
        # 下载配置
        self.download_path = Path(config.download.download_path)
        self.chunk_size = config.download.chunk_size
        self.timeout = config.download.timeout
        self.max_retries = config.download.retry_count
        self.skip_existing = config.download.skip_existing
        self.large_file_threshold = config.download.large_file_threshold
        
        # 创建下载目录
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        self.download_complete_callback: Optional[Callable] = None
        
        # 统计信息
        self.downloads_completed = 0
        self.downloads_failed = 0
        self.bytes_downloaded = 0
    
    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_download_complete_callback(self, callback: Callable[[str, bool], None]):
        """设置下载完成回调函数"""
        self.download_complete_callback = callback
    
    def _get_file_info(self, message: Message) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            message: 消息对象
            
        Returns:
            文件信息字典
        """
        file_info = {
            "file_name": None,
            "file_size": 0,
            "file_type": None,
            "media_type": None
        }
        
        if message.photo:
            file_info["media_type"] = "photo"
            file_info["file_type"] = "jpg"
            file_info["file_size"] = message.photo.file_size
            file_info["file_name"] = f"photo_{message.id}.jpg"
            
        elif message.video:
            file_info["media_type"] = "video"
            file_info["file_type"] = "mp4"
            file_info["file_size"] = message.video.file_size
            file_info["file_name"] = message.video.file_name or f"video_{message.id}.mp4"
            
        elif message.document:
            file_info["media_type"] = "document"
            file_info["file_size"] = message.document.file_size
            file_info["file_name"] = message.document.file_name or f"document_{message.id}"
            
            # 从文件名获取扩展名
            if file_info["file_name"]:
                file_info["file_type"] = Path(file_info["file_name"]).suffix.lower()
            
        elif message.audio:
            file_info["media_type"] = "audio"
            file_info["file_type"] = "mp3"
            file_info["file_size"] = message.audio.file_size
            file_info["file_name"] = message.audio.file_name or f"audio_{message.id}.mp3"
            
        elif message.voice:
            file_info["media_type"] = "voice"
            file_info["file_type"] = "oga"
            file_info["file_size"] = message.voice.file_size
            file_info["file_name"] = f"voice_{message.id}.oga"
            
        elif message.video_note:
            file_info["media_type"] = "video_note"
            file_info["file_type"] = "mp4"
            file_info["file_size"] = message.video_note.file_size
            file_info["file_name"] = f"video_note_{message.id}.mp4"
            
        elif message.animation:
            file_info["media_type"] = "animation"
            file_info["file_type"] = "gif"
            file_info["file_size"] = message.animation.file_size
            file_info["file_name"] = message.animation.file_name or f"animation_{message.id}.gif"
            
        elif message.sticker:
            file_info["media_type"] = "sticker"
            file_info["file_type"] = "webp"
            file_info["file_size"] = message.sticker.file_size
            file_info["file_name"] = f"sticker_{message.id}.webp"
        
        return file_info
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 移除非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制文件名长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        
        return filename
    
    def _get_download_path(self, file_info: Dict[str, Any], chat_title: Optional[str] = None) -> Path:
        """
        获取下载路径
        
        Args:
            file_info: 文件信息
            chat_title: 聊天标题
            
        Returns:
            下载路径
        """
        # 创建子目录
        if chat_title:
            sub_dir = self.download_path / self._sanitize_filename(chat_title)
        else:
            sub_dir = self.download_path / file_info["media_type"]
        
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件路径
        filename = self._sanitize_filename(file_info["file_name"])
        file_path = sub_dir / filename
        
        # 处理文件名冲突
        counter = 1
        original_path = file_path
        while file_path.exists():
            if self.skip_existing:
                self.logger.info(f"文件已存在，跳过: {file_path}")
                return file_path
            
            # 生成新文件名
            name = original_path.stem
            ext = original_path.suffix
            file_path = original_path.parent / f"{name}_{counter}{ext}"
            counter += 1
        
        return file_path
    
    async def _progress_callback_wrapper(self, current: int, total: int, progress: DownloadProgress):
        """进度回调包装器"""
        progress.update(current, total)
        
        if self.progress_callback:
            try:
                await self.progress_callback(progress)
            except Exception as e:
                self.logger.error(f"进度回调错误: {e}")
    
    async def download_media(self, message: Message, 
                            custom_path: Optional[Union[str, Path]] = None,
                            chat_title: Optional[str] = None) -> Optional[str]:
        """
        下载媒体文件
        
        Args:
            message: 消息对象
            custom_path: 自定义下载路径
            chat_title: 聊天标题
            
        Returns:
            下载的文件路径，如果失败则返回None
        """
        if not message.media:
            self.logger.warning("消息不包含媒体文件")
            return None
        
        # 获取文件信息
        file_info = self._get_file_info(message)
        if not file_info["file_name"]:
            self.logger.warning("无法获取文件信息")
            return None
        
        # 确定下载路径
        if custom_path:
            file_path = Path(custom_path)
            if file_path.is_dir():
                file_path = file_path / file_info["file_name"]
        else:
            file_path = self._get_download_path(file_info, chat_title)
        
        # 检查是否已存在
        if file_path.exists() and self.skip_existing:
            self.logger.info(f"文件已存在，跳过: {file_path}")
            return str(file_path)
        
        # 创建进度对象
        progress = DownloadProgress(
            file_name=file_info["file_name"],
            start_time=time.time()
        )
        
        self.logger.info(f"开始下载: {file_info['file_name']} ({file_info['file_size']} bytes)")
        
        try:
            # 选择下载策略
            if file_info["file_size"] > self.large_file_threshold:
                # 大文件使用分片下载
                result = await self._download_large_file(message, file_path, progress)
            else:
                # 小文件使用标准下载
                result = await self._download_standard_file(message, file_path, progress)
            
            if result:
                self.downloads_completed += 1
                self.bytes_downloaded += file_info["file_size"]
                self.logger.info(f"下载完成: {file_path}")
                
                if self.download_complete_callback:
                    await self.download_complete_callback(str(file_path), True)
                
                return str(file_path)
            else:
                self.downloads_failed += 1
                self.logger.error(f"下载失败: {file_info['file_name']}")
                
                if self.download_complete_callback:
                    await self.download_complete_callback(file_info["file_name"], False)
                
                return None
                
        except Exception as e:
            self.downloads_failed += 1
            self.logger.error(f"下载异常: {file_info['file_name']}", exc_info=e)
            
            if self.download_complete_callback:
                await self.download_complete_callback(file_info["file_name"], False)
            
            # 清理部分下载的文件
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            
            return None
    
    async def _download_standard_file(self, message: Message, file_path: Path, 
                                     progress: DownloadProgress) -> bool:
        """
        标准文件下载
        
        Args:
            message: 消息对象
            file_path: 文件路径
            progress: 进度对象
            
        Returns:
            是否下载成功
        """
        client = self.client_manager.client if self.client_manager else None
        if not client:
            raise DownloadError("没有可用的客户端")
        
        try:
            # 使用Pyrogram的download_media方法
            result = await asyncio.wait_for(
                client.download_media(
                    message,
                    file_name=str(file_path),
                    progress=lambda current, total: asyncio.create_task(
                        self._progress_callback_wrapper(current, total, progress)
                    )
                ),
                timeout=self.timeout
            )
            
            return result is not None
            
        except asyncio.TimeoutError:
            raise DownloadTimeoutError(f"下载超时: {file_path.name}")
        except FileReferenceExpired:
            raise DownloadError("文件引用已过期，请重新获取消息")
        except Exception as e:
            raise DownloadError(f"下载失败: {e}")
    
    async def _download_large_file(self, message: Message, file_path: Path, 
                                  progress: DownloadProgress) -> bool:
        """
        大文件分片下载
        
        Args:
            message: 消息对象
            file_path: 文件路径
            progress: 进度对象
            
        Returns:
            是否下载成功
        """
        client = self.client_manager.client if self.client_manager else None
        if not client:
            raise DownloadError("没有可用的客户端")
        
        try:
            downloaded = 0
            file_size = self._get_file_info(message)["file_size"]
            
            with open(file_path, 'wb') as file:
                async for chunk in client.stream_media(message, limit=self.chunk_size):
                    file.write(chunk)
                    downloaded += len(chunk)
                    
                    # 更新进度
                    await self._progress_callback_wrapper(downloaded, file_size, progress)
                    
                    # 检查是否完成
                    if downloaded >= file_size:
                        break
            
            return True
            
        except Exception as e:
            raise DownloadError(f"分片下载失败: {e}")
    
    async def download_multiple_media(self, messages: List[Message], 
                                    chat_title: Optional[str] = None,
                                    max_concurrent: int = 5) -> List[Optional[str]]:
        """
        批量下载多个媒体文件
        
        Args:
            messages: 消息列表
            chat_title: 聊天标题
            max_concurrent: 最大并发数
            
        Returns:
            下载结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(message: Message) -> Optional[str]:
            async with semaphore:
                return await self.download_media(message, chat_title=chat_title)
        
        tasks = [download_with_semaphore(msg) for msg in messages if msg.media]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"批量下载中的异常: {result}")
                final_results.append(None)
            else:
                final_results.append(result)
        
        return final_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        return {
            "downloads_completed": self.downloads_completed,
            "downloads_failed": self.downloads_failed,
            "bytes_downloaded": self.bytes_downloaded,
            "success_rate": (self.downloads_completed / (self.downloads_completed + self.downloads_failed)) * 100
            if (self.downloads_completed + self.downloads_failed) > 0 else 0
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.downloads_completed = 0
        self.downloads_failed = 0
        self.bytes_downloaded = 0 