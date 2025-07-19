#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统配置
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger():
    """设置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # 文件输出
    logger.add(
        log_dir / "app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 错误日志单独文件
    logger.add(
        log_dir / "error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger


def setup_custom_logger(config: dict = None):
    """
    设置自定义日志配置

    Args:
        config: 日志配置字典
    """
    if not config:
        return

    try:
        # 移除现有处理器
        logger.remove()

        # 创建日志目录
        log_dir = Path(config.get("file_path", "logs")).parent
        log_dir.mkdir(exist_ok=True)

        # 控制台输出配置
        console_config = config.get("console", {})
        if console_config.get("enabled", True):
            logger.add(
                sys.stdout,
                format=console_config.get("format",
                    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"),
                level=console_config.get("level", "INFO"),
                colorize=console_config.get("colorize", True),
                filter=lambda record: record["level"].no >= logger.level(console_config.get("level", "INFO")).no
            )

        # 文件输出配置
        file_config = config.get("file", {})
        if file_config.get("enabled", True):
            logger.add(
                file_config.get("path", log_dir / "app.log"),
                format=file_config.get("format",
                    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"),
                level=file_config.get("level", "DEBUG"),
                rotation=file_config.get("rotation", "10 MB"),
                retention=file_config.get("retention", "7 days"),
                compression=file_config.get("compression", "zip"),
                encoding="utf-8",
                enqueue=True  # 异步写入
            )

        # 错误日志单独文件
        error_config = config.get("error_file", {})
        if error_config.get("enabled", True):
            logger.add(
                error_config.get("path", log_dir / "error.log"),
                format=error_config.get("format",
                    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"),
                level="ERROR",
                rotation=error_config.get("rotation", "10 MB"),
                retention=error_config.get("retention", "30 days"),
                compression=error_config.get("compression", "zip"),
                encoding="utf-8",
                enqueue=True
            )

        # JSON格式日志（用于结构化分析）
        json_config = config.get("json_file", {})
        if json_config.get("enabled", False):
            logger.add(
                json_config.get("path", log_dir / "app.json"),
                format="{time} | {level} | {name} | {function} | {line} | {message}",
                level=json_config.get("level", "INFO"),
                rotation=json_config.get("rotation", "50 MB"),
                retention=json_config.get("retention", "3 days"),
                serialize=True,  # JSON格式
                encoding="utf-8",
                enqueue=True
            )

    except Exception as e:
        print(f"设置自定义日志配置失败: {e}")


def add_log_sink(sink_config: dict):
    """
    添加日志输出目标

    Args:
        sink_config: 输出目标配置
    """
    try:
        sink_type = sink_config.get("type", "file")

        if sink_type == "file":
            logger.add(
                sink_config["path"],
                format=sink_config.get("format", "{time} | {level} | {message}"),
                level=sink_config.get("level", "INFO"),
                rotation=sink_config.get("rotation"),
                retention=sink_config.get("retention"),
                compression=sink_config.get("compression"),
                encoding="utf-8"
            )
        elif sink_type == "console":
            logger.add(
                sys.stdout,
                format=sink_config.get("format", "<level>{message}</level>"),
                level=sink_config.get("level", "INFO"),
                colorize=sink_config.get("colorize", True)
            )

    except Exception as e:
        print(f"添加日志输出目标失败: {e}")


def log_performance(func_name: str = None):
    """
    性能日志装饰器

    Args:
        func_name: 函数名称
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or f"{func.__module__}.{func.__name__}"

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(f"[PERF] {name} 执行完成，耗时: {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[PERF] {name} 执行失败，耗时: {duration:.3f}s，错误: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(f"[PERF] {name} 执行完成，耗时: {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[PERF] {name} 执行失败，耗时: {duration:.3f}s，错误: {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_function_call(include_args: bool = False, include_result: bool = False):
    """
    函数调用日志装饰器

    Args:
        include_args: 是否包含参数
        include_result: 是否包含返回值
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = f"{func.__module__}.{func.__name__}"

            # 记录函数调用
            if include_args:
                logger.debug(f"[CALL] {name} 开始执行，参数: args={args}, kwargs={kwargs}")
            else:
                logger.debug(f"[CALL] {name} 开始执行")

            try:
                result = await func(*args, **kwargs)

                if include_result:
                    logger.debug(f"[CALL] {name} 执行成功，返回值: {result}")
                else:
                    logger.debug(f"[CALL] {name} 执行成功")

                return result
            except Exception as e:
                logger.error(f"[CALL] {name} 执行失败: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = f"{func.__module__}.{func.__name__}"

            # 记录函数调用
            if include_args:
                logger.debug(f"[CALL] {name} 开始执行，参数: args={args}, kwargs={kwargs}")
            else:
                logger.debug(f"[CALL] {name} 开始执行")

            try:
                result = func(*args, **kwargs)

                if include_result:
                    logger.debug(f"[CALL] {name} 执行成功，返回值: {result}")
                else:
                    logger.debug(f"[CALL] {name} 执行成功")

                return result
            except Exception as e:
                logger.error(f"[CALL] {name} 执行失败: {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 导入必要的模块
import time
from functools import wraps
