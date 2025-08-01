"""
配置管理模块
提供统一的配置管理和常量定义
"""

from .settings import AppConfig, TelegramConfig, DownloadConfig
from .constants import *

__all__ = [
    'AppConfig',
    'TelegramConfig', 
    'DownloadConfig',
    # 常量会在constants.py中定义
]
