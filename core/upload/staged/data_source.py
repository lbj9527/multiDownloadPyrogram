"""
数据源抽象层
定义数据源接口和具体实现
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from pyrogram.client import Client

from utils.logging_utils import LoggerMixin
from utils.message_utils import MessageUtils


class MediaType(Enum):
    """媒体类型枚举"""
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"
    ANIMATION = "animation"
    STICKER = "sticker"


@dataclass
class MediaData:
    """媒体数据模型"""
    file_data: bytes
    file_name: str
    file_size: int
    mime_type: Optional[str]
    caption: Optional[str]
    media_type: MediaType
    
    # 原始消息信息
    source_message_id: int
    source_chat_id: Optional[str] = None
    
    # 额外元数据
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return f"{self.file_name} ({self.file_size / 1024 / 1024:.1f} MB)"


class DataSource(ABC, LoggerMixin):
    """数据源抽象基类"""
    
    @abstractmethod
    async def get_media_data(self, source_item: Any) -> Optional[MediaData]:
        """
        从数据源获取媒体数据
        
        Args:
            source_item: 数据源项目（如Telegram消息）
            
        Returns:
            MediaData: 媒体数据，获取失败返回None
        """
        pass
    
    @abstractmethod
    def validate_source_item(self, source_item: Any) -> bool:
        """
        验证数据源项目是否有效
        
        Args:
            source_item: 数据源项目
            
        Returns:
            bool: 是否有效
        """
        pass


class TelegramDataSource(DataSource):
    """Telegram数据源实现"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def get_media_data(self, message: Any) -> Optional[MediaData]:
        """
        从Telegram消息获取媒体数据
        
        Args:
            message: Pyrogram消息对象
            
        Returns:
            MediaData: 媒体数据
        """
        try:
            if not self.validate_source_item(message):
                self.log_warning(f"消息 {message.id} 没有有效媒体")
                return None
            
            # 获取文件信息
            file_info = MessageUtils.get_file_info(message)
            
            # 确定媒体类型
            media_type = self._determine_media_type(message)
            
            # 下载文件数据
            self.log_info(f"开始下载消息 {message.id} 的媒体文件: {file_info['file_name']}")
            
            # 使用现有的下载管理器进行内存下载
            from core.download import DownloadManager
            from config.settings import DownloadConfig
            
            download_manager = DownloadManager(DownloadConfig())
            download_result = await download_manager.download_media_enhanced(
                self.client, message, mode="memory"
            )
            
            if not download_result:
                self.log_error(f"消息 {message.id} 下载失败")
                return None
            
            # 获取媒体尺寸和时长信息
            width, height, duration = self._get_media_dimensions(message)
            
            return MediaData(
                file_data=download_result.file_data,
                file_name=download_result.file_name,
                file_size=download_result.file_size,
                mime_type=download_result.mime_type,
                caption=download_result.original_caption or download_result.original_text,
                media_type=media_type,
                source_message_id=message.id,
                source_chat_id=str(message.chat.id) if message.chat else None,
                width=width,
                height=height,
                duration=duration
            )
            
        except Exception as e:
            self.log_error(f"获取消息 {message.id} 媒体数据失败: {e}")
            return None
    
    def validate_source_item(self, message: Any) -> bool:
        """验证Telegram消息是否有媒体"""
        if not message:
            return False
        
        return bool(message.media)
    
    def _determine_media_type(self, message: Any) -> MediaType:
        """确定媒体类型"""
        if message.photo:
            return MediaType.PHOTO
        elif message.video:
            return MediaType.VIDEO
        elif message.document:
            return MediaType.DOCUMENT
        elif message.audio:
            return MediaType.AUDIO
        elif message.voice:
            return MediaType.VOICE
        elif message.video_note:
            return MediaType.VIDEO_NOTE
        elif message.animation:
            return MediaType.ANIMATION
        elif message.sticker:
            return MediaType.STICKER
        else:
            return MediaType.DOCUMENT  # 默认为文档
    
    def _get_media_dimensions(self, message: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """获取媒体尺寸和时长信息"""
        width = height = duration = None
        
        if message.photo:
            width = getattr(message.photo, 'width', None)
            height = getattr(message.photo, 'height', None)
        elif message.video:
            width = getattr(message.video, 'width', None)
            height = getattr(message.video, 'height', None)
            duration = getattr(message.video, 'duration', None)
        elif message.audio:
            duration = getattr(message.audio, 'duration', None)
        elif message.voice:
            duration = getattr(message.voice, 'duration', None)
        elif message.video_note:
            duration = getattr(message.video_note, 'duration', None)
        elif message.animation:
            width = getattr(message.animation, 'width', None)
            height = getattr(message.animation, 'height', None)
            duration = getattr(message.animation, 'duration', None)
        
        return width, height, duration
