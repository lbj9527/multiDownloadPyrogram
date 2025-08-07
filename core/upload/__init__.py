"""
上传模块
提供文件上传和批量上传功能
包含传统上传和分阶段上传两种方式
"""

from .upload_manager import UploadManager
from .batch_uploader import BatchUploader
from .upload_strategy import UploadStrategy

# 分阶段上传模块
from .staged import (
    StagedUploadManager, StagedUploadConfig, StagedUploadResult,
    DataSource, TelegramDataSource, MediaData, MediaType,
    TemporaryStorage, TelegramMeStorage, TemporaryMediaItem,
    MediaGroupManager, MediaGroupBatch,
    TargetDistributor, DistributionResult
)

__all__ = [
    # 传统上传
    'UploadManager',
    'BatchUploader',
    'UploadStrategy',

    # 分阶段上传
    'StagedUploadManager',
    'StagedUploadConfig',
    'StagedUploadResult',
    'DataSource',
    'TelegramDataSource',
    'MediaData',
    'MediaType',
    'TemporaryStorage',
    'TelegramMeStorage',
    'TemporaryMediaItem',
    'MediaGroupManager',
    'MediaGroupBatch',
    'TargetDistributor',
    'DistributionResult'
]
