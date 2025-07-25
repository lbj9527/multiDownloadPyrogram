"""
任务分配策略基础类和接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from models.message_group import MessageGroupCollection, TaskDistributionResult


class DistributionMode(Enum):
    """分配模式"""
    RANGE_BASED = "range_based"           # 基于范围的分配（原有方式）
    MEDIA_GROUP_AWARE = "media_group_aware"  # 媒体组感知分配
    LOAD_BALANCED = "load_balanced"       # 负载均衡分配
    CUSTOM = "custom"                     # 自定义分配


class LoadBalanceMetric(Enum):
    """负载均衡指标"""
    MESSAGE_COUNT = "message_count"       # 按消息数量
    FILE_COUNT = "file_count"            # 按文件数量
    ESTIMATED_SIZE = "estimated_size"     # 按估算大小
    MIXED = "mixed"                      # 混合指标


@dataclass
class DistributionConfig:
    """分配配置"""
    mode: DistributionMode = DistributionMode.MEDIA_GROUP_AWARE
    load_balance_metric: LoadBalanceMetric = LoadBalanceMetric.FILE_COUNT
    max_imbalance_ratio: float = 0.3  # 最大不均衡比例（0.3表示最大差异30%）
    prefer_large_groups_first: bool = True  # 优先分配大组
    enable_validation: bool = True  # 启用验证
    
    # 高级配置
    custom_weights: Dict[str, float] = field(default_factory=dict)
    client_preferences: Dict[str, List[str]] = field(default_factory=dict)  # 客户端偏好
    
    def __post_init__(self):
        """后初始化验证"""
        if not 0 <= self.max_imbalance_ratio <= 1:
            raise ValueError("max_imbalance_ratio must be between 0 and 1")


class TaskDistributionStrategy(ABC):
    """任务分配策略抽象基类"""
    
    def __init__(self, config: Optional[DistributionConfig] = None):
        self.config = config or DistributionConfig()
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str]
    ) -> TaskDistributionResult:
        """
        分配任务到客户端
        
        Args:
            message_collection: 消息集合
            client_names: 客户端名称列表
            
        Returns:
            任务分配结果
        """
        pass
    
    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        pass
    
    def validate_inputs(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str]
    ) -> List[str]:
        """验证输入参数"""
        errors = []
        
        if not client_names:
            errors.append("客户端列表不能为空")
        
        if message_collection.total_messages == 0:
            errors.append("消息集合为空")
        
        if len(client_names) != len(set(client_names)):
            errors.append("客户端名称列表包含重复项")
        
        return errors
    
    def calculate_load_balance_score(self, result: TaskDistributionResult) -> float:
        """计算负载均衡得分（0-1，1表示完全均衡）"""
        stats = result.get_load_balance_stats()
        return stats.get('file_balance_ratio', 0.0)


class DistributionValidator:
    """分配结果验证器"""
    
    @staticmethod
    def validate_distribution_result(
        result: TaskDistributionResult,
        original_collection: MessageGroupCollection
    ) -> List[str]:
        """验证分配结果"""
        errors = []
        
        # 检查消息总数是否匹配
        distributed_messages = sum(
            assignment.total_messages for assignment in result.client_assignments
        )
        if distributed_messages != original_collection.total_messages:
            errors.append(
                f"分配的消息总数({distributed_messages})与原始消息数({original_collection.total_messages})不匹配"
            )
        
        # 检查是否有空分配
        empty_assignments = [
            assignment.client_name for assignment in result.client_assignments
            if assignment.total_messages == 0
        ]
        if empty_assignments:
            errors.append(f"以下客户端分配为空: {empty_assignments}")
        
        # 检查媒体组完整性
        media_group_errors = DistributionValidator._validate_media_group_integrity(result)
        errors.extend(media_group_errors)
        
        return errors
    
    @staticmethod
    def _validate_media_group_integrity(result: TaskDistributionResult) -> List[str]:
        """验证媒体组完整性"""
        errors = []
        
        # 收集所有媒体组的分布情况
        media_group_distribution = {}
        
        for assignment in result.client_assignments:
            for group in assignment.message_groups:
                if group.is_media_group:
                    if group.group_id in media_group_distribution:
                        errors.append(
                            f"媒体组 {group.group_id} 被分配到多个客户端: "
                            f"{media_group_distribution[group.group_id]} 和 {assignment.client_name}"
                        )
                    else:
                        media_group_distribution[group.group_id] = assignment.client_name
        
        return errors


class DistributionMetrics:
    """分配指标计算器"""
    
    @staticmethod
    def calculate_distribution_metrics(result: TaskDistributionResult) -> Dict[str, Any]:
        """计算分配指标"""
        if not result.client_assignments:
            return {}
        
        # 基础指标
        file_counts = [assignment.total_files for assignment in result.client_assignments]
        message_counts = [assignment.total_messages for assignment in result.client_assignments]
        size_estimates = [assignment.estimated_size for assignment in result.client_assignments]
        
        # 计算各种指标
        metrics = {
            # 基础统计
            "clients_count": len(result.client_assignments),
            "total_files": sum(file_counts),
            "total_messages": sum(message_counts),
            "total_estimated_size": sum(size_estimates),
            
            # 分布统计
            "file_distribution": {
                "min": min(file_counts),
                "max": max(file_counts),
                "avg": sum(file_counts) / len(file_counts),
                "std": DistributionMetrics._calculate_std(file_counts)
            },
            
            # 均衡性指标
            "balance_scores": {
                "file_balance": min(file_counts) / max(file_counts) if max(file_counts) > 0 else 1.0,
                "message_balance": min(message_counts) / max(message_counts) if max(message_counts) > 0 else 1.0,
                "size_balance": min(size_estimates) / max(size_estimates) if max(size_estimates) > 0 else 1.0
            },
            
            # 效率指标
            "efficiency_score": DistributionMetrics._calculate_efficiency_score(result)
        }
        
        return metrics
    
    @staticmethod
    def _calculate_std(values: List[float]) -> float:
        """计算标准差"""
        if len(values) <= 1:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    @staticmethod
    def _calculate_efficiency_score(result: TaskDistributionResult) -> float:
        """计算效率得分"""
        # 这里可以根据具体需求实现效率计算逻辑
        # 例如：考虑媒体组完整性、负载均衡等因素
        balance_stats = result.get_load_balance_stats()
        file_balance = balance_stats.get('file_balance_ratio', 0.0)
        
        # 简单的效率得分：主要基于负载均衡
        return file_balance
