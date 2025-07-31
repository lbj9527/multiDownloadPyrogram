"""
通用装饰器模块
提供统一的错误处理、重试、日志记录等装饰器
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union
import logging

from .logging_utils import get_logger
# 内联常量定义（替代config.constants）
RETRY_SETTINGS = {
    'max_retries': 3,
    'base_delay': 1.0,
    'max_delay': 60.0,
    'exponential_base': 2.0,
    'jitter': True
}

logger = get_logger(__name__)


def safe_execute(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    安全执行装饰器 - 统一异常处理
    
    Args:
        default_return: 异常时的默认返回值
        log_errors: 是否记录错误日志
        reraise: 是否重新抛出异常
        exceptions: 要捕获的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    logger.error(f"{func.__name__} 执行失败: {e}")
                if reraise:
                    raise
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    logger.error(f"{func.__name__} 执行失败: {e}")
                if reraise:
                    raise
                return default_return
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def retry_with_backoff(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    智能重试装饰器 - 指数退避算法
    
    Args:
        max_retries: 最大重试次数（默认从配置读取）
        base_delay: 基础延迟时间（默认从配置读取）
        max_delay: 最大延迟时间（默认从配置读取）
        backoff_factor: 退避因子（默认从配置读取）
        exceptions: 需要重试的异常类型
    """
    # 使用配置中的默认值
    max_retries = max_retries or RETRY_SETTINGS['max_retries']
    base_delay = base_delay or RETRY_SETTINGS['base_delay']
    max_delay = max_delay or RETRY_SETTINGS['max_delay']
    backoff_factor = backoff_factor or RETRY_SETTINGS['backoff_factor']
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = base_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        raise e
                    
                    logger.warning(
                        f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}，"
                        f"{current_delay:.1f}秒后重试"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * backoff_factor, max_delay)
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = base_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        raise e
                    
                    logger.warning(
                        f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}，"
                        f"{current_delay:.1f}秒后重试"
                    )
                    time.sleep(current_delay)
                    current_delay = min(current_delay * backoff_factor, max_delay)
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def log_execution_time(
    log_level: int = logging.INFO,
    include_args: bool = False,
    threshold_ms: Optional[float] = None
):
    """
    执行时间记录装饰器
    
    Args:
        log_level: 日志级别
        include_args: 是否包含参数信息
        threshold_ms: 只记录超过阈值的执行时间（毫秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                if threshold_ms is None or execution_time > threshold_ms:
                    args_info = f" args={args[:2]}..." if include_args and args else ""
                    logger.log(
                        log_level,
                        f"{func.__name__} 执行时间: {execution_time:.2f}ms{args_info}"
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                if threshold_ms is None or execution_time > threshold_ms:
                    args_info = f" args={args[:2]}..." if include_args and args else ""
                    logger.log(
                        log_level,
                        f"{func.__name__} 执行时间: {execution_time:.2f}ms{args_info}"
                    )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def validate_config(config_validator: Callable[[Any], bool]):
    """
    配置验证装饰器
    
    Args:
        config_validator: 配置验证函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 假设第一个参数是self，第二个是config
            if len(args) >= 2 and not config_validator(args[1]):
                raise ValueError(f"{func.__name__}: 配置验证失败")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 组合装饰器：常用的装饰器组合
def robust_operation(
    max_retries: int = 3,
    log_errors: bool = True,
    default_return: Any = None
):
    """
    健壮操作装饰器 - 组合了重试和安全执行
    """
    def decorator(func: Callable) -> Callable:
        # 先应用重试，再应用安全执行
        func = retry_with_backoff(max_retries=max_retries)(func)
        func = safe_execute(default_return=default_return, log_errors=log_errors)(func)
        return func
    return decorator
