"""
统一错误处理模块
提供标准化的错误处理、日志记录和恢复机制
"""

import traceback
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .logging_utils import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    RESOURCE = "resource"
    SYSTEM = "system"
    BUSINESS = "business"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """错误信息结构"""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    traceback_info: Optional[str] = None
    suggested_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "traceback": self.traceback_info,
            "suggested_action": self.suggested_action
        }


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
    
    def handle_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        suggested_action: Optional[str] = None,
        log_error: bool = True
    ) -> ErrorInfo:
        """
        处理错误
        
        Args:
            exception: 异常对象
            context: 错误上下文信息
            category: 错误分类
            severity: 错误严重程度
            suggested_action: 建议的解决方案
            log_error: 是否记录日志
            
        Returns:
            错误信息对象
        """
        error_type = type(exception).__name__
        message = str(exception)
        context = context or {}
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_type=error_type,
            message=message,
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            context=context,
            traceback_info=traceback.format_exc(),
            suggested_action=suggested_action
        )
        
        # 记录错误历史
        self.error_history.append(error_info)
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 记录日志
        if log_error:
            self._log_error(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_message = (
            f"[{error_info.category.value.upper()}] {error_info.error_type}: {error_info.message}"
        )
        
        if error_info.context:
            log_message += f" | Context: {error_info.context}"
        
        if error_info.suggested_action:
            log_message += f" | Suggested: {error_info.suggested_action}"
        
        # 根据严重程度选择日志级别
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {"total_errors": 0, "error_types": {}, "recent_errors": []}
        
        # 按严重程度分组
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # 最近的错误
        recent_errors = [
            error.to_dict() for error in self.error_history[-5:]
        ]
        
        return {
            "total_errors": total_errors,
            "error_types": dict(self.error_counts),
            "severity_distribution": severity_counts,
            "recent_errors": recent_errors
        }
    
    def clear_history(self):
        """清空错误历史"""
        self.error_history.clear()
        self.error_counts.clear()


# 全局错误处理器实例
global_error_handler = ErrorHandler()


def handle_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    suggested_action: Optional[str] = None
) -> ErrorInfo:
    """
    全局异常处理函数
    
    Args:
        exception: 异常对象
        context: 错误上下文
        category: 错误分类
        severity: 错误严重程度
        suggested_action: 建议的解决方案
        
    Returns:
        错误信息对象
    """
    return global_error_handler.handle_error(
        exception=exception,
        context=context,
        category=category,
        severity=severity,
        suggested_action=suggested_action
    )


def categorize_exception(exception: Exception) -> ErrorCategory:
    """
    根据异常类型自动分类
    
    Args:
        exception: 异常对象
        
    Returns:
        错误分类
    """
    exception_name = type(exception).__name__.lower()
    
    # 网络相关错误
    if any(keyword in exception_name for keyword in ['connection', 'timeout', 'network', 'socket']):
        return ErrorCategory.NETWORK
    
    # 认证相关错误
    if any(keyword in exception_name for keyword in ['auth', 'login', 'credential', 'token']):
        return ErrorCategory.AUTHENTICATION
    
    # 权限相关错误
    if any(keyword in exception_name for keyword in ['permission', 'access', 'forbidden']):
        return ErrorCategory.PERMISSION
    
    # 验证相关错误
    if any(keyword in exception_name for keyword in ['validation', 'value', 'type']):
        return ErrorCategory.VALIDATION
    
    # 资源相关错误
    if any(keyword in exception_name for keyword in ['memory', 'disk', 'file', 'resource']):
        return ErrorCategory.RESOURCE
    
    # 系统相关错误
    if any(keyword in exception_name for keyword in ['system', 'os', 'runtime']):
        return ErrorCategory.SYSTEM
    
    return ErrorCategory.UNKNOWN


def get_suggested_action(exception: Exception) -> Optional[str]:
    """
    根据异常类型提供建议的解决方案
    
    Args:
        exception: 异常对象
        
    Returns:
        建议的解决方案
    """
    exception_name = type(exception).__name__.lower()
    
    suggestions = {
        'connectionerror': '检查网络连接和代理设置',
        'timeouterror': '增加超时时间或检查网络稳定性',
        'authenticationerror': '检查API凭据和权限设置',
        'permissionerror': '检查文件/目录权限',
        'filenotfounderror': '确认文件路径是否正确',
        'valueerror': '检查输入参数的格式和范围',
        'typeerror': '检查数据类型是否匹配',
        'memoryerror': '减少内存使用或增加系统内存',
        'keyerror': '检查配置项是否完整',
    }
    
    for error_type, suggestion in suggestions.items():
        if error_type in exception_name:
            return suggestion
    
    return "查看详细错误信息并检查相关配置"


# 便捷函数
def handle_error_with_context(
    exception: Exception,
    operation: str,
    **context_kwargs
) -> ErrorInfo:
    """
    带上下文的错误处理便捷函数
    
    Args:
        exception: 异常对象
        operation: 操作名称
        **context_kwargs: 上下文信息
        
    Returns:
        错误信息对象
    """
    context = {"operation": operation, **context_kwargs}
    category = categorize_exception(exception)
    suggested_action = get_suggested_action(exception)
    
    return handle_exception(
        exception=exception,
        context=context,
        category=category,
        suggested_action=suggested_action
    )
