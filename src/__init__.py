"""
MultiDownloadPyrogram - Telegram频道历史消息批量下载工具

基于Pyrogram框架开发的高性能Telegram频道历史消息媒体文件批量下载工具，
支持多客户端并发下载、大文件分片下载、媒体组完整下载等功能。

主要特性:
- 多客户端并发下载，使用Pyrogram官方compose()方法
- 支持大文件分片下载和媒体组完整下载
- 完善的错误处理和重试机制
- 详细的下载进度和统计信息
- 支持SOCKS5代理
"""

__version__ = "1.0.0"
__author__ = "MultiDownloadPyrogram Team"
__description__ = "Telegram频道历史消息批量下载工具"

from .main import MultiDownloadApp, main

__all__ = [
    "MultiDownloadApp",
    "main",
    "__version__",
    "__author__",
    "__description__"
] 