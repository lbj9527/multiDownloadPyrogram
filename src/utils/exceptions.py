"""
异常处理模块

定义项目的自定义异常类，提供详细的错误信息和处理机制
"""

from typing import Optional, Any, Dict


class MultiDownloadError(Exception):
    """项目基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ClientError(MultiDownloadError):
    """客户端相关异常"""
    
    def __init__(self, message: str, client_id: Optional[str] = None, 
                 error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初始化客户端异常
        
        Args:
            message: 错误消息
            client_id: 客户端ID
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message, error_code, details)
        self.client_id = client_id


class ClientConnectionError(ClientError):
    """客户端连接异常"""
    pass


class ClientAuthError(ClientError):
    """客户端认证异常"""
    pass


class ClientPoolError(ClientError):
    """客户端池异常"""
    pass


class DownloadError(MultiDownloadError):
    """下载相关异常"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 message_id: Optional[int] = None, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        初始化下载异常
        
        Args:
            message: 错误消息
            file_path: 文件路径
            message_id: 消息ID
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message, error_code, details)
        self.file_path = file_path
        self.message_id = message_id


class DownloadTimeoutError(DownloadError):
    """下载超时异常"""
    pass


class DownloadFailedError(DownloadError):
    """下载失败异常"""
    pass


class ChunkDownloadError(DownloadError):
    """分片下载异常"""
    
    def __init__(self, message: str, chunk_index: Optional[int] = None, 
                 total_chunks: Optional[int] = None, **kwargs):
        """
        初始化分片下载异常
        
        Args:
            message: 错误消息
            chunk_index: 分片索引
            total_chunks: 总分片数
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks


class MediaGroupError(DownloadError):
    """媒体组异常"""
    
    def __init__(self, message: str, media_group_id: Optional[str] = None, 
                 **kwargs):
        """
        初始化媒体组异常
        
        Args:
            message: 错误消息
            media_group_id: 媒体组ID
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.media_group_id = media_group_id


class TaskError(MultiDownloadError):
    """任务相关异常"""
    
    def __init__(self, message: str, task_id: Optional[str] = None, 
                 task_type: Optional[str] = None, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        """
        初始化任务异常
        
        Args:
            message: 错误消息
            task_id: 任务ID
            task_type: 任务类型
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message, error_code, details)
        self.task_id = task_id
        self.task_type = task_type


class TaskQueueError(TaskError):
    """任务队列异常"""
    pass


class TaskTimeoutError(TaskError):
    """任务超时异常"""
    pass


class ConfigError(MultiDownloadError):
    """配置相关异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[Any] = None, **kwargs):
        """
        初始化配置异常
        
        Args:
            message: 错误消息
            config_key: 配置键
            config_value: 配置值
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class ValidationError(MultiDownloadError):
    """验证异常"""
    
    def __init__(self, message: str, field_name: Optional[str] = None, 
                 field_value: Optional[Any] = None, **kwargs):
        """
        初始化验证异常
        
        Args:
            message: 错误消息
            field_name: 字段名称
            field_value: 字段值
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value


class ProxyError(MultiDownloadError):
    """代理相关异常"""
    
    def __init__(self, message: str, proxy_name: Optional[str] = None, 
                 proxy_url: Optional[str] = None, **kwargs):
        """
        初始化代理异常
        
        Args:
            message: 错误消息
            proxy_name: 代理名称
            proxy_url: 代理URL
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.proxy_name = proxy_name
        self.proxy_url = proxy_url


class NetworkError(MultiDownloadError):
    """网络相关异常"""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 status_code: Optional[int] = None, **kwargs):
        """
        初始化网络异常
        
        Args:
            message: 错误消息
            url: 请求URL
            status_code: HTTP状态码
            **kwargs: 其他参数
        """
        super().__init__(message, **kwargs)
        self.url = url
        self.status_code = status_code


# Pyrogram相关异常处理辅助函数
def handle_pyrogram_exception(exc: Exception, context: Optional[str] = None) -> MultiDownloadError:
    """
    处理Pyrogram异常，转换为项目异常
    
    Args:
        exc: Pyrogram异常
        context: 上下文信息
        
    Returns:
        项目异常对象
    """
    exc_name = exc.__class__.__name__
    exc_message = str(exc)
    
    # FloodWait异常
    if "FloodWait" in exc_name:
        return DownloadTimeoutError(
            f"API限流，需要等待: {exc_message}",
            error_code="FLOOD_WAIT",
            details={"original_exception": exc_name, "context": context}
        )
    
    # 网络相关异常
    if any(keyword in exc_name.lower() for keyword in ["network", "connection", "timeout"]):
        return ClientConnectionError(
            f"网络连接异常: {exc_message}",
            error_code="NETWORK_ERROR",
            details={"original_exception": exc_name, "context": context}
        )
    
    # 认证相关异常
    if any(keyword in exc_name.lower() for keyword in ["auth", "unauthorized", "forbidden"]):
        return ClientAuthError(
            f"认证异常: {exc_message}",
            error_code="AUTH_ERROR",
            details={"original_exception": exc_name, "context": context}
        )
    
    # 其他异常
    return MultiDownloadError(
        f"未知异常: {exc_message}",
        error_code="UNKNOWN_ERROR",
        details={"original_exception": exc_name, "context": context}
    ) 