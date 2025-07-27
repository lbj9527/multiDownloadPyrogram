"""
任务分配模块
提供不同的任务分配策略
"""

from .base import TaskDistributionStrategy, DistributionConfig, DistributionMode
from .strategies import (
    MediaGroupAwareDistributionStrategy,
)
from .distributor import TaskDistributor

__all__ = [
    'TaskDistributionStrategy',
    'DistributionConfig',
    'DistributionMode',
    'MediaGroupAwareDistributionStrategy',
    'TaskDistributor'
]
