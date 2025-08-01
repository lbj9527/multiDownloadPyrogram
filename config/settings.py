"""
统一配置管理
从test_downloader_stream.py提取的配置参数
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class TelegramConfig:
    """Telegram API 配置"""
    # 从test_downloader_stream.py提取的硬编码配置
    api_id: int = 25098445
    api_hash: str = "cc2fa5a762621d306d8de030614e4555"
    proxy_host: str = "127.0.0.1"
    proxy_port: int = 7890
    
    # 会话配置
    session_directory: str = "sessions"
    session_names: List[str] = None
    
    def __post_init__(self):
        if self.session_names is None:
            # 默认会话名称（从test_downloader_stream.py提取）
            self.session_names = [
                "client_8618758361347_1",
                "client_8618758361347_2", 
                "client_8618758361347_3"
            ]

@dataclass
class DownloadConfig:
    """下载配置"""
    # 从test_downloader_stream.py提取的配置
    download_dir: str = "downloads"
    max_concurrent_clients: int = 3
    
    # 下载策略配置
    chunk_size: int = 1024 * 1024  # 1MB
    stream_threshold_mb: float = 50.0  # 大于50MB使用流式下载
    
    # 消息范围配置（从test_downloader_stream.py提取）
    start_message_id: int = 72710
    end_message_id: int = 72849
    
    # 频道配置
    channel: str = "@csdkl"  # 默认频道

@dataclass
class MonitoringConfig:
    """监控配置"""
    log_level: str = "INFO"
    log_directory: str = "logs"
    enable_bandwidth_monitor: bool = True
    stats_update_interval: int = 5  # 秒

@dataclass
class AppConfig:
    """应用总配置"""
    telegram: TelegramConfig = None
    download: DownloadConfig = None
    monitoring: MonitoringConfig = None
    
    def __post_init__(self):
        if self.telegram is None:
            self.telegram = TelegramConfig()
        if self.download is None:
            self.download = DownloadConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
    
    @classmethod
    def from_test_downloader_stream(cls):
        """从test_downloader_stream.py的配置创建AppConfig"""
        return cls(
            telegram=TelegramConfig(),
            download=DownloadConfig(),
            monitoring=MonitoringConfig()
        )
