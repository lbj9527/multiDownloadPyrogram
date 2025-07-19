#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载配置数据模型
"""

import re
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class DownloadStatus(str, Enum):
    """下载状态枚举"""
    PENDING = "pending"  # 等待中
    DOWNLOADING = "downloading"  # 下载中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"  # 已暂停


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"  # 文本消息
    PHOTO = "photo"  # 图片
    VIDEO = "video"  # 视频
    DOCUMENT = "document"  # 文档
    AUDIO = "audio"  # 音频
    VOICE = "voice"  # 语音
    STICKER = "sticker"  # 贴纸
    ANIMATION = "animation"  # 动画
    VIDEO_NOTE = "video_note"  # 视频笔记


class DownloadConfig(BaseModel):
    """下载配置"""
    
    channel_id: str = Field(..., description="频道ID或用户名")
    start_message_id: int = Field(default=1, description="起始消息ID")
    message_count: int = Field(..., description="下载消息数量")
    download_path: str = Field(default="./downloads", description="下载路径")
    include_media: bool = Field(default=True, description="是否包含媒体文件")
    include_text: bool = Field(default=True, description="是否包含文本消息")
    media_types: list[MessageType] = Field(default_factory=lambda: list(MessageType), description="包含的媒体类型")
    max_file_size: Optional[int] = Field(default=None, description="最大文件大小（字节）")
    
    @field_validator('channel_id')
    @classmethod
    def validate_channel_id(cls, v):
        """验证频道ID"""
        if not isinstance(v, str):
            raise ValueError("频道ID必须为字符串")
        if not v.strip():
            raise ValueError("频道ID不能为空")

        # 支持频道用户名（@开头）或数字ID
        v = v.strip()
        if v.startswith('@'):
            # 频道用户名格式验证
            if not re.match(r'^@[a-zA-Z][a-zA-Z0-9_]{4,31}$', v):
                raise ValueError("频道用户名格式错误")
        elif v.startswith('-100'):
            # 超级群组ID格式验证
            if not re.match(r'^-100\d{10,13}$', v):
                raise ValueError("频道ID格式错误")
        elif v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
            # 普通群组或用户ID
            pass
        else:
            raise ValueError("频道ID格式错误，请输入有效的频道ID或用户名")

        return v

    @field_validator('start_message_id')
    @classmethod
    def validate_start_message_id(cls, v):
        """验证起始消息ID"""
        if not isinstance(v, int) or v < 1:
            raise ValueError("起始消息ID必须为正整数")
        return v

    @field_validator('message_count')
    @classmethod
    def validate_message_count(cls, v):
        """验证消息数量"""
        if not isinstance(v, int) or v < 1:
            raise ValueError("消息数量必须为正整数")
        if v > 1000:
            raise ValueError("消息数量不能超过1000")
        return v

    @field_validator('download_path')
    @classmethod
    def validate_download_path(cls, v):
        """验证下载路径"""
        if not isinstance(v, str):
            raise ValueError("下载路径必须为字符串")
        if not v.strip():
            raise ValueError("下载路径不能为空")

        # 创建路径对象进行验证
        try:
            path = Path(v)
            # 检查路径是否有效
            if path.is_absolute():
                # 绝对路径检查
                if not path.parent.exists():
                    raise ValueError(f"下载路径的父目录不存在: {path.parent}")
            return str(path)
        except Exception as e:
            raise ValueError(f"下载路径无效: {e}")

    @field_validator('max_file_size')
    @classmethod
    def validate_max_file_size(cls, v):
        """验证最大文件大小"""
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError("最大文件大小必须为正整数")
            # 限制最大文件大小为2GB
            if v > 2 * 1024 * 1024 * 1024:
                raise ValueError("最大文件大小不能超过2GB")
        return v


class DownloadProgress(BaseModel):
    """下载进度"""
    
    total_messages: int = Field(default=0, description="总消息数")
    downloaded_messages: int = Field(default=0, description="已下载消息数")
    total_files: int = Field(default=0, description="总文件数")
    downloaded_files: int = Field(default=0, description="已下载文件数")
    total_size: int = Field(default=0, description="总大小（字节）")
    downloaded_size: int = Field(default=0, description="已下载大小（字节）")
    current_file: Optional[str] = Field(default=None, description="当前下载文件")
    download_speed: float = Field(default=0.0, description="下载速度（字节/秒）")
    eta: Optional[int] = Field(default=None, description="预计剩余时间（秒）")
    status: DownloadStatus = Field(default=DownloadStatus.PENDING, description="下载状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    
    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_messages == 0:
            return 0.0
        return (self.downloaded_messages / self.total_messages) * 100
    
    @property
    def size_progress_percentage(self) -> float:
        """计算大小进度百分比"""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded_size / self.total_size) * 100
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def format_speed(self) -> str:
        """格式化下载速度"""
        return f"{self.format_size(int(self.download_speed))}/s"
    
    def format_eta(self) -> str:
        """格式化预计剩余时间"""
        if self.eta is None:
            return "未知"
        
        if self.eta < 60:
            return f"{self.eta}秒"
        elif self.eta < 3600:
            minutes = self.eta // 60
            seconds = self.eta % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = self.eta // 3600
            minutes = (self.eta % 3600) // 60
            return f"{hours}小时{minutes}分钟"


class DownloadTask(BaseModel):
    """下载任务"""
    
    task_id: str = Field(..., description="任务ID")
    config: DownloadConfig = Field(..., description="下载配置")
    progress: DownloadProgress = Field(default_factory=DownloadProgress, description="下载进度")
    created_at: str = Field(..., description="创建时间")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    client_assignments: Dict[str, list] = Field(default_factory=dict, description="客户端任务分配")
    
    def is_active(self) -> bool:
        """检查任务是否活跃"""
        return self.progress.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED]
    
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return self.progress.status == DownloadStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.progress.status == DownloadStatus.FAILED
