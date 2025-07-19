#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序演示脚本
"""

import sys
import os
from pathlib import Path

def demo():
    """演示程序功能"""
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        print("=" * 60)
        print("Telegram多客户端消息下载器 - 功能演示")
        print("=" * 60)
        
        # 创建必要的目录
        directories = ["downloads", "logs", "sessions", "config"]
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        print("✓ 目录结构创建完成")
        
        # 测试模型
        print("\n1. 测试数据模型...")
        from src.models.client_config import ClientConfig, MultiClientConfig, AccountType
        from src.models.download_config import DownloadConfig
        from src.models.events import BaseEvent, EventType
        
        # 创建客户端配置
        client_config = ClientConfig(
            api_id=123456,
            api_hash="abcdef1234567890abcdef1234567890",
            phone_number="+8613800138000",
            session_name="demo_session"
        )
        print("✓ 客户端配置模型测试通过")
        
        # 创建下载配置
        download_config = DownloadConfig(
            channel_id="@demo_channel",
            start_message_id=1,
            message_count=10,
            download_path="./downloads"
        )
        print("✓ 下载配置模型测试通过")
        
        # 测试配置管理器
        print("\n2. 测试配置管理器...")
        from src.utils.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        app_config = config_manager.load_app_config()
        print(f"✓ 应用配置加载成功，应用名称: {app_config['app']['name']}")
        
        # 测试事件管理器
        print("\n3. 测试事件管理器...")
        from src.core.event_manager import EventManager
        
        event_manager = EventManager()
        
        # 创建测试事件
        test_event = BaseEvent(
            event_id="demo_001",
            event_type=EventType.APP_STARTED,
            message="演示事件"
        )
        
        event_manager.emit_sync(test_event)
        print("✓ 事件管理器测试通过")
        
        # 测试文件工具
        print("\n4. 测试文件工具...")
        from src.utils.file_utils import sanitize_filename, format_file_size
        
        clean_name = sanitize_filename("test<>file.txt")
        size_str = format_file_size(1024 * 1024)
        print(f"✓ 文件名清理: 'test<>file.txt' -> '{clean_name}'")
        print(f"✓ 大小格式化: 1048576 bytes -> {size_str}")
        
        # 测试错误处理
        print("\n5. 测试错误处理...")
        from src.utils.error_handler import ErrorHandler, ErrorType
        
        error_handler = ErrorHandler()
        test_error = Exception("测试错误")
        error_type = error_handler.classify_error(test_error)
        print(f"✓ 错误分类: Exception -> {error_type.value}")
        
        # 清理事件管理器
        event_manager.stop_processing()
        
        print("\n" + "=" * 60)
        print("🎉 所有核心功能测试通过！")
        print("=" * 60)
        
        print("\n📖 使用说明:")
        print("1. 运行 'python start.py' 启动GUI应用")
        print("2. 或双击 '启动应用.bat' 文件")
        print("3. 在应用中配置Telegram客户端")
        print("4. 设置下载参数并开始下载")
        
        print("\n⚠️ 注意事项:")
        print("- 需要先获取Telegram API凭据")
        print("- 访问 https://my.telegram.org/apps")
        print("- 确保网络连接正常")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = demo()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)
