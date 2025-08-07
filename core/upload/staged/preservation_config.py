"""
媒体组完整性保持配置模块
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaGroupPreservationConfig:
    """媒体组完整性保持配置"""
    enabled: bool = False                    # 是否启用媒体组完整性保持
    preserve_original_structure: bool = True # 保持原始消息结构
    group_timeout_seconds: int = 300        # 媒体组收集超时时间
    
    def validate(self):
        """验证配置"""
        if self.group_timeout_seconds < 60:
            raise ValueError("媒体组超时时间不能小于60秒")
        if self.group_timeout_seconds > 3600:
            raise ValueError("媒体组超时时间不能超过1小时")
    
    def __post_init__(self):
        """初始化后验证"""
        self.validate()
    
    def __str__(self) -> str:
        return f"MediaGroupPreservationConfig(enabled={self.enabled}, timeout={self.group_timeout_seconds}s)"


def create_preservation_config(enabled: bool = False, timeout: int = 300) -> MediaGroupPreservationConfig:
    """创建媒体组保持配置的便捷函数"""
    return MediaGroupPreservationConfig(
        enabled=enabled,
        preserve_original_structure=True,
        group_timeout_seconds=timeout
    )


def create_disabled_config() -> MediaGroupPreservationConfig:
    """创建禁用的配置"""
    return MediaGroupPreservationConfig(enabled=False)


def create_enabled_config(timeout: int = 300) -> MediaGroupPreservationConfig:
    """创建启用的配置"""
    return MediaGroupPreservationConfig(
        enabled=True,
        preserve_original_structure=True,
        group_timeout_seconds=timeout
    )
