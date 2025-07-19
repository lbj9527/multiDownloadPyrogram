#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块测试
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.utils.file_utils import (
    sanitize_filename, get_file_extension, ensure_unique_filename,
    format_file_size, create_directory_structure, get_safe_path
)
from src.utils.config_manager import ConfigManager


class TestFileUtils:
    """文件工具测试"""
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        # 测试非法字符
        assert sanitize_filename("test<>file") == "test__file"
        assert sanitize_filename("test:file") == "test_file"
        assert sanitize_filename("test/file") == "test_file"
        
        # 测试Windows保留名称
        assert sanitize_filename("CON") == "_CON"
        assert sanitize_filename("con.txt") == "_con.txt"
        
        # 测试空字符串
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"
        
        # 测试长文件名
        long_name = "a" * 250
        result = sanitize_filename(long_name)
        assert len(result) <= 200
    
    def test_get_file_extension(self):
        """测试文件扩展名获取"""
        # 模拟媒体对象
        class MockMedia:
            def __init__(self, file_name=None, mime_type=None):
                self.file_name = file_name
                self.mime_type = mime_type
        
        # 测试从文件名获取扩展名
        media = MockMedia(file_name="test.jpg")
        assert get_file_extension(media, "photo") == ".jpg"
        
        # 测试从MIME类型获取扩展名
        media = MockMedia(mime_type="image/png")
        assert get_file_extension(media, "photo") == ".png"
        
        # 测试默认扩展名
        media = MockMedia()
        assert get_file_extension(media, "photo") == ".jpg"
        assert get_file_extension(media, "video") == ".mp4"
        assert get_file_extension(media, "unknown") == ".bin"
    
    def test_format_file_size(self):
        """测试文件大小格式化"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(512) == "512 B"
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
    
    def test_ensure_unique_filename(self):
        """测试唯一文件名生成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建测试文件
            test_file = temp_path / "test.txt"
            test_file.write_text("test")
            
            # 测试唯一文件名生成
            unique_path = ensure_unique_filename(test_file)
            assert unique_path != test_file
            assert unique_path.name == "test_1.txt"
            
            # 如果文件不存在，应该返回原路径
            new_file = temp_path / "new.txt"
            unique_path = ensure_unique_filename(new_file)
            assert unique_path == new_file
    
    def test_create_directory_structure(self):
        """测试目录结构创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建目录结构
            result_dir = create_directory_structure(temp_path, "@test_channel")
            
            assert result_dir.exists()
            assert result_dir.is_dir()
            assert "@test_channel" in str(result_dir)  # @ 是合法字符，不会被替换
    
    def test_get_safe_path(self):
        """测试安全路径获取"""
        # 测试正常路径
        safe_path = get_safe_path("test/file.txt")
        assert safe_path is not None
        assert "test" in str(safe_path) and "file.txt" in str(safe_path)  # 路径包含正确的部分
        
        # 测试危险路径
        dangerous_path = get_safe_path("../../../etc/passwd")
        assert dangerous_path is None
        
        # 测试绝对路径（Windows风格）
        import platform
        if platform.system() == "Windows":
            abs_path = get_safe_path("C:\\Windows\\System32")
        else:
            abs_path = get_safe_path("/etc/passwd")
        assert abs_path is None


class TestConfigManager:
    """配置管理器测试"""
    
    def test_config_manager_initialization(self):
        """测试配置管理器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # 检查配置文件是否创建
            assert config_manager.app_config_path.exists()
            assert config_manager.client_config_path.exists()
            assert config_manager.download_config_path.exists()
    
    def test_app_config_operations(self):
        """测试应用配置操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # 加载默认配置
            app_config = config_manager.load_app_config()
            assert "app" in app_config
            assert "download" in app_config
            assert "logging" in app_config
            
            # 修改配置
            app_config["app"]["name"] = "测试应用"
            
            # 保存配置
            success = config_manager.save_app_config(app_config)
            assert success
            
            # 重新加载验证
            reloaded_config = config_manager.load_app_config()
            assert reloaded_config["app"]["name"] == "测试应用"
    
    def test_recent_channels(self):
        """测试最近频道功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # 添加最近频道
            config_manager.add_recent_channel("@test_channel", "测试频道")
            
            # 获取最近频道
            recent_channels = config_manager.get_recent_channels()
            assert len(recent_channels) == 1
            assert recent_channels[0]["id"] == "@test_channel"
            assert recent_channels[0]["name"] == "测试频道"
    
    def test_config_export_import(self):
        """测试配置导出导入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # 修改配置
            app_config = config_manager.load_app_config()
            app_config["app"]["name"] = "导出测试"
            config_manager.save_app_config(app_config)
            
            # 导出配置
            export_dir = Path(temp_dir) / "export"
            success = config_manager.export_config(str(export_dir))
            assert success
            assert (export_dir / "app_config.json").exists()
            
            # 创建新的配置管理器
            new_config_dir = Path(temp_dir) / "new_config"
            new_config_manager = ConfigManager(str(new_config_dir))
            
            # 导入配置
            success = new_config_manager.import_config(str(export_dir))
            assert success
            
            # 验证导入的配置
            imported_config = new_config_manager.load_app_config()
            assert imported_config["app"]["name"] == "导出测试"


class TestErrorHandling:
    """错误处理测试"""
    
    def test_error_classification(self):
        """测试错误分类"""
        from src.utils.error_handler import ErrorHandler, ErrorType
        from pyrogram.errors import FloodWait, Unauthorized
        
        error_handler = ErrorHandler()
        
        # 测试FloodWait错误
        flood_error = FloodWait(30)
        assert error_handler.classify_error(flood_error) == ErrorType.FLOOD_WAIT
        
        # 测试网络错误
        network_error = ConnectionError("网络连接失败")
        assert error_handler.classify_error(network_error) == ErrorType.NETWORK_ERROR
        
        # 测试认证错误
        auth_error = Unauthorized("未授权")
        assert error_handler.classify_error(auth_error) == ErrorType.AUTH_ERROR
        
        # 测试未知错误
        unknown_error = Exception("未知错误")
        assert error_handler.classify_error(unknown_error) == ErrorType.UNKNOWN_ERROR
    
    def test_retry_logic(self):
        """测试重试逻辑"""
        from src.utils.error_handler import ErrorHandler, ErrorType
        
        error_handler = ErrorHandler()
        
        # 测试网络错误重试
        network_error = ConnectionError("网络错误")
        assert error_handler.should_retry(network_error, 0) == True
        assert error_handler.should_retry(network_error, 3) == False  # 超过最大重试次数

        # 测试认证错误不重试
        from pyrogram.errors import Unauthorized
        auth_error = Unauthorized("认证失败")
        assert error_handler.should_retry(auth_error, 0) == False
    
    def test_delay_calculation(self):
        """测试延迟计算"""
        from src.utils.error_handler import ErrorHandler
        
        error_handler = ErrorHandler()
        
        # 测试指数退避
        network_error = Exception("网络错误")
        delay1 = error_handler.calculate_delay(network_error, 0)
        delay2 = error_handler.calculate_delay(network_error, 1)
        delay3 = error_handler.calculate_delay(network_error, 2)
        
        # 指数退避应该是递增的
        assert delay1 < delay2 < delay3


if __name__ == "__main__":
    pytest.main([__file__])
