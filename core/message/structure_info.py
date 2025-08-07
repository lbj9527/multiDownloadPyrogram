"""
消息结构信息模块
用于保存和管理消息的媒体组结构信息
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class MessageType(Enum):
    """消息类型枚举"""
    SINGLE_MESSAGE = "single_message"      # 单条消息
    GROUP_MEMBER = "group_member"          # 媒体组成员
    NON_MEDIA = "non_media"               # 非媒体消息


@dataclass
class MessageStructureInfo:
    """消息结构信息"""
    group_id: Optional[str] = None         # 媒体组ID
    is_single: bool = True                 # 是否为单条消息
    has_media: bool = False               # 是否包含媒体
    message_type: MessageType = MessageType.NON_MEDIA
    position: Optional[int] = None         # 在组中的位置
    total_count: Optional[int] = None      # 媒体组总数量（如果已知）
    
    @property
    def is_group_member(self) -> bool:
        """是否属于媒体组"""
        return not self.is_single and self.group_id is not None
    
    @property
    def is_media_message(self) -> bool:
        """是否为媒体消息"""
        return self.has_media
    
    def __str__(self) -> str:
        if self.is_single:
            return f"SingleMessage(has_media={self.has_media})"
        else:
            return f"GroupMember(group_id={self.group_id}, position={self.position})"


class MessageStructureExtractor:
    """消息结构信息提取器"""
    
    @staticmethod
    def extract_structure_info(message) -> MessageStructureInfo:
        """从消息中提取结构信息"""
        if not message or getattr(message, 'empty', True):
            return MessageStructureInfo()
        
        has_media = MessageStructureExtractor._has_media(message)
        
        # 检查是否为媒体组成员
        if hasattr(message, 'media_group_id') and message.media_group_id:
            return MessageStructureInfo(
                group_id=message.media_group_id,
                is_single=False,
                has_media=has_media,
                message_type=MessageType.GROUP_MEMBER,
                position=getattr(message, 'group_position', None)
            )
        else:
            # 单条消息
            message_type = MessageType.SINGLE_MESSAGE if has_media else MessageType.NON_MEDIA
            return MessageStructureInfo(
                group_id=None,
                is_single=True,
                has_media=has_media,
                message_type=message_type
            )
    
    @staticmethod
    def _has_media(message) -> bool:
        """检查消息是否包含媒体"""
        return any([
            getattr(message, 'photo', None),
            getattr(message, 'video', None),
            getattr(message, 'document', None),
            getattr(message, 'audio', None),
            getattr(message, 'voice', None),
            getattr(message, 'video_note', None),
            getattr(message, 'animation', None),
            getattr(message, 'sticker', None)
        ])
    
    @staticmethod
    def enhance_message_with_structure_info(message):
        """为消息添加结构信息属性"""
        if message and not getattr(message, 'empty', True):
            structure_info = MessageStructureExtractor.extract_structure_info(message)
            message._structure_info = structure_info
        return message
    
    @staticmethod
    def enhance_messages_batch(messages: list) -> list:
        """批量为消息添加结构信息"""
        enhanced_messages = []
        for message in messages:
            enhanced_message = MessageStructureExtractor.enhance_message_with_structure_info(message)
            enhanced_messages.append(enhanced_message)
        return enhanced_messages
