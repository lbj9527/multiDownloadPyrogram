"""
分阶段上传模块
支持先上传到临时存储，再批量分发到目标频道的上传方式
"""

from .data_source import DataSource, TelegramDataSource, MediaData, MediaType
from .temporary_storage import TemporaryStorage, TelegramMeStorage, TemporaryMediaItem
from .media_group_manager import MediaGroupManager, MediaGroupBatch
from .target_distributor import TargetDistributor, DistributionResult
from .staged_upload_manager import StagedUploadManager, StagedUploadConfig, StagedUploadResult

__all__ = [
    # 数据源
    'DataSource',
    'TelegramDataSource', 
    'MediaData',
    'MediaType',
    
    # 临时存储
    'TemporaryStorage',
    'TelegramMeStorage',
    'TemporaryMediaItem',
    
    # 媒体组管理
    'MediaGroupManager',
    'MediaGroupBatch',
    
    # 目标分发
    'TargetDistributor',
    'DistributionResult',
    
    # 主管理器
    'StagedUploadManager',
    'StagedUploadConfig',
    'StagedUploadResult'
]
