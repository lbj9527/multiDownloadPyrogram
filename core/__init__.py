"""
核心业务模块
包含消息处理、客户端管理、下载处理、任务分配等核心逻辑
"""

# 模块化导入
from .message import MessageFetcher, MessageGrouper, MessageProcessor
from .client import ClientManager, SessionManager
from .download import DownloadManager, StreamDownloader, RawDownloader
from .task_distribution import TaskDistributor, DistributionConfig, DistributionMode

__all__ = [
    # 消息处理
    'MessageGrouper',
    'MessageFetcher',
    'MessageProcessor',

    # 客户端管理
    'ClientManager',
    'SessionManager',

    # 下载处理
    'DownloadManager',
    'StreamDownloader',
    'RawDownloader',

    # 任务分配
    'TaskDistributor',
    'DistributionConfig',
    'DistributionMode'
]
