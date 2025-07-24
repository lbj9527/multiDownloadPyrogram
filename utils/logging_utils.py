"""
日志工具函数
"""

import logging
import sys
import traceback
import time
from pathlib import Path
from typing import Optional, Any, Callable
from functools import wraps
from datetime import datetime

from config.constants import LOG_LEVELS, DEFAULT_LOG_FORMAT, DEFAULT_LOG_FILE


# 全局标志，防止重复配置
_logging_configured = False

def setup_logging(
    level: str = "INFO",
    format_string: str = DEFAULT_LOG_FORMAT,
    file_path: Optional[str] = None,
    console_enabled: bool = True,
    file_enabled: bool = True,
    verbose_pyrogram: bool = False
) -> logging.Logger:
    """
    设置日志系统

    Args:
        level: 日志级别
        format_string: 日志格式
        file_path: 日志文件路径
        console_enabled: 是否启用控制台输出
        file_enabled: 是否启用文件输出
        verbose_pyrogram: 是否显示Pyrogram详细日志

    Returns:
        配置好的logger
    """
    global _logging_configured

    # 如果已经配置过，就不重复配置
    if _logging_configured:
        return logging.getLogger()

    # 验证日志级别
    if level.upper() not in LOG_LEVELS:
        level = "INFO"

    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除现有的handlers
    root_logger.handlers.clear()

    # 创建formatter
    formatter = logging.Formatter(format_string)

    # 控制台handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件handler
    if file_enabled and file_path:
        # 确保日志目录存在
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 标记为已配置
    _logging_configured = True
    
    # 配置Pyrogram日志
    pyrogram_level = logging.INFO if verbose_pyrogram else logging.WARNING
    for pyrogram_logger in ["pyrogram", "pyrogram.connection", "pyrogram.session", 
                           "pyrogram.dispatcher", "pyrogram.connection.transport"]:
        logging.getLogger(pyrogram_logger).setLevel(pyrogram_level)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return logging.getLogger(name)


def log_performance(func: Callable) -> Callable:
    """
    性能日志装饰器
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} 执行完成，耗时: {duration:.2f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {duration:.2f}秒，错误: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} 执行完成，耗时: {duration:.2f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {duration:.2f}秒，错误: {e}")
            raise
    
    # 检查是否为异步函数
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_error_with_traceback(logger: logging.Logger, message: str, exception: Exception):
    """
    记录错误和完整的堆栈跟踪
    
    Args:
        logger: logger实例
        message: 错误消息
        exception: 异常对象
    """
    error_details = {
        'message': message,
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat()
    }
    
    logger.error(f"{message}: {exception}")
    logger.debug(f"详细错误信息: {error_details}")


class PerformanceLogger:
    """性能监控日志器"""
    
    def __init__(self, logger_name: str):
        self.logger = get_logger(logger_name)
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """开始计时"""
        self.start_times[operation] = time.time()
        self.logger.debug(f"开始 {operation}")
    
    def end_timer(self, operation: str, log_level: str = "INFO"):
        """结束计时并记录"""
        if operation not in self.start_times:
            self.logger.warning(f"未找到操作 {operation} 的开始时间")
            return
        
        duration = time.time() - self.start_times[operation]
        del self.start_times[operation]
        
        log_func = getattr(self.logger, log_level.lower())
        log_func(f"{operation} 完成，耗时: {duration:.2f}秒")
        
        return duration
    
    def log_memory_usage(self):
        """记录内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            self.logger.debug(
                f"内存使用: RSS={memory_info.rss / 1024 / 1024:.1f}MB, "
                f"VMS={memory_info.vms / 1024 / 1024:.1f}MB"
            )
        except ImportError:
            self.logger.debug("psutil未安装，无法获取内存使用信息")


class ProgressLogger:
    """进度日志器"""
    
    def __init__(self, logger_name: str, total: int, log_interval: int = 10):
        self.logger = get_logger(logger_name)
        self.total = total
        self.log_interval = log_interval
        self.current = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
    
    def update(self, increment: int = 1):
        """更新进度"""
        self.current += increment
        current_time = time.time()
        
        # 检查是否需要记录日志
        if (self.current % self.log_interval == 0 or 
            self.current == self.total or
            current_time - self.last_log_time >= 5):  # 至少每5秒记录一次
            
            self.log_progress()
            self.last_log_time = current_time
    
    def log_progress(self):
        """记录当前进度"""
        if self.total == 0:
            return
        
        percentage = (self.current / self.total) * 100
        elapsed_time = time.time() - self.start_time
        
        if self.current > 0 and elapsed_time > 0:
            rate = self.current / elapsed_time
            eta = (self.total - self.current) / rate if rate > 0 else 0
            
            self.logger.info(
                f"进度: {self.current}/{self.total} ({percentage:.1f}%) "
                f"速度: {rate:.1f}/s ETA: {eta:.0f}s"
            )
        else:
            self.logger.info(f"进度: {self.current}/{self.total} ({percentage:.1f}%)")


def create_file_logger(name: str, file_path: str, level: str = "INFO") -> logging.Logger:
    """
    创建专用的文件日志器
    
    Args:
        name: logger名称
        file_path: 日志文件路径
        level: 日志级别
        
    Returns:
        文件日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加handler
    if not logger.handlers:
        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(file_path, encoding='utf-8')
        handler.setLevel(getattr(logging, level.upper()))
        
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False  # 防止传播到根logger
    
    return logger
