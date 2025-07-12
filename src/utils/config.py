"""
配置管理模块

提供配置的读取、验证和管理功能，支持多种配置源
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
import configparser
from dataclasses import dataclass, field

from .exceptions import ConfigError, ValidationError


@dataclass
class ProxyConfig:
    """代理配置"""
    scheme: str = "socks5"
    hostname: str = "127.0.0.1"
    port: int = 7890
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        proxy_dict = {
            "scheme": self.scheme,
            "hostname": self.hostname,
            "port": self.port
        }
        if self.username:
            proxy_dict["username"] = self.username
        if self.password:
            proxy_dict["password"] = self.password
        return proxy_dict
    
    def validate(self) -> None:
        """验证代理配置"""
        if self.scheme not in ["socks5", "socks4", "http"]:
            raise ValidationError(f"不支持的代理协议: {self.scheme}")
        if not (1 <= self.port <= 65535):
            raise ValidationError(f"代理端口无效: {self.port}")
        if not self.hostname:
            raise ValidationError("代理主机名不能为空")


@dataclass
class TelegramConfig:
    """Telegram配置"""
    api_id: int = 0
    api_hash: str = ""
    phone_number: Optional[str] = None
    session_string: Optional[str] = None
    max_concurrent_transmissions: int = 1
    sleep_threshold: int = 10
    no_updates: bool = True
    
    def validate(self) -> None:
        """验证Telegram配置"""
        if not self.api_id:
            raise ValidationError("API ID不能为空")
        if not self.api_hash:
            raise ValidationError("API Hash不能为空")
        if not self.phone_number and not self.session_string:
            raise ValidationError("必须提供电话号码或会话字符串")


@dataclass
class DownloadConfig:
    """下载配置"""
    download_path: str = "downloads"
    max_concurrent_downloads: int = 5
    max_clients: int = 3
    chunk_size: int = 1024 * 1024  # 1MB
    large_file_threshold: int = 50 * 1024 * 1024  # 50MB
    max_file_size: int = 2 * 1024 * 1024 * 1024  # 2GB
    timeout: int = 300  # 5分钟
    retry_count: int = 3
    retry_delay: float = 1.0
    skip_existing: bool = True
    
    def validate(self) -> None:
        """验证下载配置"""
        if self.max_concurrent_downloads < 1:
            raise ValidationError("最大并发下载数必须大于0")
        if self.max_clients < 1:
            raise ValidationError("最大客户端数必须大于0")
        if self.chunk_size < 1024:
            raise ValidationError("分片大小不能小于1KB")
        if self.timeout < 1:
            raise ValidationError("超时时间必须大于0")


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_file: Optional[str] = "multidownload.log"
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = False
    
    def validate(self) -> None:
        """验证日志配置"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValidationError(f"无效的日志级别: {self.level}")


@dataclass
class Config:
    """主配置类"""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 运行时配置
    debug: bool = False
    dry_run: bool = False
    config_file: Optional[str] = None
    
    def validate(self) -> None:
        """验证所有配置"""
        try:
            self.proxy.validate()
            self.telegram.validate()
            self.download.validate()
            self.logging.validate()
        except ValidationError as e:
            raise ConfigError(f"配置验证失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "proxy": {
                "scheme": self.proxy.scheme,
                "hostname": self.proxy.hostname,
                "port": self.proxy.port,
                "username": self.proxy.username,
                "password": self.proxy.password,
                "enabled": self.proxy.enabled
            },
            "telegram": {
                "api_id": self.telegram.api_id,
                "api_hash": self.telegram.api_hash,
                "phone_number": self.telegram.phone_number,
                "session_string": self.telegram.session_string,
                "max_concurrent_transmissions": self.telegram.max_concurrent_transmissions,
                "sleep_threshold": self.telegram.sleep_threshold,
                "no_updates": self.telegram.no_updates
            },
            "download": {
                "download_path": self.download.download_path,
                "max_concurrent_downloads": self.download.max_concurrent_downloads,
                "max_clients": self.download.max_clients,
                "chunk_size": self.download.chunk_size,
                "large_file_threshold": self.download.large_file_threshold,
                "max_file_size": self.download.max_file_size,
                "timeout": self.download.timeout,
                "retry_count": self.download.retry_count,
                "retry_delay": self.download.retry_delay,
                "skip_existing": self.download.skip_existing
            },
            "logging": {
                "level": self.logging.level,
                "log_file": self.logging.log_file,
                "log_dir": self.logging.log_dir,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
                "json_format": self.logging.json_format
            },
            "debug": self.debug,
            "dry_run": self.dry_run
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """从字典创建配置对象"""
        config = cls()
        
        # 代理配置
        if "proxy" in data:
            proxy_data = data["proxy"]
            config.proxy = ProxyConfig(**proxy_data)
        
        # Telegram配置
        if "telegram" in data:
            telegram_data = data["telegram"]
            config.telegram = TelegramConfig(**telegram_data)
        
        # 下载配置
        if "download" in data:
            download_data = data["download"]
            config.download = DownloadConfig(**download_data)
        
        # 日志配置
        if "logging" in data:
            logging_data = data["logging"]
            config.logging = LoggingConfig(**logging_data)
        
        # 运行时配置
        config.debug = data.get("debug", False)
        config.dry_run = data.get("dry_run", False)
        
        return config
    
    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        config_path = Path(file_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"保存配置文件失败: {e}")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        # 添加logger
        from .logger import get_logger
        self.logger = get_logger(f"{__name__}.ConfigManager")
        
        self.config_file = config_file or "config.json"
        self.config = Config()
        self.config.config_file = self.config_file
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置"""
        try:
            # 1. 从文件加载
            if os.path.exists(self.config_file):
                try:
                    self._load_from_file()
                except Exception as e:
                    self.logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
            
            # 2. 从环境变量加载
            self._load_from_env()
            
            # 3. 只在配置文件存在时验证，首次使用不验证
            if os.path.exists(self.config_file):
                try:
                    self.config.validate()
                except ValidationError as e:
                    self.logger.warning(f"配置验证失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"配置加载异常: {e}")
            # 发生异常时使用默认配置
            self.config = Config()
    
    def validate_for_usage(self) -> None:
        """
        验证配置是否可用于实际使用
        
        Raises:
            ConfigError: 配置验证失败
        """
        try:
            self.config.validate()
        except ValidationError as e:
            raise ConfigError(f"配置验证失败: {e}")
    
    def is_telegram_configured(self) -> bool:
        """
        检查Telegram配置是否完整
        
        Returns:
            是否配置完整
        """
        try:
            self.config.telegram.validate()
            return True
        except ValidationError:
            return False
    
    def _load_from_file(self) -> None:
        """从文件加载配置"""
        config_path = Path(self.config_file)
        
        if config_path.suffix.lower() == '.json':
            self._load_from_json()
        elif config_path.suffix.lower() in ['.ini', '.cfg']:
            self._load_from_ini()
        else:
            raise ConfigError(f"不支持的配置文件格式: {config_path.suffix}")
    
    def _load_from_json(self) -> None:
        """从JSON文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = Config.from_dict(data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"JSON配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"读取JSON配置文件失败: {e}")
    
    def _load_from_ini(self) -> None:
        """从INI文件加载配置"""
        try:
            parser = configparser.ConfigParser()
            parser.read(self.config_file, encoding='utf-8')
            
            # 转换为字典格式
            data = {}
            for section in parser.sections():
                data[section] = dict(parser[section])
            
            self.config = Config.from_dict(data)
        except Exception as e:
            raise ConfigError(f"读取INI配置文件失败: {e}")
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        env_mapping = {
            # Telegram配置
            "TELEGRAM_API_ID": ("telegram.api_id", int),
            "TELEGRAM_API_HASH": ("telegram.api_hash", str),
            "TELEGRAM_PHONE_NUMBER": ("telegram.phone_number", str),
            "TELEGRAM_SESSION_STRING": ("telegram.session_string", str),
            
            # 代理配置
            "PROXY_SCHEME": ("proxy.scheme", str),
            "PROXY_HOSTNAME": ("proxy.hostname", str),
            "PROXY_PORT": ("proxy.port", int),
            "PROXY_USERNAME": ("proxy.username", str),
            "PROXY_PASSWORD": ("proxy.password", str),
            "PROXY_ENABLED": ("proxy.enabled", bool),
            
            # 下载配置
            "DOWNLOAD_PATH": ("download.download_path", str),
            "MAX_CONCURRENT_DOWNLOADS": ("download.max_concurrent_downloads", int),
            "MAX_CLIENTS": ("download.max_clients", int),
            "CHUNK_SIZE": ("download.chunk_size", int),
            
            # 日志配置
            "LOG_LEVEL": ("logging.level", str),
            "LOG_FILE": ("logging.log_file", str),
            "LOG_DIR": ("logging.log_dir", str),
            
            # 运行时配置
            "DEBUG": ("debug", bool),
            "DRY_RUN": ("dry_run", bool)
        }
        
        for env_key, (config_key, value_type) in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                try:
                    # 类型转换
                    if value_type == bool:
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        value = int(env_value)
                    else:
                        value = env_value
                    
                    # 设置配置值
                    self._set_nested_value(self.config, config_key, value)
                except ValueError as e:
                    raise ConfigError(f"环境变量 {env_key} 值转换错误: {e}")
    
    def _set_nested_value(self, obj: Any, key: str, value: Any) -> None:
        """设置嵌套对象的值"""
        keys = key.split('.')
        current = obj
        
        for k in keys[:-1]:
            current = getattr(current, k)
        
        setattr(current, keys[-1], value)
    
    def get_config(self) -> Config:
        """获取配置对象"""
        return self.config
    
    def save_config(self, file_path: Optional[str] = None) -> None:
        """保存配置到文件"""
        target_file = file_path or self.config_file
        self.config.save_to_file(target_file)
    
    def reload_config(self) -> None:
        """重新加载配置"""
        self._load_config()
    
    def create_default_config(self, file_path: Optional[str] = None) -> None:
        """创建默认配置文件"""
        target_file = file_path or "config.json"
        default_config = Config()
        default_config.save_to_file(target_file)
    
    def print_config(self) -> None:
        """打印当前配置"""
        config_dict = self.config.to_dict()
        # 隐藏敏感信息
        if "telegram" in config_dict:
            if "api_hash" in config_dict["telegram"]:
                config_dict["telegram"]["api_hash"] = "***"
            if "session_string" in config_dict["telegram"]:
                config_dict["telegram"]["session_string"] = "***"
        
        if "proxy" in config_dict:
            if "password" in config_dict["proxy"]:
                config_dict["proxy"]["password"] = "***"
        
        print(json.dumps(config_dict, indent=2, ensure_ascii=False))


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_file)
    return _global_config_manager


def get_config() -> Config:
    """获取当前配置"""
    return get_config_manager().get_config()


def setup_config(config_file: Optional[str] = None) -> Config:
    """设置全局配置"""
    global _global_config_manager
    _global_config_manager = ConfigManager(config_file)
    return _global_config_manager.get_config() 