#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理功能测试脚本
"""

import sys
import asyncio
from pathlib import Path

def test_proxy_functionality():
    """测试代理功能"""
    try:
        # 添加src目录到Python路径
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        print("=" * 60)
        print("代理功能测试")
        print("=" * 60)
        
        # 测试代理工具模块
        print("\n1. 测试代理工具模块...")
        from src.utils.proxy_utils import ProxyManager, get_proxy_manager
        
        proxy_manager = get_proxy_manager()
        print("✓ 代理管理器创建成功")
        
        # 测试代理配置验证
        print("\n2. 测试代理配置验证...")
        
        # 测试有效配置
        valid_config = {
            "enabled": True,
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "",
            "password": ""
        }
        
        is_valid, message = proxy_manager.validate_proxy_config(valid_config)
        print(f"✓ 有效配置验证: {is_valid} - {message}")
        
        # 测试无效配置
        invalid_config = {
            "enabled": True,
            "type": "invalid_type",
            "host": "",
            "port": 99999
        }
        
        is_valid, message = proxy_manager.validate_proxy_config(invalid_config)
        print(f"✓ 无效配置验证: {is_valid} - {message}")
        
        # 测试代理URL生成
        print("\n3. 测试代理URL生成...")
        proxy_manager.set_proxy_config(valid_config)
        
        proxy_url = proxy_manager.get_proxy_url()
        print(f"✓ 代理URL: {proxy_url}")
        
        pyrogram_proxy = proxy_manager.get_pyrogram_proxy()
        print(f"✓ Pyrogram代理配置: {pyrogram_proxy}")
        
        proxy_info = proxy_manager.get_proxy_info()
        print(f"✓ 代理信息: {proxy_info}")
        
        # 测试配置管理器集成
        print("\n4. 测试配置管理器集成...")
        from src.utils.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        app_config = config_manager.load_app_config()
        
        if "proxy" in app_config:
            print("✓ 应用配置包含代理设置")
            print(f"  代理启用: {app_config['proxy']['enabled']}")
            print(f"  代理类型: {app_config['proxy']['type']}")
            print(f"  代理地址: {app_config['proxy']['host']}:{app_config['proxy']['port']}")
        else:
            print("✗ 应用配置缺少代理设置")
        
        # 测试代理连接（如果有可用的代理）
        print("\n5. 测试代理连接...")
        
        # 使用一个测试代理配置
        test_config = {
            "enabled": False,  # 默认不启用，避免实际连接
            "type": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "",
            "password": ""
        }
        
        proxy_manager.set_proxy_config(test_config)
        
        if test_config["enabled"]:
            async def test_connection():
                success, message = await proxy_manager.test_proxy_connection()
                print(f"代理连接测试: {success} - {message}")
            
            asyncio.run(test_connection())
        else:
            print("✓ 代理连接测试跳过（代理未启用）")
        
        # 测试设置窗口代理功能
        print("\n6. 测试设置窗口代理功能...")
        try:
            import customtkinter as ctk
            
            # 创建测试窗口
            root = ctk.CTk()
            root.withdraw()  # 隐藏窗口
            
            from src.ui.settings_window import SettingsWindow
            from src.utils.config_manager import ConfigManager

            # 创建设置窗口（但不显示）
            config_manager = ConfigManager()
            settings = SettingsWindow(root, config_manager)

            # 等待窗口完全初始化
            root.update_idletasks()
            
            # 测试代理相关属性是否存在
            required_attrs = [
                'proxy_enabled_var',
                'proxy_type_var', 
                'proxy_host_entry',
                'proxy_port_entry',
                'proxy_username_entry',
                'proxy_password_entry',
                'test_proxy_button',
                'proxy_status_label'
            ]
            
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(settings, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                print(f"✗ 设置窗口缺少代理属性: {missing_attrs}")
            else:
                print("✓ 设置窗口代理属性完整")
            
            # 销毁测试窗口
            root.destroy()
            
        except Exception as e:
            print(f"✗ 设置窗口测试失败: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 代理功能测试完成！")
        print("=" * 60)
        
        print("\n📖 代理使用说明:")
        print("1. 在设置窗口中启用代理")
        print("2. 选择代理类型（SOCKS5/SOCKS4/HTTP）")
        print("3. 填写代理服务器地址和端口")
        print("4. 如需要，填写用户名和密码")
        print("5. 点击'测试代理连接'验证配置")
        print("6. 保存设置后重启客户端生效")
        
        print("\n⚠️ 注意事项:")
        print("- 确保代理服务器可用")
        print("- 代理配置错误可能导致连接失败")
        print("- 建议先测试连接再保存配置")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 代理功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_proxy_functionality()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)
