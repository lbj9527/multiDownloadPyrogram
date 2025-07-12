#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主窗口GUI界面

提供下载管理、频道输入、进度显示等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import queue
import time
import json # Added missing import for json

# 修改为绝对导入
from utils.config import Config, get_config
from utils.logger import get_logger
from utils.proxy_manager import ProxyManager
from client.client_factory import ClientFactory
from task.task_manager import TaskManager
from main import MultiDownloadPyrogram  # 添加主应用类导入

# GUI相关导入
from .config_window import ConfigWindow
from .proxy_window import ProxyWindow
from .log_window import LogWindow
from .progress_window import ProgressWindow


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        self.logger = get_logger(f"{__name__}.MainWindow")
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("MultiDownloadPyrogram - Telegram下载工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 设置图标（如果有的话）
        try:
            # self.root.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # 应用程序实例
        self.app: Optional[MultiDownloadPyrogram] = None
        self.config: Optional[Config] = None
        self.is_running = False
        
        # 子窗口
        self.config_window: Optional[ConfigWindow] = None
        self.proxy_window: Optional[ProxyWindow] = None
        self.log_window: Optional[LogWindow] = None
        self.progress_window: Optional[ProgressWindow] = None
        
        # 异步事件循环
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats_data = {
            "total_files": 0,
            "downloaded_files": 0,
            "failed_files": 0,
            "total_size": 0,
            "downloaded_size": 0,
            "download_speed": 0.0,
            "active_tasks": 0
        }
        
        # 创建GUI
        self.create_widgets()
        self.setup_menu()
        self.setup_bindings()
        
        # 加载配置
        self.load_config()
        
        # 启动统计更新
        self.update_stats()
        
        self.logger.info("主窗口初始化完成")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架的权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 频道输入区域
        self.create_channel_frame(main_frame)
        
        # 下载选项区域
        self.create_options_frame(main_frame)
        
        # 控制按钮区域
        self.create_control_frame(main_frame)
        
        # 统计信息区域
        self.create_stats_frame(main_frame)
        
        # 任务列表区域
        self.create_tasks_frame(main_frame)
        
        # 状态栏
        self.create_status_bar()
    
    def create_channel_frame(self, parent):
        """创建频道输入区域"""
        # 频道输入框架
        channel_frame = ttk.LabelFrame(parent, text="频道/群组设置", padding="10")
        channel_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        channel_frame.columnconfigure(1, weight=1)
        
        # 频道用户名输入
        ttk.Label(channel_frame, text="频道用户名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.channel_var = tk.StringVar()
        channel_entry = ttk.Entry(channel_frame, textvariable=self.channel_var, width=50)
        channel_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # 浏览按钮
        ttk.Button(channel_frame, text="浏览", command=self.browse_channel).grid(row=0, column=2, padx=(5, 0))
        
        # 消息范围设置
        range_frame = ttk.Frame(channel_frame)
        range_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        range_frame.columnconfigure(1, weight=1)
        range_frame.columnconfigure(3, weight=1)
        
        ttk.Label(range_frame, text="消息范围:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        ttk.Label(range_frame, text="开始ID:").grid(row=0, column=1, sticky=tk.W, padx=(10, 5))
        self.start_id_var = tk.StringVar()
        ttk.Entry(range_frame, textvariable=self.start_id_var, width=10).grid(row=0, column=2, padx=(0, 10))
        
        ttk.Label(range_frame, text="结束ID:").grid(row=0, column=3, sticky=tk.W, padx=(10, 5))
        self.end_id_var = tk.StringVar()
        ttk.Entry(range_frame, textvariable=self.end_id_var, width=10).grid(row=0, column=4, padx=(0, 10))
        
        ttk.Label(range_frame, text="限制数量:").grid(row=0, column=5, sticky=tk.W, padx=(10, 5))
        self.limit_var = tk.StringVar()
        ttk.Entry(range_frame, textvariable=self.limit_var, width=10).grid(row=0, column=6, padx=(0, 0))
    
    def create_options_frame(self, parent):
        """创建下载选项区域"""
        options_frame = ttk.LabelFrame(parent, text="下载选项", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure(1, weight=1)
        
        # 下载路径
        ttk.Label(options_frame, text="下载路径:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.download_path_var = tk.StringVar()
        path_entry = ttk.Entry(options_frame, textvariable=self.download_path_var, width=50)
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(options_frame, text="浏览", command=self.browse_download_path).grid(row=0, column=2, padx=(5, 0))
        
        # 选项复选框
        options_row = ttk.Frame(options_frame)
        options_row.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.skip_existing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="跳过已存在文件", variable=self.skip_existing_var).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.download_media_group_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="下载媒体组", variable=self.download_media_group_var).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        self.use_proxy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text="使用代理", variable=self.use_proxy_var).grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_row, text="模拟运行", variable=self.dry_run_var).grid(row=0, column=3, sticky=tk.W)
    
    def create_control_frame(self, parent):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 主要控制按钮
        self.start_button = ttk.Button(control_frame, text="开始下载", command=self.start_download)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="停止下载", command=self.stop_download, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.pause_button = ttk.Button(control_frame, text="暂停", command=self.pause_download, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=2, padx=(0, 10))
        
        self.clear_button = ttk.Button(control_frame, text="清空列表", command=self.clear_tasks)
        self.clear_button.grid(row=0, column=3, padx=(0, 20))
        
        # 窗口按钮
        ttk.Button(control_frame, text="代理设置", command=self.open_proxy_window).grid(row=0, column=4, padx=(0, 10))
        ttk.Button(control_frame, text="日志窗口", command=self.open_log_window).grid(row=0, column=5, padx=(0, 10))
        ttk.Button(control_frame, text="进度窗口", command=self.open_progress_window).grid(row=0, column=6, padx=(0, 10))
    
    def create_stats_frame(self, parent):
        """创建统计信息区域"""
        stats_frame = ttk.LabelFrame(parent, text="统计信息", padding="10")
        stats_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建统计标签
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 文件统计
        ttk.Label(stats_grid, text="总文件数:").grid(row=0, column=0, sticky=tk.W)
        self.total_files_label = ttk.Label(stats_grid, text="0")
        self.total_files_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_grid, text="已下载:").grid(row=0, column=2, sticky=tk.W)
        self.downloaded_files_label = ttk.Label(stats_grid, text="0")
        self.downloaded_files_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(stats_grid, text="失败:").grid(row=0, column=4, sticky=tk.W)
        self.failed_files_label = ttk.Label(stats_grid, text="0")
        self.failed_files_label.grid(row=0, column=5, sticky=tk.W, padx=(5, 20))
        
        # 大小统计
        ttk.Label(stats_grid, text="总大小:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.total_size_label = ttk.Label(stats_grid, text="0 MB")
        self.total_size_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text="已下载:").grid(row=1, column=2, sticky=tk.W, pady=(5, 0))
        self.downloaded_size_label = ttk.Label(stats_grid, text="0 MB")
        self.downloaded_size_label.grid(row=1, column=3, sticky=tk.W, padx=(5, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text="下载速度:").grid(row=1, column=4, sticky=tk.W, pady=(5, 0))
        self.speed_label = ttk.Label(stats_grid, text="0 MB/s")
        self.speed_label.grid(row=1, column=5, sticky=tk.W, padx=(5, 20), pady=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(stats_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 进度文本
        self.progress_label = ttk.Label(stats_frame, text="0%")
        self.progress_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
    
    def create_tasks_frame(self, parent):
        """创建任务列表区域"""
        tasks_frame = ttk.LabelFrame(parent, text="下载任务", padding="10")
        tasks_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        tasks_frame.columnconfigure(0, weight=1)
        tasks_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ("ID", "文件名", "大小", "状态", "进度", "速度")
        self.tasks_tree = ttk.Treeview(tasks_frame, columns=columns, show="headings", height=12)
        
        # 设置列头
        self.tasks_tree.heading("ID", text="ID")
        self.tasks_tree.heading("文件名", text="文件名")
        self.tasks_tree.heading("大小", text="大小")
        self.tasks_tree.heading("状态", text="状态")
        self.tasks_tree.heading("进度", text="进度")
        self.tasks_tree.heading("速度", text="速度")
        
        # 设置列宽
        self.tasks_tree.column("ID", width=60, minwidth=60)
        self.tasks_tree.column("文件名", width=300, minwidth=200)
        self.tasks_tree.column("大小", width=80, minwidth=80)
        self.tasks_tree.column("状态", width=80, minwidth=80)
        self.tasks_tree.column("进度", width=80, minwidth=80)
        self.tasks_tree.column("速度", width=80, minwidth=80)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(tasks_frame, orient=tk.VERTICAL, command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tasks_frame, orient=tk.HORIZONTAL, command=self.tasks_tree.xview)
        self.tasks_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.tasks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="重新下载", command=self.retry_task)
        self.context_menu.add_command(label="暂停任务", command=self.pause_task)
        self.context_menu.add_command(label="取消任务", command=self.cancel_task)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除任务", command=self.delete_task)
        self.context_menu.add_command(label="打开文件位置", command=self.open_file_location)
        
        # 绑定右键菜单
        self.tasks_tree.bind("<Button-3>", self.show_context_menu)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 状态文本
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.status_label = ttk.Label(self.status_bar, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=(10, 0))
        
        # 配置状态
        self.config_status_var = tk.StringVar()
        self.config_status_var.set("未配置")
        self.config_status_label = ttk.Label(self.status_bar, textvariable=self.config_status_var)
        self.config_status_label.grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建配置", command=self.new_config)
        file_menu.add_command(label="打开配置", command=self.open_config)
        file_menu.add_command(label="保存配置", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="配置设置", command=self.open_config_window)
        tools_menu.add_command(label="代理管理", command=self.open_proxy_window)
        tools_menu.add_command(label="日志窗口", command=self.open_log_window)
        tools_menu.add_command(label="进度窗口", command=self.open_progress_window)
        tools_menu.add_separator()
        tools_menu.add_command(label="检查客户端状态", command=self.check_client_status)
        tools_menu.add_command(label="重试客户端", command=self.retry_clients)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def setup_bindings(self):
        """设置事件绑定"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 键盘快捷键
        self.root.bind('<Control-o>', lambda e: self.open_config())
        self.root.bind('<Control-s>', lambda e: self.save_config())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<F5>', lambda e: self.refresh_tasks())
    
    def load_config(self):
        """加载配置"""
        try:
            self.config = get_config()
            
            # 更新GUI
            self.download_path_var.set(self.config.download.download_path)
            self.skip_existing_var.set(self.config.download.skip_existing)
            self.use_proxy_var.set(self.config.proxy.enabled)
            
            # 检查Telegram配置是否完整
            from utils.config import get_config_manager
            config_manager = get_config_manager()
            if config_manager.is_telegram_configured():
                self.config_status_var.set("配置完整")
                self.status_var.set("配置加载成功")
            else:
                self.config_status_var.set("需要配置API")
                self.status_var.set("请先配置Telegram API信息")
                
                # 提示用户配置API信息
                messagebox.showinfo(
                    "配置提示", 
                    "检测到这是首次使用，请先配置Telegram API信息：\n\n"
                    "1. 点击菜单栏的 '设置' -> '配置设置'\n"
                    "2. 在Telegram标签页中填入API ID和API Hash\n"
                    "3. 填入电话号码或会话字符串\n\n"
                    "获取API信息：https://my.telegram.org/auth"
                )
            
            self.logger.info("配置加载完成")
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            # 使用默认配置
            from utils.config import Config
            self.config = Config()
            self.config_status_var.set("配置错误")
            self.status_var.set("使用默认配置")
            
            # 设置默认值
            self.download_path_var.set("downloads")
            self.skip_existing_var.set(True)
            self.use_proxy_var.set(False)
    
    def save_config(self):
        """保存配置"""
        if not self.config:
            messagebox.showerror("错误", "没有配置可保存")
            return
        
        try:
            # 更新配置
            self.config.download.download_path = self.download_path_var.get()
            self.config.download.skip_existing = self.skip_existing_var.get()
            self.config.proxy.enabled = self.use_proxy_var.get()
            
            # 保存到文件
            self.config.save_to_file("config.json")
            
            self.status_var.set("配置保存成功")
            messagebox.showinfo("成功", "配置已保存")
            
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
            messagebox.showerror("错误", f"配置保存失败: {e}")
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    def update_stats(self):
        """更新统计信息"""
        try:
            # 更新统计标签
            self.total_files_label.config(text=str(self.stats_data["total_files"]))
            self.downloaded_files_label.config(text=str(self.stats_data["downloaded_files"]))
            self.failed_files_label.config(text=str(self.stats_data["failed_files"]))
            
            self.total_size_label.config(text=self.format_size(self.stats_data["total_size"]))
            self.downloaded_size_label.config(text=self.format_size(self.stats_data["downloaded_size"]))
            self.speed_label.config(text=f"{self.stats_data['download_speed']:.1f} MB/s")
            
            # 更新进度条
            if self.stats_data["total_files"] > 0:
                progress = (self.stats_data["downloaded_files"] / self.stats_data["total_files"]) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{progress:.1f}%")
            else:
                self.progress_var.set(0)
                self.progress_label.config(text="0%")
            
            # 每隔1秒更新一次
            self.root.after(1000, self.update_stats)
            
        except Exception as e:
            self.logger.error(f"更新统计信息失败: {e}")
            self.root.after(1000, self.update_stats)
    
    # 事件处理方法
    def browse_channel(self):
        """浏览频道"""
        # 这里可以实现频道选择功能
        pass
    
    def browse_download_path(self):
        """浏览下载路径"""
        path = filedialog.askdirectory()
        if path:
            self.download_path_var.set(path)
    
    def start_download(self):
        """开始下载"""
        channel = self.channel_var.get().strip()
        if not channel:
            messagebox.showerror("错误", "请输入频道用户名")
            return
        
        # 检查配置是否完整
        try:
            from utils.config import get_config_manager
            config_manager = get_config_manager()
            
            if not config_manager.is_telegram_configured():
                messagebox.showerror(
                    "配置不完整", 
                    "Telegram配置不完整，请先配置API信息：\n\n"
                    "1. 点击菜单栏的 '设置' -> '配置设置'\n"
                    "2. 在Telegram标签页中填入API ID和API Hash\n"
                    "3. 填入电话号码或会话字符串\n\n"
                    "配置完成后再开始下载。"
                )
                return
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            messagebox.showerror("错误", f"配置验证失败: {e}")
            return
        
        try:
            # 更新配置
            self.config.download.download_path = self.download_path_var.get()
            self.config.download.skip_existing = self.skip_existing_var.get()
            self.config.proxy.enabled = self.use_proxy_var.get()
            
            # 启动下载任务
            self.start_download_task(channel)
            
            # 更新按钮状态
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.NORMAL)
            
            self.is_running = True
            self.status_var.set("下载中...")
            
        except Exception as e:
            self.logger.error(f"启动下载失败: {e}")
            messagebox.showerror("错误", f"启动下载失败: {e}")
    
    def stop_download(self):
        """停止下载"""
        try:
            if self.app:
                # 停止下载任务
                self.stop_download_task()
            
            # 更新按钮状态
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.DISABLED)
            
            self.is_running = False
            self.status_var.set("已停止")
            
        except Exception as e:
            self.logger.error(f"停止下载失败: {e}")
            messagebox.showerror("错误", f"停止下载失败: {e}")
    
    def pause_download(self):
        """暂停下载"""
        # 这里可以实现暂停功能
        pass
    
    def clear_tasks(self):
        """清空任务列表"""
        if messagebox.askyesno("确认", "确定要清空任务列表吗？"):
            for item in self.tasks_tree.get_children():
                self.tasks_tree.delete(item)
    
    def start_download_task(self, channel: str):
        """启动下载任务"""
        def run_download():
            exception_obj = None
            try:
                # 创建事件循环
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # 创建应用实例
                self.app = MultiDownloadPyrogram()
                
                # 运行下载任务
                self.loop.run_until_complete(self.run_download_async(channel))
                
            except Exception as e:
                exception_obj = e
                self.logger.error(f"下载任务异常: {e}")
            finally:
                if self.loop:
                    self.loop.close()
                
                # 在主线程中显示错误
                if exception_obj:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"下载失败: {exception_obj}"))
        
        # 在新线程中运行
        self.thread = threading.Thread(target=run_download, daemon=True)
        self.thread.start()
    
    async def run_download_async(self, channel: str):
        """异步运行下载"""
        try:
            # 初始化应用
            await self.app.initialize()
            await self.app.start()
            
            # 检查客户端状态
            pool_info = self.app.task_manager.client_pool.get_pool_info()
            available_clients = pool_info["available_clients"]
            total_clients = pool_info["total_clients"]
            
            if available_clients == 0:
                error_msg = f"没有可用的客户端 ({available_clients}/{total_clients})"
                if total_clients > 0:
                    error_msg += "\n\n可能的原因：\n1. 网络连接问题\n2. 代理配置错误\n3. API认证失败\n4. 客户端连接超时"
                raise RuntimeError(error_msg)
            
            # 获取参数
            limit = None
            start_id = None
            end_id = None
            
            if self.limit_var.get():
                limit = int(self.limit_var.get())
            if self.start_id_var.get():
                start_id = int(self.start_id_var.get())
            if self.end_id_var.get():
                end_id = int(self.end_id_var.get())
            
            # 开始下载
            task_ids = await self.app.download_channel_history(
                channel, limit=limit, 
                start_message_id=start_id, 
                end_message_id=end_id
            )
            
            self.logger.info(f"已添加 {len(task_ids)} 个下载任务")
            
        except Exception as e:
            self.logger.error(f"异步下载失败: {e}")
            raise
    
    def stop_download_task(self):
        """停止下载任务"""
        if self.app:
            asyncio.run_coroutine_threadsafe(self.app.stop(), self.loop)
    
    # 子窗口操作
    def open_config_window(self):
        """打开配置窗口"""
        if self.config_window is None or not self.config_window.is_open():
            self.config_window = ConfigWindow(self.root, self.config)
        else:
            self.config_window.focus()
    
    def open_proxy_window(self):
        """打开代理窗口"""
        if self.proxy_window is None or not self.proxy_window.is_open():
            self.proxy_window = ProxyWindow(self.root)
        else:
            self.proxy_window.focus()
    
    def open_log_window(self):
        """打开日志窗口"""
        if self.log_window is None or not self.log_window.is_open():
            self.log_window = LogWindow(self.root)
        else:
            self.log_window.focus()
    
    def open_progress_window(self):
        """打开进度窗口"""
        if self.progress_window is None or not self.progress_window.is_open():
            self.progress_window = ProgressWindow(self.root)
        else:
            self.progress_window.focus()
    
    # 菜单事件处理
    def new_config(self):
        """新建配置"""
        pass
    
    def open_config(self):
        """打开配置文件"""
        file_path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 重新加载配置
                self.load_config()
                messagebox.showinfo("成功", "配置文件已加载")
                
            except Exception as e:
                messagebox.showerror("错误", f"加载配置文件失败: {e}")
    
    def show_help(self):
        """显示帮助"""
        help_text = """
MultiDownloadPyrogram 使用说明

1. 基本使用:
   - 在"频道用户名"框中输入要下载的频道用户名 (如: @channel_name)
   - 设置下载路径和其他选项
   - 点击"开始下载"按钮

2. 高级功能:
   - 消息范围: 可以设置开始ID、结束ID和限制数量
   - 代理设置: 在工具菜单中配置代理
   - 日志窗口: 查看详细的下载日志
   - 进度窗口: 查看实时下载进度

3. 快捷键:
   - Ctrl+O: 打开配置文件
   - Ctrl+S: 保存配置
   - Ctrl+Q: 退出程序
   - F1: 显示帮助
   - F5: 刷新任务列表

4. 注意事项:
   - 首次使用需要配置API ID和API Hash
   - 建议使用代理以提高下载稳定性
   - 大文件会自动分片下载
        """
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
MultiDownloadPyrogram

版本: 1.0.0
基于Pyrogram框架开发的高性能Telegram媒体下载工具

特性:
- 多客户端并发下载
- 大文件分片下载
- 媒体组完整下载
- 代理支持
- 断点续传
- 现代化GUI界面

开发者: Your Name
项目地址: https://github.com/your-username/multiDownloadPyrogram
        """
        messagebox.showinfo("关于", about_text)
    
    def quit_app(self):
        """退出应用"""
        self.on_closing()
    
    # 右键菜单事件
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择点击的项目
        item = self.tasks_tree.identify_row(event.y)
        if item:
            self.tasks_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def retry_task(self):
        """重新下载任务"""
        pass
    
    def pause_task(self):
        """暂停任务"""
        pass
    
    def cancel_task(self):
        """取消任务"""
        pass
    
    def delete_task(self):
        """删除任务"""
        selected = self.tasks_tree.selection()
        if selected:
            for item in selected:
                self.tasks_tree.delete(item)
    
    def open_file_location(self):
        """打开文件位置"""
        pass
    
    def refresh_tasks(self):
        """刷新任务列表"""
        pass
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if messagebox.askyesno("确认", "正在下载中，确定要退出吗？"):
                self.stop_download()
                self.root.after(1000, self.root.destroy)
        else:
            self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

    def check_client_status(self):
        """检查客户端状态"""
        try:
            if not self.app:
                messagebox.showinfo("状态", "请先启动下载任务")
                return
            
            pool_info = self.app.task_manager.client_pool.get_pool_info()
            available_clients = pool_info["available_clients"]
            total_clients = pool_info["total_clients"]
            
            status_text = f"客户端池状态:\n"
            status_text += f"总客户端数: {total_clients}\n"
            status_text += f"可用客户端数: {available_clients}\n"
            status_text += f"可用率: {(available_clients/total_clients*100):.1f}%" if total_clients > 0 else "可用率: 0%"
            
            if available_clients == 0:
                status_text += "\n\n建议操作:\n"
                status_text += "1. 检查网络连接\n"
                status_text += "2. 验证代理设置\n"
                status_text += "3. 确认API配置正确\n"
                status_text += "4. 尝试重新启动程序"
                
                messagebox.showwarning("客户端状态", status_text)
            else:
                messagebox.showinfo("客户端状态", status_text)
                
        except Exception as e:
            self.logger.error(f"检查客户端状态失败: {e}")
            messagebox.showerror("错误", f"检查客户端状态失败: {e}")
    
    def retry_clients(self):
        """重试所有客户端"""
        try:
            if not self.app:
                messagebox.showinfo("状态", "请先启动下载任务")
                return
            
            # 重试所有可重试的客户端
            retry_count = 0
            for manager in self.app.task_manager.client_pool.client_managers:
                if manager.can_retry():
                    try:
                        # 在后台重试
                        asyncio.create_task(manager.reconnect())
                        retry_count += 1
                    except Exception as e:
                        self.logger.error(f"重试客户端失败: {manager.client_id}, {e}")
            
            if retry_count > 0:
                messagebox.showinfo("重试", f"正在重试 {retry_count} 个客户端...\n请稍后再次检查状态")
            else:
                messagebox.showinfo("重试", "没有需要重试的客户端")
                
        except Exception as e:
            self.logger.error(f"重试客户端失败: {e}")
            messagebox.showerror("错误", f"重试客户端失败: {e}")


def main():
    """主函数"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main() 