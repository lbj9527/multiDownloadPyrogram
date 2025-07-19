#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端配置数据模型
"""

import re
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AccountType(str, Enum):
    """账户类型枚举"""
    NORMAL = "normal"  # 普通账户，支持3个客户端
    PREMIUM = "premium"  # Premium账户，支持4个客户端


class ClientStatus(str, Enum):
    """客户端状态枚举"""
    NOT_LOGGED_IN = "not_logged_in"  # 未登录
    LOGGING_IN = "logging_in"  # 登录中
    LOGGED_IN = "logged_in"  # 已登录
    LOGIN_FAILED = "login_failed"  # 登录失败
    DISABLED = "disabled"  # 已禁用
    ERROR = "error"  # 错误状态


class ClientConfig(BaseModel):
    """单个客户端配置"""
    
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API Hash")
    phone_number: str = Field(..., description="电话号码（含国家代码）")
    session_name: str = Field(..., description="会话名称")
    enabled: bool = Field(default=True, description="是否启用")
    status: ClientStatus = Field(default=ClientStatus.NOT_LOGGED_IN, description="客户端状态")
    last_active: Optional[str] = Field(default=None, description="最后活跃时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    
    @field_validator('api_id')
    @classmethod
    def validate_api_id(cls, v):
        """验证API ID"""
        if not isinstance(v, int) or v <= 0:
            raise ValueError("API ID必须为正整数")
        if not (10000 <= v <= 9999999999):  # 5-10位数字
            raise ValueError("API ID必须为5-10位数字")
        return v

    @field_validator('api_hash')
    @classmethod
    def validate_api_hash(cls, v):
        """验证API Hash"""
        if not isinstance(v, str):
            raise ValueError("API Hash必须为字符串")
        if len(v) != 32:
            raise ValueError("API Hash必须为32位字符串")
        if not re.match(r'^[a-f0-9]{32}$', v.lower()):
            raise ValueError("API Hash必须为32位十六进制字符串")
        return v.lower()

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """验证电话号码"""
        if not isinstance(v, str):
            raise ValueError("电话号码必须为字符串")
        # 支持国际格式，必须包含国家代码
        if not re.match(r'^\+\d{1,4}\d{6,15}$', v):
            raise ValueError("电话号码格式错误，必须包含国家代码（如+86、+1等）")
        return v

    @field_validator('session_name')
    @classmethod
    def validate_session_name(cls, v):
        """验证会话名称"""
        if not isinstance(v, str):
            raise ValueError("会话名称必须为字符串")
        if not v.strip():
            raise ValueError("会话名称不能为空")
        if not (2 <= len(v) <= 50):
            raise ValueError("会话名称长度必须在2-50个字符之间")
        # 支持中文、英文、数字和下划线
        if not re.match(r'^[\w\u4e00-\u9fff]+$', v):
            raise ValueError("会话名称只能包含中文、英文、数字和下划线")
        return v


class MultiClientConfig(BaseModel):
    """多客户端配置"""
    
    account_type: AccountType = Field(..., description="账户类型")
    clients: List[ClientConfig] = Field(default_factory=list, description="客户端列表")
    
    @field_validator('clients')
    @classmethod
    def validate_clients(cls, v, info):
        """验证客户端列表"""
        account_type = info.data.get('account_type') if info.data else None
        if not account_type:
            return v

        # 根据账户类型限制客户端数量
        max_clients = 3 if account_type == AccountType.NORMAL else 4
        if len(v) > max_clients:
            raise ValueError(f"{account_type.value}账户最多支持{max_clients}个客户端")

        # 检查会话名称唯一性
        session_names = [client.session_name for client in v]
        if len(session_names) != len(set(session_names)):
            raise ValueError("会话名称必须唯一")

        # 确保至少有一个客户端启用
        enabled_clients = [client for client in v if client.enabled]
        if v and not enabled_clients:
            raise ValueError("至少需要启用一个客户端")

        return v
    
    def get_enabled_clients(self) -> List[ClientConfig]:
        """获取启用的客户端列表"""
        return [client for client in self.clients if client.enabled]
    
    def get_max_clients(self) -> int:
        """获取最大客户端数量"""
        return 3 if self.account_type == AccountType.NORMAL else 4
    
    def can_add_client(self) -> bool:
        """检查是否可以添加客户端"""
        return len(self.clients) < self.get_max_clients()
    
    def can_disable_client(self, session_name: str) -> bool:
        """检查是否可以禁用指定客户端"""
        enabled_clients = self.get_enabled_clients()
        if len(enabled_clients) <= 1:
            return False
        
        target_client = next((c for c in self.clients if c.session_name == session_name), None)
        return target_client is not None and target_client.enabled
