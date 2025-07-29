"""
应用程序设置配置
集中管理所有配置项，支持环境变量和配置文件
使用Pydantic进行配置验证（如果可用）
"""

import os
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

# 加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    # 如果没有安装python-dotenv，给出提示
    print("⚠️ 建议安装 python-dotenv 以支持.env文件: pip install python-dotenv")

# 导入常量
from .constants import (
    DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE,
    DEFAULT_MAX_RETRIES, DEFAULT_UPLOAD_ENABLED, DEFAULT_UPLOAD_DELAY,
    DEFAULT_PRESERVE_MEDIA_GROUPS, DEFAULT_PRESERVE_CAPTIONS, DEFAULT_BATCH_DELAY,
    DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT, DEFAULT_LOG_FILE,
    DEFAULT_LOG_FILE_ENABLED, DEFAULT_LOG_CONSOLE_ENABLED, DEFAULT_VERBOSE_PYROGRAM,
    STORAGE_MODES, DEFAULT_SESSION_NAMES, DEFAULT_SESSION_DIRECTORY
)

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
from .task_distribution import TaskDistributionConfig


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
        batch_size: int = Field(DEFAULT_BATCH_SIZE, description="批次大小", ge=1, le=MAX_BATCH_SIZE)
        max_concurrent_clients: int = Field(3, description="最大并发客户端数", ge=1, le=10)
        download_directory: str = Field("downloads", description="下载目录")
        session_directory: str = Field(DEFAULT_SESSION_DIRECTORY, description="会话文件目录")
        batch_delay: float = Field(DEFAULT_BATCH_DELAY, description="批次间延迟（秒）", ge=0.0, le=5.0)

    class UploadConfig(ConfigBase):
        """上传配置"""
        enabled: bool = Field(DEFAULT_UPLOAD_ENABLED, description="是否启用上传功能")
        target_channel: str = Field("", description="上传目标频道")
        preserve_media_groups: bool = Field(DEFAULT_PRESERVE_MEDIA_GROUPS, description="保持媒体组格式")
        preserve_captions: bool = Field(DEFAULT_PRESERVE_CAPTIONS, description="保持原始说明文字")
        upload_delay: float = Field(DEFAULT_UPLOAD_DELAY, description="上传间隔（秒）", ge=0.1, le=10.0)
        max_retries: int = Field(DEFAULT_MAX_RETRIES, description="最大重试次数", ge=1, le=10)

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
        batch_size: int = DEFAULT_BATCH_SIZE
        max_concurrent_clients: int = 3
        download_directory: str = "downloads"
        session_directory: str = DEFAULT_SESSION_DIRECTORY
        batch_delay: float = DEFAULT_BATCH_DELAY

    @dataclass
    class UploadConfig:
        """上传配置"""
        enabled: bool = DEFAULT_UPLOAD_ENABLED
        target_channel: str = ""
        preserve_media_groups: bool = DEFAULT_PRESERVE_MEDIA_GROUPS
        preserve_captions: bool = DEFAULT_PRESERVE_CAPTIONS
        upload_delay: float = DEFAULT_UPLOAD_DELAY
        max_retries: int = DEFAULT_MAX_RETRIES
    
    @property
    def total_messages(self) -> int:
        return self.end_message_id - self.start_message_id + 1


if PYDANTIC_AVAILABLE:
    class StorageConfig(ConfigBase):
        """存储配置"""
        storage_mode: str = Field("upload", description="存储模式 (raw/upload/hybrid)")
        archive_after_days: int = Field(30, description="归档天数", ge=1)
        cleanup_after_days: int = Field(90, description="清理天数", ge=1)

        @classmethod
        def from_env(cls) -> 'StorageConfig':
            """从环境变量创建配置"""
            # 验证存储模式
            storage_mode = os.getenv("STORAGE_MODE", "upload")
            if storage_mode not in STORAGE_MODES:
                storage_mode = "upload"

            return cls(
                storage_mode=storage_mode,
                archive_after_days=int(os.getenv("ARCHIVE_AFTER_DAYS", "30")),
                cleanup_after_days=int(os.getenv("CLEANUP_AFTER_DAYS", "90"))
            )

    class LoggingConfig(ConfigBase):
        """日志配置"""
        level: str = Field("INFO", description="日志级别")
        format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="日志格式")
        file_enabled: bool = Field(True, description="启用文件日志")
        file_path: str = Field("logs/downloader.log", description="日志文件路径")
        console_enabled: bool = Field(True, description="启用控制台日志")
        verbose_pyrogram: bool = Field(False, description="详细Pyrogram日志")

        @classmethod
        def from_env(cls) -> 'LoggingConfig':
            """从环境变量创建配置"""
            return cls(
                level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL),
                format=os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT),
                file_enabled=os.getenv("LOG_FILE_ENABLED", str(DEFAULT_LOG_FILE_ENABLED).lower()).lower() == "true",
                file_path=os.getenv("LOG_FILE_PATH", DEFAULT_LOG_FILE),
                console_enabled=os.getenv("LOG_CONSOLE_ENABLED", str(DEFAULT_LOG_CONSOLE_ENABLED).lower()).lower() == "true",
                verbose_pyrogram=os.getenv("VERBOSE_PYROGRAM", str(DEFAULT_VERBOSE_PYROGRAM).lower()).lower() == "true"
            )
else:
    @dataclass
    class StorageConfig:
        """存储配置"""
        storage_mode: str = "upload"  # 支持 raw/upload/hybrid 模式
        archive_after_days: int = 30
        cleanup_after_days: int = 90

        @classmethod
        def from_env(cls) -> 'StorageConfig':
            """从环境变量创建配置"""
            # 验证存储模式
            storage_mode = os.getenv("STORAGE_MODE", "upload")
            if storage_mode not in STORAGE_MODES:
                storage_mode = "upload"

            return cls(
                storage_mode=storage_mode,
                archive_after_days=int(os.getenv("ARCHIVE_AFTER_DAYS", "30")),
                cleanup_after_days=int(os.getenv("CLEANUP_AFTER_DAYS", "90"))
            )

    @dataclass
    class LoggingConfig:
        """日志配置"""
        level: str = "INFO"
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_enabled: bool = True
        file_path: str = "logs/downloader.log"
        console_enabled: bool = True
        verbose_pyrogram: bool = False

        @classmethod
        def from_env(cls) -> 'LoggingConfig':
            """从环境变量创建配置"""
            return cls(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                file_enabled=os.getenv("LOG_FILE_ENABLED", "true").lower() == "true",
                file_path=os.getenv("LOG_FILE_PATH", "logs/downloader.log"),
                console_enabled=os.getenv("LOG_CONSOLE_ENABLED", "true").lower() == "true",
                verbose_pyrogram=os.getenv("VERBOSE_PYROGRAM", "false").lower() == "true"
            )


class AppSettings:
    """应用程序主配置类"""

    def __init__(self, config_file: Optional[str] = None):
        # 准备配置数据
        telegram_data = {
            "api_id": int(os.getenv("API_ID", "0")),  # 必须通过环境变量设置
            "api_hash": os.getenv("API_HASH", ""),  # 必须通过环境变量设置
            "phone_number": os.getenv("PHONE_NUMBER", ""),  # 必须通过环境变量设置
            "proxy": {
                "scheme": "socks5",
                "hostname": os.getenv("PROXY_HOST", "127.0.0.1"),
                "port": int(os.getenv("PROXY_PORT", "7890"))
            } if os.getenv("USE_PROXY", "false").lower() == "true" else None
        }

        download_data = {
            "target_channel": os.getenv("TARGET_CHANNEL", ""),  # 必须通过环境变量设置
            "start_message_id": int(os.getenv("START_MESSAGE_ID", "1")),  # 默认从消息1开始
            "end_message_id": int(os.getenv("END_MESSAGE_ID", "100")),  # 默认到消息100
            "batch_size": int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
            "max_concurrent_clients": int(os.getenv("MAX_CONCURRENT_CLIENTS", "3")),
            "download_directory": os.getenv("DOWNLOAD_DIRECTORY", "downloads"),
            "session_directory": os.getenv("SESSION_DIRECTORY", DEFAULT_SESSION_DIRECTORY),
            "batch_delay": float(os.getenv("DOWNLOAD_BATCH_DELAY", str(DEFAULT_BATCH_DELAY)))  # 批次间延迟
        }

        upload_data = {
            "enabled": os.getenv("UPLOAD_ENABLED", str(DEFAULT_UPLOAD_ENABLED).lower()).lower() == "true",  # 默认禁用
            "target_channel": os.getenv("UPLOAD_TARGET_CHANNEL", ""),  # 必须通过环境变量设置
            "preserve_media_groups": os.getenv("PRESERVE_MEDIA_GROUPS", str(DEFAULT_PRESERVE_MEDIA_GROUPS).lower()).lower() == "true",
            "preserve_captions": os.getenv("PRESERVE_CAPTIONS", str(DEFAULT_PRESERVE_CAPTIONS).lower()).lower() == "true",
            "upload_delay": float(os.getenv("UPLOAD_DELAY", str(DEFAULT_UPLOAD_DELAY))),  # 默认延迟
            "max_retries": int(os.getenv("UPLOAD_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        }

        # 创建配置对象
        if PYDANTIC_AVAILABLE:
            self.telegram = TelegramConfig(**telegram_data)
            self.download = DownloadConfig(**download_data)
            self.upload = UploadConfig(**upload_data)
            self.storage = StorageConfig.from_env()
            self.logging = LoggingConfig.from_env()
            self.task_distribution = TaskDistributionConfig.from_env()
        else:
            self.telegram = TelegramConfig(**telegram_data)
            self.download = DownloadConfig(**download_data)
            self.upload = UploadConfig(**upload_data)
            self.storage = StorageConfig.from_env()
            self.logging = LoggingConfig.from_env()
            self.task_distribution = TaskDistributionConfig.from_env()
        
        # 如果提供了配置文件，加载配置
        if config_file and Path(config_file).exists():
            self._load_from_file(config_file)
    
    def _load_from_file(self, config_file: str):
        """从配置文件加载设置"""
        # TODO: 实现配置文件加载逻辑（JSON/YAML）
        pass
    
    def get_session_files(self) -> List[str]:
        """获取会话文件列表"""
        session_files = []
        for session_name in DEFAULT_SESSION_NAMES[:self.download.max_concurrent_clients]:
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

            if not self.telegram.api_id or self.telegram.api_id == 0:
                errors.append("API_ID 不能为空，请在.env文件中设置")

            if not self.telegram.api_hash:
                errors.append("API_HASH 不能为空，请在.env文件中设置")

            if not self.telegram.phone_number:
                errors.append("PHONE_NUMBER 不能为空，请在.env文件中设置")

            if not self.download.target_channel:
                errors.append("TARGET_CHANNEL 不能为空，请在.env文件中设置")

            if self.download.start_message_id >= self.download.end_message_id:
                errors.append("开始消息ID必须小于结束消息ID")

            if self.download.batch_size <= 0 or self.download.batch_size > 200:
                errors.append("批次大小必须在1-200之间")

            # 如果启用上传功能，检查上传目标频道
            if self.upload.enabled and not self.upload.target_channel:
                errors.append("启用上传功能时，UPLOAD_TARGET_CHANNEL 不能为空")

            return errors


# 全局配置实例 - 延迟初始化
app_settings = None

def get_app_settings():
    """获取应用配置实例（延迟初始化）"""
    global app_settings
    if app_settings is None:
        app_settings = AppSettings()
    return app_settings

# 为了向后兼容，在模块级别提供实例
try:
    app_settings = AppSettings()
except Exception as e:
    print(f"⚠️ 配置初始化警告: {e}")
    app_settings = None
