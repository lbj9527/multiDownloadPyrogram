"""
接口层模块
为未来的UI、API等提供统一的接口
"""

from .download_interface import DownloadInterface
from .core_interfaces import (
    MessageProcessorInterface,
    UploadHandlerInterface,
    FileProcessorInterface,
    NullUploadHandler,
    ProcessResult
)

__all__ = [
    'DownloadInterface',
    'MessageProcessorInterface',
    'UploadHandlerInterface',
    'FileProcessorInterface',
    'NullUploadHandler',
    'ProcessResult'
]
