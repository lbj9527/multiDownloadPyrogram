"""
日志管理模块

提供统一的日志记录功能，支持文件日志、控制台日志和不同级别的日志输出
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import json
import traceback


class Logger:
    """日志管理器"""
    
    _instances: Dict[str, 'Logger'] = {}
    
    def __new__(cls, name: str = "MultiDownloadPyrogram", **kwargs) -> 'Logger':
        """单例模式，确保同名logger只有一个实例"""
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
        return cls._instances[name]
    
    def __init__(self, name: str = "MultiDownloadPyrogram", 
                 level: Union[int, str] = logging.INFO,
                 log_file: Optional[str] = None,
                 log_dir: Optional[str] = None,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 console_output: bool = True,
                 json_format: bool = False):
        """
        初始化日志管理器
        
        Args:
            name: logger名称
            level: 日志级别
            log_file: 日志文件名
            log_dir: 日志目录
            max_file_size: 日志文件最大大小
            backup_count: 备份文件数量
            console_output: 是否输出到控制台
            json_format: 是否使用JSON格式
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 清除已有的handlers
        self.logger.handlers.clear()
        
        # 创建日志目录
        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志格式
        self.json_format = json_format
        self.formatter = self._create_formatter()
        
        # 配置文件处理器
        if log_file:
            self._setup_file_handler(log_file, max_file_size, backup_count)
        
        # 配置控制台处理器
        if console_output:
            self._setup_console_handler()
        
        # 配置pyrogram日志级别
        self._setup_pyrogram_logging()
    
    def _create_formatter(self) -> logging.Formatter:
        """创建日志格式器"""
        if self.json_format:
            return JsonFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
    
    def _setup_file_handler(self, log_file: str, max_file_size: int, backup_count: int):
        """设置文件处理器"""
        log_path = self.log_dir / log_file
        
        # 使用RotatingFileHandler支持日志轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_console_handler(self):
        """设置控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_pyrogram_logging(self):
        """配置Pyrogram日志级别"""
        # 设置pyrogram日志级别为WARNING，减少噪音
        logging.getLogger("pyrogram").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.session").setLevel(logging.INFO)
        logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录DEBUG级别日志"""
        self.logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录INFO级别日志"""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录WARNING级别日志"""
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, exc_info: Optional[Exception] = None, 
              extra: Optional[Dict[str, Any]] = None):
        """记录ERROR级别日志"""
        extra = extra or {}
        if exc_info:
            extra['exception'] = {
                'type': exc_info.__class__.__name__,
                'message': str(exc_info),
                'traceback': traceback.format_exc()
            }
        self.logger.error(message, extra=extra, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None,
                 extra: Optional[Dict[str, Any]] = None):
        """记录CRITICAL级别日志"""
        extra = extra or {}
        if exc_info:
            extra['exception'] = {
                'type': exc_info.__class__.__name__,
                'message': str(exc_info),
                'traceback': traceback.format_exc()
            }
        self.logger.critical(message, extra=extra, exc_info=exc_info)
    
    def log_download_progress(self, current: int, total: int, filename: str, 
                            speed: Optional[float] = None):
        """记录下载进度"""
        percentage = (current / total) * 100 if total > 0 else 0
        extra = {
            'download_progress': {
                'current': current,
                'total': total,
                'percentage': percentage,
                'filename': filename,
                'speed_mbps': speed
            }
        }
        self.info(f"下载进度: {filename} - {percentage:.1f}%", extra=extra)
    
    def log_client_status(self, client_id: str, status: str, message: Optional[str] = None):
        """记录客户端状态"""
        extra = {
            'client_status': {
                'client_id': client_id,
                'status': status,
                'message': message
            }
        }
        self.info(f"客户端状态: {client_id} - {status}", extra=extra)
    
    def log_task_status(self, task_id: str, task_type: str, status: str, 
                       progress: Optional[Dict[str, Any]] = None):
        """记录任务状态"""
        extra = {
            'task_status': {
                'task_id': task_id,
                'task_type': task_type,
                'status': status,
                'progress': progress
            }
        }
        self.info(f"任务状态: {task_id} - {status}", extra=extra)
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """记录性能指标"""
        extra = {
            'performance_metrics': metrics
        }
        self.info("性能指标记录", extra=extra)
    
    @classmethod
    def get_logger(cls, name: str = "MultiDownloadPyrogram") -> 'Logger':
        """获取logger实例"""
        return cls(name)


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON格式"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process_id': record.process,
            'thread_id': record.thread
        }
        
        # 添加extra字段
        if hasattr(record, 'extra') and record.extra:
            log_data.update(record.extra)
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))


# 全局默认logger实例
default_logger = Logger.get_logger()


def get_logger(name: Optional[str] = None) -> Logger:
    """
    获取日志实例
    
    Args:
        name: logger名称，如果为None则返回默认logger
        
    Returns:
        Logger实例
    """
    if name:
        return Logger.get_logger(name)
    return default_logger


def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 log_dir: Optional[str] = None,
                 console_output: bool = True,
                 json_format: bool = False) -> Logger:
    """
    设置全局日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件名
        log_dir: 日志目录
        console_output: 是否输出到控制台
        json_format: 是否使用JSON格式
        
    Returns:
        配置好的Logger实例
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    return Logger(
        name="MultiDownloadPyrogram",
        level=level,
        log_file=log_file,
        log_dir=log_dir,
        console_output=console_output,
        json_format=json_format
    ) 