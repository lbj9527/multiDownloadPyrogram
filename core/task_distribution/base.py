"""
任务分配策略基础类和接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

from models.message_group import MessageGroupCollection, TaskDistributionResult


class DistributionMode(Enum):
    """分配模式"""
    MEDIA_GROUP_AWARE = "media_group_aware"  # 媒体组感知分配


class LoadBalanceMetric(Enum):
    """负载均衡指标"""
    ESTIMATED_SIZE = "estimated_size"     # 按真实文件大小


@dataclass
class DistributionConfig:
    """分配配置"""
    mode: DistributionMode = DistributionMode.MEDIA_GROUP_AWARE
    load_balance_metric: LoadBalanceMetric = LoadBalanceMetric.ESTIMATED_SIZE
    prefer_large_groups_first: bool = True  # 优先分配大组
    enable_validation: bool = True  # 启用验证



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
            client: Pyrogram客户端（用于消息验证，可选）
            channel: 频道名称（用于消息验证，可选）

        Returns:
            任务分配结果
        """
        pass
    
    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        pass
    







