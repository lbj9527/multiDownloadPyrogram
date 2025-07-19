#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置窗口
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any

from ..utils.config_manager import ConfigManager
from ..utils.logger import get_logger


class SettingsWindow:
    """设置窗口类"""
    
    def __init__(self, parent, config_manager: ConfigManager):
        """
        初始化设置窗口
        
        Args:
            parent: 父窗口
            config_manager: 配置管理器
        """
        self.parent = parent
        self.config_manager = config_manager
        self.logger = get_logger(__name__)
        
        # 当前配置
        self.current_config = self.config_manager.load_app_config()
        
        # 创建窗口
        self.window = None
        
    def show(self):
        """显示设置窗口"""
        if self.window is not None:
            self.window.focus()
            return
        
        # 创建设置窗口
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("设置")
        self.window.geometry("600x500")
        self.window.resizable(False, False)
        
        # 设置窗口图标
        try:
            self.window.iconbitmap("assets/icon.ico")
        except:
            pass
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 创建界面
        self.setup_ui()
        
        # 加载当前设置
        self.load_settings()
        
        # 使窗口模态
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 居中显示
        self.center_window()
    
    def center_window(self):
        """居中显示窗口"""
        # 检查窗口是否存在
        if not self.window:
            self.logger.error("窗口对象不存在，无法居中")
            return

        try:
            # 更新窗口以获取准确的尺寸
            self.window.update_idletasks()

            # 获取窗口大小，如果获取失败则使用默认值
            width = self.window.winfo_width()
            height = self.window.winfo_height()

            # 如果窗口尺寸无效，使用默认尺寸
            if width <= 1 or height <= 1:
                width = 800  # 默认宽度
                height = 600  # 默认高度
                self.logger.warning("窗口尺寸获取失败，使用默认尺寸")

            # 获取屏幕大小
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()

            # 验证屏幕尺寸
            if screen_width <= 0 or screen_height <= 0:
                self.logger.error("屏幕尺寸获取失败")
                return

            # 确保窗口不会超出屏幕边界
            if width > screen_width:
                width = int(screen_width * 0.9)
            if height > screen_height:
                height = int(screen_height * 0.9)

            # 计算居中位置
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)

            # 设置窗口位置和大小
            geometry = f"{width}x{height}+{x}+{y}"
            self.window.geometry(geometry)

            self.logger.debug(f"窗口居中设置: {geometry}")

        except Exception as e:
            self.logger.error(f"窗口居中失败: {e}")
            # 如果居中失败，至少确保窗口可见
            try:
                if self.window:
                    self.window.geometry("800x600+100+100")
            except Exception as fallback_error:
                self.logger.error(f"窗口位置设置完全失败: {fallback_error}")
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 创建选项卡
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # 应用设置选项卡
        self.create_app_settings_tab()
        
        # 下载设置选项卡
        self.create_download_settings_tab()
        
        # 日志设置选项卡
        self.create_logging_settings_tab()

        # 代理设置选项卡
        self.create_proxy_settings_tab()

        # 按钮框架
        self.create_buttons()
    
    def create_app_settings_tab(self):
        """创建应用设置选项卡"""
        app_tab = self.tabview.add("应用设置")
        
        # 主题设置
        theme_frame = ctk.CTkFrame(app_tab)
        theme_frame.pack(fill="x", padx=10, pady=10)
        
        theme_label = ctk.CTkLabel(theme_frame, text="主题设置", font=ctk.CTkFont(size=14, weight="bold"))
        theme_label.pack(pady=(10, 5))
        
        self.theme_var = ctk.StringVar(value=self.current_config.get("app", {}).get("theme", "dark"))
        
        theme_option_frame = ctk.CTkFrame(theme_frame)
        theme_option_frame.pack(pady=(0, 10))
        
        dark_radio = ctk.CTkRadioButton(theme_option_frame, text="深色主题", variable=self.theme_var, value="dark")
        dark_radio.pack(side="left", padx=20, pady=10)
        
        light_radio = ctk.CTkRadioButton(theme_option_frame, text="浅色主题", variable=self.theme_var, value="light")
        light_radio.pack(side="left", padx=20, pady=10)
        
        # 窗口设置
        window_frame = ctk.CTkFrame(app_tab)
        window_frame.pack(fill="x", padx=10, pady=10)
        
        window_label = ctk.CTkLabel(window_frame, text="窗口设置", font=ctk.CTkFont(size=14, weight="bold"))
        window_label.pack(pady=(10, 5))
        
        # 窗口大小
        size_frame = ctk.CTkFrame(window_frame)
        size_frame.pack(fill="x", padx=10, pady=5)
        
        width_label = ctk.CTkLabel(size_frame, text="宽度:")
        width_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.width_entry = ctk.CTkEntry(size_frame, width=100)
        self.width_entry.grid(row=0, column=1, padx=5, pady=5)
        
        height_label = ctk.CTkLabel(size_frame, text="高度:")
        height_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        self.height_entry = ctk.CTkEntry(size_frame, width=100)
        self.height_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # 语言设置
        lang_frame = ctk.CTkFrame(app_tab)
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="语言设置", font=ctk.CTkFont(size=14, weight="bold"))
        lang_label.pack(pady=(10, 5))
        
        self.language_var = ctk.StringVar(value=self.current_config.get("app", {}).get("language", "zh"))
        language_combo = ctk.CTkComboBox(lang_frame, variable=self.language_var, values=["zh", "en"])
        language_combo.pack(pady=(0, 10))
    
    def create_download_settings_tab(self):
        """创建下载设置选项卡"""
        download_tab = self.tabview.add("下载设置")
        
        # 默认路径
        path_frame = ctk.CTkFrame(download_tab)
        path_frame.pack(fill="x", padx=10, pady=10)
        
        path_label = ctk.CTkLabel(path_frame, text="默认下载路径", font=ctk.CTkFont(size=14, weight="bold"))
        path_label.pack(pady=(10, 5))
        
        path_input_frame = ctk.CTkFrame(path_frame)
        path_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.download_path_entry = ctk.CTkEntry(path_input_frame, placeholder_text="下载路径")
        self.download_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=5)
        
        browse_button = ctk.CTkButton(path_input_frame, text="浏览", width=80, command=self.browse_download_path)
        browse_button.pack(side="right", padx=5, pady=5)
        
        # 并发设置
        concurrent_frame = ctk.CTkFrame(download_tab)
        concurrent_frame.pack(fill="x", padx=10, pady=10)
        
        concurrent_label = ctk.CTkLabel(concurrent_frame, text="并发设置", font=ctk.CTkFont(size=14, weight="bold"))
        concurrent_label.pack(pady=(10, 5))
        
        concurrent_input_frame = ctk.CTkFrame(concurrent_frame)
        concurrent_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        max_downloads_label = ctk.CTkLabel(concurrent_input_frame, text="最大并发下载数:")
        max_downloads_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.max_downloads_entry = ctk.CTkEntry(concurrent_input_frame, width=100)
        self.max_downloads_entry.grid(row=0, column=1, padx=5, pady=5)
        
        timeout_label = ctk.CTkLabel(concurrent_input_frame, text="超时时间(秒):")
        timeout_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.timeout_entry = ctk.CTkEntry(concurrent_input_frame, width=100)
        self.timeout_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 其他选项
        options_frame = ctk.CTkFrame(download_tab)
        options_frame.pack(fill="x", padx=10, pady=10)
        
        options_label = ctk.CTkLabel(options_frame, text="其他选项", font=ctk.CTkFont(size=14, weight="bold"))
        options_label.pack(pady=(10, 5))
        
        self.auto_create_folders_var = ctk.BooleanVar()
        auto_create_check = ctk.CTkCheckBox(options_frame, text="自动创建文件夹", variable=self.auto_create_folders_var)
        auto_create_check.pack(pady=5)
    
    def create_logging_settings_tab(self):
        """创建日志设置选项卡"""
        logging_tab = self.tabview.add("日志设置")
        
        # 日志级别
        level_frame = ctk.CTkFrame(logging_tab)
        level_frame.pack(fill="x", padx=10, pady=10)
        
        level_label = ctk.CTkLabel(level_frame, text="日志级别", font=ctk.CTkFont(size=14, weight="bold"))
        level_label.pack(pady=(10, 5))
        
        self.log_level_var = ctk.StringVar()
        level_combo = ctk.CTkComboBox(level_frame, variable=self.log_level_var, 
                                     values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        level_combo.pack(pady=(0, 10))
        
        # 日志文件设置
        file_frame = ctk.CTkFrame(logging_tab)
        file_frame.pack(fill="x", padx=10, pady=10)
        
        file_label = ctk.CTkLabel(file_frame, text="日志文件设置", font=ctk.CTkFont(size=14, weight="bold"))
        file_label.pack(pady=(10, 5))
        
        file_input_frame = ctk.CTkFrame(file_frame)
        file_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        max_size_label = ctk.CTkLabel(file_input_frame, text="最大文件大小:")
        max_size_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.max_file_size_entry = ctk.CTkEntry(file_input_frame, width=100)
        self.max_file_size_entry.grid(row=0, column=1, padx=5, pady=5)
        
        backup_count_label = ctk.CTkLabel(file_input_frame, text="备份文件数:")
        backup_count_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.backup_count_entry = ctk.CTkEntry(file_input_frame, width=100)
        self.backup_count_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 控制台输出
        console_frame = ctk.CTkFrame(logging_tab)
        console_frame.pack(fill="x", padx=10, pady=10)
        
        console_label = ctk.CTkLabel(console_frame, text="控制台输出", font=ctk.CTkFont(size=14, weight="bold"))
        console_label.pack(pady=(10, 5))
        
        self.console_output_var = ctk.BooleanVar()
        console_check = ctk.CTkCheckBox(console_frame, text="启用控制台输出", variable=self.console_output_var)
        console_check.pack(pady=(0, 10))

    def create_proxy_settings_tab(self):
        """创建代理设置选项卡"""
        proxy_tab = self.tabview.add("代理设置")

        # 代理启用设置
        enable_frame = ctk.CTkFrame(proxy_tab)
        enable_frame.pack(fill="x", padx=10, pady=10)

        enable_label = ctk.CTkLabel(enable_frame, text="代理设置", font=ctk.CTkFont(size=14, weight="bold"))
        enable_label.pack(pady=(10, 5))

        self.proxy_enabled_var = ctk.BooleanVar()
        proxy_enable_check = ctk.CTkCheckBox(enable_frame, text="启用代理",
                                           variable=self.proxy_enabled_var,
                                           command=self.on_proxy_enabled_changed)
        proxy_enable_check.pack(pady=(0, 10))

        # 代理类型设置
        type_frame = ctk.CTkFrame(proxy_tab)
        type_frame.pack(fill="x", padx=10, pady=10)

        type_label = ctk.CTkLabel(type_frame, text="代理类型", font=ctk.CTkFont(size=14, weight="bold"))
        type_label.pack(pady=(10, 5))

        self.proxy_type_var = ctk.StringVar()
        proxy_type_combo = ctk.CTkComboBox(type_frame, variable=self.proxy_type_var,
                                         values=["socks5", "socks4", "http"])
        proxy_type_combo.pack(pady=(0, 10))

        # 代理服务器设置
        server_frame = ctk.CTkFrame(proxy_tab)
        server_frame.pack(fill="x", padx=10, pady=10)

        server_label = ctk.CTkLabel(server_frame, text="代理服务器", font=ctk.CTkFont(size=14, weight="bold"))
        server_label.pack(pady=(10, 5))

        server_input_frame = ctk.CTkFrame(server_frame)
        server_input_frame.pack(fill="x", padx=10, pady=(0, 10))

        host_label = ctk.CTkLabel(server_input_frame, text="主机:")
        host_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.proxy_host_entry = ctk.CTkEntry(server_input_frame, width=200, placeholder_text="127.0.0.1")
        self.proxy_host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        port_label = ctk.CTkLabel(server_input_frame, text="端口:")
        port_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.proxy_port_entry = ctk.CTkEntry(server_input_frame, width=100, placeholder_text="1080")
        self.proxy_port_entry.grid(row=0, column=3, padx=5, pady=5)

        # 配置网格权重
        server_input_frame.grid_columnconfigure(1, weight=1)

        # 认证设置
        auth_frame = ctk.CTkFrame(proxy_tab)
        auth_frame.pack(fill="x", padx=10, pady=10)

        auth_label = ctk.CTkLabel(auth_frame, text="认证信息（可选）", font=ctk.CTkFont(size=14, weight="bold"))
        auth_label.pack(pady=(10, 5))

        auth_input_frame = ctk.CTkFrame(auth_frame)
        auth_input_frame.pack(fill="x", padx=10, pady=(0, 10))

        username_label = ctk.CTkLabel(auth_input_frame, text="用户名:")
        username_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.proxy_username_entry = ctk.CTkEntry(auth_input_frame, width=150, placeholder_text="用户名（可选）")
        self.proxy_username_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        password_label = ctk.CTkLabel(auth_input_frame, text="密码:")
        password_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.proxy_password_entry = ctk.CTkEntry(auth_input_frame, width=150, placeholder_text="密码（可选）", show="*")
        self.proxy_password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 配置网格权重
        auth_input_frame.grid_columnconfigure(1, weight=1)

        # 测试按钮
        test_frame = ctk.CTkFrame(proxy_tab)
        test_frame.pack(fill="x", padx=10, pady=10)

        test_label = ctk.CTkLabel(test_frame, text="连接测试", font=ctk.CTkFont(size=14, weight="bold"))
        test_label.pack(pady=(10, 5))

        test_button_frame = ctk.CTkFrame(test_frame)
        test_button_frame.pack(pady=(0, 10))

        self.test_proxy_button = ctk.CTkButton(test_button_frame, text="测试代理连接",
                                             command=self.test_proxy_connection)
        self.test_proxy_button.pack(side="left", padx=5, pady=5)

        self.proxy_status_label = ctk.CTkLabel(test_button_frame, text="")
        self.proxy_status_label.pack(side="left", padx=10, pady=5)

    def create_buttons(self):
        """创建按钮"""
        button_frame = ctk.CTkFrame(self.window)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 确定按钮
        ok_button = ctk.CTkButton(button_frame, text="确定", command=self.save_settings)
        ok_button.pack(side="right", padx=5, pady=10)
        
        # 取消按钮
        cancel_button = ctk.CTkButton(button_frame, text="取消", command=self.on_close)
        cancel_button.pack(side="right", padx=5, pady=10)
        
        # 应用按钮
        apply_button = ctk.CTkButton(button_frame, text="应用", command=self.apply_settings)
        apply_button.pack(side="right", padx=5, pady=10)
        
        # 重置按钮
        reset_button = ctk.CTkButton(button_frame, text="重置", command=self.reset_settings)
        reset_button.pack(side="left", padx=5, pady=10)
    
    def load_settings(self):
        """加载当前设置"""
        try:
            # 应用设置
            app_config = self.current_config.get("app", {})
            window_size = app_config.get("window_size", {})
            self.width_entry.insert(0, str(window_size.get("width", 1200)))
            self.height_entry.insert(0, str(window_size.get("height", 800)))
            
            # 下载设置
            download_config = self.current_config.get("download", {})
            self.download_path_entry.insert(0, download_config.get("default_path", "./downloads"))
            self.max_downloads_entry.insert(0, str(download_config.get("max_concurrent_downloads", 5)))
            self.timeout_entry.insert(0, str(download_config.get("timeout", 30)))
            self.auto_create_folders_var.set(download_config.get("auto_create_folders", True))
            
            # 日志设置
            logging_config = self.current_config.get("logging", {})
            self.log_level_var.set(logging_config.get("level", "INFO"))
            self.max_file_size_entry.insert(0, logging_config.get("max_file_size", "10MB"))
            self.backup_count_entry.insert(0, str(logging_config.get("backup_count", 5)))
            self.console_output_var.set(logging_config.get("console_output", True))

            # 代理设置
            proxy_config = self.current_config.get("proxy", {})
            self.proxy_enabled_var.set(proxy_config.get("enabled", False))
            self.proxy_type_var.set(proxy_config.get("type", "socks5"))
            self.proxy_host_entry.insert(0, proxy_config.get("host", "127.0.0.1"))
            self.proxy_port_entry.insert(0, str(proxy_config.get("port", 1080)))
            self.proxy_username_entry.insert(0, proxy_config.get("username", ""))
            self.proxy_password_entry.insert(0, proxy_config.get("password", ""))

            # 更新代理控件状态
            self.on_proxy_enabled_changed()

        except Exception as e:
            self.logger.error(f"加载设置失败: {e}")
    
    def browse_download_path(self):
        """浏览下载路径"""
        try:
            from tkinter import filedialog
            
            folder_path = filedialog.askdirectory(
                title="选择下载文件夹",
                initialdir=self.download_path_entry.get() or "./downloads"
            )
            
            if folder_path:
                self.download_path_entry.delete(0, tk.END)
                self.download_path_entry.insert(0, folder_path)
                
        except Exception as e:
            self.logger.error(f"浏览文件夹失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        if self.apply_settings():
            self.on_close()
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 收集设置
            new_config = self.current_config.copy()
            
            # 应用设置
            new_config["app"]["theme"] = self.theme_var.get()
            new_config["app"]["language"] = self.language_var.get()
            new_config["app"]["window_size"]["width"] = int(self.width_entry.get())
            new_config["app"]["window_size"]["height"] = int(self.height_entry.get())
            
            # 下载设置
            new_config["download"]["default_path"] = self.download_path_entry.get()
            new_config["download"]["max_concurrent_downloads"] = int(self.max_downloads_entry.get())
            new_config["download"]["timeout"] = int(self.timeout_entry.get())
            new_config["download"]["auto_create_folders"] = self.auto_create_folders_var.get()
            
            # 日志设置
            new_config["logging"]["level"] = self.log_level_var.get()
            new_config["logging"]["max_file_size"] = self.max_file_size_entry.get()
            new_config["logging"]["backup_count"] = int(self.backup_count_entry.get())
            new_config["logging"]["console_output"] = self.console_output_var.get()

            # 代理设置
            new_config["proxy"]["enabled"] = self.proxy_enabled_var.get()
            new_config["proxy"]["type"] = self.proxy_type_var.get()
            new_config["proxy"]["host"] = self.proxy_host_entry.get().strip()
            new_config["proxy"]["port"] = int(self.proxy_port_entry.get())
            new_config["proxy"]["username"] = self.proxy_username_entry.get().strip()
            new_config["proxy"]["password"] = self.proxy_password_entry.get().strip()

            # 保存配置
            if self.config_manager.save_app_config(new_config):
                self.current_config = new_config
                self.logger.info("设置已保存")
                return True
            else:
                self.logger.error("保存设置失败")
                return False
                
        except ValueError as e:
            self.logger.error(f"设置值无效: {e}")
            return False
        except Exception as e:
            self.logger.error(f"应用设置失败: {e}")
            return False
    
    def reset_settings(self):
        """重置设置"""
        try:
            # 重新加载默认配置
            self.current_config = self.config_manager.load_app_config()
            
            # 清空所有输入框
            for widget in [self.width_entry, self.height_entry, self.download_path_entry,
                          self.max_downloads_entry, self.timeout_entry, self.max_file_size_entry,
                          self.backup_count_entry, self.proxy_host_entry, self.proxy_port_entry,
                          self.proxy_username_entry, self.proxy_password_entry]:
                widget.delete(0, tk.END)
            
            # 重新加载设置
            self.load_settings()
            
            self.logger.info("设置已重置")
            
        except Exception as e:
            self.logger.error(f"重置设置失败: {e}")
    
    def on_proxy_enabled_changed(self):
        """代理启用状态变化处理"""
        enabled = self.proxy_enabled_var.get()

        # 更新代理相关控件的状态
        widgets = [
            self.proxy_host_entry,
            self.proxy_port_entry,
            self.proxy_username_entry,
            self.proxy_password_entry,
            self.test_proxy_button
        ]

        for widget in widgets:
            if enabled:
                widget.configure(state="normal")
            else:
                widget.configure(state="disabled")

        # 清空状态标签
        self.proxy_status_label.configure(text="")

    def test_proxy_connection(self):
        """测试代理连接"""
        try:
            import asyncio
            import aiohttp
            import threading

            # 更新状态
            self.proxy_status_label.configure(text="正在测试...", text_color="orange")
            self.test_proxy_button.configure(state="disabled")

            # 获取代理设置
            proxy_type = self.proxy_type_var.get()
            proxy_host = self.proxy_host_entry.get().strip()
            proxy_port = self.proxy_port_entry.get().strip()
            proxy_username = self.proxy_username_entry.get().strip()
            proxy_password = self.proxy_password_entry.get().strip()

            # 验证输入
            if not proxy_host or not proxy_port:
                self.proxy_status_label.configure(text="请填写主机和端口", text_color="red")
                self.test_proxy_button.configure(state="normal")
                return

            try:
                port = int(proxy_port)
                if port <= 0 or port > 65535:
                    raise ValueError("端口范围无效")
            except ValueError:
                self.proxy_status_label.configure(text="端口号无效", text_color="red")
                self.test_proxy_button.configure(state="normal")
                return

            # 在新线程中测试连接
            def test_connection():
                try:
                    # 构建代理URL
                    if proxy_username and proxy_password:
                        proxy_url = f"{proxy_type}://{proxy_username}:{proxy_password}@{proxy_host}:{port}"
                    else:
                        proxy_url = f"{proxy_type}://{proxy_host}:{port}"

                    async def test_async():
                        timeout = aiohttp.ClientTimeout(total=10)
                        connector = aiohttp.TCPConnector()

                        async with aiohttp.ClientSession(
                            connector=connector,
                            timeout=timeout
                        ) as session:
                            test_url = self.current_config.get("proxy", {}).get("test_url", "https://api.telegram.org")

                            async with session.get(
                                test_url,
                                proxy=proxy_url
                            ) as response:
                                if response.status == 200:
                                    return True, "连接成功"
                                else:
                                    return False, f"HTTP {response.status}"

                    # 运行异步测试
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success, message = loop.run_until_complete(test_async())

                        # 更新UI（在主线程中）
                        if self.window:
                            self.window.after(0, lambda: self.update_proxy_test_result(success, message))
                    finally:
                        loop.close()

                except Exception as e:
                    # 更新UI（在主线程中）
                    if self.window:
                        self.window.after(0, lambda: self.update_proxy_test_result(False, str(e)))

            # 启动测试线程
            test_thread = threading.Thread(target=test_connection, daemon=True)
            test_thread.start()

        except Exception as e:
            self.proxy_status_label.configure(text=f"测试失败: {e}", text_color="red")
            self.test_proxy_button.configure(state="normal")
            self.logger.error(f"代理测试失败: {e}")

    def update_proxy_test_result(self, success: bool, message: str):
        """更新代理测试结果"""
        if success:
            self.proxy_status_label.configure(text=f"✓ {message}", text_color="green")
        else:
            self.proxy_status_label.configure(text=f"✗ {message}", text_color="red")

        self.test_proxy_button.configure(state="normal")

    def on_close(self):
        """关闭窗口"""
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None
