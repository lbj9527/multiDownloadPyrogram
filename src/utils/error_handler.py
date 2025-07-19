#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和重试机制
"""

import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from enum import Enum

from pyrogram.errors import (
    FloodWait, BadRequest, Forbidden,
    AuthKeyUnregistered, Unauthorized, SessionPasswordNeeded,
    PhoneNumberInvalid, PhoneCodeInvalid, PasswordHashInvalid,
    InternalServerError, ServiceUnavailable
)

from ..models.events import EventType, create_error_event
from ..utils.logger import get_logger


class ErrorType(Enum):
    """错误类型枚举"""
    FLOOD_WAIT = "flood_wait"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    PERMISSION_ERROR = "permission_error"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """重试策略枚举"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, event_callback: Optional[Callable] = None):
        """
        初始化错误处理器
        
        Args:
            event_callback: 事件回调函数
        """
        self.event_callback = event_callback
        self.logger = get_logger(__name__)
        
        # 错误统计
        self.error_stats: Dict[str, int] = {}
        self.last_errors: List[Dict[str, Any]] = []
        self.max_error_history = 100
        
        # 重试配置
        self.retry_configs = {
            ErrorType.FLOOD_WAIT: {
                "strategy": RetryStrategy.NO_RETRY,  # FloodWait需要特殊处理
                "max_retries": 0,
                "base_delay": 0
            },
            ErrorType.NETWORK_ERROR: {
                "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 3,
                "base_delay": 2
            },
            ErrorType.RATE_LIMIT: {
                "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 2,
                "base_delay": 5
            },
            ErrorType.SERVER_ERROR: {
                "strategy": RetryStrategy.LINEAR_BACKOFF,
                "max_retries": 2,
                "base_delay": 3
            },
            ErrorType.AUTH_ERROR: {
                "strategy": RetryStrategy.NO_RETRY,
                "max_retries": 0,
                "base_delay": 0
            },
            ErrorType.PERMISSION_ERROR: {
                "strategy": RetryStrategy.NO_RETRY,
                "max_retries": 0,
                "base_delay": 0
            },
            ErrorType.UNKNOWN_ERROR: {
                "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 1,
                "base_delay": 1
            }
        }
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            
        Returns:
            ErrorType: 错误类型
        """
        if isinstance(error, FloodWait):
            return ErrorType.FLOOD_WAIT
        elif isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return ErrorType.NETWORK_ERROR
        elif isinstance(error, (AuthKeyUnregistered, Unauthorized, SessionPasswordNeeded,
                               PhoneNumberInvalid, PhoneCodeInvalid, PasswordHashInvalid)):
            return ErrorType.AUTH_ERROR
        elif isinstance(error, (Forbidden, BadRequest)):
            return ErrorType.PERMISSION_ERROR
        elif "TooManyRequests" in str(type(error)):
            return ErrorType.RATE_LIMIT
        elif isinstance(error, (InternalServerError, ServiceUnavailable)):
            return ErrorType.SERVER_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def should_retry(self, error: Exception, retry_count: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 异常对象
            retry_count: 当前重试次数
            
        Returns:
            bool: 是否应该重试
        """
        error_type = self.classify_error(error)
        config = self.retry_configs.get(error_type, {})
        
        max_retries = config.get("max_retries", 0)
        strategy = config.get("strategy", RetryStrategy.NO_RETRY)
        
        return strategy != RetryStrategy.NO_RETRY and retry_count < max_retries
    
    def calculate_delay(self, error: Exception, retry_count: int) -> float:
        """
        计算重试延迟时间
        
        Args:
            error: 异常对象
            retry_count: 当前重试次数
            
        Returns:
            float: 延迟时间（秒）
        """
        error_type = self.classify_error(error)
        config = self.retry_configs.get(error_type, {})
        
        strategy = config.get("strategy", RetryStrategy.FIXED_DELAY)
        base_delay = config.get("base_delay", 1)
        
        if strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # 指数退避：base_delay * (2 ^ retry_count) + 随机抖动
            delay = base_delay * (2 ** retry_count)
            jitter = random.uniform(0, delay * 0.1)  # 10%的随机抖动
            return delay + jitter
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            # 线性退避：base_delay * (retry_count + 1)
            return base_delay * (retry_count + 1)
        elif strategy == RetryStrategy.FIXED_DELAY:
            # 固定延迟
            return base_delay
        else:
            return 0
    
    async def handle_flood_wait(self, error: FloodWait, context: str = "") -> bool:
        """
        处理FloodWait错误
        
        Args:
            error: FloodWait异常
            context: 上下文信息
            
        Returns:
            bool: 是否成功处理
        """
        try:
            wait_time = error.value
            self.logger.warning(f"触发FloodWait，需要等待 {wait_time} 秒 - {context}")
            
            # 记录错误
            self.record_error(error, context)
            
            # 发送事件
            if self.event_callback:
                event = create_error_event(
                    EventType.ERROR_FLOOD_WAIT,
                    f"触发限流，等待 {wait_time} 秒",
                    error_details={"wait_time": wait_time, "context": context},
                    source="error_handler"
                )
                self.event_callback(event)
            
            # 等待指定时间
            await asyncio.sleep(wait_time)
            
            self.logger.info(f"FloodWait等待完成 - {context}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理FloodWait失败: {e}")
            return False
    
    async def handle_network_error(self, error: Exception, context: str = "") -> bool:
        """
        处理网络错误
        
        Args:
            error: 网络异常
            context: 上下文信息
            
        Returns:
            bool: 是否成功处理
        """
        try:
            self.logger.warning(f"网络错误: {error} - {context}")
            
            # 记录错误
            self.record_error(error, context)
            
            # 发送事件
            if self.event_callback:
                event = create_error_event(
                    EventType.ERROR_NETWORK,
                    f"网络错误: {error}",
                    error_details={"error": str(error), "context": context},
                    source="error_handler"
                )
                self.event_callback(event)
            
            # 简单的网络检查
            await self.check_network_connectivity()
            
            return True
            
        except Exception as e:
            self.logger.error(f"处理网络错误失败: {e}")
            return False
    
    async def check_network_connectivity(self) -> bool:
        """
        检查网络连接性
        
        Returns:
            bool: 网络是否可用
        """
        try:
            import aiohttp
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get("https://www.google.com") as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.warning(f"网络连接检查失败: {e}")
            return False
    
    def record_error(self, error: Exception, context: str = ""):
        """
        记录错误信息
        
        Args:
            error: 异常对象
            context: 上下文信息
        """
        try:
            error_type = self.classify_error(error)
            error_key = error_type.value
            
            # 更新统计
            self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1
            
            # 记录错误详情
            error_record = {
                "timestamp": time.time(),
                "type": error_type.value,
                "error": str(error),
                "context": context,
                "error_class": error.__class__.__name__
            }
            
            self.last_errors.append(error_record)
            
            # 限制历史记录大小
            if len(self.last_errors) > self.max_error_history:
                self.last_errors = self.last_errors[-self.max_error_history:]
                
        except Exception as e:
            self.logger.error(f"记录错误失败: {e}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            Dict[str, Any]: 错误统计
        """
        return {
            "error_counts": self.error_stats.copy(),
            "total_errors": sum(self.error_stats.values()),
            "recent_errors": self.last_errors[-10:],  # 最近10个错误
            "error_types": list(self.error_stats.keys())
        }
    
    def clear_error_stats(self):
        """清空错误统计"""
        self.error_stats.clear()
        self.last_errors.clear()
        self.logger.info("错误统计已清空")


def with_retry(max_retries: int = 3, error_handler: Optional[ErrorHandler] = None,
               context: str = ""):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        error_handler: 错误处理器
        context: 上下文信息
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for retry_count in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as error:
                    last_error = error
                    
                    # 如果有错误处理器，使用它来判断是否重试
                    if error_handler:
                        if not error_handler.should_retry(error, retry_count):
                            break
                        
                        # 特殊处理FloodWait
                        if isinstance(error, FloodWait):
                            await error_handler.handle_flood_wait(error, context)
                            continue
                        
                        # 处理其他错误
                        if isinstance(error, (NetworkError, ConnectionError)):
                            await error_handler.handle_network_error(error, context)
                        
                        # 计算延迟时间
                        delay = error_handler.calculate_delay(error, retry_count)
                        if delay > 0:
                            await asyncio.sleep(delay)
                    else:
                        # 简单的重试逻辑
                        if retry_count < max_retries:
                            delay = 2 ** retry_count  # 指数退避
                            await asyncio.sleep(delay)
            
            # 所有重试都失败，抛出最后一个错误
            raise last_error
        
        return wrapper
    return decorator


# 全局错误处理器实例
global_error_handler = ErrorHandler()
