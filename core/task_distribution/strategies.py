"""
具体的任务分配策略实现
"""

import heapq
from typing import List, Dict, Any, Set
from utils import get_logger
from utils.message_validator import MessageValidator, MessageIdFilter

from .base import TaskDistributionStrategy, DistributionConfig, LoadBalanceMetric
from models.message_group import (
    MessageGroupCollection, 
    TaskDistributionResult, 
    ClientTaskAssignment,
    MessageGroup
)

logger = get_logger(__name__)


class RangeBasedDistributionStrategy(TaskDistributionStrategy):
    """基于范围的分配策略（原有方式）"""
    
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        client=None,
        channel: str = None
    ) -> TaskDistributionResult:
        """基于消息ID范围分配任务"""
        logger.info("使用基于范围的分配策略")
        
        # 验证输入
        errors = self.validate_inputs(message_collection, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")
        
        result = TaskDistributionResult(distribution_strategy="RangeBasedDistribution")
        
        # 获取所有消息并按ID排序
        all_messages = []
        for group in message_collection.media_groups.values():
            all_messages.extend(group.messages)
        all_messages.extend(message_collection.single_messages)
        
        # 按消息ID排序
        all_messages.sort(key=lambda msg: msg.id if msg and hasattr(msg, 'id') else 0)
        
        # 平均分配
        messages_per_client = len(all_messages) // len(client_names)
        remainder = len(all_messages) % len(client_names)
        
        start_idx = 0
        for i, client_name in enumerate(client_names):
            # 计算这个客户端应该处理的消息数量
            messages_count = messages_per_client + (1 if i < remainder else 0)
            end_idx = start_idx + messages_count
            
            # 创建客户端分配
            assignment = ClientTaskAssignment(client_name=client_name)
            
            # 将消息转换为单消息组
            for j in range(start_idx, min(end_idx, len(all_messages))):
                message = all_messages[j]
                if message:
                    single_group = MessageGroup(
                        group_id=f"range_{message.id}",
                        group_type="single_message"
                    )
                    single_group.add_message(message)
                    assignment.add_group(single_group)
            
            result.add_assignment(assignment)
            start_idx = end_idx
        
        logger.info(f"范围分配完成: {len(client_names)} 个客户端")
        return result
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            "name": "RangeBasedDistribution",
            "description": "按消息ID范围平均分配",
            "preserves_media_groups": False,
            "load_balance_quality": "good",
            "complexity": "low"
        }


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

        # 验证消息ID
        validator = MessageValidator()
        valid_ids, invalid_ids, validation_stats = await validator.validate_message_ids(
            client, channel, all_message_ids
        )

        if not invalid_ids:
            return message_collection
        valid_ids_set = set(valid_ids)

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


class LoadBalancedDistributionStrategy(TaskDistributionStrategy):
    """高级负载均衡分配策略"""
    
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        client=None,
        channel: str = None
    ) -> TaskDistributionResult:
        """高级负载均衡分配"""
        logger.info("使用高级负载均衡分配策略")
        
        # 验证输入
        errors = self.validate_inputs(message_collection, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")
        
        result = TaskDistributionResult(distribution_strategy="LoadBalancedDistribution")
        
        # 使用堆来维护客户端负载
        client_heap = []
        client_assignments = {}
        
        # 初始化客户端
        for i, client_name in enumerate(client_names):
            assignment = ClientTaskAssignment(client_name=client_name)
            client_assignments[i] = assignment
            # 堆中存储 (负载值, 客户端索引)
            heapq.heappush(client_heap, (0, i))
        
        # 获取所有组并排序
        all_groups = message_collection.get_all_groups()
        all_groups.sort(key=lambda g: self._calculate_group_weight(g), reverse=True)
        
        # 分配组
        for group in all_groups:
            # 获取当前负载最小的客户端
            current_load, client_idx = heapq.heappop(client_heap)
            
            # 分配组到该客户端
            assignment = client_assignments[client_idx]
            assignment.add_group(group)
            
            # 计算新的负载并重新加入堆
            new_load = self._calculate_assignment_load(assignment)
            heapq.heappush(client_heap, (new_load, client_idx))
        
        # 添加到结果
        for assignment in client_assignments.values():
            result.add_assignment(assignment)
        
        # 优化分配（可选）
        if self.config.max_imbalance_ratio < 1.0:
            result = await self._optimize_distribution(result)
        
        return result
    
    def _calculate_group_weight(self, group: MessageGroup) -> float:
        """计算组的权重"""
        metric = self.config.load_balance_metric
        
        if metric == LoadBalanceMetric.FILE_COUNT:
            return float(group.total_files)
        elif metric == LoadBalanceMetric.MESSAGE_COUNT:
            return float(len(group))
        elif metric == LoadBalanceMetric.ESTIMATED_SIZE:
            return float(group.estimated_size)
        else:  # MIXED
            return group.total_files * 0.6 + group.estimated_size / (1024*1024) * 0.4
    
    def _calculate_assignment_load(self, assignment: ClientTaskAssignment) -> float:
        """计算分配的负载"""
        metric = self.config.load_balance_metric
        
        if metric == LoadBalanceMetric.FILE_COUNT:
            return float(assignment.total_files)
        elif metric == LoadBalanceMetric.MESSAGE_COUNT:
            return float(assignment.total_messages)
        elif metric == LoadBalanceMetric.ESTIMATED_SIZE:
            return float(assignment.estimated_size)
        else:  # MIXED
            return assignment.total_files * 0.6 + assignment.estimated_size / (1024*1024) * 0.4
    
    async def _optimize_distribution(self, result: TaskDistributionResult) -> TaskDistributionResult:
        """优化分配结果"""
        # 这里可以实现更复杂的优化算法
        # 例如：组交换、负载重平衡等
        logger.debug("执行分配优化...")
        
        # 简单的优化：检查是否需要调整
        stats = result.get_load_balance_stats()
        if stats['file_balance_ratio'] < (1.0 - self.config.max_imbalance_ratio):
            logger.warning(f"负载不均衡比例 {stats['file_balance_ratio']:.3f} "
                          f"超过阈值 {1.0 - self.config.max_imbalance_ratio:.3f}")
        
        return result
    

    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) <= 1:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            "name": "LoadBalancedDistribution",
            "description": "高级负载均衡分配，支持多种均衡指标",
            "preserves_media_groups": True,
            "load_balance_quality": "excellent",
            "complexity": "high"
        }
