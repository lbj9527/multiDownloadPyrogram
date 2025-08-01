"""
具体的任务分配策略实现
"""

import logging
from typing import List, Dict, Any

from .base import TaskDistributionStrategy, DistributionConfig
from models.message_group import (
    MessageGroupCollection,
    TaskDistributionResult,
    ClientTaskAssignment,
    MessageGroup
)

logger = logging.getLogger(__name__)

# 简单的消息验证器
class MessageValidator:
    @staticmethod
    def validate_message(message) -> bool:
        """简单的消息验证"""
        return message is not None and hasattr(message, 'id')


class MediaGroupAwareDistributionStrategy(TaskDistributionStrategy):
    """媒体组感知的分配策略"""
    
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str]
    ) -> TaskDistributionResult:
        """媒体组感知的任务分配"""

        # 验证输入
        errors = self.validate_inputs(message_collection, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")

        result = TaskDistributionResult(distribution_strategy="MediaGroupAwareDistribution")

        # 消息ID验证已在消息获取阶段完成，无需重复验证

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
        """根据估算大小找到负载最小的客户端"""
        # 使用估算大小作为负载均衡指标
        loads = [assignment.estimated_size for assignment in assignments]
        return loads.index(min(loads))




    def get_strategy_info(self) -> Dict[str, Any]:
        return {
            "name": "MediaGroupAwareDistribution",
            "description": "保持媒体组完整性的智能分配",
            "preserves_media_groups": True,
            "load_balance_quality": "good",
            "complexity": "medium"
        }



