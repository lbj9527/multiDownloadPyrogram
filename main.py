#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram多客户端消息下载器
主程序入口
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger


def main():
    """主程序入口"""
    # 设置日志
    setup_logger()
    
    # 创建必要的目录
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("sessions", exist_ok=True)
    
    # 启动GUI应用
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
