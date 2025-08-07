"""
临时存储抽象层
定义临时存储接口和具体实现
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from io import BytesIO
import time

from pyrogram.client import Client
from pyrogram.types import Message

from utils.logging_utils import LoggerMixin
from .data_source import MediaData, MediaType


@dataclass
class TemporaryMediaItem:
    """临时媒体项"""
    media_data: MediaData
    storage_reference: str  # 存储引用（如消息ID）
    storage_time: float

    # Telegram特定信息
    message_id: Optional[int] = None
    chat_id: Optional[str] = None
    file_id: Optional[str] = None  # Telegram文件ID，用于InputMedia
    
    def __post_init__(self):
        if self.storage_time is None:
            self.storage_time = time.time()
    
    def get_age_seconds(self) -> float:
        """获取存储时长（秒）"""
        return time.time() - self.storage_time


class TemporaryStorage(ABC, LoggerMixin):
    """临时存储抽象基类"""
    
    @abstractmethod
    async def store_media(self, media_data: MediaData) -> Optional[TemporaryMediaItem]:
        """
        存储媒体到临时位置
        
        Args:
            media_data: 媒体数据
            
        Returns:
            TemporaryMediaItem: 临时媒体项，存储失败返回None
        """
        pass
    
    @abstractmethod
    async def cleanup_media(self, item: TemporaryMediaItem) -> bool:
        """
        清理临时媒体
        
        Args:
            item: 临时媒体项
            
        Returns:
            bool: 清理是否成功
        """
        pass
    
    @abstractmethod
    async def cleanup_batch(self, items: List[TemporaryMediaItem]) -> int:
        """
        批量清理临时媒体
        
        Args:
            items: 临时媒体项列表
            
        Returns:
            int: 成功清理的数量
        """
        pass


class TelegramMeStorage(TemporaryStorage):
    """Telegram Me聊天临时存储实现"""
    
    def __init__(self, client: Client):
        self.client = client
        self.storage_chat = "me"  # 存储到自己的聊天
    
    async def store_media(self, media_data: MediaData) -> Optional[TemporaryMediaItem]:
        """
        将媒体存储到me聊天
        
        Args:
            media_data: 媒体数据
            
        Returns:
            TemporaryMediaItem: 临时媒体项
        """
        try:
            self.log_info(f"开始将媒体存储到me聊天: {media_data.get_display_name()}")
            
            # 准备文件数据
            file_data = BytesIO(media_data.file_data)
            file_data.name = media_data.file_name
            
            # 根据媒体类型选择上传方法
            message = await self._upload_by_type(media_data, file_data)
            
            if not message:
                self.log_error(f"上传媒体到me聊天失败: {media_data.file_name}")
                return None
            
            self.log_info(f"媒体已存储到me聊天: {media_data.file_name} (消息ID: {message.id})")
            
            # 从消息中提取file_id
            file_id = self._extract_file_id(message, media_data.media_type)

            return TemporaryMediaItem(
                media_data=media_data,
                storage_reference=str(message.id),
                storage_time=time.time(),
                message_id=message.id,
                chat_id=self.storage_chat,
                file_id=file_id
            )
            
        except Exception as e:
            self.log_error(f"存储媒体到me聊天失败: {e}")
            return None

    def _extract_file_id(self, message, media_type: MediaType) -> Optional[str]:
        """从消息中提取file_id"""
        try:
            if media_type == MediaType.PHOTO and message.photo:
                return message.photo.file_id
            elif media_type == MediaType.VIDEO and message.video:
                return message.video.file_id
            elif media_type == MediaType.DOCUMENT and message.document:
                return message.document.file_id
            elif media_type == MediaType.AUDIO and message.audio:
                return message.audio.file_id
            elif media_type == MediaType.VOICE and message.voice:
                return message.voice.file_id
            elif media_type == MediaType.VIDEO_NOTE and message.video_note:
                return message.video_note.file_id
            elif media_type == MediaType.ANIMATION and message.animation:
                return message.animation.file_id
            else:
                self.log_warning(f"无法提取file_id，未知媒体类型: {media_type}")
                return None
        except Exception as e:
            self.log_error(f"提取file_id失败: {e}")
            return None
    
    async def cleanup_media(self, item: TemporaryMediaItem) -> bool:
        """
        从me聊天删除临时媒体
        
        Args:
            item: 临时媒体项
            
        Returns:
            bool: 删除是否成功
        """
        try:
            if not item.message_id:
                self.log_warning("临时媒体项没有消息ID，无法删除")
                return False
            
            await self.client.delete_messages(self.storage_chat, item.message_id)
            self.log_info(f"已从me聊天删除临时媒体: {item.media_data.file_name} (消息ID: {item.message_id})")
            return True
            
        except Exception as e:
            self.log_error(f"删除临时媒体失败: {e}")
            return False
    
    async def cleanup_batch(self, items: List[TemporaryMediaItem]) -> int:
        """
        批量删除临时媒体
        
        Args:
            items: 临时媒体项列表
            
        Returns:
            int: 成功删除的数量
        """
        if not items:
            return 0
        
        try:
            # 收集消息ID
            message_ids = [item.message_id for item in items if item.message_id]
            
            if not message_ids:
                self.log_warning("没有有效的消息ID可以删除")
                return 0
            
            # 批量删除
            await self.client.delete_messages(self.storage_chat, message_ids)
            
            self.log_info(f"已从me聊天批量删除 {len(message_ids)} 个临时媒体")
            return len(message_ids)
            
        except Exception as e:
            self.log_error(f"批量删除临时媒体失败: {e}")
            
            # 尝试逐个删除
            success_count = 0
            for item in items:
                if await self.cleanup_media(item):
                    success_count += 1
            
            return success_count
    
    async def _upload_by_type(self, media_data: MediaData, file_data: BytesIO) -> Optional[Message]:
        """
        根据媒体类型选择上传方法
        
        Args:
            media_data: 媒体数据
            file_data: 文件数据流
            
        Returns:
            Message: 上传后的消息对象
        """
        caption = media_data.caption or ""
        
        try:
            if media_data.media_type == MediaType.PHOTO:
                return await self.client.send_photo(
                    chat_id=self.storage_chat,
                    photo=file_data,
                    caption=caption
                )
            elif media_data.media_type == MediaType.VIDEO:
                return await self.client.send_video(
                    chat_id=self.storage_chat,
                    video=file_data,
                    caption=caption,
                    width=media_data.width,
                    height=media_data.height,
                    duration=media_data.duration
                )
            elif media_data.media_type == MediaType.AUDIO:
                return await self.client.send_audio(
                    chat_id=self.storage_chat,
                    audio=file_data,
                    caption=caption,
                    duration=media_data.duration
                )
            elif media_data.media_type == MediaType.VOICE:
                return await self.client.send_voice(
                    chat_id=self.storage_chat,
                    voice=file_data,
                    caption=caption,
                    duration=media_data.duration
                )
            elif media_data.media_type == MediaType.VIDEO_NOTE:
                return await self.client.send_video_note(
                    chat_id=self.storage_chat,
                    video_note=file_data,
                    duration=media_data.duration
                )
            elif media_data.media_type == MediaType.ANIMATION:
                return await self.client.send_animation(
                    chat_id=self.storage_chat,
                    animation=file_data,
                    caption=caption,
                    width=media_data.width,
                    height=media_data.height,
                    duration=media_data.duration
                )
            elif media_data.media_type == MediaType.STICKER:
                return await self.client.send_sticker(
                    chat_id=self.storage_chat,
                    sticker=file_data
                )
            else:  # DOCUMENT 或其他
                return await self.client.send_document(
                    chat_id=self.storage_chat,
                    document=file_data,
                    caption=caption,
                    file_name=media_data.file_name
                )
                
        except Exception as e:
            self.log_error(f"上传媒体类型 {media_data.media_type.value} 失败: {e}")
            return None
