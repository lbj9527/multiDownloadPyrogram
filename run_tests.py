#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本
"""

import sys
import os
import subprocess
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行测试...")
    print("=" * 60)
    
    # 检查pytest是否安装
    try:
        import pytest
    except ImportError:
        print("错误: pytest未安装，请运行: pip install pytest")
        return False
    
    # 运行测试
    test_args = [
        "-v",  # 详细输出
        "--tb=short",  # 简短的错误回溯
        "--color=yes",  # 彩色输出
        "tests/"  # 测试目录
    ]
    
    try:
        result = pytest.main(test_args)
        
        if result == 0:
            print("\n" + "=" * 60)
            print("所有测试通过！")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("部分测试失败！")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return False


def check_code_quality():
    """检查代码质量"""
    print("\n" + "=" * 60)
    print("检查代码质量...")
    print("=" * 60)
    
    # 检查是否安装了代码质量工具
    tools = {
        "flake8": "代码风格检查",
        "black": "代码格式化",
        "mypy": "类型检查"
    }
    
    available_tools = []
    for tool, description in tools.items():
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
            available_tools.append((tool, description))
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"警告: {tool} 未安装 ({description})")
    
    if not available_tools:
        print("建议安装代码质量工具: pip install flake8 black mypy")
        return True
    
    # 运行可用的工具
    all_passed = True
    
    for tool, description in available_tools:
        print(f"\n运行 {tool} ({description})...")
        
        try:
            if tool == "flake8":
                result = subprocess.run([
                    "flake8", "src/", "--max-line-length=100", 
                    "--ignore=E203,W503"
                ], capture_output=True, text=True)
            elif tool == "black":
                result = subprocess.run([
                    "black", "--check", "--diff", "src/"
                ], capture_output=True, text=True)
            elif tool == "mypy":
                result = subprocess.run([
                    "mypy", "src/", "--ignore-missing-imports"
                ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ {tool} 检查通过")
            else:
                print(f"✗ {tool} 检查失败:")
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                all_passed = False
                
        except Exception as e:
            print(f"运行 {tool} 时发生错误: {e}")
            all_passed = False
    
    return all_passed


def check_dependencies():
    """检查依赖项"""
    print("\n" + "=" * 60)
    print("检查依赖项...")
    print("=" * 60)
    
    # 读取requirements.txt
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("错误: requirements.txt 文件不存在")
        return False
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    missing_packages = []
    
    for requirement in requirements:
        package_name = requirement.split('>=')[0].split('==')[0].split('<')[0]
        
        try:
            __import__(package_name.replace('-', '_'))
            print(f"✓ {package_name}")
        except ImportError:
            print(f"✗ {package_name} (未安装)")
            missing_packages.append(requirement)
    
    if missing_packages:
        print(f"\n缺少以下依赖项:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行: pip install -r requirements.txt")
        return False
    
    print("\n所有依赖项已安装")
    return True


def performance_test():
    """性能测试"""
    print("\n" + "=" * 60)
    print("运行性能测试...")
    print("=" * 60)
    
    import time
    import asyncio
    
    # 测试配置管理器性能
    print("测试配置管理器性能...")
    start_time = time.time()
    
    try:
        from src.utils.config_manager import ConfigManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # 多次读写配置
            for i in range(100):
                app_config = config_manager.load_app_config()
                app_config["test"] = f"value_{i}"
                config_manager.save_app_config(app_config)
        
        elapsed = time.time() - start_time
        print(f"✓ 配置管理器性能测试完成，耗时: {elapsed:.3f}s")
        
    except Exception as e:
        print(f"✗ 配置管理器性能测试失败: {e}")
        return False
    
    # 测试事件管理器性能
    print("测试事件管理器性能...")
    start_time = time.time()
    
    try:
        from src.core.event_manager import EventManager
        from src.models.events import BaseEvent, EventType
        
        event_manager = EventManager()
        
        # 发送大量事件
        for i in range(1000):
            event = BaseEvent(
                event_id=f"test_{i}",
                event_type=EventType.APP_STARTED,
                message=f"测试事件 {i}"
            )
            event_manager.emit_sync(event)
        
        elapsed = time.time() - start_time
        print(f"✓ 事件管理器性能测试完成，耗时: {elapsed:.3f}s")
        
        # 清理
        event_manager.stop_processing()
        
    except Exception as e:
        print(f"✗ 事件管理器性能测试失败: {e}")
        return False
    
    return True


def main():
    """主函数"""
    print("Telegram多客户端消息下载器 - 测试套件")
    print("=" * 60)
    
    all_passed = True
    
    # 检查依赖项
    if not check_dependencies():
        all_passed = False
    
    # 运行单元测试
    if not run_tests():
        all_passed = False
    
    # 检查代码质量
    if not check_code_quality():
        print("代码质量检查有问题，但不影响功能")
    
    # 运行性能测试
    if not performance_test():
        all_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！应用已准备就绪。")
    else:
        print("❌ 部分测试失败，请检查上述错误信息。")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
