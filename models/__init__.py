"""
数据模型模块
定义应用程序中使用的所有数据结构
"""

from .download_task import DownloadTask, TaskRange, TaskResult, TaskStatus
from .client_info import ClientInfo, ClientStatus
from .file_info import FileInfo, MediaInfo, CompressionInfo, FileType, CompressionType

__all__ = [
    'DownloadTask',
    'TaskRange',
    'TaskResult',
    'TaskStatus',
    'ClientInfo',
    'ClientStatus',
    'FileInfo',
    'MediaInfo',
    'CompressionInfo',
    'FileType',
    'CompressionType'
]
