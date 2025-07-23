"""
配置模块
提供应用程序的所有配置信息
"""

from .settings import AppSettings, app_settings
from .constants import *

__all__ = [
    'AppSettings',
    'app_settings',
    'DEFAULT_BATCH_SIZE',
    'MAX_CONCURRENT_DOWNLOADS',
    'SUPPORTED_MEDIA_TYPES',
    'FILE_EXTENSIONS'
]
