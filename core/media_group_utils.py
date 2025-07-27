"""
媒体组工具类
统一处理媒体组相关的逻辑，避免代码重复
"""

from typing import Any, Optional
from utils import get_logger

logger = get_logger(__name__)


class MediaGroupUtils:
    """媒体组工具类 - 统一的媒体组处理逻辑"""
    
    @staticmethod
    def is_media_group_message(message: Any) -> bool:
        """检查是否为媒体组消息"""
        return (hasattr(message, 'media_group_id') and 
                message.media_group_id is not None)
    
    @staticmethod
    def get_media_group_id(message: Any) -> Optional[str]:
        """获取媒体组ID"""
        if MediaGroupUtils.is_media_group_message(message):
            return message.media_group_id
        return None
    
    @staticmethod
    def generate_filename_for_message(message: Any, extension: str = "") -> str:
        """
        为消息生成文件名
        
        Args:
            message: 消息对象
            extension: 文件扩展名
            
        Returns:
            生成的文件名
        """
        if MediaGroupUtils.is_media_group_message(message):
            # 媒体组消息：媒体组ID-消息ID.扩展名
            base_name = f"{message.media_group_id}-{message.id}"
        else:
            # 单条消息：msg-消息ID.扩展名
            base_name = f"msg-{message.id}"
        
        return f"{base_name}{extension}"
    
    @staticmethod
    def get_message_caption(message: Any) -> Optional[str]:
        """获取消息的说明文字"""
        if hasattr(message, 'caption') and message.caption:
            return message.caption
        elif hasattr(message, 'text') and message.text:
            return message.text
        return None
