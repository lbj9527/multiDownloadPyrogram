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




class MediaGroupAwareDistributionStrategy(TaskDistributionStrategy):
    """媒体组感知的分配策略"""

    def __init__(self, config: DistributionConfig, preserve_structure: bool = False):
        super().__init__(config)
        self.preserve_structure = preserve_structure

    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str]
    ) -> TaskDistributionResult:
        """媒体组感知的任务分配"""

        # 验证输入
        if not client_names:
            raise ValueError("客户端列表不能为空")
        if message_collection.total_messages == 0:
            raise ValueError("消息集合为空")
        if len(client_names) != len(set(client_names)):
            raise ValueError("客户端名称列表包含重复项")

        if self.preserve_structure:
            return await self._distribute_with_structure_preservation(message_collection, client_names)
        else:
            return await self._distribute_traditional(message_collection, client_names)

    async def _distribute_traditional(self, message_collection: MessageGroupCollection,
                                    client_names: List[str]) -> TaskDistributionResult:
        """传统的媒体组感知分配"""
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

    async def _distribute_with_structure_preservation(self, message_collection: MessageGroupCollection,
                                                    client_names: List[str]) -> TaskDistributionResult:
        """结构保持的任务分配"""
        result = TaskDistributionResult(distribution_strategy="StructurePreservationDistribution")

        # 初始化客户端分配
        client_assignments = [
            ClientTaskAssignment(client_name=name) for name in client_names
        ]

        # 获取所有组
        all_groups = message_collection.get_all_groups()

        # 分离原始媒体组和单消息组
        original_groups = [g for g in all_groups if g.group_type == "original_media_group"]
        single_message_groups = [g for g in all_groups if g.group_type != "original_media_group"]

        # 优先分配原始媒体组（保持完整性）
        for group in original_groups:
            min_load_client_idx = self._find_min_load_client(client_assignments)
            client_assignments[min_load_client_idx].add_group(group)

            logger.debug(f"分配原始媒体组 {group.group_id} ({group.total_files}个文件) 到 {client_assignments[min_load_client_idx].client_name}")

        # 分配单消息组
        for group in single_message_groups:
            min_load_client_idx = self._find_min_load_client(client_assignments)
            client_assignments[min_load_client_idx].add_group(group)

        # 添加到结果
        for assignment in client_assignments:
            result.add_assignment(assignment)

        return result
    
    def _find_min_load_client(self, assignments: List[ClientTaskAssignment]) -> int:
        """根据真实文件大小找到负载最小的客户端"""
        # 使用真实文件大小作为负载均衡指标
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



