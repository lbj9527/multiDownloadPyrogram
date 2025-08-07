"""
消息分组器
"""

from typing import List, Dict, Any
import logging
from models.message_group import MessageGroup, MessageGroupCollection
from utils.logging_utils import LoggerMixin

logger = logging.getLogger(__name__)

# 简单的媒体组检查函数
def is_media_group_message(message) -> bool:
    """检查是否为媒体组消息"""
    return hasattr(message, 'media_group_id') and message.media_group_id is not None


class MessageGrouper(LoggerMixin):
    """消息分组器"""

    def __init__(self, preserve_structure: bool = False):
        self.preserve_structure = preserve_structure

    def group_messages_from_list(self, messages: List[Any]) -> MessageGroupCollection:
        """
        从已获取的消息列表进行媒体组分析

        Args:
            messages: 消息对象列表

        Returns:
            消息组集合
        """
        self.log_info(f"开始分析 {len(messages)} 条消息的媒体组")

        # 根据配置选择分组策略
        if self.preserve_structure:
            collection = self._group_with_structure_preservation(messages)
        else:
            collection = self._group_messages(messages)

        # 记录统计信息
        stats = collection.get_statistics()
        self.log_info(f"媒体组分析完成: {stats['media_groups_count']} 个媒体组, {stats['single_messages_count']} 条单独消息")

        return collection

    def _group_messages(self, messages: List[Any]) -> MessageGroupCollection:
        """将消息按媒体组分组"""
        collection = MessageGroupCollection()
        media_groups_dict: Dict[str, MessageGroup] = {}
        
        for message in messages:
            if not message:
                continue
            
            if is_media_group_message(message):
                # 媒体组消息
                group_id = message.media_group_id
                
                if group_id not in media_groups_dict:
                    media_groups_dict[group_id] = MessageGroup(
                        group_id=group_id,
                        group_type="media_group"
                    )
                
                media_groups_dict[group_id].add_message(message)
            else:
                # 单条消息
                collection.add_single_message(message)
        
        # 添加所有媒体组到集合
        for group in media_groups_dict.values():
            collection.add_media_group(group)
        

        self.log_info(f"发现 {len(media_groups_dict)} 个媒体组，{len(collection.single_messages)} 条单消息")

        return collection

    def _group_with_structure_preservation(self, messages: List[Any]) -> MessageGroupCollection:
        """保持结构的消息分组"""
        collection = MessageGroupCollection()
        media_groups_dict: Dict[str, MessageGroup] = {}

        for message in messages:
            if not message or not hasattr(message, '_structure_info'):
                continue

            structure_info = message._structure_info

            if structure_info.is_single and structure_info.has_media:
                # 单条媒体消息
                collection.add_single_message(message)
            elif structure_info.is_group_member and structure_info.has_media:
                # 媒体组消息
                group_id = structure_info.group_id

                if group_id not in media_groups_dict:
                    media_groups_dict[group_id] = MessageGroup(
                        group_id=group_id,
                        group_type="original_media_group"  # 新类型：原始媒体组
                    )

                media_groups_dict[group_id].add_message(message)
            # 非媒体消息被忽略

        # 添加所有媒体组到集合
        for group in media_groups_dict.values():
            collection.add_media_group(group)

        self.log_info(f"结构保持模式: 发现 {len(media_groups_dict)} 个原始媒体组，{len(collection.single_messages)} 条单消息")

        return collection
