"""
任务分配相关配置
"""

import os
from typing import Dict, List, Optional
from enum import Enum

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    from dataclasses import dataclass, field
    PYDANTIC_AVAILABLE = False


# 导入核心模块中的枚举定义，避免重复
try:
    from core.task_distribution.base import DistributionMode as TaskDistributionMode, LoadBalanceMetric
except ImportError:
    # 如果导入失败，使用本地定义
    class TaskDistributionMode(str, Enum):
        """任务分配模式"""
        RANGE_BASED = "range_based"
        MEDIA_GROUP_AWARE = "media_group_aware"
        LOAD_BALANCED = "load_balanced"
        AUTO = "auto"  # 自动选择

    class LoadBalanceMetric(str, Enum):
        """负载均衡指标"""
        MESSAGE_COUNT = "message_count"
        FILE_COUNT = "file_count"
        ESTIMATED_SIZE = "estimated_size"
        MIXED = "mixed"


if PYDANTIC_AVAILABLE:
    class TaskDistributionConfig(BaseModel):
        """任务分配配置"""
        
        # 基础配置
        mode: TaskDistributionMode = Field(
            default=TaskDistributionMode.MEDIA_GROUP_AWARE,
            description="任务分配模式"
        )
        
        load_balance_metric: LoadBalanceMetric = Field(
            default=LoadBalanceMetric.FILE_COUNT,
            description="负载均衡指标"
        )
        
        max_imbalance_ratio: float = Field(
            default=0.3,
            description="最大不均衡比例",
            ge=0.0,
            le=1.0
        )
        
        prefer_large_groups_first: bool = Field(
            default=True,
            description="优先分配大组"
        )
        
        enable_validation: bool = Field(
            default=True,
            description="启用分配结果验证"
        )

        enable_message_id_validation: bool = Field(
            default=True,
            description="启用消息ID有效性验证"
        )
        
        # 高级配置
        batch_size: int = Field(
            default=200,
            description="消息批量获取大小",
            gt=0,
            le=1000
        )
        
        max_retries: int = Field(
            default=3,
            description="最大重试次数",
            ge=0,
            le=10
        )
        
        enable_strategy_comparison: bool = Field(
            default=False,
            description="启用策略比较模式"
        )
        
        auto_recommendation: bool = Field(
            default=True,
            description="启用自动策略推荐"
        )
        
        # 性能配置
        enable_parallel_grouping: bool = Field(
            default=True,
            description="启用并行分组"
        )
        
        grouping_timeout: float = Field(
            default=30.0,
            description="分组超时时间（秒）",
            gt=0
        )
        
        @classmethod
        def from_env(cls) -> 'TaskDistributionConfig':
            """从环境变量创建配置"""
            return cls(
                mode=TaskDistributionMode(
                    os.getenv('TASK_DISTRIBUTION_MODE', TaskDistributionMode.MEDIA_GROUP_AWARE)
                ),
                load_balance_metric=LoadBalanceMetric(
                    os.getenv('LOAD_BALANCE_METRIC', LoadBalanceMetric.FILE_COUNT)
                ),
                max_imbalance_ratio=float(
                    os.getenv('MAX_IMBALANCE_RATIO', '0.3')
                ),
                prefer_large_groups_first=os.getenv(
                    'PREFER_LARGE_GROUPS_FIRST', 'true'
                ).lower() == 'true',
                enable_validation=os.getenv(
                    'ENABLE_DISTRIBUTION_VALIDATION', 'true'
                ).lower() == 'true',
                enable_message_id_validation=os.getenv(
                    'ENABLE_MESSAGE_ID_VALIDATION', 'true'
                ).lower() == 'true',
                batch_size=int(os.getenv('BATCH_SIZE', '200')),
                max_retries=int(os.getenv('GROUPING_MAX_RETRIES', '3')),
                enable_strategy_comparison=os.getenv(
                    'ENABLE_STRATEGY_COMPARISON', 'false'
                ).lower() == 'true',
                auto_recommendation=os.getenv(
                    'AUTO_STRATEGY_RECOMMENDATION', 'true'
                ).lower() == 'true',
                enable_parallel_grouping=os.getenv(
                    'ENABLE_PARALLEL_GROUPING', 'true'
                ).lower() == 'true',
                grouping_timeout=float(os.getenv('GROUPING_TIMEOUT', '30.0'))
            )

else:
    @dataclass
    class TaskDistributionConfig:
        """任务分配配置（dataclass版本）"""
        
        # 基础配置
        mode: TaskDistributionMode = TaskDistributionMode.MEDIA_GROUP_AWARE
        load_balance_metric: LoadBalanceMetric = LoadBalanceMetric.FILE_COUNT
        max_imbalance_ratio: float = 0.3
        prefer_large_groups_first: bool = True
        enable_validation: bool = True
        enable_message_id_validation: bool = True
        
        # 高级配置
        batch_size: int = 200
        max_retries: int = 3
        enable_strategy_comparison: bool = False
        auto_recommendation: bool = True
        
        # 性能配置
        enable_parallel_grouping: bool = True
        grouping_timeout: float = 30.0
        
        @classmethod
        def from_env(cls) -> 'TaskDistributionConfig':
            """从环境变量创建配置"""
            return cls(
                mode=TaskDistributionMode(
                    os.getenv('TASK_DISTRIBUTION_MODE', TaskDistributionMode.MEDIA_GROUP_AWARE)
                ),
                load_balance_metric=LoadBalanceMetric(
                    os.getenv('LOAD_BALANCE_METRIC', LoadBalanceMetric.FILE_COUNT)
                ),
                max_imbalance_ratio=float(
                    os.getenv('MAX_IMBALANCE_RATIO', '0.3')
                ),
                prefer_large_groups_first=os.getenv(
                    'PREFER_LARGE_GROUPS_FIRST', 'true'
                ).lower() == 'true',
                enable_validation=os.getenv(
                    'ENABLE_DISTRIBUTION_VALIDATION', 'true'
                ).lower() == 'true',
                enable_message_id_validation=os.getenv(
                    'ENABLE_MESSAGE_ID_VALIDATION', 'true'
                ).lower() == 'true',
                batch_size=int(os.getenv('BATCH_SIZE', '200')),
                max_retries=int(os.getenv('GROUPING_MAX_RETRIES', '3')),
                enable_strategy_comparison=os.getenv(
                    'ENABLE_STRATEGY_COMPARISON', 'false'
                ).lower() == 'true',
                auto_recommendation=os.getenv(
                    'AUTO_STRATEGY_RECOMMENDATION', 'true'
                ).lower() == 'true',
                enable_parallel_grouping=os.getenv(
                    'ENABLE_PARALLEL_GROUPING', 'true'
                ).lower() == 'true',
                grouping_timeout=float(os.getenv('GROUPING_TIMEOUT', '30.0'))
            )
        
        def validate(self) -> List[str]:
            """验证配置"""
            errors = []
            
            if not 0 <= self.max_imbalance_ratio <= 1:
                errors.append("max_imbalance_ratio must be between 0 and 1")
            
            if self.batch_size <= 0 or self.batch_size > 1000:
                errors.append("batch_size must be between 1 and 1000")
            
            if self.max_retries < 0 or self.max_retries > 10:
                errors.append("max_retries must be between 0 and 10")
            
            if self.grouping_timeout <= 0:
                errors.append("grouping_timeout must be greater than 0")
            
            return errors
