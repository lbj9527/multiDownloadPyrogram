"""
上传单元模块
定义上传的基本单元和相关类型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum
import time

from .temporary_storage import TemporaryMediaItem


class UploadUnitType(Enum):
    """上传单元类型"""
    SINGLE_MESSAGE = "single_message"      # 单条消息
    ORIGINAL_GROUP = "original_group"      # 原始媒体组
    BATCH_GROUP = "batch_group"           # 批量组（传统模式）


@dataclass
class UploadUnit:
    """上传单元（替代MediaGroupBatch）"""
    unit_type: UploadUnitType
    items: List[TemporaryMediaItem]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_time: float = field(default_factory=time.time)
    
    def get_total_size(self) -> int:
        """获取总大小"""
        return sum(item.media_data.file_size for item in self.items)
    
    def get_item_count(self) -> int:
        """获取项目数量"""
        return len(self.items)
    
    def is_valid_for_telegram(self) -> bool:
        """检查是否符合Telegram API限制"""
        return len(self.items) <= 10  # Telegram媒体组最大10个文件
    
    def is_single_message(self) -> bool:
        """是否为单条消息"""
        return self.unit_type == UploadUnitType.SINGLE_MESSAGE
    
    def is_media_group(self) -> bool:
        """是否为媒体组"""
        return self.unit_type in [UploadUnitType.ORIGINAL_GROUP, UploadUnitType.BATCH_GROUP]
    
    def get_description(self) -> str:
        """获取描述信息"""
        if self.unit_type == UploadUnitType.SINGLE_MESSAGE:
            return f"单条消息({self.get_item_count()}个文件)"
        elif self.unit_type == UploadUnitType.ORIGINAL_GROUP:
            group_id = self.metadata.get("original_group_id", "unknown")
            return f"原始媒体组({group_id}, {self.get_item_count()}个文件)"
        elif self.unit_type == UploadUnitType.BATCH_GROUP:
            group_type = self.metadata.get("group_type", "unknown")
            return f"批量组({group_type}, {self.get_item_count()}个文件)"
        else:
            return f"未知类型({self.get_item_count()}个文件)"
    
    def __str__(self) -> str:
        return f"UploadUnit({self.get_description()})"


def create_single_message_unit(item: TemporaryMediaItem, **metadata) -> UploadUnit:
    """创建单条消息上传单元"""
    return UploadUnit(
        unit_type=UploadUnitType.SINGLE_MESSAGE,
        items=[item],
        metadata={**metadata, "preserve_single": True}
    )


def create_original_group_unit(items: List[TemporaryMediaItem], group_id: str, **metadata) -> UploadUnit:
    """创建原始媒体组上传单元"""
    return UploadUnit(
        unit_type=UploadUnitType.ORIGINAL_GROUP,
        items=items,
        metadata={
            **metadata,
            "original_group_id": group_id,
            "preserve_structure": True,
            "item_count": len(items)
        }
    )


def create_batch_group_unit(items: List[TemporaryMediaItem], group_type: str, **metadata) -> UploadUnit:
    """创建批量组上传单元"""
    return UploadUnit(
        unit_type=UploadUnitType.BATCH_GROUP,
        items=items,
        metadata={
            **metadata,
            "group_type": group_type,
            "batch_mode": True,
            "item_count": len(items)
        }
    )
