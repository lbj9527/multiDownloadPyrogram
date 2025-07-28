"""
消息ID验证器
用于验证消息ID的有效性，过滤无效的消息ID
"""

import asyncio
from typing import List, Dict, Any, Tuple, Set
from pyrogram import Client
from pyrogram.errors import FloodWait

from utils import get_logger, retry_async
from config.constants import SUPPORTED_MEDIA_TYPES

logger = get_logger(__name__)


class MessageValidator:
    """消息ID验证器"""
    
    def __init__(self, batch_size: int = 200):
        """
        初始化验证器
        
        Args:
            batch_size: 批次大小，默认200（Pyrogram限制）
        """
        self.batch_size = batch_size
        self.stats = {
            "total_checked": 0,
            "valid_messages": 0,
            "invalid_messages": 0,
            "api_calls": 0,
            "validation_time": 0.0
        }
    
    async def validate_message_ids(
        self,
        client: Client,
        channel: str,
        message_ids: List[int]
    ) -> Tuple[List[int], List[int], Dict[str, Any]]:
        """
        验证消息ID列表的有效性
        
        Args:
            client: Pyrogram客户端
            channel: 频道名称
            message_ids: 要验证的消息ID列表
            
        Returns:
            (有效消息ID列表, 无效消息ID列表, 验证统计信息)
        """
        import time
        start_time = time.time()
        
        valid_ids = []
        invalid_ids = []
        
        # 重置统计
        self.stats["total_checked"] = len(message_ids)
        self.stats["api_calls"] = 0
        
        # 分批验证
        for i in range(0, len(message_ids), self.batch_size):
            batch_ids = message_ids[i:i + self.batch_size]
            
            try:
                batch_valid, batch_invalid = await self._validate_batch(
                    client, channel, batch_ids
                )
                
                valid_ids.extend(batch_valid)
                invalid_ids.extend(batch_invalid)
                

                
                # 避免过于频繁的API调用
                if i + self.batch_size < len(message_ids):
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                # 将整个批次标记为无效
                invalid_ids.extend(batch_ids)
        
        # 更新统计
        self.stats["valid_messages"] = len(valid_ids)
        self.stats["invalid_messages"] = len(invalid_ids)
        self.stats["validation_time"] = time.time() - start_time
        

        
        return valid_ids, invalid_ids, self.stats.copy()
    
    @retry_async(max_retries=3, delay=1.0)
    async def _validate_batch(
        self,
        client: Client,
        channel: str,
        message_ids: List[int]
    ) -> Tuple[List[int], List[int]]:
        """
        验证一批消息ID
        
        Args:
            client: Pyrogram客户端
            channel: 频道名称
            message_ids: 消息ID列表
            
        Returns:
            (有效消息ID列表, 无效消息ID列表)
        """
        try:
            self.stats["api_calls"] += 1
            
            # 使用get_messages批量获取消息
            messages = await client.get_messages(channel, message_ids)
            
            # 确保返回列表
            if not isinstance(messages, list):
                messages = [messages] if messages else []
            
            # 验证每个消息
            valid_ids = []
            invalid_ids = []
            
            for i, message in enumerate(messages):
                message_id = message_ids[i]
                
                if self._is_valid_message(message):
                    valid_ids.append(message_id)
                else:
                    invalid_ids.append(message_id)
            
            return valid_ids, invalid_ids
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            raise  # 重新抛出异常以触发重试
        except Exception as e:
            # 返回所有消息为无效
            return [], message_ids
    
    def _is_valid_message(self, message: Any) -> bool:
        """
        判断消息是否有效
        
        根据以下规则判断：
        1. 消息不为None（存在）
        2. 消息有ID属性
        3. 对于非纯文本消息，必须包含媒体或文本内容
        
        Args:
            message: 消息对象
            
        Returns:
            消息是否有效
        """
        # 基本存在性检查
        if message is None:
            return False
        
        # 检查是否有ID
        if not hasattr(message, 'id') or message.id is None:
            return False
        
        # 检查消息内容
        has_text = hasattr(message, 'text') and message.text
        has_caption = hasattr(message, 'caption') and message.caption
        has_media = self._has_media(message)
        
        # 消息必须有文本、说明文字或媒体内容之一
        if not (has_text or has_caption or has_media):
            return False
        
        return True
    
    def _has_media(self, message: Any) -> bool:
        """
        检查消息是否包含媒体
        
        Args:
            message: 消息对象
            
        Returns:
            是否包含媒体
        """
        if not message:
            return False
        
        # 检查通用media属性
        if hasattr(message, 'media') and message.media:
            return True
        
        # 检查具体的媒体类型
        for media_type in SUPPORTED_MEDIA_TYPES:
            if hasattr(message, media_type) and getattr(message, media_type):
                return True
        
        return False
    
    def get_validation_report(self) -> str:
        """
        获取验证报告
        
        Returns:
            格式化的验证报告
        """
        if self.stats["total_checked"] == 0:
            return "尚未进行消息验证"
        
        valid_rate = (self.stats["valid_messages"] / self.stats["total_checked"]) * 100
        
        report = [
            "📊 消息ID验证报告",
            "=" * 40,
            f"总检查数量: {self.stats['total_checked']}",
            f"有效消息: {self.stats['valid_messages']} ({valid_rate:.1f}%)",
            f"无效消息: {self.stats['invalid_messages']} ({100-valid_rate:.1f}%)",
            f"API调用次数: {self.stats['api_calls']}",
            f"验证耗时: {self.stats['validation_time']:.2f} 秒",
            "=" * 40
        ]
        
        return "\n".join(report)
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_checked": 0,
            "valid_messages": 0,
            "invalid_messages": 0,
            "api_calls": 0,
            "validation_time": 0.0
        }


class MessageIdFilter:
    """消息ID过滤器 - 用于在分配前过滤无效消息ID"""
    
    @staticmethod
    def filter_message_ids_from_groups(
        message_groups: List[Any],
        valid_message_ids: Set[int]
    ) -> List[Any]:
        """
        从消息组中过滤出有效的消息ID
        
        Args:
            message_groups: 消息组列表
            valid_message_ids: 有效消息ID集合
            
        Returns:
            过滤后的消息组列表
        """
        filtered_groups = []
        
        for group in message_groups:
            # 过滤组内的消息
            valid_messages = []
            for message in group.messages:
                if hasattr(message, 'id') and message.id in valid_message_ids:
                    valid_messages.append(message)
            
            # 如果组内还有有效消息，则保留该组
            if valid_messages:
                # 创建新的组对象，只包含有效消息
                from models.message_group import MessageGroup
                filtered_group = MessageGroup(
                    group_id=group.group_id,
                    group_type=group.group_type
                )
                filtered_group.messages = valid_messages
                filtered_group.total_files = len(valid_messages)
                
                # 重新计算估算大小
                filtered_group.estimated_size = 0
                for message in valid_messages:
                    filtered_group._update_estimated_size(message)
                
                filtered_groups.append(filtered_group)
        
        return filtered_groups
    
    @staticmethod
    def filter_single_messages(
        single_messages: List[Any],
        valid_message_ids: Set[int]
    ) -> List[Any]:
        """
        过滤单条消息列表
        
        Args:
            single_messages: 单条消息列表
            valid_message_ids: 有效消息ID集合
            
        Returns:
            过滤后的单条消息列表
        """
        return [
            message for message in single_messages
            if hasattr(message, 'id') and message.id in valid_message_ids
        ]
