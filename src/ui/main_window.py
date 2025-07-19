#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import customtkinter as ctk
import asyncio
import threading

from ..utils.config_manager import ConfigManager
from ..utils.logger import get_logger
from ..core.event_manager import event_manager
from ..models.events import BaseEvent, EventType
from .client_config_frame import ClientConfigFrame
from .download_frame import DownloadFrame
from .log_frame import LogFrame


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        self.logger = get_logger(__name__)
        
        # 配置管理器
        self.config_manager = ConfigManager()
        
        # 加载应用配置
        self.app_config = self.config_manager.load_app_config()

        # 初始化代理配置
        self._initialize_proxy_config()

        # 设置CustomTkinter主题
        ctk.set_appearance_mode(self.app_config["app"]["theme"])
        ctk.set_default_color_theme("blue")
        
        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title(self.app_config["app"]["name"])
        
        # 设置窗口大小和位置
        window_config = self.app_config["app"]["window_size"]
        width = window_config["width"]
        height = window_config["height"]
        
        # 计算居中位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 600)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap("assets/icon.ico")
        except:
            pass
        
        # 创建界面组件
        self.setup_ui()
        
        # 绑定事件
        self.setup_events()
        
        # 异步事件循环
        self.loop = None
        self.loop_thread = None
        
        self.logger.info("主窗口初始化完成")
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建标题栏
        self.create_title_bar()
        
        # 创建选项卡
        self.create_tabs()
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_title_bar(self):
        """创建标题栏"""
        title_frame = ctk.CTkFrame(self.main_frame)
        title_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 应用标题
        title_label = ctk.CTkLabel(
            title_frame,
            text=self.app_config["app"]["name"],
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left", padx=10, pady=10)
        
        # 版本信息
        version_label = ctk.CTkLabel(
            title_frame,
            text=f"v{self.app_config['app']['version']}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        version_label.pack(side="left", padx=(0, 10), pady=10)
        
        # 主题切换按钮
        self.theme_button = ctk.CTkButton(
            title_frame,
            text="🌙",
            width=40,
            height=30,
            command=self.toggle_theme
        )
        self.theme_button.pack(side="right", padx=10, pady=10)
        
        # 设置按钮
        settings_button = ctk.CTkButton(
            title_frame,
            text="⚙️",
            width=40,
            height=30,
            command=self.open_settings
        )
        settings_button.pack(side="right", padx=(0, 5), pady=10)
    
    def create_tabs(self):
        """创建选项卡"""
        # 创建选项卡视图
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 客户端配置选项卡
        self.client_tab = self.tabview.add("客户端配置")
        self.client_config_frame = ClientConfigFrame(
            self.client_tab,
            self.config_manager,
            event_manager
        )
        
        # 消息下载选项卡
        self.download_tab = self.tabview.add("消息下载")
        self.download_frame = DownloadFrame(
            self.download_tab,
            self.config_manager,
            event_manager
        )

        # 设置下载框架的父窗口引用，以便获取客户端管理器
        self.download_frame.main_window = self
        
        # 日志查看选项卡
        self.log_tab = self.tabview.add("日志查看")
        self.log_frame = LogFrame(
            self.log_tab,
            event_manager
        )
        
        # 设置默认选项卡
        self.tabview.set("客户端配置")
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_frame = ctk.CTkFrame(self.main_frame)
        self.status_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="就绪",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # 连接状态指示器
        self.connection_indicator = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.connection_indicator.pack(side="right", padx=10, pady=5)
        
        # 连接状态文本
        self.connection_label = ctk.CTkLabel(
            self.status_frame,
            text="未连接",
            font=ctk.CTkFont(size=12)
        )
        self.connection_label.pack(side="right", padx=(0, 5), pady=5)
    
    def setup_events(self):
        """设置事件处理"""
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 订阅事件管理器的事件
        event_manager.subscribe_all(self.on_event_received)
        
        # 定时更新状态
        self.update_status()
    
    def on_event_received(self, event: BaseEvent):
        """处理接收到的事件"""
        try:
            # 在主线程中更新UI
            self.root.after(0, self._update_ui_from_event, event)
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")
    
    def _update_ui_from_event(self, event: BaseEvent):
        """从事件更新UI（在主线程中执行）"""
        try:
            # 更新状态栏
            if event.event_type in [EventType.CLIENT_LOGIN_SUCCESS, EventType.CLIENT_DISCONNECTED]:
                self.update_connection_status()
            
            # 更新状态消息
            if event.severity.value in ["error", "critical"]:
                self.update_status(f"错误: {event.message}", "red")
            elif event.event_type == EventType.DOWNLOAD_STARTED:
                self.update_status("开始下载...", "blue")
            elif event.event_type == EventType.DOWNLOAD_COMPLETED:
                self.update_status("下载完成", "green")
            elif event.event_type == EventType.CLIENT_LOGIN_SUCCESS:
                self.update_status("客户端登录成功", "green")
                
        except Exception as e:
            self.logger.error(f"更新UI失败: {e}")
    
    def update_status(self, message: str = "就绪", color: str = "white"):
        """更新状态栏消息"""
        try:
            self.status_label.configure(text=message, text_color=color)
            
            # 5秒后恢复默认状态
            if message != "就绪":
                self.root.after(5000, lambda: self.update_status())
        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")
    
    def update_connection_status(self):
        """更新连接状态"""
        try:
            # 获取客户端连接状态
            if hasattr(self.client_config_frame, 'client_manager') and self.client_config_frame.client_manager:
                enabled_clients = self.client_config_frame.client_manager.get_enabled_clients()
                if enabled_clients:
                    self.connection_indicator.configure(text_color="green")
                    self.connection_label.configure(text=f"已连接 ({len(enabled_clients)})")
                else:
                    self.connection_indicator.configure(text_color="red")
                    self.connection_label.configure(text="未连接")
            else:
                self.connection_indicator.configure(text_color="gray")
                self.connection_label.configure(text="未配置")
        except Exception as e:
            self.logger.error(f"更新连接状态失败: {e}")
    
    def toggle_theme(self):
        """切换主题"""
        try:
            current_theme = ctk.get_appearance_mode()
            new_theme = "light" if current_theme == "Dark" else "dark"
            
            ctk.set_appearance_mode(new_theme)
            
            # 更新配置
            self.app_config["app"]["theme"] = new_theme
            self.config_manager.save_app_config(self.app_config)
            
            # 更新按钮图标
            self.theme_button.configure(text="☀️" if new_theme == "dark" else "🌙")
            
            self.logger.info(f"主题切换为: {new_theme}")
            
        except Exception as e:
            self.logger.error(f"切换主题失败: {e}")
    
    def open_settings(self):
        """打开设置窗口"""
        try:
            from .settings_window import SettingsWindow
            settings_window = SettingsWindow(self.root, self.config_manager)
            settings_window.show()
        except Exception as e:
            self.logger.error(f"打开设置窗口失败: {e}")
    
    def start_async_loop(self):
        """启动异步事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        self.logger.info("异步事件循环已启动")

    def _initialize_proxy_config(self):
        """初始化代理配置"""
        try:
            from ..utils.proxy_utils import update_proxy_config
            proxy_config = self.app_config.get("proxy", {})
            update_proxy_config(proxy_config)

            if proxy_config.get("enabled", False):
                self.logger.info(f"代理已启用: {proxy_config.get('host')}:{proxy_config.get('port')}")
            else:
                self.logger.debug("代理未启用")

        except Exception as e:
            self.logger.error(f"初始化代理配置失败: {e}")

    def stop_async_loop(self):
        """停止异步事件循环"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.logger.info("异步事件循环已停止")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            self.logger.info("正在关闭应用...")
            
            # 停止事件管理器
            event_manager.stop_processing()
            
            # 停止异步循环
            self.stop_async_loop()
            
            # 保存配置
            self.config_manager.save_app_config(self.app_config)
            
            # 关闭窗口
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"关闭应用时发生错误: {e}")
            self.root.destroy()
    
    def run(self):
        """运行应用"""
        try:
            # 启动异步事件循环
            self.start_async_loop()
            
            # 启动主循环
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"运行应用失败: {e}")
        finally:
            # 确保清理资源
            self.stop_async_loop()
            event_manager.stop_processing()
