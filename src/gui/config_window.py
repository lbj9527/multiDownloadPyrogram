#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置窗口

提供应用程序配置的管理界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any
import json

# 修改为绝对导入
from utils.config import Config, TelegramConfig, ProxyConfig, DownloadConfig, LoggingConfig
from utils.logger import get_logger


class ConfigWindow:
    """配置窗口类"""
    
    def __init__(self, parent: tk.Tk, config: Optional[Config] = None):
        """
        初始化配置窗口
        
        Args:
            parent: 父窗口
            config: 配置对象
        """
        self.parent = parent
        self.config = config or Config()
        self.logger = get_logger(f"{__name__}.ConfigWindow")
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("配置设置")
        self.window.geometry("600x500")
        self.window.resizable(True, True)
        
        # 设置窗口图标
        try:
            # self.window.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # 变量
        self.is_modified = False
        self.setup_variables()
        
        # 创建GUI
        self.create_widgets()
        self.load_config()
        
        # 绑定事件
        self.setup_bindings()
        
        # 窗口居中
        self.center_window()
        
        self.logger.info("配置窗口初始化完成")
    
    def setup_variables(self):
        """设置变量"""
        # Telegram配置
        self.api_id_var = tk.StringVar()
        self.api_hash_var = tk.StringVar()
        self.phone_number_var = tk.StringVar()
        self.session_string_var = tk.StringVar()
        self.max_concurrent_transmissions_var = tk.IntVar()
        self.sleep_threshold_var = tk.IntVar()
        self.no_updates_var = tk.BooleanVar()
        
        # 代理配置
        self.proxy_enabled_var = tk.BooleanVar()
        self.proxy_scheme_var = tk.StringVar()
        self.proxy_hostname_var = tk.StringVar()
        self.proxy_port_var = tk.IntVar()
        self.proxy_username_var = tk.StringVar()
        self.proxy_password_var = tk.StringVar()
        
        # 下载配置
        self.download_path_var = tk.StringVar()
        self.max_concurrent_downloads_var = tk.IntVar()
        self.max_clients_var = tk.IntVar()
        self.chunk_size_var = tk.IntVar()
        self.large_file_threshold_var = tk.IntVar()
        self.max_file_size_var = tk.IntVar()
        self.timeout_var = tk.IntVar()
        self.retry_count_var = tk.IntVar()
        self.retry_delay_var = tk.DoubleVar()
        self.skip_existing_var = tk.BooleanVar()
        
        # 日志配置
        self.log_level_var = tk.StringVar()
        self.log_file_var = tk.StringVar()
        self.log_dir_var = tk.StringVar()
        self.max_file_size_var = tk.IntVar()
        self.backup_count_var = tk.IntVar()
        self.console_output_var = tk.BooleanVar()
        self.json_format_var = tk.BooleanVar()
        
        # 运行时配置
        self.debug_var = tk.BooleanVar()
        self.dry_run_var = tk.BooleanVar()
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置窗口的权重
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 创建Notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建各个配置页面
        self.create_telegram_tab()
        self.create_proxy_tab()
        self.create_download_tab()
        self.create_logging_tab()
        self.create_runtime_tab()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 按钮
        ttk.Button(button_frame, text="保存", command=self.save_config).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="应用", command=self.apply_config).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="重置", command=self.reset_config).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="导入", command=self.import_config).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(button_frame, text="导出", command=self.export_config).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(button_frame, text="取消", command=self.cancel).grid(row=0, column=5, padx=(0, 0))
    
    def create_telegram_tab(self):
        """创建Telegram配置页面"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Telegram")
        
        # API配置
        api_frame = ttk.LabelFrame(frame, text="API配置", padding="10")
        api_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        api_frame.columnconfigure(1, weight=1)
        
        ttk.Label(api_frame, text="API ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(api_frame, textvariable=self.api_id_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        ttk.Label(api_frame, text="API Hash:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(api_frame, textvariable=self.api_hash_var, width=30, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        ttk.Label(api_frame, text="电话号码:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(api_frame, textvariable=self.phone_number_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        # 会话配置
        session_frame = ttk.LabelFrame(frame, text="会话配置", padding="10")
        session_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        session_frame.columnconfigure(1, weight=1)
        
        ttk.Label(session_frame, text="会话字符串:").grid(row=0, column=0, sticky=tk.W, pady=2)
        session_entry = tk.Text(session_frame, height=3, width=50)
        session_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        # 绑定会话字符串变量
        def update_session_string(*args):
            self.session_string_var.set(session_entry.get("1.0", tk.END).strip())
        
        session_entry.bind("<KeyRelease>", update_session_string)
        session_entry.bind("<FocusOut>", update_session_string)
        
        # 存储session_entry引用
        self.session_entry = session_entry
    
    def create_proxy_tab(self):
        """创建代理配置页面"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="代理")
        
        # 代理启用
        ttk.Checkbutton(frame, text="启用代理", variable=self.proxy_enabled_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # 代理服务器配置
        proxy_frame = ttk.LabelFrame(frame, text="代理服务器", padding="10")
        proxy_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        proxy_frame.columnconfigure(1, weight=1)
        
        ttk.Label(proxy_frame, text="协议:").grid(row=0, column=0, sticky=tk.W, pady=2)
        proxy_scheme_combo = ttk.Combobox(proxy_frame, textvariable=self.proxy_scheme_var, values=["socks5", "socks4", "http"], width=10)
        proxy_scheme_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(proxy_frame, text="主机:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(proxy_frame, textvariable=self.proxy_hostname_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        ttk.Label(proxy_frame, text="端口:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(proxy_frame, from_=1, to=65535, textvariable=self.proxy_port_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 代理认证
        auth_frame = ttk.LabelFrame(frame, text="代理认证 (可选)", padding="10")
        auth_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        auth_frame.columnconfigure(1, weight=1)
        
        ttk.Label(auth_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(auth_frame, textvariable=self.proxy_username_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        ttk.Label(auth_frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(auth_frame, textvariable=self.proxy_password_var, width=30, show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
        
        # 代理测试按钮
        ttk.Button(frame, text="测试代理连接", command=self.test_proxy).grid(row=3, column=0, sticky=tk.W, pady=5)
    
    def create_download_tab(self):
        """创建下载配置页面"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="下载")
        
        # 下载路径
        path_frame = ttk.LabelFrame(frame, text="下载路径", padding="10")
        path_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="下载目录:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(path_frame, textvariable=self.download_path_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(path_frame, text="浏览", command=self.browse_download_path).grid(row=0, column=2, pady=2)
        
        # 并发配置
        concurrent_frame = ttk.LabelFrame(frame, text="并发配置", padding="10")
        concurrent_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        concurrent_frame.columnconfigure(1, weight=1)
        
        ttk.Label(concurrent_frame, text="最大并发下载:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(concurrent_frame, from_=1, to=20, textvariable=self.max_concurrent_downloads_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(concurrent_frame, text="最大客户端数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(concurrent_frame, from_=1, to=10, textvariable=self.max_clients_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 文件配置
        file_frame = ttk.LabelFrame(frame, text="文件配置", padding="10")
        file_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="分片大小(MB):").grid(row=0, column=0, sticky=tk.W, pady=2)
        chunk_size_spin = ttk.Spinbox(file_frame, from_=1, to=100, textvariable=self.chunk_size_var, width=10)
        chunk_size_spin.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(file_frame, text="大文件阈值(MB):").grid(row=1, column=0, sticky=tk.W, pady=2)
        large_file_spin = ttk.Spinbox(file_frame, from_=10, to=1000, textvariable=self.large_file_threshold_var, width=10)
        large_file_spin.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(file_frame, text="最大文件大小(MB):").grid(row=2, column=0, sticky=tk.W, pady=2)
        max_file_spin = ttk.Spinbox(file_frame, from_=100, to=10000, textvariable=self.max_file_size_var, width=10)
        max_file_spin.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 其他配置
        other_frame = ttk.LabelFrame(frame, text="其他配置", padding="10")
        other_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        other_frame.columnconfigure(1, weight=1)
        
        ttk.Label(other_frame, text="超时时间(秒):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(other_frame, from_=30, to=3600, textvariable=self.timeout_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(other_frame, text="重试次数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(other_frame, from_=0, to=10, textvariable=self.retry_count_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(other_frame, text="重试延迟(秒):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(other_frame, from_=0.1, to=60.0, increment=0.1, textvariable=self.retry_delay_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Checkbutton(other_frame, text="跳过已存在文件", variable=self.skip_existing_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 绑定分片大小变量转换
        def update_chunk_size(*args):
            self.chunk_size_var.set(int(chunk_size_spin.get()) * 1024 * 1024)
        
        def update_large_file_threshold(*args):
            self.large_file_threshold_var.set(int(large_file_spin.get()) * 1024 * 1024)
        
        def update_max_file_size(*args):
            self.max_file_size_var.set(int(max_file_spin.get()) * 1024 * 1024)
        
        chunk_size_spin.bind("<FocusOut>", update_chunk_size)
        large_file_spin.bind("<FocusOut>", update_large_file_threshold)
        max_file_spin.bind("<FocusOut>", update_max_file_size)
    
    def create_logging_tab(self):
        """创建日志配置页面"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="日志")
        
        # 日志级别
        level_frame = ttk.LabelFrame(frame, text="日志级别", padding="10")
        level_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        level_frame.columnconfigure(1, weight=1)
        
        ttk.Label(level_frame, text="日志级别:").grid(row=0, column=0, sticky=tk.W, pady=2)
        level_combo = ttk.Combobox(level_frame, textvariable=self.log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], width=15)
        level_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 日志文件
        file_frame = ttk.LabelFrame(frame, text="日志文件", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="日志文件:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.log_file_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.browse_log_file).grid(row=0, column=2, pady=2)
        
        ttk.Label(file_frame, text="日志目录:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.log_dir_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.browse_log_dir).grid(row=1, column=2, pady=2)
        
        # 日志轮转
        rotation_frame = ttk.LabelFrame(frame, text="日志轮转", padding="10")
        rotation_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        rotation_frame.columnconfigure(1, weight=1)
        
        ttk.Label(rotation_frame, text="最大文件大小(MB):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(rotation_frame, from_=1, to=100, textvariable=self.max_file_size_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        ttk.Label(rotation_frame, text="备份文件数:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(rotation_frame, from_=1, to=20, textvariable=self.backup_count_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 日志选项
        options_frame = ttk.LabelFrame(frame, text="日志选项", padding="10")
        options_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="控制台输出", variable=self.console_output_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(options_frame, text="JSON格式", variable=self.json_format_var).grid(row=1, column=0, sticky=tk.W, pady=2)
    
    def create_runtime_tab(self):
        """创建运行时配置页面"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="运行时")
        
        # 运行时选项
        runtime_frame = ttk.LabelFrame(frame, text="运行时选项", padding="10")
        runtime_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(runtime_frame, text="调试模式", variable=self.debug_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Checkbutton(runtime_frame, text="模拟运行", variable=self.dry_run_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # 配置文件操作
        config_frame = ttk.LabelFrame(frame, text="配置文件", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(0, weight=1)
        
        ttk.Button(config_frame, text="重置为默认配置", command=self.reset_to_default).grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        ttk.Button(config_frame, text="验证配置", command=self.validate_config).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        ttk.Button(config_frame, text="清空所有配置", command=self.clear_all_config).grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
    
    def setup_bindings(self):
        """设置事件绑定"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 键盘快捷键
        self.window.bind('<Control-s>', lambda e: self.save_config())
        self.window.bind('<Control-w>', lambda e: self.cancel())
        self.window.bind('<Escape>', lambda e: self.cancel())
        
        # 监听配置变化
        for var in [self.api_id_var, self.api_hash_var, self.phone_number_var, 
                   self.proxy_enabled_var, self.proxy_hostname_var, self.proxy_port_var,
                   self.download_path_var, self.max_concurrent_downloads_var]:
            var.trace('w', self.on_config_changed)
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_config(self):
        """加载配置到界面"""
        try:
            # Telegram配置
            self.api_id_var.set(str(self.config.telegram.api_id) if self.config.telegram.api_id else "")
            self.api_hash_var.set(self.config.telegram.api_hash or "")
            self.phone_number_var.set(self.config.telegram.phone_number or "")
            self.session_string_var.set(self.config.telegram.session_string or "")
            if hasattr(self, 'session_entry'):
                self.session_entry.delete("1.0", tk.END)
                self.session_entry.insert("1.0", self.config.telegram.session_string or "")
            
            self.max_concurrent_transmissions_var.set(self.config.telegram.max_concurrent_transmissions)
            self.sleep_threshold_var.set(self.config.telegram.sleep_threshold)
            self.no_updates_var.set(self.config.telegram.no_updates)
            
            # 代理配置
            self.proxy_enabled_var.set(self.config.proxy.enabled)
            self.proxy_scheme_var.set(self.config.proxy.scheme)
            self.proxy_hostname_var.set(self.config.proxy.hostname)
            self.proxy_port_var.set(self.config.proxy.port)
            self.proxy_username_var.set(self.config.proxy.username or "")
            self.proxy_password_var.set(self.config.proxy.password or "")
            
            # 下载配置
            self.download_path_var.set(self.config.download.download_path)
            self.max_concurrent_downloads_var.set(self.config.download.max_concurrent_downloads)
            self.max_clients_var.set(self.config.download.max_clients)
            self.chunk_size_var.set(self.config.download.chunk_size // (1024 * 1024))  # 转换为MB
            self.large_file_threshold_var.set(self.config.download.large_file_threshold // (1024 * 1024))  # 转换为MB
            self.max_file_size_var.set(self.config.download.max_file_size // (1024 * 1024))  # 转换为MB
            self.timeout_var.set(self.config.download.timeout)
            self.retry_count_var.set(self.config.download.retry_count)
            self.retry_delay_var.set(self.config.download.retry_delay)
            self.skip_existing_var.set(self.config.download.skip_existing)
            
            # 日志配置
            self.log_level_var.set(self.config.logging.level)
            self.log_file_var.set(self.config.logging.log_file or "")
            self.log_dir_var.set(self.config.logging.log_dir)
            self.max_file_size_var.set(self.config.logging.max_file_size // (1024 * 1024))  # 转换为MB
            self.backup_count_var.set(self.config.logging.backup_count)
            self.console_output_var.set(self.config.logging.console_output)
            self.json_format_var.set(self.config.logging.json_format)
            
            # 运行时配置
            self.debug_var.set(self.config.debug)
            self.dry_run_var.set(self.config.dry_run)
            
            self.is_modified = False
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            messagebox.showerror("错误", f"加载配置失败: {e}")
    
    def save_config_to_object(self):
        """保存界面配置到配置对象"""
        try:
            # Telegram配置
            api_id_str = self.api_id_var.get().strip()
            if api_id_str:
                try:
                    self.config.telegram.api_id = int(api_id_str)
                except ValueError:
                    messagebox.showerror("错误", "API ID必须是数字")
                    return False
            else:
                self.config.telegram.api_id = 0
                
            self.config.telegram.api_hash = self.api_hash_var.get().strip()
            self.config.telegram.phone_number = self.phone_number_var.get().strip() or None
            
            # 从Text widget获取会话字符串
            if hasattr(self, 'session_entry'):
                session_string = self.session_entry.get("1.0", tk.END).strip()
                self.config.telegram.session_string = session_string or None
            else:
                self.config.telegram.session_string = self.session_string_var.get().strip() or None
            
            self.config.telegram.max_concurrent_transmissions = self.max_concurrent_transmissions_var.get()
            self.config.telegram.sleep_threshold = self.sleep_threshold_var.get()
            self.config.telegram.no_updates = self.no_updates_var.get()
            
            # 代理配置
            self.config.proxy.enabled = self.proxy_enabled_var.get()
            self.config.proxy.scheme = self.proxy_scheme_var.get()
            self.config.proxy.hostname = self.proxy_hostname_var.get().strip()
            
            # 代理端口验证
            try:
                port = self.proxy_port_var.get()
                if port < 1 or port > 65535:
                    messagebox.showerror("错误", "代理端口必须在1-65535之间")
                    return False
                self.config.proxy.port = port
            except:
                messagebox.showerror("错误", "代理端口必须是有效数字")
                return False
                
            self.config.proxy.username = self.proxy_username_var.get().strip() or None
            self.config.proxy.password = self.proxy_password_var.get().strip() or None
            
            # 下载配置
            self.config.download.download_path = self.download_path_var.get().strip()
            self.config.download.max_concurrent_downloads = self.max_concurrent_downloads_var.get()
            self.config.download.max_clients = self.max_clients_var.get()
            self.config.download.chunk_size = self.chunk_size_var.get() * 1024 * 1024  # 转换为字节
            self.config.download.large_file_threshold = self.large_file_threshold_var.get() * 1024 * 1024  # 转换为字节
            self.config.download.max_file_size = self.max_file_size_var.get() * 1024 * 1024  # 转换为字节
            self.config.download.timeout = self.timeout_var.get()
            self.config.download.retry_count = self.retry_count_var.get()
            self.config.download.retry_delay = self.retry_delay_var.get()
            self.config.download.skip_existing = self.skip_existing_var.get()
            
            # 日志配置
            self.config.logging.level = self.log_level_var.get()
            self.config.logging.log_file = self.log_file_var.get().strip() or None
            self.config.logging.log_dir = self.log_dir_var.get().strip()
            self.config.logging.max_file_size = self.max_file_size_var.get() * 1024 * 1024  # 转换为字节
            self.config.logging.backup_count = self.backup_count_var.get()
            self.config.logging.console_output = self.console_output_var.get()
            self.config.logging.json_format = self.json_format_var.get()
            
            # 运行时配置
            self.config.debug = self.debug_var.get()
            self.config.dry_run = self.dry_run_var.get()
            
            self.is_modified = False
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False
    
    def save_config(self):
        """保存配置"""
        if not self.save_config_to_object():
            return
            
        try:
            # 验证配置
            self.config.validate()
            
            # 保存到文件
            from utils.config import get_config_manager
            config_manager = get_config_manager()
            config_manager.config = self.config
            config_manager.save_config()
            
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()
            
        except Exception as e:
            if "API ID不能为空" in str(e) or "API Hash不能为空" in str(e):
                result = messagebox.askyesno(
                    "配置不完整", 
                    f"配置验证失败: {e}\n\n是否仍要保存配置？\n（稍后可以继续完善配置）"
                )
                if result:
                    try:
                        # 强制保存，跳过验证
                        from utils.config import get_config_manager
                        config_manager = get_config_manager()
                        config_manager.config = self.config
                        config_manager.save_config()
                        messagebox.showinfo("成功", "配置已保存（请记得补充完整的API信息）")
                        self.window.destroy()
                    except Exception as save_e:
                        messagebox.showerror("错误", f"保存配置文件失败: {save_e}")
            else:
                messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def apply_config(self):
        """应用配置"""
        if not self.save_config_to_object():
            return
            
        try:
            # 验证配置
            self.config.validate()
            
            # 应用配置
            from utils.config import get_config_manager
            config_manager = get_config_manager()
            config_manager.config = self.config
            
            messagebox.showinfo("成功", "配置已应用")
            
        except Exception as e:
            if "API ID不能为空" in str(e) or "API Hash不能为空" in str(e):
                messagebox.showwarning("配置不完整", f"配置验证失败: {e}\n\n配置已临时应用，但可能无法正常使用")
            else:
                messagebox.showerror("错误", f"应用配置失败: {e}")
    
    def reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置所有配置吗？"):
            self.load_config()
    
    def import_config(self):
        """导入配置"""
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.config = Config.from_dict(config_data)
                self.load_config()
                messagebox.showinfo("成功", "配置文件已导入")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入配置文件失败: {e}")
    
    def export_config(self):
        """导出配置"""
        file_path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                self.save_config_to_object()
                self.config.save_to_file(file_path)
                messagebox.showinfo("成功", "配置文件已导出")
                
            except Exception as e:
                messagebox.showerror("错误", f"导出配置文件失败: {e}")
    
    def test_proxy(self):
        """测试代理连接"""
        if not self.save_config_to_object():
            return
            
        try:
            # 测试代理连接
            import asyncio
            from utils.proxy_manager import test_proxy_connection
            
            def test_proxy_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(test_proxy_connection(self.config.proxy))
                    loop.close()
                    return result
                except Exception as e:
                    return False, str(e)
            
            # 显示测试中对话框
            test_dialog = tk.Toplevel(self.window)
            test_dialog.title("测试代理")
            test_dialog.geometry("300x100")
            test_dialog.resizable(False, False)
            
            # 居中显示
            test_dialog.transient(self.window)
            test_dialog.grab_set()
            
            label = tk.Label(test_dialog, text="正在测试代理连接...", font=("Arial", 10))
            label.pack(pady=30)
            
            test_dialog.update()
            
            # 在新线程中测试
            import threading
            
            def run_test():
                try:
                    result = test_proxy_async()
                    test_dialog.destroy()
                    
                    if result:
                        messagebox.showinfo("测试成功", "代理连接测试成功！")
                    else:
                        messagebox.showerror("测试失败", "代理连接测试失败，请检查配置")
                except Exception as e:
                    test_dialog.destroy()
                    messagebox.showerror("测试失败", f"代理测试异常: {e}")
            
            thread = threading.Thread(target=run_test, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"代理测试失败: {e}")
    
    def browse_download_path(self):
        """浏览下载路径"""
        path = filedialog.askdirectory()
        if path:
            self.download_path_var.set(path)
    
    def browse_log_file(self):
        """浏览日志文件"""
        file_path = filedialog.asksaveasfilename(
            title="选择日志文件",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        if file_path:
            self.log_file_var.set(file_path)
    
    def browse_log_dir(self):
        """浏览日志目录"""
        path = filedialog.askdirectory()
        if path:
            self.log_dir_var.set(path)
    
    def reset_to_default(self):
        """重置为默认配置"""
        if messagebox.askyesno("确认", "确定要重置为默认配置吗？"):
            self.config = Config()
            self.load_config()
    
    def validate_config(self):
        """验证配置"""
        if not self.save_config_to_object():
            return
            
        try:
            self.config.validate()
            messagebox.showinfo("成功", "配置验证通过！")
        except Exception as e:
            messagebox.showerror("验证失败", f"配置验证失败: {e}")
    
    def clear_all_config(self):
        """清空所有配置"""
        if messagebox.askyesno("确认", "确定要清空所有配置吗？"):
            # 清空所有变量
            for var in [self.api_id_var, self.api_hash_var, self.phone_number_var,
                       self.proxy_hostname_var, self.proxy_username_var, self.proxy_password_var,
                       self.download_path_var, self.log_file_var, self.log_dir_var]:
                var.set("")
            
            # 重置会话文本
            if hasattr(self, 'session_entry'):
                self.session_entry.delete("1.0", tk.END)
    
    def on_config_changed(self, *args):
        """配置变化事件"""
        self.is_modified = True
    
    def cancel(self):
        """取消"""
        if self.is_modified:
            if messagebox.askyesno("确认", "配置已修改，确定要取消吗？"):
                self.window.destroy()
        else:
            self.window.destroy()
    
    def on_closing(self):
        """窗口关闭事件"""
        self.cancel()
    
    def is_open(self) -> bool:
        """检查窗口是否打开"""
        try:
            return self.window.winfo_exists()
        except:
            return False
    
    def focus(self):
        """聚焦窗口"""
        self.window.focus_set()
        self.window.lift() 