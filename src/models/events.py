#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件数据模型
"""

from typing import Any, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class EventType(str, Enum):
    """事件类型枚举"""
    # 客户端事件
    CLIENT_LOGIN_START = "client_login_start"
    CLIENT_LOGIN_SUCCESS = "client_login_success"
    CLIENT_LOGIN_FAILED = "client_login_failed"
    CLIENT_DISCONNECTED = "client_disconnected"
    CLIENT_RECONNECTED = "client_reconnected"
    CLIENT_STATUS_CHANGED = "client_status_changed"
    
    # 下载事件
    DOWNLOAD_STARTED = "download_started"
    DOWNLOAD_PROGRESS = "download_progress"
    DOWNLOAD_FILE_COMPLETED = "download_file_completed"
    DOWNLOAD_COMPLETED = "download_completed"
    DOWNLOAD_FAILED = "download_failed"
    DOWNLOAD_CANCELLED = "download_cancelled"
    DOWNLOAD_PAUSED = "download_paused"
    DOWNLOAD_RESUMED = "download_resumed"
    
    # 错误事件
    ERROR_FLOOD_WAIT = "error_flood_wait"
    ERROR_NETWORK = "error_network"
    ERROR_AUTH = "error_auth"
    ERROR_PERMISSION = "error_permission"
    ERROR_UNKNOWN = "error_unknown"
    
    # 系统事件
    APP_STARTED = "app_started"
    APP_SHUTDOWN = "app_shutdown"
    CONFIG_UPDATED = "config_updated"


class EventSeverity(str, Enum):
    """事件严重程度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """基础事件模型"""
    
    event_id: str = Field(..., description="事件ID")
    event_type: EventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="事件严重程度")
    message: str = Field(..., description="事件消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="事件数据")
    source: Optional[str] = Field(default=None, description="事件源")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class ClientEvent(BaseEvent):
    """客户端事件"""
    
    client_name: str = Field(..., description="客户端名称")
    client_status: Optional[str] = Field(default=None, description="客户端状态")


class DownloadEvent(BaseEvent):
    """下载事件"""
    
    task_id: str = Field(..., description="任务ID")
    channel_id: Optional[str] = Field(default=None, description="频道ID")
    progress_data: Optional[Dict[str, Any]] = Field(default=None, description="进度数据")


class ErrorEvent(BaseEvent):
    """错误事件"""
    
    error_code: Optional[str] = Field(default=None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    retry_count: int = Field(default=0, description="重试次数")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.severity = EventSeverity.ERROR


class SystemEvent(BaseEvent):
    """系统事件"""
    
    system_info: Optional[Dict[str, Any]] = Field(default=None, description="系统信息")


# 事件工厂函数
def create_client_event(
    event_type: EventType,
    client_name: str,
    message: str,
    client_status: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO
) -> ClientEvent:
    """创建客户端事件"""
    import uuid
    return ClientEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        message=message,
        client_name=client_name,
        client_status=client_status,
        data=data,
        severity=severity,
        source="client_manager"
    )


def create_download_event(
    event_type: EventType,
    task_id: str,
    message: str,
    channel_id: Optional[str] = None,
    progress_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO
) -> DownloadEvent:
    """创建下载事件"""
    import uuid
    return DownloadEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        message=message,
        task_id=task_id,
        channel_id=channel_id,
        progress_data=progress_data,
        data=data,
        severity=severity,
        source="download_manager"
    )


def create_error_event(
    event_type: EventType,
    message: str,
    error_code: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    retry_count: int = 0,
    data: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
) -> ErrorEvent:
    """创建错误事件"""
    import uuid
    return ErrorEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        message=message,
        error_code=error_code,
        error_details=error_details,
        retry_count=retry_count,
        data=data,
        source=source
    )


class ConfigUpdatedEvent(BaseModel):
    """配置更新事件"""
    model_config = ConfigDict(extra='forbid')

    event_id: str = Field(..., description="事件ID")
    event_type: EventType = Field(default=EventType.CONFIG_UPDATED, description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    message: str = Field(..., description="事件消息")
    config_type: str = Field(..., description="配置类型")
    config_data: Optional[Dict[str, Any]] = Field(None, description="配置数据")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="严重程度")
    source: str = Field(default="config", description="事件源")


def create_system_event(
    event_type: EventType,
    message: str,
    system_info: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO
) -> SystemEvent:
    """创建系统事件"""
    import uuid
    return SystemEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        message=message,
        system_info=system_info,
        data=data,
        severity=severity,
        source="system"
    )


def create_config_updated_event(
    message: str,
    config_type: str,
    config_data: Optional[Dict[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO
) -> ConfigUpdatedEvent:
    """创建配置更新事件"""
    import uuid
    return ConfigUpdatedEvent(
        event_id=str(uuid.uuid4()),
        message=message,
        config_type=config_type,
        config_data=config_data,
        severity=severity
    )
