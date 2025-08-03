"""
日志工具类
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from config.constants import LOG_FORMAT, DEFAULT_LOG_LEVEL

def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    clear_log: bool = True,
    suppress_pyrogram: bool = True
) -> logging.Logger:
    """
    设置日志配置
    """
    # 创建日志目录
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 清除日志文件（如果需要）
        if clear_log and log_file.exists():
            log_file.unlink()
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式器
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 屏蔽pyrogram的详细日志输出
    if suppress_pyrogram:
        _suppress_pyrogram_logs()

    return root_logger

def _suppress_pyrogram_logs():
    """屏蔽pyrogram的详细日志输出"""
    # 设置pyrogram相关日志器的级别为ERROR，只显示错误信息
    pyrogram_loggers = [
        "pyrogram",
        "pyrogram.connection",
        "pyrogram.connection.connection",
        "pyrogram.connection.transport",
        "pyrogram.connection.transport.tcp",
        "pyrogram.connection.transport.tcp.tcp",
        "pyrogram.session",
        "pyrogram.session.session"
    ]

    for logger_name in pyrogram_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    # 对于dispatcher，设置为WARNING级别（可能需要看到一些重要信息）
    logging.getLogger("pyrogram.dispatcher").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)

class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志器"""
        return logging.getLogger(self.__class__.__name__)
    
    def log_info(self, message: str, *args, **kwargs):
        """记录信息日志"""
        self.logger.info(message, *args, **kwargs)
    
    def log_warning(self, message: str, *args, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, *args, **kwargs)
    
    def log_error(self, message: str, *args, **kwargs):
        """记录错误日志"""
        self.logger.error(message, *args, **kwargs)
    
    def log_debug(self, message: str, *args, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, *args, **kwargs)
