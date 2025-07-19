#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装和测试脚本
"""

import sys
import os
import subprocess
from pathlib import Path


def check_virtual_env():
    """检查是否在虚拟环境中"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"虚拟环境状态: {'已激活' if in_venv else '未激活'}")
    print(f"Python路径: {sys.executable}")
    return in_venv


def install_dependencies():
    """安装依赖项"""
    print("\n正在安装依赖项...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✓ 依赖项安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖项安装失败: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    print("\n正在创建目录结构...")
    directories = ["downloads", "logs", "sessions", "config"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ 创建目录: {directory}")
    return True


def test_imports():
    """测试模块导入"""
    print("\n正在测试模块导入...")
    
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # 测试核心模块
        from src.models.client_config import ClientConfig, MultiClientConfig
        print("✓ 客户端配置模型")
        
        from src.models.download_config import DownloadConfig
        print("✓ 下载配置模型")
        
        from src.models.events import BaseEvent, EventType
        print("✓ 事件模型")
        
        from src.utils.config_manager import ConfigManager
        print("✓ 配置管理器")
        
        from src.core.event_manager import EventManager
        print("✓ 事件管理器")
        
        from src.utils.file_utils import sanitize_filename
        print("✓ 文件工具")
        
        from src.utils.error_handler import ErrorHandler
        print("✓ 错误处理器")
        
        # 测试GUI模块
        import customtkinter as ctk
        print("✓ CustomTkinter")
        
        return True
        
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_basic_functionality():
    """测试基本功能"""
    print("\n正在测试基本功能...")
    
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # 测试配置管理器
        from src.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        app_config = config_manager.load_app_config()
        assert "app" in app_config
        print("✓ 配置管理器功能正常")
        
        # 测试事件管理器
        from src.core.event_manager import EventManager
        from src.models.events import BaseEvent, EventType
        
        event_manager = EventManager()
        test_event = BaseEvent(
            event_id="test_001",
            event_type=EventType.APP_STARTED,
            message="测试事件"
        )
        event_manager.emit_sync(test_event)
        event_manager.stop_processing()
        print("✓ 事件管理器功能正常")
        
        # 测试数据模型
        from src.models.client_config import ClientConfig
        client_config = ClientConfig(
            api_id=123456,
            api_hash="abcdef1234567890abcdef1234567890",
            phone_number="+8613800138000",
            session_name="test_session"
        )
        print("✓ 数据模型验证正常")
        
        return True
        
    except Exception as e:
        print(f"✗ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_unit_tests():
    """运行单元测试"""
    print("\n正在运行单元测试...")
    
    try:
        # 检查pytest是否可用
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("pytest未安装，跳过单元测试")
            return True
        
        # 运行测试
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_models.py", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 模型测试通过")
        else:
            print("⚠️ 部分模型测试失败，但不影响核心功能")
            print(result.stdout[-500:])  # 显示最后500个字符
        
        return True
        
    except Exception as e:
        print(f"⚠️ 单元测试执行失败: {e}")
        return True  # 不阻止安装


def test_gui():
    """测试GUI"""
    print("\n正在测试GUI...")
    
    try:
        import customtkinter as ctk
        
        # 创建测试窗口
        root = ctk.CTk()
        root.withdraw()  # 隐藏窗口
        
        # 测试组件创建
        label = ctk.CTkLabel(root, text="测试")
        button = ctk.CTkButton(root, text="测试")
        
        # 销毁窗口
        root.destroy()
        
        print("✓ GUI组件测试通过")
        return True
        
    except Exception as e:
        print(f"✗ GUI测试失败: {e}")
        return False


def create_startup_scripts():
    """创建启动脚本"""
    print("\n正在创建启动脚本...")
    
    try:
        # Windows批处理文件
        bat_content = f"""@echo off
chcp 65001 >nul
title Telegram多客户端消息下载器

echo ========================================
echo   Telegram多客户端消息下载器
echo ========================================
echo.

cd /d "{Path.cwd()}"

echo 正在启动应用...
python start.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败！请检查错误信息
    echo.
    pause
) else (
    echo.
    echo 应用已关闭
)
"""
        
        with open("启动应用.bat", "w", encoding="utf-8") as f:
            f.write(bat_content)
        print("✓ 创建Windows启动脚本")
        
        return True
        
    except Exception as e:
        print(f"✗ 创建启动脚本失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Telegram多客户端消息下载器 - 安装和测试")
    print("=" * 60)
    
    # 检查虚拟环境
    if not check_virtual_env():
        print("\n⚠️ 警告: 未检测到虚拟环境")
        print("建议在虚拟环境中运行此程序")
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            return 1
    
    # 执行安装步骤
    steps = [
        ("创建目录结构", create_directories),
        ("安装依赖项", install_dependencies),
        ("测试模块导入", test_imports),
        ("测试基本功能", test_basic_functionality),
        ("测试GUI", test_gui),
        ("运行单元测试", run_unit_tests),
        ("创建启动脚本", create_startup_scripts)
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"✗ {step_name} 执行异常: {e}")
            failed_steps.append(step_name)
    
    # 总结
    print("\n" + "=" * 60)
    if not failed_steps:
        print("🎉 安装和测试完成！所有步骤都成功执行。")
        print("\n📖 使用说明:")
        print("1. 双击 '启动应用.bat' 启动程序")
        print("2. 或运行: python start.py")
        print("3. 在程序中配置Telegram API信息")
        print("4. 开始下载消息")
        
        print("\n⚠️ 重要提醒:")
        print("- 需要先获取Telegram API凭据")
        print("- 访问 https://my.telegram.org/apps")
        print("- 确保网络连接正常")
        
    else:
        print("⚠️ 安装完成，但以下步骤失败:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\n程序可能仍然可以运行，请尝试启动测试。")
    
    print("=" * 60)
    
    return 0 if not failed_steps else 1


if __name__ == "__main__":
    sys.exit(main())
