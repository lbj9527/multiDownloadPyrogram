"""
任务分配器
统一管理不同的分配策略
"""

from typing import Dict, List, Any, Optional, Type
from utils import get_logger

from .base import (
    TaskDistributionStrategy, 
    DistributionConfig, 
    DistributionMode,
    DistributionValidator,
    DistributionMetrics
)
from .strategies import (
    RangeBasedDistributionStrategy,
    MediaGroupAwareDistributionStrategy,
    LoadBalancedDistributionStrategy
)
from models.message_group import MessageGroupCollection, TaskDistributionResult

logger = get_logger(__name__)


class TaskDistributor:
    """任务分配器"""
    
    def __init__(self, config: Optional[DistributionConfig] = None):
        self.config = config or DistributionConfig()
        self._strategies: Dict[DistributionMode, Type[TaskDistributionStrategy]] = {
            DistributionMode.RANGE_BASED: RangeBasedDistributionStrategy,
            DistributionMode.MEDIA_GROUP_AWARE: MediaGroupAwareDistributionStrategy,
            DistributionMode.LOAD_BALANCED: LoadBalancedDistributionStrategy
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
            
        Returns:
            任务分配结果
        """
        # 确定使用的策略
        mode = strategy_mode or self.config.mode
        strategy = self._get_strategy(mode)
        
        logger.info(f"开始任务分配，策略: {mode.value}, 客户端数量: {len(client_names)}")
        
        try:
            # 执行分配
            result = await strategy.distribute_tasks(message_collection, client_names)
            
            # 验证结果
            if self.config.enable_validation:
                validation_errors = DistributionValidator.validate_distribution_result(
                    result, message_collection
                )
                if validation_errors:
                    logger.warning(f"分配结果验证发现问题: {validation_errors}")
            
            # 计算指标
            metrics = DistributionMetrics.calculate_distribution_metrics(result)
            
            # 更新统计
            self._update_stats(result, mode, metrics)
            
            # 记录结果
            self._log_distribution_result(result, metrics)
            
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
    
    def register_strategy(
        self, 
        mode: DistributionMode, 
        strategy_class: Type[TaskDistributionStrategy]
    ):
        """注册自定义分配策略"""
        self._strategies[mode] = strategy_class
        logger.info(f"注册自定义分配策略: {mode.value}")
    
    def get_available_strategies(self) -> Dict[DistributionMode, Dict[str, Any]]:
        """获取可用的分配策略信息"""
        strategies_info = {}
        
        for mode, strategy_class in self._strategies.items():
            # 创建临时实例获取信息
            temp_strategy = strategy_class(self.config)
            strategies_info[mode] = temp_strategy.get_strategy_info()
        
        return strategies_info
    
    def _update_stats(
        self, 
        result: TaskDistributionResult, 
        mode: DistributionMode,
        metrics: Dict[str, Any]
    ):
        """更新统计信息"""
        self.stats["distributions_performed"] += 1
        self.stats["total_messages_distributed"] += result.total_messages
        
        # 更新平均均衡得分
        balance_score = metrics.get("balance_scores", {}).get("file_balance", 0.0)
        current_avg = self.stats["average_balance_score"]
        count = self.stats["distributions_performed"]
        self.stats["average_balance_score"] = (current_avg * (count - 1) + balance_score) / count
        
        # 更新策略使用统计
        strategy_name = mode.value
        if strategy_name not in self.stats["strategy_usage"]:
            self.stats["strategy_usage"][strategy_name] = 0
        self.stats["strategy_usage"][strategy_name] += 1
    
    def _log_distribution_result(
        self, 
        result: TaskDistributionResult, 
        metrics: Dict[str, Any]
    ):
        """记录分配结果"""
        logger.info("=" * 60)
        logger.info("📊 任务分配结果")
        logger.info("=" * 60)
        
        # 基础信息
        logger.info(f"分配策略: {result.distribution_strategy}")
        logger.info(f"客户端数量: {metrics['clients_count']}")
        logger.info(f"总文件数: {metrics['total_files']}")
        logger.info(f"总消息数: {metrics['total_messages']}")
        
        # 负载均衡信息
        balance_scores = metrics.get("balance_scores", {})
        logger.info(f"文件负载均衡: {balance_scores.get('file_balance', 0):.3f}")
        logger.info(f"大小负载均衡: {balance_scores.get('size_balance', 0):.3f}")
        
        # 客户端分配详情
        logger.info("-" * 60)
        for assignment in result.client_assignments:
            stats = assignment.get_statistics()
            logger.info(f"{assignment.client_name}: {stats['total_files']} 文件, "
                       f"{stats['media_groups_count']} 媒体组, "
                       f"{stats['estimated_size'] / (1024*1024):.1f} MB")
        
        logger.info("=" * 60)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分配器统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "distributions_performed": 0,
            "total_messages_distributed": 0,
            "average_balance_score": 0.0,
            "strategy_usage": {}
        }
    
    def get_current_strategy_info(self) -> Optional[Dict[str, Any]]:
        """获取当前策略信息"""
        if self._current_strategy:
            return self._current_strategy.get_strategy_info()
        return None
    
    async def compare_strategies(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        strategies: Optional[List[DistributionMode]] = None
    ) -> Dict[DistributionMode, Dict[str, Any]]:
        """
        比较不同分配策略的效果
        
        Args:
            message_collection: 消息集合
            client_names: 客户端名称列表
            strategies: 要比较的策略列表（可选）
            
        Returns:
            策略比较结果
        """
        if strategies is None:
            strategies = list(self._strategies.keys())
        
        comparison_results = {}
        
        for strategy_mode in strategies:
            try:
                logger.info(f"测试策略: {strategy_mode.value}")
                
                # 执行分配
                result = await self.distribute_tasks(
                    message_collection, client_names, strategy_mode
                )
                
                # 计算指标
                metrics = DistributionMetrics.calculate_distribution_metrics(result)
                
                # 获取策略信息
                strategy_info = self._get_strategy(strategy_mode).get_strategy_info()
                
                comparison_results[strategy_mode] = {
                    "strategy_info": strategy_info,
                    "metrics": metrics,
                    "result_summary": result.get_summary()
                }
                
            except Exception as e:
                logger.error(f"测试策略 {strategy_mode.value} 失败: {e}")
                comparison_results[strategy_mode] = {
                    "error": str(e)
                }
        
        return comparison_results
    
    def recommend_strategy(
        self,
        message_collection: MessageGroupCollection,
        client_names: List[str],
        priority: str = "balance"  # "balance", "speed", "integrity"
    ) -> DistributionMode:
        """
        推荐最适合的分配策略
        
        Args:
            message_collection: 消息集合
            client_names: 客户端名称列表
            priority: 优先级 ("balance": 负载均衡, "speed": 速度, "integrity": 完整性)
            
        Returns:
            推荐的分配策略
        """
        stats = message_collection.get_statistics()
        
        # 根据数据特征和优先级推荐策略
        if priority == "speed" and stats["media_groups_count"] == 0:
            # 没有媒体组且优先速度，使用范围分配
            return DistributionMode.RANGE_BASED
        elif priority == "integrity" or stats["media_groups_count"] > 0:
            # 有媒体组或优先完整性，使用媒体组感知
            return DistributionMode.MEDIA_GROUP_AWARE
        elif priority == "balance":
            # 优先负载均衡，使用高级负载均衡
            return DistributionMode.LOAD_BALANCED
        else:
            # 默认使用媒体组感知
            return DistributionMode.MEDIA_GROUP_AWARE
