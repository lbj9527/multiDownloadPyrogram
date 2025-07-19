#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理系统
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar
from datetime import datetime

from pydantic import BaseModel, ValidationError

from ..models.client_config import MultiClientConfig, AccountType
from ..models.download_config import DownloadConfig
from ..utils.logger import get_logger

T = TypeVar('T', bound=BaseModel)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.logger = get_logger(__name__)
        
        # 配置文件路径
        self.app_config_path = self.config_dir / "app_config.json"
        self.client_config_path = self.config_dir / "client_config.json"
        self.download_config_path = self.config_dir / "download_config.json"
        
        # 默认配置
        self.default_app_config = {
            "app": {
                "name": "Telegram消息管理器",
                "version": "1.0.0",
                "window_size": {
                    "width": 1200,
                    "height": 800
                },
                "theme": "dark",
                "language": "zh"
            },
            "download": {
                "default_path": "./downloads",
                "max_concurrent_downloads": 5,
                "chunk_size": 1024,
                "timeout": 30,
                "auto_create_folders": True
            },
            "logging": {
                "level": "INFO",
                "file_path": "./logs/app.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "console_output": True
            },
            "ui": {
                "auto_refresh_interval": 1000,
                "show_progress_details": True,
                "confirm_before_download": True,
                "minimize_to_tray": False
            }
        }
        
        # 初始化配置文件
        self._initialize_configs()
    
    def _initialize_configs(self):
        """初始化配置文件"""
        # 创建默认应用配置
        if not self.app_config_path.exists():
            self.save_app_config(self.default_app_config)
            self.logger.info("创建默认应用配置文件")
        
        # 创建空的客户端配置
        if not self.client_config_path.exists():
            default_client_config = {
                "account_type": AccountType.NORMAL.value,
                "clients": []
            }
            self.save_json_config(self.client_config_path, default_client_config)
            self.logger.info("创建默认客户端配置文件")
        
        # 创建空的下载配置
        if not self.download_config_path.exists():
            default_download_config = {
                "recent_channels": [],
                "default_settings": {
                    "start_message_id": 1,
                    "message_count": 100,
                    "include_media": True,
                    "include_text": True,
                    "media_types": ["photo", "video", "document", "audio"],
                    "max_file_size": None
                }
            }
            self.save_json_config(self.download_config_path, default_download_config)
            self.logger.info("创建默认下载配置文件")
    
    def load_json_config(self, file_path: Path) -> Dict[str, Any]:
        """
        加载JSON配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置数据
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.logger.debug(f"加载配置文件: {file_path}")
                return config
            else:
                self.logger.warning(f"配置文件不存在: {file_path}")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误 {file_path}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}
    
    def save_json_config(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """
        保存JSON配置文件
        
        Args:
            file_path: 配置文件路径
            config: 配置数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 创建备份
            if file_path.exists():
                backup_path = file_path.with_suffix(f'.bak.{int(datetime.now().timestamp())}')
                try:
                    file_path.rename(backup_path)
                except OSError:
                    # Windows上可能出现文件被占用的情况，跳过备份
                    pass

                # 只保留最近5个备份
                self._cleanup_backups(file_path)
            
            # 保存配置
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"保存配置文件: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置文件失败 {file_path}: {e}")
            return False
    
    def _cleanup_backups(self, original_path: Path):
        """清理旧的备份文件"""
        try:
            backup_pattern = f"{original_path.stem}.bak.*"
            backup_files = list(original_path.parent.glob(backup_pattern))
            
            # 按修改时间排序，保留最新的5个
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files[5:]:
                backup_file.unlink()
                self.logger.debug(f"删除旧备份文件: {backup_file}")
                
        except Exception as e:
            self.logger.error(f"清理备份文件失败: {e}")
    
    def load_app_config(self) -> Dict[str, Any]:
        """加载应用配置"""
        config = self.load_json_config(self.app_config_path)
        
        # 合并默认配置
        merged_config = self._merge_configs(self.default_app_config, config)
        
        return merged_config
    
    def save_app_config(self, config: Dict[str, Any]) -> bool:
        """保存应用配置"""
        success = self.save_json_config(self.app_config_path, config)

        # 如果保存成功，更新代理配置
        if success and "proxy" in config:
            try:
                from .proxy_utils import update_proxy_config
                update_proxy_config(config["proxy"])
                self.logger.debug("代理配置已更新")
            except Exception as e:
                self.logger.error(f"更新代理配置失败: {e}")

        return success
    
    def load_client_config(self) -> Optional[MultiClientConfig]:
        """
        加载客户端配置
        
        Returns:
            Optional[MultiClientConfig]: 客户端配置对象
        """
        try:
            config_data = self.load_json_config(self.client_config_path)
            if not config_data:
                return None
            
            # 验证并创建配置对象
            client_config = MultiClientConfig(**config_data)
            return client_config
            
        except ValidationError as e:
            self.logger.error(f"客户端配置验证失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"加载客户端配置失败: {e}")
            return None
    
    def save_client_config(self, config: MultiClientConfig) -> bool:
        """
        保存客户端配置
        
        Args:
            config: 客户端配置对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            config_data = config.dict()
            return self.save_json_config(self.client_config_path, config_data)
        except Exception as e:
            self.logger.error(f"保存客户端配置失败: {e}")
            return False
    
    def load_download_config(self) -> Dict[str, Any]:
        """加载下载配置"""
        return self.load_json_config(self.download_config_path)
    
    def save_download_config(self, config: Dict[str, Any]) -> bool:
        """保存下载配置"""
        return self.save_json_config(self.download_config_path, config)
    
    def add_recent_channel(self, channel_id: str, channel_name: str = None):
        """
        添加最近使用的频道
        
        Args:
            channel_id: 频道ID
            channel_name: 频道名称
        """
        try:
            config = self.load_download_config()
            recent_channels = config.get("recent_channels", [])
            
            # 移除已存在的记录
            recent_channels = [ch for ch in recent_channels if ch.get("id") != channel_id]
            
            # 添加新记录到开头
            new_channel = {
                "id": channel_id,
                "name": channel_name or channel_id,
                "last_used": datetime.now().isoformat()
            }
            recent_channels.insert(0, new_channel)
            
            # 只保留最近10个
            recent_channels = recent_channels[:10]
            
            config["recent_channels"] = recent_channels
            self.save_download_config(config)
            
        except Exception as e:
            self.logger.error(f"添加最近频道失败: {e}")
    
    def get_recent_channels(self) -> list:
        """获取最近使用的频道列表"""
        config = self.load_download_config()
        return config.get("recent_channels", [])
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并配置，用户配置覆盖默认配置
        
        Args:
            default: 默认配置
            user: 用户配置
            
        Returns:
            Dict[str, Any]: 合并后的配置
        """
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def validate_config(self, config_data: Dict[str, Any], model_class: Type[T]) -> Optional[T]:
        """
        验证配置数据
        
        Args:
            config_data: 配置数据
            model_class: 配置模型类
            
        Returns:
            Optional[T]: 验证后的配置对象
        """
        try:
            return model_class(**config_data)
        except ValidationError as e:
            self.logger.error(f"配置验证失败: {e}")
            return None
    
    def export_config(self, export_path: str) -> bool:
        """
        导出所有配置到指定路径
        
        Args:
            export_path: 导出路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出各个配置文件
            configs = {
                "app_config.json": self.load_app_config(),
                "client_config.json": self.load_json_config(self.client_config_path),
                "download_config.json": self.load_download_config()
            }
            
            for filename, config in configs.items():
                export_file = export_dir / filename
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"配置导出成功: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        从指定路径导入配置
        
        Args:
            import_path: 导入路径
            
        Returns:
            bool: 导入是否成功
        """
        try:
            import_dir = Path(import_path)
            if not import_dir.exists():
                self.logger.error(f"导入路径不存在: {import_path}")
                return False
            
            # 导入各个配置文件
            config_files = {
                "app_config.json": self.app_config_path,
                "client_config.json": self.client_config_path,
                "download_config.json": self.download_config_path
            }
            
            for filename, target_path in config_files.items():
                import_file = import_dir / filename
                if import_file.exists():
                    with open(import_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    self.save_json_config(target_path, config)
            
            self.logger.info(f"配置导入成功: {import_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            return False
