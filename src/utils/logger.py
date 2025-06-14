"""
日志管理模块
提供统一的日志记录功能，支持不同级别的日志输出和文件记录
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class Logger:
    """日志管理器"""
    
    def __init__(self, name: str = "MultiDownloadPyrogram"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # 彩色格式化器
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # 文件处理器 - 详细日志
        file_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, f"{self.name}.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 文件格式化器
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 错误日志处理器
        error_handler = RotatingFileHandler(
            filename=os.path.join(log_dir, f"{self.name}_error.log"),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """调试日志"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """信息日志"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """警告日志"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """错误日志"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """异常日志（包含堆栈跟踪）"""
        self.logger.exception(message, *args, **kwargs)


class DownloadLogger:
    """下载专用日志记录器"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.download_stats = {
            'total_files': 0,
            'downloaded_files': 0,
            'failed_files': 0,
            'total_bytes': 0,
            'downloaded_bytes': 0,
            'start_time': None
        }
    
    def start_download_session(self, total_files: int = 0):
        """开始下载会话"""
        self.download_stats['total_files'] = total_files
        self.download_stats['start_time'] = datetime.now()
        self.logger.info(f"开始下载会话，预计下载 {total_files} 个文件")
    
    def log_file_start(self, filename: str, file_size: int = 0):
        """记录文件开始下载"""
        self.logger.info(f"开始下载文件: {filename} ({self._format_size(file_size)})")
    
    def log_file_success(self, filename: str, file_size: int = 0, duration: float = 0):
        """记录文件下载成功"""
        self.download_stats['downloaded_files'] += 1
        self.download_stats['downloaded_bytes'] += file_size
        
        speed = file_size / duration if duration > 0 else 0
        self.logger.info(
            f"下载完成: {filename} "
            f"({self._format_size(file_size)}, "
            f"{duration:.1f}s, "
            f"{self._format_size(speed)}/s)"
        )
    
    def log_file_error(self, filename: str, error: str):
        """记录文件下载失败"""
        self.download_stats['failed_files'] += 1
        self.logger.error(f"下载失败: {filename} - {error}")
    
    def log_progress(self, current: int, total: int, speed: float = 0):
        """记录下载进度"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.logger.info(
            f"下载进度: {percentage:.1f}% "
            f"({current}/{total}, "
            f"{self._format_size(speed)}/s)"
        )
    
    def log_session_summary(self):
        """记录下载会话总结"""
        if self.download_stats['start_time']:
            duration = (datetime.now() - self.download_stats['start_time']).total_seconds()
            success_rate = (
                self.download_stats['downloaded_files'] / 
                max(self.download_stats['total_files'], 1) * 100
            )
            
            self.logger.info(
                f"下载会话完成: "
                f"成功 {self.download_stats['downloaded_files']}/"
                f"{self.download_stats['total_files']} 个文件 "
                f"({success_rate:.1f}%), "
                f"失败 {self.download_stats['failed_files']} 个, "
                f"总计 {self._format_size(self.download_stats['downloaded_bytes'])}, "
                f"耗时 {duration:.1f}s"
            )
    
    @staticmethod
    def _format_size(size_bytes: float) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024.0 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"


# 全局日志实例
_logger: Optional[Logger] = None
_download_logger: Optional[DownloadLogger] = None


def get_logger() -> Logger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def get_download_logger() -> DownloadLogger:
    """获取下载日志实例"""
    global _download_logger
    if _download_logger is None:
        _download_logger = DownloadLogger(get_logger())
    return _download_logger


def setup_pyrogram_logging():
    """设置Pyrogram日志级别"""
    # 设置Pyrogram相关日志级别，避免过多输出
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("pyrogram.session").setLevel(logging.INFO)
    logging.getLogger("pyrogram.connection").setLevel(logging.WARNING) 