"""
数据模型模块
定义应用程序中使用的所有数据结构
"""

from .message_group import MessageGroup, MessageGroupCollection
from .download_result import DownloadResult
from .template_config import TemplateConfig, TemplateVariable, TemplateMode, VariableType
from .upload_task import UploadTask, UploadStatus, UploadType, UploadProgress, BatchUploadResult
from .workflow_config import WorkflowConfig, WorkflowType, PriorityLevel

__all__ = [
    'MessageGroup',
    'MessageGroupCollection',
    'DownloadResult',
    'TemplateConfig',
    'TemplateVariable',
    'TemplateMode',
    'VariableType',
    'UploadTask',
    'UploadStatus',
    'UploadType',
    'UploadProgress',
    'BatchUploadResult',
    'WorkflowConfig',
    'WorkflowType',
    'PriorityLevel'
]
