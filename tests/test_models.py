#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型测试
"""

import pytest
from pydantic import ValidationError

from src.models.client_config import ClientConfig, MultiClientConfig, AccountType, ClientStatus
from src.models.download_config import DownloadConfig, DownloadProgress, MessageType
from src.models.events import BaseEvent, EventType, EventSeverity


class TestClientConfig:
    """客户端配置测试"""
    
    def test_valid_client_config(self):
        """测试有效的客户端配置"""
        config = ClientConfig(
            api_id=123456,
            api_hash="abcdef1234567890abcdef1234567890",
            phone_number="+8613800138000",
            session_name="test_session"
        )
        
        assert config.api_id == 123456
        assert config.api_hash == "abcdef1234567890abcdef1234567890"
        assert config.phone_number == "+8613800138000"
        assert config.session_name == "test_session"
        assert config.enabled is True
        assert config.status == ClientStatus.NOT_LOGGED_IN
    
    def test_invalid_api_id(self):
        """测试无效的API ID"""
        with pytest.raises(ValidationError):
            ClientConfig(
                api_id=123,  # 太短
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name="test_session"
            )
    
    def test_invalid_api_hash(self):
        """测试无效的API Hash"""
        with pytest.raises(ValidationError):
            ClientConfig(
                api_id=123456,
                api_hash="invalid_hash",  # 不是32位十六进制
                phone_number="+8613800138000",
                session_name="test_session"
            )
    
    def test_invalid_phone_number(self):
        """测试无效的电话号码"""
        with pytest.raises(ValidationError):
            ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="13800138000",  # 缺少国家代码
                session_name="test_session"
            )
    
    def test_invalid_session_name(self):
        """测试无效的会话名称"""
        with pytest.raises(ValidationError):
            ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name=""  # 空名称
            )


class TestMultiClientConfig:
    """多客户端配置测试"""
    
    def test_normal_account_max_clients(self):
        """测试普通账户最大客户端数量"""
        clients = []
        for i in range(3):
            clients.append(ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name=f"session_{i}"
            ))
        
        config = MultiClientConfig(
            account_type=AccountType.NORMAL,
            clients=clients
        )
        
        assert len(config.clients) == 3
        assert config.get_max_clients() == 3
    
    def test_premium_account_max_clients(self):
        """测试Premium账户最大客户端数量"""
        clients = []
        for i in range(4):
            clients.append(ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name=f"session_{i}"
            ))
        
        config = MultiClientConfig(
            account_type=AccountType.PREMIUM,
            clients=clients
        )
        
        assert len(config.clients) == 4
        assert config.get_max_clients() == 4
    
    def test_exceed_max_clients(self):
        """测试超过最大客户端数量"""
        clients = []
        for i in range(5):  # 超过普通账户限制
            clients.append(ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name=f"session_{i}"
            ))
        
        with pytest.raises(ValidationError):
            MultiClientConfig(
                account_type=AccountType.NORMAL,
                clients=clients
            )
    
    def test_duplicate_session_names(self):
        """测试重复的会话名称"""
        clients = []
        for i in range(2):
            clients.append(ClientConfig(
                api_id=123456,
                api_hash="abcdef1234567890abcdef1234567890",
                phone_number="+8613800138000",
                session_name="same_name"  # 相同名称
            ))
        
        with pytest.raises(ValidationError):
            MultiClientConfig(
                account_type=AccountType.NORMAL,
                clients=clients
            )


class TestDownloadConfig:
    """下载配置测试"""
    
    def test_valid_download_config(self):
        """测试有效的下载配置"""
        config = DownloadConfig(
            channel_id="@test_channel",
            start_message_id=1,
            message_count=100,
            download_path="./downloads"
        )
        
        assert config.channel_id == "@test_channel"
        assert config.start_message_id == 1
        assert config.message_count == 100
        assert config.download_path == "downloads"  # 路径验证器会标准化路径
        assert config.include_media is True
        assert config.include_text is True
    
    def test_invalid_channel_id(self):
        """测试无效的频道ID"""
        with pytest.raises(ValidationError):
            DownloadConfig(
                channel_id="",  # 空ID
                start_message_id=1,
                message_count=100,
                download_path="./downloads"
            )
    
    def test_invalid_message_count(self):
        """测试无效的消息数量"""
        with pytest.raises(ValidationError):
            DownloadConfig(
                channel_id="@test_channel",
                start_message_id=1,
                message_count=1001,  # 超过限制
                download_path="./downloads"
            )
    
    def test_invalid_start_message_id(self):
        """测试无效的起始消息ID"""
        with pytest.raises(ValidationError):
            DownloadConfig(
                channel_id="@test_channel",
                start_message_id=0,  # 必须大于0
                message_count=100,
                download_path="./downloads"
            )


class TestDownloadProgress:
    """下载进度测试"""
    
    def test_progress_calculation(self):
        """测试进度计算"""
        progress = DownloadProgress(
            total_messages=100,
            downloaded_messages=50
        )
        
        assert progress.progress_percentage == 50.0
    
    def test_size_formatting(self):
        """测试大小格式化"""
        progress = DownloadProgress()
        
        assert progress.format_size(0) == "0 B"
        assert progress.format_size(1024) == "1.00 KB"
        assert progress.format_size(1024 * 1024) == "1.00 MB"
        assert progress.format_size(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_speed_formatting(self):
        """测试速度格式化"""
        progress = DownloadProgress(download_speed=1024)
        
        assert progress.format_speed() == "1.00 KB/s"
    
    def test_eta_formatting(self):
        """测试剩余时间格式化"""
        progress = DownloadProgress()
        
        progress.eta = 30
        assert progress.format_eta() == "30秒"
        
        progress.eta = 90
        assert progress.format_eta() == "1分30秒"
        
        progress.eta = 3661
        assert progress.format_eta() == "1小时1分钟"


class TestEvents:
    """事件测试"""
    
    def test_base_event_creation(self):
        """测试基础事件创建"""
        from datetime import datetime
        
        event = BaseEvent(
            event_id="test_id",
            event_type=EventType.APP_STARTED,
            message="测试消息"
        )
        
        assert event.event_id == "test_id"
        assert event.event_type == EventType.APP_STARTED
        assert event.message == "测试消息"
        assert event.severity == EventSeverity.INFO
        assert isinstance(event.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__])
