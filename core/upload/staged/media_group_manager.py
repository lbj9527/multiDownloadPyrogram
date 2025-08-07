"""
媒体组管理器
负责将临时媒体项组织成媒体组并创建InputMedia对象
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import time

from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio

from utils.logging_utils import LoggerMixin
from .data_source import MediaType
from .temporary_storage import TemporaryMediaItem


class MediaGroupType(Enum):
    """媒体组类型"""
    PHOTO_VIDEO = "photo_video"  # 照片和视频混合组
    DOCUMENT = "document"        # 文档组
    AUDIO = "audio"             # 音频组
    MIXED = "mixed"             # 混合组（不推荐）


@dataclass
class MediaGroupBatch:
    """媒体组批次"""
    group_type: MediaGroupType
    items: List[TemporaryMediaItem] = field(default_factory=list)
    created_time: float = field(default_factory=time.time)
    
    def __len__(self) -> int:
        return len(self.items)
    
    def is_full(self, max_size: int = 10) -> bool:
        """检查批次是否已满"""
        return len(self.items) >= max_size
    
    def can_add_item(self, item: TemporaryMediaItem) -> bool:
        """检查是否可以添加项目到此批次"""
        media_type = item.media_data.media_type
        
        if self.group_type == MediaGroupType.PHOTO_VIDEO:
            return media_type in [MediaType.PHOTO, MediaType.VIDEO, MediaType.ANIMATION]
        elif self.group_type == MediaGroupType.DOCUMENT:
            return media_type == MediaType.DOCUMENT
        elif self.group_type == MediaGroupType.AUDIO:
            return media_type in [MediaType.AUDIO, MediaType.VOICE]
        else:  # MIXED
            return True
    
    def get_total_size(self) -> int:
        """获取批次总大小（字节）"""
        return sum(item.media_data.file_size for item in self.items)


class MediaGroupManager(LoggerMixin):
    """媒体组管理器"""
    
    def __init__(self, batch_size: int = 10, auto_send_threshold: int = 10):
        self.batch_size = batch_size
        self.auto_send_threshold = auto_send_threshold
        
        # 不同类型的批次
        self.photo_video_batches: List[MediaGroupBatch] = []
        self.document_batches: List[MediaGroupBatch] = []
        self.audio_batches: List[MediaGroupBatch] = []
        
        # 统计信息
        self.stats = {
            "total_items": 0,
            "batches_created": 0,
            "items_by_type": {}
        }
    
    async def add_media_item(self, item: TemporaryMediaItem) -> Optional[MediaGroupBatch]:
        """
        添加媒体项到合适的批次
        
        Args:
            item: 临时媒体项
            
        Returns:
            MediaGroupBatch: 如果批次已满，返回完整的批次；否则返回None
        """
        try:
            self.stats["total_items"] += 1
            media_type = item.media_data.media_type
            
            # 更新类型统计
            type_name = media_type.value
            self.stats["items_by_type"][type_name] = self.stats["items_by_type"].get(type_name, 0) + 1
            
            # 根据媒体类型选择合适的批次
            if media_type in [MediaType.PHOTO, MediaType.VIDEO, MediaType.ANIMATION]:
                return await self._add_to_photo_video_batch(item)
            elif media_type == MediaType.DOCUMENT:
                return await self._add_to_document_batch(item)
            elif media_type in [MediaType.AUDIO, MediaType.VOICE]:
                return await self._add_to_audio_batch(item)
            else:
                # 其他类型（如贴纸、视频笔记）作为文档处理
                self.log_warning(f"未知媒体类型 {media_type}，作为文档处理")
                return await self._add_to_document_batch(item)
                
        except Exception as e:
            self.log_error(f"添加媒体项失败: {e}")
            return None
    
    async def get_ready_batches(self) -> List[MediaGroupBatch]:
        """
        获取所有准备好的批次（已满或超时的批次）
        
        Returns:
            List[MediaGroupBatch]: 准备好的批次列表
        """
        ready_batches = []
        
        # 检查所有批次类型
        for batch_list in [self.photo_video_batches, self.document_batches, self.audio_batches]:
            for batch in batch_list[:]:  # 使用切片避免修改列表时的问题
                if batch.is_full(self.batch_size) or self._is_batch_timeout(batch):
                    ready_batches.append(batch)
                    batch_list.remove(batch)
        
        return ready_batches
    
    async def flush_all_batches(self) -> List[MediaGroupBatch]:
        """
        强制获取所有批次（无论是否已满）
        
        Returns:
            List[MediaGroupBatch]: 所有批次列表
        """
        all_batches = []
        
        # 收集所有非空批次
        for batch_list in [self.photo_video_batches, self.document_batches, self.audio_batches]:
            for batch in batch_list:
                if batch.items:  # 只返回非空批次
                    all_batches.append(batch)
            batch_list.clear()  # 清空列表
        
        return all_batches
    
    async def create_input_media_group(self, batch: MediaGroupBatch) -> List[Any]:
        """
        为批次创建InputMedia对象列表
        
        Args:
            batch: 媒体组批次
            
        Returns:
            List[InputMedia]: InputMedia对象列表
        """
        try:
            input_media_list = []
            
            for item in batch.items:
                input_media = await self._create_input_media(item)
                if input_media:
                    input_media_list.append(input_media)
            
            self.log_info(f"为 {batch.group_type.value} 批次创建了 {len(input_media_list)} 个InputMedia对象")
            return input_media_list
            
        except Exception as e:
            self.log_error(f"创建InputMedia组失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "pending_batches": {
                "photo_video": len(self.photo_video_batches),
                "document": len(self.document_batches),
                "audio": len(self.audio_batches)
            }
        }
    
    async def _add_to_photo_video_batch(self, item: TemporaryMediaItem) -> Optional[MediaGroupBatch]:
        """添加到照片/视频批次"""
        # 寻找可以添加的现有批次
        for batch in self.photo_video_batches:
            if not batch.is_full(self.batch_size) and batch.can_add_item(item):
                batch.items.append(item)
                if batch.is_full(self.batch_size):
                    self.photo_video_batches.remove(batch)
                    self.stats["batches_created"] += 1
                    return batch
                return None
        
        # 创建新批次
        new_batch = MediaGroupBatch(MediaGroupType.PHOTO_VIDEO, [item])
        if new_batch.is_full(self.batch_size):
            self.stats["batches_created"] += 1
            return new_batch
        else:
            self.photo_video_batches.append(new_batch)
            return None
    
    async def _add_to_document_batch(self, item: TemporaryMediaItem) -> Optional[MediaGroupBatch]:
        """添加到文档批次"""
        # 寻找可以添加的现有批次
        for batch in self.document_batches:
            if not batch.is_full(self.batch_size):
                batch.items.append(item)
                if batch.is_full(self.batch_size):
                    self.document_batches.remove(batch)
                    self.stats["batches_created"] += 1
                    return batch
                return None
        
        # 创建新批次
        new_batch = MediaGroupBatch(MediaGroupType.DOCUMENT, [item])
        if new_batch.is_full(self.batch_size):
            self.stats["batches_created"] += 1
            return new_batch
        else:
            self.document_batches.append(new_batch)
            return None
    
    async def _add_to_audio_batch(self, item: TemporaryMediaItem) -> Optional[MediaGroupBatch]:
        """添加到音频批次"""
        # 寻找可以添加的现有批次
        for batch in self.audio_batches:
            if not batch.is_full(self.batch_size):
                batch.items.append(item)
                if batch.is_full(self.batch_size):
                    self.audio_batches.remove(batch)
                    self.stats["batches_created"] += 1
                    return batch
                return None
        
        # 创建新批次
        new_batch = MediaGroupBatch(MediaGroupType.AUDIO, [item])
        if new_batch.is_full(self.batch_size):
            self.stats["batches_created"] += 1
            return new_batch
        else:
            self.audio_batches.append(new_batch)
            return None
    
    def _is_batch_timeout(self, batch: MediaGroupBatch, timeout_seconds: float = 300) -> bool:
        """检查批次是否超时（5分钟）"""
        return time.time() - batch.created_time > timeout_seconds
    
    async def _create_input_media(self, item: TemporaryMediaItem) -> Optional[Any]:
        """
        为临时媒体项创建InputMedia对象
        
        Args:
            item: 临时媒体项
            
        Returns:
            InputMedia: 对应的InputMedia对象
        """
        try:
            media_data = item.media_data
            media_type = media_data.media_type
            caption = media_data.caption or ""
            
            # 使用file_id作为媒体引用
            media_reference = item.file_id

            if not media_reference:
                self.log_error(f"无法获取file_id: {media_data.file_name}")
                return None
            
            if media_type == MediaType.PHOTO:
                return InputMediaPhoto(
                    media=media_reference,
                    caption=caption
                )
            elif media_type == MediaType.VIDEO:
                return InputMediaVideo(
                    media=media_reference,
                    caption=caption,
                    width=media_data.width,
                    height=media_data.height,
                    duration=media_data.duration
                )
            elif media_type == MediaType.AUDIO:
                return InputMediaAudio(
                    media=media_reference,
                    caption=caption,
                    duration=media_data.duration
                )
            elif media_type in [MediaType.DOCUMENT, MediaType.VOICE, MediaType.VIDEO_NOTE, 
                              MediaType.ANIMATION, MediaType.STICKER]:
                return InputMediaDocument(
                    media=media_reference,
                    caption=caption
                )
            else:
                self.log_warning(f"不支持的媒体类型: {media_type}")
                return None
                
        except Exception as e:
            self.log_error(f"创建InputMedia失败: {e}")
            return None
