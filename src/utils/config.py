"""
配置管理模块
负责管理应用程序的所有配置项，包括API配置、代理配置、下载配置等
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json


@dataclass
class APIConfig:
    """Telegram API配置"""
    api_id: int
    api_hash: str
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """从环境变量加载API配置"""
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        if not api_id or not api_hash:
            raise ValueError("请设置环境变量 TELEGRAM_API_ID 和 TELEGRAM_API_HASH")
        
        return cls(api_id=int(api_id), api_hash=api_hash)


@dataclass
class ProxyConfig:
    """代理配置"""
    scheme: str = "socks5"
    hostname: str = "127.0.0.1"
    port: int = 7890
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为Pyrogram客户端所需的字典格式"""
        config = {
            "scheme": self.scheme,
            "hostname": self.hostname,
            "port": self.port
        }
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
        return config


@dataclass
class TaskConfig:
    """任务配置"""
    # 目标频道
    channel_username: str = ""
    
    # 消息范围
    start_message_id: Optional[int] = None
    end_message_id: Optional[int] = None
    limit: Optional[int] = 1000
    
    def __post_init__(self):
        """验证任务配置"""
        if not self.channel_username:
            raise ValueError("频道用户名不能为空")
        
        # 确保频道名以@开头
        if not self.channel_username.startswith('@'):
            self.channel_username = f"@{self.channel_username}"
        
        # 验证消息ID范围
        if (self.start_message_id is not None and 
            self.end_message_id is not None and 
            self.start_message_id > self.end_message_id):
            raise ValueError("起始消息ID不能大于结束消息ID")


@dataclass
class DownloadConfig:
    """下载配置"""
    # 客户端配置
    client_count: int = 3
    max_concurrent_transmissions: int = 1
    sleep_threshold: int = 10
    
    # 下载配置
    download_dir: str = "downloads"
    large_file_threshold: int = 50 * 1024 * 1024  # 50MB
    chunk_size: int = 1024 * 1024  # 1MB
    max_retries: int = 3
    
    # 性能配置
    max_concurrent_downloads: int = 5
    progress_update_interval: float = 1.0
    
    def __post_init__(self):
        """确保下载目录存在"""
        os.makedirs(self.download_dir, exist_ok=True)


@dataclass
class AppConfig:
    """应用程序总配置"""
    api: APIConfig
    proxy: ProxyConfig
    download: DownloadConfig
    task: TaskConfig
    
    @classmethod
    def load_from_file(cls, config_path: str = "config.json") -> 'AppConfig':
        """从配置文件加载配置"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 解析各个配置部分
            api_config = APIConfig(**config_data.get('api', {}))
            proxy_config = ProxyConfig(**config_data.get('proxy', {}))
            download_config = DownloadConfig(**config_data.get('download', {}))
            task_config = TaskConfig(**config_data.get('task', {}))
            
            return cls(api=api_config, proxy=proxy_config, download=download_config, task=task_config)
        else:
            # 使用默认配置
            return cls.default()
    
    @classmethod
    def default(cls) -> 'AppConfig':
        """创建默认配置"""
        return cls(
            api=APIConfig.from_env(),
            proxy=ProxyConfig(),
            download=DownloadConfig(),
            task=TaskConfig()
        )
    
    def save_to_file(self, config_path: str = "config.json"):
        """保存配置到文件"""
        config_data = {
            'api': {
                'api_id': self.api.api_id,
                'api_hash': self.api.api_hash
            },
            'proxy': {
                'scheme': self.proxy.scheme,
                'hostname': self.proxy.hostname,
                'port': self.proxy.port,
                'username': self.proxy.username,
                'password': self.proxy.password
            },
            'download': {
                'client_count': self.download.client_count,
                'max_concurrent_transmissions': self.download.max_concurrent_transmissions,
                'sleep_threshold': self.download.sleep_threshold,
                'download_dir': self.download.download_dir,
                'large_file_threshold': self.download.large_file_threshold,
                'chunk_size': self.download.chunk_size,
                'max_retries': self.download.max_retries,
                'max_concurrent_downloads': self.download.max_concurrent_downloads,
                'progress_update_interval': self.download.progress_update_interval
            },
            'task': {
                'channel_username': self.task.channel_username,
                'start_message_id': self.task.start_message_id,
                'end_message_id': self.task.end_message_id,
                'limit': self.task.limit
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)


# 全局配置实例
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置实例"""
    global config
    if config is None:
        config = AppConfig.default()
    return config


def init_config(config_path: str = "config.json") -> AppConfig:
    """初始化全局配置"""
    global config
    config = AppConfig.load_from_file(config_path)
    return config 