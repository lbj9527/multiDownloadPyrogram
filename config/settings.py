"""
应用程序设置配置
集中管理所有配置项，支持环境变量和配置文件
使用Pydantic进行配置验证（如果可用）
"""

import os
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

try:
    from pydantic import BaseModel, Field
    try:
        # Pydantic V2
        from pydantic import field_validator, model_validator
        PYDANTIC_V2 = True
    except ImportError:
        # Pydantic V1
        from pydantic import validator as field_validator, root_validator as model_validator
        PYDANTIC_V2 = False
    PYDANTIC_AVAILABLE = True
except ImportError:
    from dataclasses import dataclass
    PYDANTIC_AVAILABLE = False
    PYDANTIC_V2 = False

from .validators import ConfigValidator


# 配置基类
if PYDANTIC_AVAILABLE:
    class ConfigBase(BaseModel):
        """Pydantic配置基类"""
        class Config:
            # 允许额外字段
            extra = "forbid"
            # 验证赋值
            validate_assignment = True
            # 使用枚举值
            use_enum_values = True
else:
    # 如果没有Pydantic，使用dataclass作为基类
    ConfigBase = object


if PYDANTIC_AVAILABLE:
    class TelegramConfig(ConfigBase):
        """Telegram API 配置"""
        api_id: int = Field(..., description="Telegram API ID", gt=0)
        api_hash: str = Field(..., description="Telegram API Hash", min_length=32, max_length=32)
        phone_number: str = Field(..., description="手机号码", pattern=r'^\+\d{10,15}$')
        proxy: Optional[Dict[str, Union[str, int]]] = Field(None, description="代理配置")

        @field_validator('api_hash')
        @classmethod
        def validate_api_hash(cls, v):
            if not v or len(v) != 32:
                raise ValueError('API Hash必须是32位字符串')
            return v

        @field_validator('proxy')
        @classmethod
        def validate_proxy(cls, v):
            if v is not None:
                errors = ConfigValidator.validate_proxy_config(v)
                if errors:
                    raise ValueError(f"代理配置错误: {'; '.join(errors)}")
            return v
else:
    @dataclass
    class TelegramConfig:
        """Telegram API 配置"""
        api_id: int
        api_hash: str
        phone_number: str
        proxy: Optional[Dict[str, Union[str, int]]] = None


if PYDANTIC_AVAILABLE:
    class DownloadConfig(ConfigBase):
        """下载配置"""
        target_channel: str = Field(..., description="目标频道", min_length=1)
        start_message_id: int = Field(..., description="开始消息ID", gt=0)
        end_message_id: int = Field(..., description="结束消息ID", gt=0)
        batch_size: int = Field(200, description="批次大小", ge=1, le=200)
        max_concurrent_clients: int = Field(3, description="最大并发客户端数", ge=1, le=10)
        download_directory: str = Field("downloads", description="下载目录")
        session_directory: str = Field("sessions", description="会话文件目录")

    class UploadConfig(ConfigBase):
        """上传配置"""
        enabled: bool = Field(False, description="是否启用上传功能")
        target_channel: str = Field("", description="上传目标频道")
        preserve_media_groups: bool = Field(True, description="保持媒体组格式")
        preserve_captions: bool = Field(True, description="保持原始说明文字")
        upload_delay: float = Field(1.0, description="上传间隔（秒）", ge=0.1, le=10.0)
        max_retries: int = Field(3, description="最大重试次数", ge=1, le=10)

        def __post_init__(self):
            """后初始化验证"""
            if hasattr(self, 'start_message_id') and hasattr(self, 'end_message_id'):
                if self.start_message_id >= self.end_message_id:
                    raise ValueError('开始消息ID必须小于结束消息ID')
else:
    @dataclass
    class DownloadConfig:
        """下载配置"""
        target_channel: str
        start_message_id: int
        end_message_id: int
        batch_size: int = 200
        max_concurrent_clients: int = 3
        download_directory: str = "downloads"
        session_directory: str = "sessions"

    @dataclass
    class UploadConfig:
        """上传配置"""
        enabled: bool = False
        target_channel: str = ""
        preserve_media_groups: bool = True
        preserve_captions: bool = True
        upload_delay: float = 1.0
        max_retries: int = 3
    
    @property
    def total_messages(self) -> int:
        return self.end_message_id - self.start_message_id + 1


if PYDANTIC_AVAILABLE:
    class StorageConfig(ConfigBase):
        """存储配置"""
        storage_mode: str = Field("upload", description="存储模式 (raw/upload/hybrid)")
        archive_after_days: int = Field(30, description="归档天数", ge=1)
        cleanup_after_days: int = Field(90, description="清理天数", ge=1)

    class LoggingConfig(ConfigBase):
        """日志配置"""
        level: str = Field("INFO", description="日志级别")
        format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式")
        file_enabled: bool = Field(True, description="启用文件日志")
        file_path: str = Field("logs/downloader.log", description="日志文件路径")
        console_enabled: bool = Field(True, description="启用控制台日志")
        verbose_pyrogram: bool = Field(False, description="详细Pyrogram日志")
else:
    @dataclass
    class StorageConfig:
        """存储配置"""
        storage_mode: str = "upload"  # 支持 raw/upload/hybrid 模式
        archive_after_days: int = 30
        cleanup_after_days: int = 90

    @dataclass
    class LoggingConfig:
        """日志配置"""
        level: str = "INFO"
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_enabled: bool = True
        file_path: str = "logs/downloader.log"
        console_enabled: bool = True
        verbose_pyrogram: bool = False


class AppSettings:
    """应用程序主配置类"""

    def __init__(self, config_file: Optional[str] = None):
        # 准备配置数据
        telegram_data = {
            "api_id": int(os.getenv("API_ID", "25098445")),
            "api_hash": os.getenv("API_HASH", "cc2fa5a762621d306d8de030614e4555"),
            "phone_number": os.getenv("PHONE_NUMBER", "+8618758361347"),
            "proxy": {
                "scheme": "socks5",
                "hostname": "127.0.0.1",
                "port": 7890
            } if os.getenv("USE_PROXY", "true").lower() == "true" else None
        }

        download_data = {
            "target_channel": os.getenv("TARGET_CHANNEL", "csdkl"),
            "start_message_id": int(os.getenv("START_MESSAGE_ID", "72126")),
            "end_message_id": int(os.getenv("END_MESSAGE_ID", "72155")),
            "batch_size": int(os.getenv("BATCH_SIZE", "200")),
            "max_concurrent_clients": int(os.getenv("MAX_CLIENTS", "3")),
            "download_directory": os.getenv("DOWNLOAD_DIR", "downloads"),
            "session_directory": os.getenv("SESSION_DIR", "sessions")
        }

        upload_data = {
            "enabled": os.getenv("UPLOAD_ENABLED", "true").lower() == "true",  # 默认启用
            "target_channel": os.getenv("UPLOAD_TARGET_CHANNEL", "@wghrwf"),  # 默认目标频道
            "preserve_media_groups": os.getenv("PRESERVE_MEDIA_GROUPS", "true").lower() == "true",
            "preserve_captions": os.getenv("PRESERVE_CAPTIONS", "true").lower() == "true",
            "upload_delay": float(os.getenv("UPLOAD_DELAY", "1.5")),  # 默认1.5秒延迟
            "max_retries": int(os.getenv("UPLOAD_MAX_RETRIES", "3"))
        }

        # 创建配置对象
        if PYDANTIC_AVAILABLE:
            self.telegram = TelegramConfig(**telegram_data)
            self.download = DownloadConfig(**download_data)
            self.upload = UploadConfig(**upload_data)
            self.storage = StorageConfig()
            self.logging = LoggingConfig()
        else:
            self.telegram = TelegramConfig(**telegram_data)
            self.download = DownloadConfig(**download_data)
            self.upload = UploadConfig(**upload_data)
            self.storage = StorageConfig()
            self.logging = LoggingConfig()
        
        # 如果提供了配置文件，加载配置
        if config_file and Path(config_file).exists():
            self._load_from_file(config_file)
    
    def _load_from_file(self, config_file: str):
        """从配置文件加载设置"""
        # TODO: 实现配置文件加载逻辑（JSON/YAML）
        pass
    
    def get_session_files(self) -> List[str]:
        """获取会话文件列表"""
        session_names = [
            "client_session_1",
            "client_session_2",
            "client_session_3"
        ]

        session_files = []
        for session_name in session_names[:self.download.max_concurrent_clients]:
            session_files.append(session_name)

        return session_files
    
    def get_download_directory(self) -> Path:
        """获取下载目录路径"""
        return Path(self.download.download_directory)
    
    def validate(self) -> List[str]:
        """验证配置的有效性"""
        if PYDANTIC_AVAILABLE:
            # Pydantic模型会在创建时自动验证
            # 这里只需要进行额外的业务逻辑验证
            return ConfigValidator.validate_complete_config(self)
        else:
            # 对于dataclass，使用传统验证方式
            errors = []

            if not self.telegram.api_id:
                errors.append("API_ID 不能为空")

            if not self.telegram.api_hash:
                errors.append("API_HASH 不能为空")

            if self.download.start_message_id >= self.download.end_message_id:
                errors.append("开始消息ID必须小于结束消息ID")

            if self.download.batch_size <= 0 or self.download.batch_size > 200:
                errors.append("批次大小必须在1-200之间")

            return errors


# 全局配置实例
app_settings = AppSettings()
