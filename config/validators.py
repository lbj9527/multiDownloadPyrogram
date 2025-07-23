"""
配置验证器模块
提供统一的配置验证逻辑
"""

import os
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from dataclasses import fields, is_dataclass

from .constants import STORAGE_MODES, FILE_TYPE_CATEGORIES


class ConfigValidator:
    """统一配置验证器"""
    
    @staticmethod
    def validate_api_credentials(api_id: Union[int, str], api_hash: str) -> List[str]:
        """验证API凭据"""
        errors = []
        
        # 验证API ID
        try:
            api_id_int = int(api_id) if isinstance(api_id, str) else api_id
            if api_id_int <= 0:
                errors.append("API_ID 必须是正整数")
        except (ValueError, TypeError):
            errors.append("API_ID 必须是有效的数字")
        
        # 验证API Hash
        if not api_hash or not isinstance(api_hash, str):
            errors.append("API_HASH 不能为空")
        elif len(api_hash) != 32:
            errors.append("API_HASH 长度必须为32位")
        elif not re.match(r'^[a-f0-9]{32}$', api_hash):
            errors.append("API_HASH 必须是32位十六进制字符串")
        
        return errors
    
    @staticmethod
    def validate_phone_number(phone: str) -> List[str]:
        """验证手机号码"""
        errors = []
        
        if not phone:
            errors.append("手机号码不能为空")
            return errors
        
        # 移除空格和特殊字符
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # 检查格式
        if not re.match(r'^\+\d{10,15}$', clean_phone):
            errors.append("手机号码格式无效，应为 +国家代码+号码 格式")
        
        return errors
    
    @staticmethod
    def validate_proxy_config(proxy: Optional[Dict[str, Any]]) -> List[str]:
        """验证代理配置"""
        errors = []
        
        if proxy is None:
            return errors
        
        required_fields = ['scheme', 'hostname', 'port']
        for field in required_fields:
            if field not in proxy:
                errors.append(f"代理配置缺少必需字段: {field}")
        
        # 验证scheme
        if 'scheme' in proxy:
            valid_schemes = ['socks5', 'socks4', 'http', 'https']
            if proxy['scheme'] not in valid_schemes:
                errors.append(f"代理协议必须是: {', '.join(valid_schemes)}")
        
        # 验证hostname
        if 'hostname' in proxy:
            hostname = proxy['hostname']
            if not hostname or not isinstance(hostname, str):
                errors.append("代理主机名不能为空")
        
        # 验证port
        if 'port' in proxy:
            try:
                port = int(proxy['port'])
                if not (1 <= port <= 65535):
                    errors.append("代理端口必须在1-65535范围内")
            except (ValueError, TypeError):
                errors.append("代理端口必须是有效数字")
        
        return errors
    
    @staticmethod
    def validate_download_config(
        target_channel: str,
        start_message_id: int,
        end_message_id: int,
        batch_size: int,
        max_concurrent_clients: int
    ) -> List[str]:
        """验证下载配置"""
        errors = []
        
        # 验证频道名称
        if not target_channel:
            errors.append("目标频道不能为空")
        elif not re.match(r'^[a-zA-Z0-9_]+$', target_channel.replace('@', '')):
            errors.append("频道名称格式无效")
        
        # 验证消息ID范围
        if start_message_id <= 0:
            errors.append("开始消息ID必须大于0")
        
        if end_message_id <= 0:
            errors.append("结束消息ID必须大于0")
        
        if start_message_id >= end_message_id:
            errors.append("开始消息ID必须小于结束消息ID")
        
        # 验证批次大小
        if batch_size <= 0 or batch_size > 200:
            errors.append("批次大小必须在1-200之间")
        
        # 验证客户端数量
        if max_concurrent_clients <= 0 or max_concurrent_clients > 10:
            errors.append("并发客户端数量必须在1-10之间")
        
        return errors
    
    @staticmethod
    def validate_storage_config(storage_mode: str) -> List[str]:
        """验证存储配置"""
        errors = []
        
        if storage_mode not in STORAGE_MODES:
            errors.append(f"存储模式必须是: {', '.join(STORAGE_MODES)}")
        
        return errors
    
    @staticmethod
    def validate_logging_config(
        level: str,
        file_path: str,
        file_enabled: bool,
        console_enabled: bool
    ) -> List[str]:
        """验证日志配置"""
        errors = []
        
        # 验证日志级别
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() not in valid_levels:
            errors.append(f"日志级别必须是: {', '.join(valid_levels)}")
        
        # 验证文件路径
        if file_enabled:
            if not file_path:
                errors.append("启用文件日志时，文件路径不能为空")
            else:
                try:
                    log_dir = Path(file_path).parent
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"无法创建日志目录: {e}")
        
        # 至少启用一种输出方式
        if not file_enabled and not console_enabled:
            errors.append("必须至少启用控制台或文件日志输出")
        
        return errors
    
    @staticmethod
    def validate_environment_variables() -> List[str]:
        """验证环境变量（可选检查）"""
        errors = []

        # 注意：这里只是警告，不是错误，因为配置可能有默认值
        # 如果需要强制使用环境变量，可以取消注释下面的代码

        # required_env_vars = ['API_ID', 'API_HASH']
        # for var in required_env_vars:
        #     if not os.getenv(var):
        #         errors.append(f"建议设置环境变量: {var}")

        return errors
    
    @staticmethod
    def validate_dataclass_config(config_obj: Any) -> List[str]:
        """验证数据类配置对象"""
        errors = []
        
        if not is_dataclass(config_obj):
            errors.append("配置对象必须是数据类")
            return errors
        
        # 检查必需字段
        for field in fields(config_obj):
            value = getattr(config_obj, field.name)
            
            # 检查非空字段
            if field.default is None and value is None:
                errors.append(f"必需字段 {field.name} 不能为空")
            
            # 检查字符串字段
            if field.type == str and isinstance(value, str) and not value.strip():
                errors.append(f"字符串字段 {field.name} 不能为空字符串")
        
        return errors
    
    @classmethod
    def validate_complete_config(cls, config) -> List[str]:
        """完整配置验证"""
        all_errors = []

        # 验证Telegram配置
        if hasattr(config, 'telegram'):
            telegram = config.telegram

            # 验证API凭据（使用实际配置值，不检查环境变量）
            api_errors = cls.validate_api_credentials(
                telegram.api_id, telegram.api_hash
            )
            # 过滤掉关于环境变量的错误，因为我们有默认值
            filtered_api_errors = [
                error for error in api_errors
                if "环境变量" not in error
            ]
            all_errors.extend(filtered_api_errors)

            all_errors.extend(cls.validate_phone_number(telegram.phone_number))
            all_errors.extend(cls.validate_proxy_config(telegram.proxy))

        # 验证下载配置
        if hasattr(config, 'download'):
            download = config.download
            all_errors.extend(cls.validate_download_config(
                download.target_channel,
                download.start_message_id,
                download.end_message_id,
                download.batch_size,
                download.max_concurrent_clients
            ))

        # 验证存储配置
        if hasattr(config, 'storage'):
            storage = config.storage
            all_errors.extend(cls.validate_storage_config(storage.storage_mode))

        # 验证日志配置
        if hasattr(config, 'logging'):
            logging_config = config.logging
            all_errors.extend(cls.validate_logging_config(
                logging_config.level,
                logging_config.file_path,
                logging_config.file_enabled,
                logging_config.console_enabled
            ))

        return all_errors


# 便捷验证函数
def validate_config(config) -> List[str]:
    """验证配置的便捷函数"""
    return ConfigValidator.validate_complete_config(config)


def is_valid_config(config) -> bool:
    """检查配置是否有效"""
    return len(validate_config(config)) == 0
