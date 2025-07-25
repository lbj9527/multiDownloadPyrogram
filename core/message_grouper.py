"""
消息分组器
负责从Telegram获取消息并按媒体组进行分组
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pyrogram import Client
from pyrogram.errors import FloodWait

from models.message_group import MessageGroup, MessageGroupCollection
from utils import get_logger, retry_async

logger = get_logger(__name__)


class MessageGrouper:
    """消息分组器"""
    
    def __init__(self, batch_size: int = 200, max_retries: int = 3):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.stats = {
            "total_messages_fetched": 0,
            "failed_messages": 0,
            "media_groups_found": 0,
            "single_messages_found": 0,
            "api_calls_made": 0
        }
    
    async def group_messages_from_range(
        self,
        client: Client,
        channel: str,
        start_message_id: int,
        end_message_id: int
    ) -> MessageGroupCollection:
        """
        从消息范围获取并分组消息
        
        Args:
            client: Pyrogram客户端
            channel: 频道名称
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            
        Returns:
            消息组集合
        """
        logger.info(f"开始分组消息范围: {start_message_id}-{end_message_id}")
        
        # 获取所有消息
        all_messages = await self._fetch_messages_in_batches(
            client, channel, start_message_id, end_message_id
        )
        
        # 分组消息
        collection = self._group_messages(all_messages)
        
        # 记录统计信息
        stats = collection.get_statistics()
        logger.info(f"消息分组完成: {stats}")
        
        return collection
    
    async def _fetch_messages_in_batches(
        self,
        client: Client,
        channel: str,
        start_message_id: int,
        end_message_id: int
    ) -> List[Any]:
        """分批获取消息"""
        all_messages = []
        message_ids = list(range(start_message_id, end_message_id + 1))
        
        logger.info(f"需要获取 {len(message_ids)} 条消息，分 {len(message_ids) // self.batch_size + 1} 批")
        
        for i in range(0, len(message_ids), self.batch_size):
            batch_ids = message_ids[i:i + self.batch_size]
            batch_messages = await self._fetch_message_batch_with_retry(
                client, channel, batch_ids
            )
            all_messages.extend(batch_messages)
            
            # 显示进度
            progress = (i + len(batch_ids)) / len(message_ids) * 100
            logger.info(f"消息获取进度: {progress:.1f}% ({i + len(batch_ids)}/{len(message_ids)})")
            
            # 避免过于频繁的API调用
            if i + self.batch_size < len(message_ids):
                await asyncio.sleep(0.1)
        
        # 过滤None消息
        valid_messages = [msg for msg in all_messages if msg is not None]
        failed_count = len(all_messages) - len(valid_messages)
        
        self.stats["total_messages_fetched"] = len(valid_messages)
        self.stats["failed_messages"] = failed_count
        
        if failed_count > 0:
            logger.warning(f"有 {failed_count} 条消息获取失败")
        
        return valid_messages
    
    @retry_async(max_retries=3, delay=1.0)
    async def _fetch_message_batch_with_retry(
        self,
        client: Client,
        channel: str,
        message_ids: List[int]
    ) -> List[Any]:
        """带重试的批量获取消息"""
        try:
            self.stats["api_calls_made"] += 1
            messages = await client.get_messages(channel, message_ids)
            
            # 确保返回列表
            if not isinstance(messages, list):
                messages = [messages] if messages else []
            
            return messages
            
        except FloodWait as e:
            logger.warning(f"遇到限流，等待 {e.value} 秒")
            await asyncio.sleep(e.value)
            raise  # 重新抛出异常以触发重试
        except Exception as e:
            logger.error(f"获取消息批次失败: {e}")
            # 返回对应数量的None，保持索引对应关系
            return [None] * len(message_ids)
    
    def _group_messages(self, messages: List[Any]) -> MessageGroupCollection:
        """将消息按媒体组分组"""
        collection = MessageGroupCollection()
        media_groups_dict: Dict[str, MessageGroup] = {}
        
        for message in messages:
            if not message:
                continue
            
            if self._is_media_group_message(message):
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
        
        # 更新统计
        self.stats["media_groups_found"] = len(media_groups_dict)
        self.stats["single_messages_found"] = len(collection.single_messages)
        
        logger.info(f"发现 {len(media_groups_dict)} 个媒体组，{len(collection.single_messages)} 条单消息")
        
        return collection
    
    def _is_media_group_message(self, message: Any) -> bool:
        """检查是否为媒体组消息"""
        return (hasattr(message, 'media_group_id') and 
                message.media_group_id is not None)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_messages_fetched": 0,
            "failed_messages": 0,
            "media_groups_found": 0,
            "single_messages_found": 0,
            "api_calls_made": 0
        }


class MessageGroupValidator:
    """消息组验证器"""
    
    @staticmethod
    def validate_message_group(group: MessageGroup) -> List[str]:
        """验证消息组"""
        errors = []
        
        if not group.messages:
            errors.append(f"消息组 {group.group_id} 为空")
        
        if group.is_media_group:
            # 验证媒体组的一致性
            group_ids = set()
            for message in group.messages:
                if hasattr(message, 'media_group_id'):
                    group_ids.add(message.media_group_id)
            
            if len(group_ids) > 1:
                errors.append(f"媒体组 {group.group_id} 包含不同的group_id: {group_ids}")
            
            if group.group_id not in group_ids:
                errors.append(f"媒体组 {group.group_id} 的group_id不匹配")
        
        return errors
    
    @staticmethod
    def validate_message_collection(collection: MessageGroupCollection) -> List[str]:
        """验证消息集合"""
        errors = []
        
        # 验证每个媒体组
        for group in collection.media_groups.values():
            group_errors = MessageGroupValidator.validate_message_group(group)
            errors.extend(group_errors)
        
        # 检查重复消息
        all_message_ids = set()
        for group in collection.media_groups.values():
            for message in group.messages:
                if message and hasattr(message, 'id'):
                    if message.id in all_message_ids:
                        errors.append(f"发现重复消息ID: {message.id}")
                    all_message_ids.add(message.id)
        
        for message in collection.single_messages:
            if message and hasattr(message, 'id'):
                if message.id in all_message_ids:
                    errors.append(f"发现重复消息ID: {message.id}")
                all_message_ids.add(message.id)
        
        return errors
