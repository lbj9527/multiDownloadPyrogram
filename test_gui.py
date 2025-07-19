#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI测试脚本
"""

import sys
import os
from pathlib import Path

def test_gui():
    """测试GUI启动"""
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # 创建必要的目录
        directories = ["downloads", "logs", "sessions", "config"]
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        
        print("正在测试GUI组件...")
        
        # 测试CustomTkinter
        import customtkinter as ctk
        print("✓ CustomTkinter导入成功")
        
        # 测试创建窗口
        root = ctk.CTk()
        root.title("测试窗口")
        root.geometry("400x300")
        
        # 添加一些组件
        label = ctk.CTkLabel(root, text="GUI测试成功！")
        label.pack(pady=20)
        
        button = ctk.CTkButton(root, text="关闭", command=root.quit)
        button.pack(pady=10)
        
        print("✓ GUI组件创建成功")
        print("显示测试窗口（3秒后自动关闭）...")
        
        # 3秒后自动关闭
        root.after(3000, root.quit)
        
        # 显示窗口
        root.mainloop()
        
        print("✓ GUI测试完成")
        return True
        
    except Exception as e:
        print(f"✗ GUI测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_gui()
    sys.exit(0 if success else 1)
