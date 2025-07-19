#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单启动脚本
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # 创建必要的目录
        directories = ["downloads", "logs", "sessions", "config"]
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        
        # 导入并运行主程序
        from src.ui.main_window import MainWindow
        from src.utils.logger import setup_logger
        
        # 设置日志
        setup_logger()
        
        print("启动Telegram多客户端消息下载器...")
        
        # 创建并运行应用
        app = MainWindow()
        app.run()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所有依赖项: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
