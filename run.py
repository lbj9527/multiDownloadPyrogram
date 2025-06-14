#!/usr/bin/env python3
"""
MultiDownloadPyrogram 运行脚本
简化的程序入口，使用配置文件运行
"""

import sys
import asyncio
from src.main import main

if __name__ == "__main__":
    try:
        print("MultiDownloadPyrogram - Telegram频道历史消息批量下载工具")
        print("使用配置文件 config.json 中的设置运行...")
        print("-" * 50)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1) 