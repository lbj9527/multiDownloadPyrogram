#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

def main():
    """主函数"""
    print("MultiDownloadPyrogram GUI启动器")
    print("=" * 50)
    print("正在启动GUI界面...")
    print("提示: 如果首次运行，请确保已安装所有依赖包")
    print("安装命令: pip install -r requirements.txt")
    print("-" * 50)
    
    try:
        # 现在可以直接导入GUI模块
        from gui_launcher import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保项目结构正确，并且已安装所有依赖")
        input("按Enter键退出...")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        input("按Enter键退出...")
        sys.exit(1)

if __name__ == "__main__":
    main() 