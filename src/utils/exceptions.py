"""
异常处理模块
定义项目中使用的各种自定义异常，提供统一的错误处理机制
"""

from typing import Optional, Any


class MultiDownloadError(Exception):
    """项目基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "MULTI_DOWNLOAD_ERROR"
        self.details = details or {}


class ConfigurationError(MultiDownloadError):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message)
        self.config_key = config_key
        self.error_code = "CONFIG_ERROR"


class ClientError(MultiDownloadError):
    """客户端相关异常"""
    
    def __init__(self, message: str, client_id: Optional[str] = None):
        super().__init__(message)
        self.client_id = client_id
        self.error_code = "CLIENT_ERROR"


class ClientAuthenticationError(ClientError):
    """客户端认证异常"""
    
    def __init__(self, message: str, client_id: Optional[str] = None):
        super().__init__(message, client_id)
        self.error_code = "CLIENT_AUTH_ERROR"


class NetworkError(MultiDownloadError):
    """网络相关异常"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.error_code = "NETWORK_ERROR"


class RateLimitError(MultiDownloadError):
    """速率限制异常"""
    
    def __init__(self, message: str, wait_time: Optional[int] = None):
        super().__init__(message)
        self.wait_time = wait_time or 60
        self.error_code = "RATE_LIMIT_ERROR"


class DownloadError(MultiDownloadError):
    """下载相关异常"""
    
    def __init__(self, message: str, filename: Optional[str] = None, message_id: Optional[int] = None):
        super().__init__(message)
        self.filename = filename
        self.message_id = message_id
        self.error_code = "DOWNLOAD_ERROR"


class FileError(DownloadError):
    """文件相关异常"""
    
    def __init__(self, message: str, filename: Optional[str] = None, file_path: Optional[str] = None):
        super().__init__(message, filename)
        self.file_path = file_path
        self.error_code = "FILE_ERROR"


class FileNotFoundError(FileError):
    """文件未找到异常"""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(message, filename)
        self.error_code = "FILE_NOT_FOUND"


class FileSizeError(FileError):
    """文件大小异常"""
    
    def __init__(self, message: str, filename: str, expected_size: int, actual_size: int):
        super().__init__(message, filename)
        self.expected_size = expected_size
        self.actual_size = actual_size
        self.error_code = "FILE_SIZE_ERROR"


class MediaGroupError(DownloadError):
    """媒体组下载异常"""
    
    def __init__(self, message: str, group_id: Optional[str] = None, message_id: Optional[int] = None):
        super().__init__(message, message_id=message_id)
        self.group_id = group_id
        self.error_code = "MEDIA_GROUP_ERROR"


class TaskError(MultiDownloadError):
    """任务相关异常"""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(message)
        self.task_id = task_id
        self.error_code = "TASK_ERROR"


class QueueError(TaskError):
    """队列相关异常"""
    
    def __init__(self, message: str, queue_name: Optional[str] = None):
        super().__init__(message)
        self.queue_name = queue_name
        self.error_code = "QUEUE_ERROR"


# 异常处理工具函数

def handle_pyrogram_exception(exception: Exception) -> MultiDownloadError:
    """
    将Pyrogram异常转换为项目异常
    
    Args:
        exception: Pyrogram异常
        
    Returns:
        MultiDownloadError: 转换后的项目异常
    """
    exception_name = exception.__class__.__name__
    message = str(exception)
    
    # FloodWait异常处理
    if exception_name == "FloodWait":
        wait_time = getattr(exception, 'value', None) or getattr(exception, 'x', None)
        return RateLimitError(f"频率限制，需要等待 {wait_time} 秒", wait_time)
    
    # 认证相关异常
    elif exception_name in ["SessionPasswordNeeded", "PhoneCodeInvalid", "PhoneNumberInvalid", 
                           "AuthBytesInvalid", "UserDeactivated", "AuthKeyUnregistered"]:
        return ClientAuthenticationError(f"客户端认证失败: {message}")
    
    # 网络相关异常
    elif exception_name in ["NetworkError", "TimeoutError", "ConnectionError", "OSError"]:
        return NetworkError(f"网络连接异常: {message}")
    
    # 文件相关异常
    elif exception_name in ["FileIdInvalid", "FileReferenceExpired", "FileLocationInvalid"]:
        return FileNotFoundError(f"文件无效或已过期: {message}")
    
    # 权限相关异常
    elif exception_name in ["ChatAdminRequired", "UserNotParticipant", "ChannelPrivate"]:
        return ClientError(f"权限不足: {message}")
    
    # 其他异常
    else:
        return MultiDownloadError(f"Pyrogram异常: {message}", exception_name)


def is_retryable_error(exception: Exception) -> bool:
    """
    判断异常是否可重试
    
    Args:
        exception: 异常对象
        
    Returns:
        bool: 是否可重试
    """
    if isinstance(exception, (NetworkError, RateLimitError)):
        return True
    
    if isinstance(exception, FileError):
        return False
    
    if isinstance(exception, ClientAuthenticationError):
        return False
    
    # Pyrogram异常类型检查
    exception_name = exception.__class__.__name__
    retryable_exceptions = [
        "NetworkError", "TimeoutError", "FloodWait", 
        "InternalServerError", "ServiceUnavailable"
    ]
    
    return exception_name in retryable_exceptions


def get_retry_delay(exception: Exception, attempt: int) -> int:
    """
    根据异常类型和重试次数计算延迟时间
    
    Args:
        exception: 异常对象
        attempt: 重试次数
        
    Returns:
        int: 延迟秒数
    """
    if isinstance(exception, RateLimitError):
        return exception.wait_time
    
    # FloodWait异常
    if hasattr(exception, 'value'):
        return exception.value
    if hasattr(exception, 'x'):
        return exception.x
    
    # 指数退避策略
    return min(2 ** attempt, 300)  # 最大5分钟


def format_exception_message(exception: Exception) -> str:
    """
    格式化异常消息
    
    Args:
        exception: 异常对象
        
    Returns:
        str: 格式化的消息
    """
    if isinstance(exception, MultiDownloadError):
        parts = [f"[{exception.error_code}]", exception.message]
        
        if hasattr(exception, 'filename') and exception.filename:
            parts.append(f"文件: {exception.filename}")
        
        if hasattr(exception, 'client_id') and exception.client_id:
            parts.append(f"客户端: {exception.client_id}")
        
        return " - ".join(parts)
    
    return str(exception) 