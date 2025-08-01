"""
任务分配器
统一管理不同的分配策略
"""

import logging
from typing import Dict, List, Optional, Type

from .base import (
    TaskDistributionStrategy,
    DistributionConfig,
    DistributionMode
)
from .strategies import (
    MediaGroupAwareDistributionStrategy,
)
from models.message_group import MessageGroupCollection, TaskDistributionResult

logger = logging.getLogger(__name__)


class TaskDistributor:
    """任务分配器"""
    
    def __init__(self, config: Optional[DistributionConfig] = None):
        self.config = config or DistributionConfig()
        self._strategies: Dict[DistributionMode, Type[TaskDistributionStrategy]] = {
            DistributionMode.MEDIA_GROUP_AWARE: MediaGroupAwareDistributionStrategy,
        }
        self._current_strategy: Optional[TaskDistributionStrategy] = None
        self.stats = {
            "distributions_performed": 0,
            "total_messages_distributed": 0,
            "average_balance_score": 0.0,
            "strategy_usage": {}
        }
    
    async def distribute_tasks(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        strategy_mode: Optional[DistributionMode] = None
    ) -> TaskDistributionResult:
        """
        分配任务

        Args:
            message_collection: 消息集合
            client_names: 客户端名称列表
            strategy_mode: 分配策略模式（可选，默认使用配置中的模式）
            client: Pyrogram客户端（用于消息验证，可选）
            channel: 频道名称（用于消息验证，可选）

        Returns:
            任务分配结果
        """
        # 确定使用的策略
        mode = strategy_mode or self.config.mode
        strategy = self._get_strategy(mode)
        

        
        try:
            # 执行分配
            result = await strategy.distribute_tasks(
                message_collection, client_names
            )

            # 更新统计
            self._update_stats(result, mode)

            return result

        except Exception as e:
            logger.error(f"任务分配失败: {e}")
            raise
    
    def _get_strategy(self, mode: DistributionMode) -> TaskDistributionStrategy:
        """获取分配策略实例"""
        if mode not in self._strategies:
            raise ValueError(f"不支持的分配策略: {mode}")
        
        strategy_class = self._strategies[mode]
        strategy = strategy_class(self.config)
        self._current_strategy = strategy
        
        return strategy
    

    
    def _update_stats(
        self,
        result: TaskDistributionResult,
        mode: DistributionMode
    ):
        """更新统计信息"""
        self.stats["distributions_performed"] += 1
        self.stats["total_messages_distributed"] += result.total_messages

        # 更新策略使用统计
        strategy_name = mode.value
        if strategy_name not in self.stats["strategy_usage"]:
            self.stats["strategy_usage"][strategy_name] = 0
        self.stats["strategy_usage"][strategy_name] += 1
    

    

