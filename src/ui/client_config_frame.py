#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端配置界面
"""

import tkinter as tk
import customtkinter as ctk
import asyncio
from typing import Optional, List

from ..models.client_config import ClientConfig, ClientStatus, MultiClientConfig, AccountType
from ..core.client_manager import ClientManager
from ..core.event_manager import EventManager
from ..models.events import BaseEvent, EventType
from ..utils.config_manager import ConfigManager
from ..utils.logger import get_logger


class ClientConfigFrame:
    """客户端配置框架"""
    
    def __init__(self, parent, config_manager: ConfigManager, event_manager: EventManager):
        """
        初始化客户端配置框架
        
        Args:
            parent: 父窗口
            config_manager: 配置管理器
            event_manager: 事件管理器
        """
        self.parent = parent
        self.config_manager = config_manager
        self.event_manager = event_manager
        self.logger = get_logger(__name__)
        
        # 客户端管理器
        self.client_manager: Optional[ClientManager] = None
        
        # 当前配置
        self.current_config: Optional[MultiClientConfig] = None
        
        # UI组件
        self.client_widgets = []
        
        # 创建界面
        self.setup_ui()
        
        # 加载配置
        self.load_config()
        
        # 订阅事件
        self.event_manager.subscribe(EventType.CLIENT_LOGIN_SUCCESS, self.on_client_event)
        self.event_manager.subscribe(EventType.CLIENT_LOGIN_FAILED, self.on_client_event)
        self.event_manager.subscribe(EventType.CLIENT_STATUS_CHANGED, self.on_client_event)
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建账户类型选择区域
        self.create_account_type_section()
        
        # 创建客户端配置区域
        self.create_client_config_section()
        
        # 创建操作按钮区域
        self.create_action_buttons()
    
    def create_account_type_section(self):
        """创建账户类型选择区域"""
        # 账户类型框架
        account_frame = ctk.CTkFrame(self.main_frame)
        account_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 标题
        title_label = ctk.CTkLabel(
            account_frame,
            text="账户类型选择",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # 说明文本
        info_label = ctk.CTkLabel(
            account_frame,
            text="普通账户支持3个客户端，Premium账户支持4个客户端",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(pady=(0, 10))
        
        # 账户类型选择
        self.account_type_var = ctk.StringVar(value=AccountType.NORMAL.value)
        
        account_type_frame = ctk.CTkFrame(account_frame)
        account_type_frame.pack(pady=(0, 10))
        
        normal_radio = ctk.CTkRadioButton(
            account_type_frame,
            text="普通账户 (3个客户端)",
            variable=self.account_type_var,
            value=AccountType.NORMAL.value,
            command=self.on_account_type_changed
        )
        normal_radio.pack(side="left", padx=20, pady=10)
        
        premium_radio = ctk.CTkRadioButton(
            account_type_frame,
            text="Premium账户 (4个客户端)",
            variable=self.account_type_var,
            value=AccountType.PREMIUM.value,
            command=self.on_account_type_changed
        )
        premium_radio.pack(side="left", padx=20, pady=10)
    
    def create_client_config_section(self):
        """创建客户端配置区域"""
        # 客户端配置框架
        self.client_config_frame = ctk.CTkFrame(self.main_frame)
        self.client_config_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 标题
        title_label = ctk.CTkLabel(
            self.client_config_frame,
            text="客户端配置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # 滚动框架
        self.scroll_frame = ctk.CTkScrollableFrame(self.client_config_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 初始化客户端配置UI
        self.update_client_config_ui()
    
    def create_action_buttons(self):
        """创建操作按钮区域"""
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # 保存配置按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存配置",
            command=self.save_config
        )
        save_button.pack(side="left", padx=10, pady=10)
        
        # 测试连接按钮
        test_button = ctk.CTkButton(
            button_frame,
            text="测试连接",
            command=self.test_connections
        )
        test_button.pack(side="left", padx=5, pady=10)
        
        # 全部登录按钮
        login_all_button = ctk.CTkButton(
            button_frame,
            text="全部登录",
            command=self.login_all_clients
        )
        login_all_button.pack(side="left", padx=5, pady=10)
        
        # 全部登出按钮
        logout_all_button = ctk.CTkButton(
            button_frame,
            text="全部登出",
            command=self.logout_all_clients
        )
        logout_all_button.pack(side="left", padx=5, pady=10)
        
        # 状态刷新按钮
        refresh_button = ctk.CTkButton(
            button_frame,
            text="刷新状态",
            command=self.refresh_status
        )
        refresh_button.pack(side="right", padx=10, pady=10)
    
    def on_account_type_changed(self):
        """账户类型改变事件"""
        self.update_client_config_ui()
    
    def update_client_config_ui(self):
        """更新客户端配置UI"""
        # 清除现有的客户端配置UI
        for widget in self.client_widgets:
            widget.destroy()
        self.client_widgets.clear()
        
        # 获取账户类型
        account_type = AccountType(self.account_type_var.get())
        max_clients = 3 if account_type == AccountType.NORMAL else 4
        
        # 创建客户端配置UI
        for i in range(max_clients):
            client_frame = self.create_client_widget(i + 1)
            self.client_widgets.append(client_frame)
    
    def create_client_widget(self, client_number: int) -> ctk.CTkFrame:
        """
        创建单个客户端配置组件
        
        Args:
            client_number: 客户端编号
            
        Returns:
            ctk.CTkFrame: 客户端配置框架
        """
        # 客户端框架
        client_frame = ctk.CTkFrame(self.scroll_frame)
        client_frame.pack(fill="x", padx=5, pady=5)
        
        # 标题和状态
        header_frame = ctk.CTkFrame(client_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"客户端 {client_number}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(side="left", padx=5, pady=5)
        
        # 状态指示器
        status_label = ctk.CTkLabel(
            header_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        status_label.pack(side="right", padx=5, pady=5)
        
        status_text = ctk.CTkLabel(
            header_frame,
            text="未配置",
            font=ctk.CTkFont(size=12)
        )
        status_text.pack(side="right", padx=(0, 5), pady=5)
        
        # 配置输入区域
        config_frame = ctk.CTkFrame(client_frame)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # API ID
        api_id_label = ctk.CTkLabel(config_frame, text="API ID:")
        api_id_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        api_id_entry = ctk.CTkEntry(config_frame, placeholder_text="输入API ID")
        api_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # API Hash
        api_hash_label = ctk.CTkLabel(config_frame, text="API Hash:")
        api_hash_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        api_hash_entry = ctk.CTkEntry(config_frame, placeholder_text="输入API Hash")
        api_hash_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # 电话号码
        phone_label = ctk.CTkLabel(config_frame, text="电话号码:")
        phone_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        phone_entry = ctk.CTkEntry(config_frame, placeholder_text="输入电话号码 (如+86138...)")
        phone_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # 会话名称
        session_label = ctk.CTkLabel(config_frame, text="会话名称:")
        session_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        session_entry = ctk.CTkEntry(config_frame, placeholder_text="输入会话名称")
        session_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        # 设置列权重
        config_frame.grid_columnconfigure(1, weight=1)
        
        # 操作按钮
        button_frame = ctk.CTkFrame(client_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # 启用/禁用开关
        enabled_var = ctk.BooleanVar(value=True)
        enabled_switch = ctk.CTkSwitch(
            button_frame,
            text="启用",
            variable=enabled_var
        )
        enabled_switch.pack(side="left", padx=5, pady=5)
        
        # 登录按钮
        login_button = ctk.CTkButton(
            button_frame,
            text="登录",
            width=80,
            command=lambda: self.login_client(client_number - 1)
        )
        login_button.pack(side="right", padx=5, pady=5)
        
        # 登出按钮
        logout_button = ctk.CTkButton(
            button_frame,
            text="登出",
            width=80,
            command=lambda: self.logout_client(client_number - 1)
        )
        logout_button.pack(side="right", padx=5, pady=5)
        
        # 保存组件引用
        client_frame.api_id_entry = api_id_entry
        client_frame.api_hash_entry = api_hash_entry
        client_frame.phone_entry = phone_entry
        client_frame.session_entry = session_entry
        client_frame.enabled_var = enabled_var
        client_frame.status_label = status_label
        client_frame.status_text = status_text
        client_frame.login_button = login_button
        client_frame.logout_button = logout_button
        client_frame.client_number = client_number
        
        return client_frame

    def load_config(self):
        """加载配置"""
        try:
            # 加载客户端配置
            self.current_config = self.config_manager.load_client_config()

            if self.current_config:
                # 设置账户类型
                self.account_type_var.set(self.current_config.account_type.value)

                # 更新UI
                self.update_client_config_ui()

                # 填充客户端配置
                for i, client_config in enumerate(self.current_config.clients):
                    if i < len(self.client_widgets):
                        widget = self.client_widgets[i]
                        widget.api_id_entry.insert(0, str(client_config.api_id))
                        widget.api_hash_entry.insert(0, client_config.api_hash)
                        widget.phone_entry.insert(0, client_config.phone_number)
                        widget.session_entry.insert(0, client_config.session_name)
                        widget.enabled_var.set(client_config.enabled)

                        # 更新状态
                        self.update_client_status(i, client_config.status)

                # 创建客户端管理器
                self.client_manager = ClientManager(self.current_config, self.on_client_manager_event)

                self.logger.info("客户端配置加载完成")
            else:
                # 创建默认配置
                self.current_config = MultiClientConfig(
                    account_type=AccountType.NORMAL,
                    clients=[]
                )

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            # 获取账户类型
            account_type = AccountType(self.account_type_var.get())

            # 收集客户端配置
            clients = []
            for widget in self.client_widgets:
                api_id_text = widget.api_id_entry.get().strip()
                api_hash_text = widget.api_hash_entry.get().strip()
                phone_text = widget.phone_entry.get().strip()
                session_text = widget.session_entry.get().strip()

                # 跳过空配置
                if not all([api_id_text, api_hash_text, phone_text, session_text]):
                    continue

                try:
                    client_config = ClientConfig(
                        api_id=int(api_id_text),
                        api_hash=api_hash_text,
                        phone_number=phone_text,
                        session_name=session_text,
                        enabled=widget.enabled_var.get()
                    )
                    clients.append(client_config)
                except Exception as e:
                    self.logger.error(f"客户端 {widget.client_number} 配置无效: {e}")
                    self.show_error(f"客户端 {widget.client_number} 配置无效: {e}")
                    return

            # 创建多客户端配置
            try:
                self.current_config = MultiClientConfig(
                    account_type=account_type,
                    clients=clients
                )

                # 保存配置
                if self.config_manager.save_client_config(self.current_config):
                    # 重新创建客户端管理器
                    if self.client_manager:
                        asyncio.create_task(self.client_manager.shutdown_all_clients())

                    self.client_manager = ClientManager(self.current_config, self.on_client_manager_event)

                    self.show_success("配置保存成功")
                    self.logger.info("客户端配置保存成功")
                else:
                    self.show_error("配置保存失败")

            except Exception as e:
                self.logger.error(f"配置验证失败: {e}")
                self.show_error(f"配置验证失败: {e}")

        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            self.show_error(f"保存配置失败: {e}")

    def login_client(self, client_index: int):
        """登录指定客户端"""
        if not self.client_manager or client_index >= len(self.current_config.clients):
            return

        client_config = self.current_config.clients[client_index]

        # 在异步线程中执行登录
        def login_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self.client_manager.login_client(client_config.session_name)
                )
                if success:
                    self.logger.info(f"客户端 {client_config.session_name} 登录成功")
                else:
                    self.logger.error(f"客户端 {client_config.session_name} 登录失败")
            except Exception as e:
                self.logger.error(f"客户端登录异常: {e}")
            finally:
                loop.close()

        import threading
        threading.Thread(target=login_async, daemon=True).start()

    def logout_client(self, client_index: int):
        """登出指定客户端"""
        if not self.client_manager or client_index >= len(self.current_config.clients):
            return

        client_config = self.current_config.clients[client_index]

        # 在异步线程中执行登出
        def logout_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self.client_manager.logout_client(client_config.session_name)
                )
                if success:
                    self.logger.info(f"客户端 {client_config.session_name} 登出成功")
                else:
                    self.logger.error(f"客户端 {client_config.session_name} 登出失败")
            except Exception as e:
                self.logger.error(f"客户端登出异常: {e}")
            finally:
                loop.close()

        import threading
        threading.Thread(target=logout_async, daemon=True).start()

    def login_all_clients(self):
        """登录所有客户端"""
        if not self.client_manager:
            self.show_error("请先保存配置")
            return

        for i in range(len(self.current_config.clients)):
            self.login_client(i)

    def logout_all_clients(self):
        """登出所有客户端"""
        if not self.client_manager:
            return

        def logout_all_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.client_manager.shutdown_all_clients())
                self.logger.info("所有客户端已登出")
            except Exception as e:
                self.logger.error(f"登出所有客户端异常: {e}")
            finally:
                loop.close()

        import threading
        threading.Thread(target=logout_all_async, daemon=True).start()

    def test_connections(self):
        """测试连接"""
        if not self.client_manager:
            self.show_error("请先保存配置")
            return

        def test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for client_config in self.current_config.clients:
                    if client_config.enabled:
                        success = loop.run_until_complete(
                            self.client_manager.check_client_connection(client_config.session_name)
                        )
                        status = "连接正常" if success else "连接失败"
                        self.logger.info(f"客户端 {client_config.session_name}: {status}")
            except Exception as e:
                self.logger.error(f"测试连接异常: {e}")
            finally:
                loop.close()

        import threading
        threading.Thread(target=test_async, daemon=True).start()

    def refresh_status(self):
        """刷新状态"""
        if not self.client_manager:
            return

        for i, client_config in enumerate(self.current_config.clients):
            status = self.client_manager.get_client_status(client_config.session_name)
            if status:
                self.update_client_status(i, status)

    def update_client_status(self, client_index: int, status: ClientStatus):
        """更新客户端状态显示"""
        if client_index >= len(self.client_widgets):
            return

        widget = self.client_widgets[client_index]

        # 状态颜色映射
        status_colors = {
            ClientStatus.NOT_LOGGED_IN: "gray",
            ClientStatus.LOGGING_IN: "yellow",
            ClientStatus.LOGGED_IN: "green",
            ClientStatus.LOGIN_FAILED: "red",
            ClientStatus.DISABLED: "gray",
            ClientStatus.ERROR: "red"
        }

        # 状态文本映射
        status_texts = {
            ClientStatus.NOT_LOGGED_IN: "未登录",
            ClientStatus.LOGGING_IN: "登录中",
            ClientStatus.LOGGED_IN: "已登录",
            ClientStatus.LOGIN_FAILED: "登录失败",
            ClientStatus.DISABLED: "已禁用",
            ClientStatus.ERROR: "错误"
        }

        color = status_colors.get(status, "gray")
        text = status_texts.get(status, "未知")

        widget.status_label.configure(text_color=color)
        widget.status_text.configure(text=text)

        # 更新按钮状态
        if status == ClientStatus.LOGGED_IN:
            widget.login_button.configure(state="disabled")
            widget.logout_button.configure(state="normal")
        else:
            widget.login_button.configure(state="normal")
            widget.logout_button.configure(state="disabled")

    def on_client_event(self, event: BaseEvent):
        """处理客户端事件"""
        try:
            # 在主线程中更新UI
            if self.parent:
                self.parent.after(0, self._update_ui_from_client_event, event)
            else:
                self.logger.warning("父窗口对象不存在，无法更新UI")
        except Exception as e:
            self.logger.error(f"处理客户端事件失败: {e}")

    def _update_ui_from_client_event(self, event: BaseEvent):
        """从客户端事件更新UI"""
        try:
            if hasattr(event, 'client_name'):
                # 查找对应的客户端
                for i, client_config in enumerate(self.current_config.clients):
                    if client_config.session_name == event.client_name:
                        if hasattr(event, 'client_status'):
                            status = ClientStatus(event.client_status)
                            self.update_client_status(i, status)
                        break
        except Exception as e:
            self.logger.error(f"更新客户端UI失败: {e}")

    def on_client_manager_event(self, event: BaseEvent):
        """客户端管理器事件回调"""
        # 转发到事件管理器
        self.event_manager.emit(event)

    def show_success(self, message: str):
        """显示成功消息"""
        # 这里可以实现一个简单的消息提示
        self.logger.info(message)

    def show_error(self, message: str):
        """显示错误消息"""
        # 这里可以实现一个简单的错误提示
        self.logger.error(message)
