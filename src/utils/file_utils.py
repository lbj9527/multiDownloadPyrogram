#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理工具
"""

import re
import os
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符，确保Windows平台兼容性
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    if not filename:
        return "unnamed"
    
    # Windows非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    
    # 替换非法字符为下划线
    clean_name = re.sub(illegal_chars, '_', filename)
    
    # 移除控制字符
    clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)
    
    # 移除首尾空格和点
    clean_name = clean_name.strip(' .')
    
    # 限制长度（Windows路径限制）
    if len(clean_name) > 200:
        clean_name = clean_name[:200]
    
    # 避免Windows保留名称
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_upper = clean_name.upper()
    if name_upper in reserved_names or name_upper.split('.')[0] in reserved_names:
        clean_name = f"_{clean_name}"
    
    return clean_name or "unnamed"


def get_file_extension(media, media_type: str) -> str:
    """
    根据媒体类型和MIME类型获取文件扩展名
    
    Args:
        media: 媒体对象
        media_type: 媒体类型
        
    Returns:
        str: 文件扩展名（包含点）
    """
    # 首先尝试从文件名获取扩展名
    if hasattr(media, 'file_name') and media.file_name:
        _, ext = os.path.splitext(media.file_name)
        if ext:
            return ext.lower()
    
    # 根据MIME类型确定扩展名
    mime_type = getattr(media, 'mime_type', '')
    
    # 常见MIME类型映射
    mime_extensions = {
        # 图片
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/svg+xml': '.svg',
        
        # 视频
        'video/mp4': '.mp4',
        'video/avi': '.avi',
        'video/mkv': '.mkv',
        'video/mov': '.mov',
        'video/wmv': '.wmv',
        'video/flv': '.flv',
        'video/webm': '.webm',
        'video/3gpp': '.3gp',
        
        # 音频
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/wav': '.wav',
        'audio/flac': '.flac',
        'audio/aac': '.aac',
        'audio/ogg': '.ogg',
        'audio/wma': '.wma',
        'audio/m4a': '.m4a',
        
        # 文档
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'text/plain': '.txt',
        'text/csv': '.csv',
        'application/json': '.json',
        'application/xml': '.xml',
        'text/html': '.html',
        
        # 压缩文件
        'application/zip': '.zip',
        'application/x-rar-compressed': '.rar',
        'application/x-7z-compressed': '.7z',
        'application/x-tar': '.tar',
        'application/gzip': '.gz',
        
        # 其他
        'application/octet-stream': '.bin',
    }
    
    if mime_type in mime_extensions:
        return mime_extensions[mime_type]
    
    # 根据媒体类型设置默认扩展名
    default_extensions = {
        'photo': '.jpg',
        'video': '.mp4',
        'document': '.bin',
        'audio': '.mp3',
        'voice': '.ogg',
        'sticker': '.webp',
        'animation': '.gif',
        'video_note': '.mp4'
    }
    
    return default_extensions.get(media_type, '.bin')


def ensure_unique_filename(file_path: Path) -> Path:
    """
    确保文件名唯一，如果文件已存在则添加数字后缀
    
    Args:
        file_path: 文件路径
        
    Returns:
        Path: 唯一的文件路径
    """
    if not file_path.exists():
        return file_path
    
    # 分离文件名和扩展名
    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    
    # 添加数字后缀
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化的文件大小
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def create_directory_structure(base_path: Path, channel_id: str) -> Path:
    """
    创建下载目录结构
    
    Args:
        base_path: 基础路径
        channel_id: 频道ID
        
    Returns:
        Path: 创建的目录路径
    """
    # 清理频道ID作为目录名
    clean_channel = sanitize_filename(channel_id)
    
    # 创建目录结构：base_path/channel_name/YYYY-MM-DD
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    download_dir = base_path / clean_channel / date_str
    download_dir.mkdir(parents=True, exist_ok=True)
    
    return download_dir


def get_safe_path(path_str: str) -> Optional[Path]:
    """
    获取安全的路径对象
    
    Args:
        path_str: 路径字符串
        
    Returns:
        Optional[Path]: 安全的路径对象，如果路径无效则返回None
    """
    try:
        path = Path(path_str)
        # 检查路径是否包含危险字符
        if '..' in str(path):
            return None
        # 检查是否为绝对路径
        if path.is_absolute():
            return None
        # 检查是否以/开头（Unix风格的绝对路径）
        if str(path).startswith('/'):
            return None
        return path
    except Exception:
        return None
