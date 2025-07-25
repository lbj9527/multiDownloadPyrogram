"""
具体的任务分配策略实现
"""

import heapq
from typing import List, Dict, Any
from utils import get_logger

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
        client_names: List[str]
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
        client_names: List[str]
    ) -> TaskDistributionResult:
        """媒体组感知的任务分配"""
        logger.info("使用媒体组感知的分配策略")
        
        # 验证输入
        errors = self.validate_inputs(message_collection, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")
        
        result = TaskDistributionResult(distribution_strategy="MediaGroupAwareDistribution")
        
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
        
        # 记录分配统计
        self._log_distribution_stats(result)
        
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
    
    def _log_distribution_stats(self, result: TaskDistributionResult):
        """记录分配统计信息"""
        stats = result.get_load_balance_stats()
        logger.info(f"媒体组感知分配完成:")
        logger.info(f"  客户端数量: {stats['clients_count']}")
        logger.info(f"  文件分布: {stats['file_distribution']}")
        logger.info(f"  负载均衡比例: {stats['file_balance_ratio']:.3f}")
        
        for assignment in result.client_assignments:
            assignment_stats = assignment.get_statistics()
            logger.info(f"  {assignment.client_name}: {assignment_stats['total_files']} 文件, "
                       f"{assignment_stats['media_groups_count']} 媒体组")
    
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
        client_names: List[str]
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
        
        self._log_distribution_stats(result)
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
    
    def _log_distribution_stats(self, result: TaskDistributionResult):
        """记录分配统计信息"""
        stats = result.get_load_balance_stats()
        logger.info(f"高级负载均衡分配完成:")
        logger.info(f"  负载均衡得分: {stats['file_balance_ratio']:.3f}")
        logger.info(f"  文件分布标准差: {self._calculate_std(stats['file_distribution']):.2f}")
    
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
