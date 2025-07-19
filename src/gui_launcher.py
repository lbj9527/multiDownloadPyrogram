"""
GUI启动器

提供GUI应用程序的启动入口
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import asyncio
import logging

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.config import get_config, setup_config
from utils.logger import setup_logging, get_logger
from utils.proxy_manager import setup_proxy_manager


def setup_environment():
    """设置环境"""
    try:
        # 设置配置
        config = setup_config()
        
        # 设置日志
        logger = setup_logging(
            log_level=config.logging.level,
            log_file=config.logging.log_file,
            log_dir=config.logging.log_dir,
            console_output=config.logging.console_output,
            json_format=config.logging.json_format
        )
        
        # 设置代理管理器
        if config.proxy.enabled:
            setup_proxy_manager([("default", config.proxy)])
        
        return config, logger
        
    except Exception as e:
        # 如果设置失败，显示错误信息
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror("初始化错误", f"初始化环境失败: {e}")
        root.destroy()
        return None, None


def check_dependencies():
    """检查依赖"""
    required_modules = [
        'pyrogram',
        'aiofiles',
        'aiohttp',
        'tgcrypto'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        root = tk.Tk()
        root.withdraw()
        error_msg = f"缺少以下依赖模块:\n{', '.join(missing_modules)}\n\n请运行以下命令安装:\npip install -r requirements.txt"
        messagebox.showerror("依赖错误", error_msg)
        root.destroy()
        return False
    
    return True


def main():
    """主函数"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("错误: 需要Python 3.8或更高版本")
            print(f"当前版本: {sys.version}")
            input("按Enter键退出...")
            return
        
        # 检查必要的依赖
        required_packages = ['pyrogram', 'aiohttp', 'tkinter']
        missing_packages = []
        
        for package in required_packages:
            try:
                if package == 'tkinter':
                    import tkinter
                else:
                    __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"错误: 缺少必要的依赖包: {', '.join(missing_packages)}")
            print("请运行: pip install -r requirements.txt")
            input("按Enter键退出...")
            return
        
        # 设置环境变量
        os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
        
        # 导入GUI模块
        from gui import MainWindow
        
        # 启动GUI
        app = MainWindow()
        app.run()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("详细错误信息:")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")
    except Exception as e:
        print(f"启动失败: {e}")
        print("详细错误信息:")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")


if __name__ == "__main__":
    main() 