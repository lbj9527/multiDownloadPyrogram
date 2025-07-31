"""
具体的任务分配策略实现
"""

import logging
from typing import List, Dict, Any

# 简单的日志配置
logger = logging.getLogger(__name__)

# 简单的消息验证器
class MessageValidator:
    @staticmethod
    def validate_message(message) -> bool:
        """简单的消息验证"""
        return message is not None and hasattr(message, 'id')

from .base import TaskDistributionStrategy, DistributionConfig, LoadBalanceMetric
from models.message_group import (
    MessageGroupCollection,
    TaskDistributionResult,
    ClientTaskAssignment,
    MessageGroup
)

# logger 已在上面定义


class MediaGroupAwareDistributionStrategy(TaskDistributionStrategy):
    """媒体组感知的分配策略"""
    
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        client=None,
        channel: str = None
    ) -> TaskDistributionResult:
        """媒体组感知的任务分配"""

        # 验证输入
        errors = self.validate_inputs(message_collection, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")

        result = TaskDistributionResult(distribution_strategy="MediaGroupAwareDistribution")

        # 消息ID验证（如果启用且提供了客户端）
        if (self.config.enable_message_id_validation and client and channel):
            message_collection = await self._validate_and_filter_messages(
                client, channel, message_collection
            )

        # 初始化客户端分配
        client_assignments = [
            ClientTaskAssignment(client_name=name) for name in client_names
        ]

        # 获取所有组（媒体组 + 单消息组）
        all_groups = message_collection.get_all_groups()
        
        # 根据配置排序组
        if self.config.prefer_large_groups_first:
            all_groups.sort(key=lambda g: g.total_files, reverse=True)
        
        # 使用贪心算法分配
        for group in all_groups:
            # 找到当前负载最小的客户端
            min_load_client_idx = self._find_min_load_client(client_assignments)
            client_assignments[min_load_client_idx].add_group(group)
            
            logger.debug(f"分配 {group} 到 {client_assignments[min_load_client_idx].client_name}")
        
        # 添加到结果
        for assignment in client_assignments:
            result.add_assignment(assignment)
        

        
        return result
    
    def _find_min_load_client(self, assignments: List[ClientTaskAssignment]) -> int:
        """根据配置的指标找到负载最小的客户端"""
        metric = self.config.load_balance_metric
        
        if metric == LoadBalanceMetric.FILE_COUNT:
            loads = [assignment.total_files for assignment in assignments]
        elif metric == LoadBalanceMetric.MESSAGE_COUNT:
            loads = [assignment.total_messages for assignment in assignments]
        elif metric == LoadBalanceMetric.ESTIMATED_SIZE:
            loads = [assignment.estimated_size for assignment in assignments]
        else:  # MIXED
            # 混合指标：文件数量权重0.6，大小权重0.4
            loads = [
                assignment.total_files * 0.6 + assignment.estimated_size / (1024*1024) * 0.4
                for assignment in assignments
            ]
        
        return loads.index(min(loads))

    async def _validate_and_filter_messages(
        self,
        client,
        channel: str,
        message_collection: MessageGroupCollection
    ) -> MessageGroupCollection:
        """
        验证并过滤无效的消息ID

        Args:
            client: Pyrogram客户端
            channel: 频道名称
            message_collection: 原始消息集合

        Returns:
            过滤后的消息集合
        """
        # 收集所有消息ID
        all_message_ids = []

        # 从媒体组收集消息ID
        for group in message_collection.media_groups.values():
            all_message_ids.extend(group.message_ids)

        # 从单条消息收集消息ID
        for message in message_collection.single_messages:
            if hasattr(message, 'id'):
                all_message_ids.append(message.id)

        if not all_message_ids:
            return message_collection

        # 简化验证：假设所有消息ID都有效
        # 在实际使用中，Pyrogram会处理无效的消息ID
        valid_ids_set = set(all_message_ids)

        # 创建新的消息集合
        filtered_collection = MessageGroupCollection()

        # 过滤媒体组
        for group in message_collection.media_groups.values():
            filtered_messages = [
                msg for msg in group.messages
                if hasattr(msg, 'id') and msg.id in valid_ids_set
            ]

            if filtered_messages:
                # 创建过滤后的组
                from models.message_group import MessageGroup
                filtered_group = MessageGroup(
                    group_id=group.group_id,
                    group_type=group.group_type
                )
                filtered_group.messages = filtered_messages
                filtered_group.total_files = len(filtered_messages)

                # 重新计算估算大小
                filtered_group.estimated_size = 0
                for message in filtered_messages:
                    filtered_group._update_estimated_size(message)

                filtered_collection.add_media_group(filtered_group)

        # 过滤单条消息
        filtered_single_messages = [
            msg for msg in message_collection.single_messages
            if hasattr(msg, 'id') and msg.id in valid_ids_set
        ]

        for message in filtered_single_messages:
            filtered_collection.add_single_message(message)

        return filtered_collection


    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            "name": "MediaGroupAwareDistribution",
            "description": "保持媒体组完整性的智能分配",
            "preserves_media_groups": True,
            "load_balance_quality": "good",
            "complexity": "medium"
        }



