"""
媒体组下载器模块

专门处理Telegram媒体组的完整下载，确保相册中的所有文件都被下载
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass
from pyrogram import Client
from pyrogram.types import Message

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import MediaGroupError, DownloadError
from client.client_manager import ClientManager
from .media_downloader import MediaDownloader, DownloadProgress


@dataclass
class MediaGroupInfo:
    """媒体组信息"""
    group_id: str
    messages: List[Message]
    total_files: int
    total_size: int
    group_type: str  # "album", "mixed"
    
    @property
    def file_types(self) -> Set[str]:
        """获取文件类型集合"""
        types = set()
        for message in self.messages:
            if message.photo:
                types.add("photo")
            elif message.video:
                types.add("video")
            elif message.document:
                types.add("document")
            elif message.audio:
                types.add("audio")
        return types


@dataclass
class GroupDownloadProgress:
    """媒体组下载进度"""
    group_id: str
    total_files: int
    completed_files: int
    failed_files: int
    total_size: int
    downloaded_size: int
    current_file: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """获取总进度百分比"""
        return (self.completed_files / self.total_files) * 100 if self.total_files > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "group_id": self.group_id,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "percentage": self.percentage,
            "current_file": self.current_file
        }


class GroupDownloader:
    """媒体组下载器"""
    
    def __init__(self, config: Config, client_manager: Optional[ClientManager] = None):
        """
        初始化媒体组下载器
        
        Args:
            config: 配置对象
            client_manager: 客户端管理器
        """
        self.config = config
        self.client_manager = client_manager
        self.logger = get_logger(f"{__name__}.GroupDownloader")
        
        # 媒体下载器
        self.media_downloader = MediaDownloader(config, client_manager)
        
        # 下载配置
        self.download_path = Path(config.download.download_path)
        self.max_concurrent_files = min(3, config.download.max_concurrent_downloads)
        self.create_group_folder = True
        self.group_folder_format = "Group_{group_id}"
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        self.file_progress_callback: Optional[Callable] = None
        
        # 统计信息
        self.groups_downloaded = 0
        self.groups_failed = 0
        self.files_downloaded = 0
        self.files_failed = 0
        self.bytes_downloaded = 0
        
        # 缓存已处理的媒体组
        self.processed_groups: Set[str] = set()
    
    def set_progress_callback(self, callback: Callable[[GroupDownloadProgress], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_file_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """设置文件进度回调函数"""
        self.file_progress_callback = callback
        self.media_downloader.set_progress_callback(callback)
    
    async def get_media_group_info(self, message: Message) -> Optional[MediaGroupInfo]:
        """
        获取媒体组信息
        
        Args:
            message: 媒体组中的任意一条消息
            
        Returns:
            媒体组信息对象
        """
        if not message.media_group_id:
            return None
        
        client = self.client_manager.client if self.client_manager else None
        if not client:
            raise MediaGroupError("没有可用的客户端", media_group_id=message.media_group_id)
        
        try:
            # 获取媒体组中的所有消息
            media_group = await client.get_media_group(
                message.chat.id, 
                message.id
            )
            
            if not media_group:
                self.logger.warning(f"无法获取媒体组: {message.media_group_id}")
                return None
            
            # 计算总大小
            total_size = 0
            for msg in media_group:
                if msg.photo:
                    total_size += msg.photo.file_size or 0
                elif msg.video:
                    total_size += msg.video.file_size or 0
                elif msg.document:
                    total_size += msg.document.file_size or 0
                elif msg.audio:
                    total_size += msg.audio.file_size or 0
            
            # 确定组类型
            file_types = set()
            for msg in media_group:
                if msg.photo:
                    file_types.add("photo")
                elif msg.video:
                    file_types.add("video")
                elif msg.document:
                    file_types.add("document")
                elif msg.audio:
                    file_types.add("audio")
            
            if file_types == {"photo"}:
                group_type = "album"
            elif file_types == {"video"}:
                group_type = "album"
            elif file_types == {"photo", "video"}:
                group_type = "album"
            else:
                group_type = "mixed"
            
            return MediaGroupInfo(
                group_id=message.media_group_id,
                messages=media_group,
                total_files=len(media_group),
                total_size=total_size,
                group_type=group_type
            )
            
        except Exception as e:
            self.logger.error(f"获取媒体组信息失败: {e}")
            raise MediaGroupError(f"获取媒体组信息失败: {e}", media_group_id=message.media_group_id)
    
    def _get_group_download_path(self, group_info: MediaGroupInfo, 
                                chat_title: Optional[str] = None) -> Path:
        """
        获取媒体组下载路径
        
        Args:
            group_info: 媒体组信息
            chat_title: 聊天标题
            
        Returns:
            下载路径
        """
        # 基础路径
        if chat_title:
            base_path = self.download_path / self._sanitize_filename(chat_title)
        else:
            base_path = self.download_path
        
        # 创建组文件夹
        if self.create_group_folder:
            group_folder_name = self.group_folder_format.format(
                group_id=group_info.group_id,
                group_type=group_info.group_type,
                file_count=group_info.total_files
            )
            group_path = base_path / group_folder_name
        else:
            group_path = base_path
        
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        return filename
    
    async def download_media_group(self, message: Message, 
                                  chat_title: Optional[str] = None) -> Optional[List[str]]:
        """
        下载媒体组
        
        Args:
            message: 媒体组中的任意一条消息
            chat_title: 聊天标题
            
        Returns:
            下载的文件路径列表，如果失败则返回None
        """
        if not message.media_group_id:
            self.logger.warning("消息不属于媒体组")
            return None
        
        # 检查是否已处理过
        if message.media_group_id in self.processed_groups:
            self.logger.info(f"媒体组已处理过: {message.media_group_id}")
            return None
        
        # 获取媒体组信息
        group_info = await self.get_media_group_info(message)
        if not group_info:
            return None
        
        # 标记为已处理
        self.processed_groups.add(message.media_group_id)
        
        self.logger.info(f"开始下载媒体组: {group_info.group_id}, 文件数: {group_info.total_files}")
        
        # 获取下载路径
        group_path = self._get_group_download_path(group_info, chat_title)
        
        # 创建进度对象
        progress = GroupDownloadProgress(
            group_id=group_info.group_id,
            total_files=group_info.total_files,
            completed_files=0,
            failed_files=0,
            total_size=group_info.total_size,
            downloaded_size=0
        )
        
        # 下载所有文件
        download_results = []
        
        try:
            # 创建下载任务
            semaphore = asyncio.Semaphore(self.max_concurrent_files)
            
            async def download_file_with_semaphore(msg: Message, index: int):
                async with semaphore:
                    return await self._download_group_file(msg, group_path, progress, index)
            
            # 并发下载所有文件
            tasks = [
                download_file_with_semaphore(msg, i) 
                for i, msg in enumerate(group_info.messages)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            successful_downloads = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"媒体组文件下载异常: {result}")
                    download_results.append(None)
                    progress.failed_files += 1
                elif result:
                    download_results.append(result)
                    successful_downloads += 1
                else:
                    download_results.append(None)
                    progress.failed_files += 1
            
            # 更新最终进度
            progress.completed_files = successful_downloads
            if self.progress_callback:
                await self.progress_callback(progress)
            
            # 更新统计信息
            if successful_downloads == group_info.total_files:
                self.groups_downloaded += 1
                self.logger.info(f"媒体组下载完成: {group_info.group_id}")
            else:
                self.groups_failed += 1
                self.logger.error(f"媒体组下载失败: {group_info.group_id}, 成功: {successful_downloads}/{group_info.total_files}")
            
            self.files_downloaded += successful_downloads
            self.files_failed += progress.failed_files
            
            return download_results
            
        except Exception as e:
            self.groups_failed += 1
            self.logger.error(f"媒体组下载异常: {group_info.group_id}", exc_info=e)
            return None
    
    async def _download_group_file(self, message: Message, group_path: Path, 
                                  progress: GroupDownloadProgress, index: int) -> Optional[str]:
        """
        下载媒体组中的单个文件
        
        Args:
            message: 消息对象
            group_path: 组下载路径
            progress: 进度对象
            index: 文件索引
            
        Returns:
            下载的文件路径，如果失败则返回None
        """
        try:
            # 设置当前文件
            file_info = self.media_downloader._get_file_info(message)
            progress.current_file = file_info.get("file_name", f"file_{index}")
            
            if self.progress_callback:
                await self.progress_callback(progress)
            
            # 下载文件
            result = await self.media_downloader.download_media(
                message, 
                custom_path=group_path
            )
            
            if result:
                # 更新进度
                file_size = file_info.get("file_size", 0)
                progress.downloaded_size += file_size
                self.bytes_downloaded += file_size
                
                self.logger.debug(f"媒体组文件下载完成: {result}")
                return result
            else:
                self.logger.error(f"媒体组文件下载失败: {file_info.get('file_name', 'unknown')}")
                return None
                
        except Exception as e:
            self.logger.error(f"媒体组文件下载异常: {e}")
            return None
    
    async def download_multiple_groups(self, messages: List[Message], 
                                     chat_title: Optional[str] = None) -> List[Optional[List[str]]]:
        """
        批量下载多个媒体组
        
        Args:
            messages: 消息列表
            chat_title: 聊天标题
            
        Returns:
            下载结果列表
        """
        # 按媒体组ID分组
        groups = {}
        for message in messages:
            if message.media_group_id:
                if message.media_group_id not in groups:
                    groups[message.media_group_id] = message
        
        self.logger.info(f"发现 {len(groups)} 个媒体组")
        
        # 下载所有组
        results = []
        for group_id, representative_message in groups.items():
            try:
                result = await self.download_media_group(representative_message, chat_title)
                results.append(result)
            except Exception as e:
                self.logger.error(f"媒体组下载失败: {group_id}", exc_info=e)
                results.append(None)
        
        return results
    
    def is_group_processed(self, group_id: str) -> bool:
        """检查媒体组是否已处理"""
        return group_id in self.processed_groups
    
    def mark_group_processed(self, group_id: str):
        """标记媒体组为已处理"""
        self.processed_groups.add(group_id)
    
    def clear_processed_groups(self):
        """清除已处理的媒体组缓存"""
        self.processed_groups.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        return {
            "groups_downloaded": self.groups_downloaded,
            "groups_failed": self.groups_failed,
            "files_downloaded": self.files_downloaded,
            "files_failed": self.files_failed,
            "bytes_downloaded": self.bytes_downloaded,
            "group_success_rate": (self.groups_downloaded / (self.groups_downloaded + self.groups_failed)) * 100
            if (self.groups_downloaded + self.groups_failed) > 0 else 0,
            "file_success_rate": (self.files_downloaded / (self.files_downloaded + self.files_failed)) * 100
            if (self.files_downloaded + self.files_failed) > 0 else 0
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.groups_downloaded = 0
        self.groups_failed = 0
        self.files_downloaded = 0
        self.files_failed = 0
        self.bytes_downloaded = 0
        self.processed_groups.clear() 