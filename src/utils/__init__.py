"""
工具模块包
包含配置管理、日志记录、异常处理等工具功能
"""

from .config import AppConfig, get_config, init_config
from .logger import get_logger, get_download_logger, setup_pyrogram_logging
from .exceptions import (
    MultiDownloadError, ConfigurationError, ClientError,
    DownloadError, NetworkError, RateLimitError,
    handle_pyrogram_exception, is_retryable_error, get_retry_delay
)

__all__ = [
    # 配置管理
    "AppConfig",
    "get_config", 
    "init_config",
    
    # 日志管理
    "get_logger",
    "get_download_logger",
    "setup_pyrogram_logging",
    
    # 异常处理
    "MultiDownloadError",
    "ConfigurationError",
    "ClientError",
    "DownloadError",
    "NetworkError", 
    "RateLimitError",
    "handle_pyrogram_exception",
    "is_retryable_error",
    "get_retry_delay"
] 