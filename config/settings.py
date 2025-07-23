"""
应用程序设置配置
集中管理所有配置项，支持环境变量和配置文件
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from pathlib import Path


@dataclass
class TelegramConfig:
    """Telegram API 配置"""
    api_id: int
    api_hash: str
    phone_number: str
    proxy: Optional[Dict[str, Union[str, int]]] = None


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
    
    @property
    def total_messages(self) -> int:
        return self.end_message_id - self.start_message_id + 1


@dataclass
class StorageConfig:
    """存储配置"""
    storage_mode: str = "raw"  # 只支持原始存储模式
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
        self.telegram = TelegramConfig(
            api_id=int(os.getenv("API_ID", "25098445")),
            api_hash=os.getenv("API_HASH", "cc2fa5a762621d306d8de030614e4555"),
            phone_number=os.getenv("PHONE_NUMBER", "+8618758361347"),
            proxy={
                "scheme": "socks5",
                "hostname": "127.0.0.1",
                "port": 7890
            } if os.getenv("USE_PROXY", "true").lower() == "true" else None
        )
        
        self.download = DownloadConfig(
            target_channel=os.getenv("TARGET_CHANNEL", "csdkl"),
            start_message_id=int(os.getenv("START_MESSAGE_ID", "72006")),
            end_message_id=int(os.getenv("END_MESSAGE_ID", "72155")),
            batch_size=int(os.getenv("BATCH_SIZE", "200")),
            max_concurrent_clients=int(os.getenv("MAX_CLIENTS", "3"))
        )
        
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
