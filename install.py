#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装脚本
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("需要Python 3.8或更高版本")
        return False
    
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_system_requirements():
    """检查系统要求"""
    print("\n检查系统要求...")
    
    system = platform.system()
    print(f"操作系统: {system} {platform.release()}")
    
    if system == "Windows":
        version = platform.version()
        print(f"Windows版本: {version}")
        
        # 检查是否为Windows 10/11
        if "10." in version or "11." in version:
            print("✓ 支持的Windows版本")
        else:
            print("⚠️ 建议使用Windows 10或11")
    else:
        print("⚠️ 此应用主要为Windows设计，其他系统可能存在兼容性问题")
    
    return True


def install_dependencies():
    """安装依赖项"""
    print("\n安装依赖项...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt文件不存在")
        return False
    
    try:
        # 升级pip
        print("升级pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        print("✓ pip已升级")
        
        # 安装依赖
        print("安装项目依赖...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✓ 依赖项安装完成")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装依赖项失败: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    print("\n创建目录结构...")
    
    directories = [
        "downloads",
        "logs", 
        "sessions",
        "config"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        print(f"✓ 创建目录: {directory}")
    
    return True


def setup_config():
    """设置初始配置"""
    print("\n设置初始配置...")
    
    try:
        # 导入配置管理器
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from src.utils.config_manager import ConfigManager
        
        # 初始化配置
        config_manager = ConfigManager()
        print("✓ 配置文件已创建")
        
        return True
        
    except Exception as e:
        print(f"❌ 设置配置失败: {e}")
        return False


def run_tests():
    """运行基本测试"""
    print("\n运行基本测试...")
    
    try:
        # 测试导入主要模块
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from src.models.client_config import ClientConfig, MultiClientConfig
        from src.models.download_config import DownloadConfig
        from src.utils.config_manager import ConfigManager
        from src.core.event_manager import EventManager
        
        print("✓ 核心模块导入成功")
        
        # 测试配置管理器
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            app_config = config_manager.load_app_config()
            assert "app" in app_config
        
        print("✓ 配置管理器测试通过")
        
        # 测试事件管理器
        event_manager = EventManager()
        event_manager.stop_processing()
        
        print("✓ 事件管理器测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def create_shortcuts():
    """创建快捷方式"""
    print("\n创建启动脚本...")
    
    try:
        # 创建启动脚本
        if platform.system() == "Windows":
            # Windows批处理文件
            bat_content = f"""@echo off
cd /d "{Path.cwd()}"
python main.py
pause
"""
            with open("启动应用.bat", "w", encoding="gbk") as f:
                f.write(bat_content)
            print("✓ 创建Windows启动脚本: 启动应用.bat")
            
            # 测试脚本
            test_bat_content = f"""@echo off
cd /d "{Path.cwd()}"
python run_tests.py
pause
"""
            with open("运行测试.bat", "w", encoding="gbk") as f:
                f.write(test_bat_content)
            print("✓ 创建测试脚本: 运行测试.bat")
        
        else:
            # Unix shell脚本
            sh_content = f"""#!/bin/bash
cd "{Path.cwd()}"
python3 main.py
"""
            with open("start_app.sh", "w") as f:
                f.write(sh_content)
            os.chmod("start_app.sh", 0o755)
            print("✓ 创建启动脚本: start_app.sh")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建启动脚本失败: {e}")
        return False


def print_usage_instructions():
    """打印使用说明"""
    print("\n" + "=" * 60)
    print("🎉 安装完成！")
    print("=" * 60)
    
    print("\n📖 使用说明:")
    print("1. 启动应用:")
    if platform.system() == "Windows":
        print("   - 双击 '启动应用.bat' 文件")
        print("   - 或在命令行运行: python main.py")
    else:
        print("   - 运行: ./start_app.sh")
        print("   - 或在命令行运行: python3 main.py")
    
    print("\n2. 配置客户端:")
    print("   - 在'客户端配置'选项卡中添加Telegram API信息")
    print("   - 选择账户类型（普通或Premium）")
    print("   - 填写API ID、API Hash、电话号码和会话名称")
    print("   - 点击'登录'按钮登录客户端")
    
    print("\n3. 下载消息:")
    print("   - 在'消息下载'选项卡中设置下载参数")
    print("   - 输入频道ID或用户名")
    print("   - 设置起始消息ID和下载数量")
    print("   - 选择下载路径和媒体类型")
    print("   - 点击'开始下载'")
    
    print("\n4. 查看日志:")
    print("   - 在'日志查看'选项卡中查看运行日志")
    print("   - 可以按级别和类型过滤日志")
    
    print("\n⚠️ 重要提醒:")
    print("- 首次使用需要获取Telegram API凭据")
    print("- 访问 https://my.telegram.org/apps 创建应用")
    print("- 确保网络连接正常")
    print("- 遵守Telegram的使用条款和API限制")
    
    print("\n🔧 故障排除:")
    if platform.system() == "Windows":
        print("- 运行测试: 双击 '运行测试.bat'")
    else:
        print("- 运行测试: python3 run_tests.py")
    print("- 查看日志文件: logs/app.log")
    print("- 检查配置文件: config/")
    
    print("\n📞 获取帮助:")
    print("- 查看README.md文件")
    print("- 检查GitHub Issues")
    print("- 查看Telegram API文档")
    
    print("\n" + "=" * 60)


def main():
    """主安装函数"""
    print("Telegram多客户端消息下载器 - 安装程序")
    print("=" * 60)
    
    steps = [
        ("检查Python版本", check_python_version),
        ("检查系统要求", check_system_requirements),
        ("安装依赖项", install_dependencies),
        ("创建目录结构", create_directories),
        ("设置初始配置", setup_config),
        ("运行基本测试", run_tests),
        ("创建启动脚本", create_shortcuts)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"\n❌ 安装失败: {step_name}")
            return 1
    
    print_usage_instructions()
    return 0


if __name__ == "__main__":
    sys.exit(main())
