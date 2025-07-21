#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户端配置界面
"""

import tkinter as tk
import customtkinter as ctk
import asyncio
from typing import Optional, List
from datetime import datetime

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
        self.client_status_widgets = {}  # 存储客户端状态组件的引用
        self.login_buttons = {}  # 存储登录按钮的引用
        self.logout_buttons = {}  # 存储登出按钮的引用
        
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

        # 配置状态显示区域
        self.status_frame = ctk.CTkFrame(self.client_config_frame)
        self.status_frame.pack(fill="x", padx=10, pady=5)

        # API设置按钮区域
        self.api_button_frame = ctk.CTkFrame(self.client_config_frame)
        self.api_button_frame.pack(fill="x", padx=10, pady=10)

        # 创建API设置按钮
        self.api_settings_button = ctk.CTkButton(
            self.api_button_frame,
            text="🔧 API 设置",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.open_api_settings
        )
        self.api_settings_button.pack(pady=15)

        # 初始化客户端状态显示
        self.update_client_status_display()
    
    def create_action_buttons(self):
        """创建操作按钮区域"""
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=5, pady=(5, 0))

        # 测试连接按钮
        self.test_button = ctk.CTkButton(
            button_frame,
            text="测试连接",
            command=self.test_connections
        )
        self.test_button.pack(side="left", padx=10, pady=10)
    
    def on_account_type_changed(self):
        """账户类型改变事件"""
        try:
            # 更新显示
            self.update_client_status_display()

            # 自动保存账户类型变更
            if self.current_config:
                account_type = AccountType(self.account_type_var.get())
                self.current_config.account_type = account_type

                # 保存配置
                if self.config_manager.save_client_config(self.current_config):
                    self.logger.info(f"账户类型已更新为: {account_type.value}")
                else:
                    self.logger.error("保存账户类型变更失败")
        except Exception as e:
            self.logger.error(f"账户类型变更处理失败: {e}")
    
    def update_client_status_display(self):
        """更新客户端状态显示"""
        # 清除现有的状态显示
        for widget in self.status_frame.winfo_children():
            widget.destroy()

        # 获取账户类型和最大客户端数
        account_type = AccountType(self.account_type_var.get())
        max_clients = 3 if account_type == AccountType.NORMAL else 4

        # 创建状态显示标题
        status_title = ctk.CTkLabel(
            self.status_frame,
            text="客户端状态",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        status_title.pack(pady=(10, 5))

        # 创建客户端状态网格
        status_grid_frame = ctk.CTkFrame(self.status_frame)
        status_grid_frame.pack(pady=(0, 10))

        # 清除旧的组件引用
        self.client_status_widgets.clear()
        self.login_buttons.clear()
        self.logout_buttons.clear()

        # 显示每个客户端的状态
        for i in range(max_clients):
            client_status_frame = ctk.CTkFrame(status_grid_frame)
            client_status_frame.grid(row=i // 2, column=i % 2, padx=10, pady=5, sticky="ew")

            # 获取客户端会话名称
            session_name = f"session_{i + 1}"
            if (self.current_config and
                i < len(self.current_config.clients)):
                session_name = self.current_config.clients[i].session_name

            # 客户端编号
            client_label = ctk.CTkLabel(
                client_status_frame,
                text=f"客户端 {i + 1}",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            client_label.pack(side="left", padx=10, pady=8)

            # 状态指示器和文本
            status_text, status_color = self.get_client_status_info(i)

            # 操作按钮区域
            button_frame = ctk.CTkFrame(client_status_frame)
            button_frame.pack(side="right", padx=5, pady=5)

            # 登录按钮
            login_button = ctk.CTkButton(
                button_frame,
                text="登录",
                width=50,
                height=25,
                font=ctk.CTkFont(size=10),
                command=lambda idx=i: self.login_client(idx)
            )
            login_button.pack(side="right", padx=2)
            self.login_buttons[session_name] = login_button

            # 登出按钮
            logout_button = ctk.CTkButton(
                button_frame,
                text="登出",
                width=50,
                height=25,
                font=ctk.CTkFont(size=10),
                command=lambda idx=i: self.logout_client(idx)
            )
            logout_button.pack(side="right", padx=2)
            self.logout_buttons[session_name] = logout_button

            status_indicator = ctk.CTkLabel(
                client_status_frame,
                text="●",
                font=ctk.CTkFont(size=14),
                text_color=status_color
            )
            status_indicator.pack(side="right", padx=(0, 5), pady=8)

            status_label = ctk.CTkLabel(
                client_status_frame,
                text=status_text,
                font=ctk.CTkFont(size=11)
            )
            status_label.pack(side="right", padx=(0, 5), pady=8)

            # 保存状态组件引用
            self.client_status_widgets[session_name] = {
                'status_indicator': status_indicator,
                'status_label': status_label,
                'client_index': i
            }

        # 更新按钮状态（实现顺序登录控制）
        self.update_login_button_states()

        # 设置网格列权重
        status_grid_frame.grid_columnconfigure(0, weight=1)
        status_grid_frame.grid_columnconfigure(1, weight=1)

    def get_client_status_info(self, client_index: int) -> tuple:
        """
        获取客户端状态信息

        Args:
            client_index: 客户端索引

        Returns:
            tuple: (状态文本, 状态颜色)
        """
        if not self.current_config or client_index >= len(self.current_config.clients):
            return "未配置", "gray"

        client = self.current_config.clients[client_index]

        if not client.enabled:
            return "已禁用", "gray"

        if not client.api_id or not client.api_hash or not client.phone_number:
            return "配置不完整", "orange"

        # 检查客户端管理器中的状态
        if self.client_manager:
            session_name = client.session_name
            if session_name in self.client_manager.client_status:
                status = self.client_manager.client_status[session_name]
                if status == ClientStatus.LOGGED_IN:
                    return "已登录", "green"
                elif status == ClientStatus.LOGGING_IN:
                    return "登录中", "blue"
                elif status == ClientStatus.LOGIN_FAILED:
                    return "登录失败", "red"
                elif status == ClientStatus.NOT_LOGGED_IN:
                    return "未登录", "orange"
                elif status == ClientStatus.ERROR:
                    return "错误", "red"
                elif status == ClientStatus.DISABLED:
                    return "已禁用", "gray"

        return "未连接", "gray"

    def update_login_button_states(self):
        """更新登录按钮状态（实现顺序登录控制）"""
        try:
            if not self.client_manager:
                # 如果没有客户端管理器，禁用所有按钮
                for session_name in self.login_buttons:
                    self.login_buttons[session_name].configure(state="disabled")
                    self.logout_buttons[session_name].configure(state="disabled")
                return

            # 获取按钮状态
            button_states = self.client_manager.get_login_button_states()

            # 更新每个按钮的状态
            for session_name, login_button in self.login_buttons.items():
                # 登录按钮状态
                if session_name in button_states:
                    login_enabled = button_states[session_name]
                    login_button.configure(state="normal" if login_enabled else "disabled")
                else:
                    login_button.configure(state="disabled")

                # 登出按钮状态（只有已登录的客户端才能登出）
                if (session_name in self.client_manager.client_status and
                    self.client_manager.client_status[session_name] == ClientStatus.LOGGED_IN):
                    self.logout_buttons[session_name].configure(state="normal")
                else:
                    self.logout_buttons[session_name].configure(state="disabled")

        except Exception as e:
            self.logger.error(f"更新登录按钮状态失败: {e}")

    def check_disable_client_constraint(self, client_index: int) -> bool:
        """
        检查禁用客户端的约束（强制启用约束）

        Args:
            client_index: 客户端索引

        Returns:
            bool: 是否可以禁用
        """
        try:
            if not self.current_config or client_index >= len(self.current_config.clients):
                return False

            client_config = self.current_config.clients[client_index]

            if not self.client_manager:
                return True

            can_disable, error_msg = self.client_manager.can_disable_client(client_config.session_name)

            if not can_disable:
                # 显示错误提示
                import tkinter.messagebox as messagebox
                messagebox.showerror("禁用失败", error_msg)
                return False

            return True

        except Exception as e:
            self.logger.error(f"检查禁用约束失败: {e}")
            return False

    def open_api_settings(self):
        """打开API设置窗口"""
        try:
            from .api_settings_window import APISettingsWindow

            # 获取当前账户类型
            account_type = AccountType(self.account_type_var.get())

            # 获取当前客户端配置，只传递有效的配置
            clients = []
            if self.current_config and self.current_config.clients:
                # 只复制有效的客户端配置
                for client in self.current_config.clients:
                    if (client.api_id > 0 and
                        client.api_hash and
                        client.phone_number and
                        client.session_name):
                        clients.append(client)

            # 创建API设置窗口
            api_window = APISettingsWindow(
                parent=self.parent,
                account_type=account_type,
                clients=clients,
                on_save_callback=self.on_api_settings_saved
            )

            # 显示窗口
            api_window.show()

        except Exception as e:
            self.logger.error(f"打开API设置窗口失败: {e}")
            # 显示用户友好的错误信息
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror("错误", f"无法打开API设置窗口: {e}")
            except:
                pass

    def on_api_settings_saved(self, updated_clients: List[ClientConfig]):
        """API设置保存回调"""
        try:
            # 更新当前配置
            account_type = AccountType(self.account_type_var.get())

            if not self.current_config:
                self.current_config = MultiClientConfig(
                    account_type=account_type,
                    clients=updated_clients
                )
            else:
                self.current_config.account_type = account_type
                self.current_config.clients = updated_clients

            # 保存配置
            if self.config_manager.save_client_config(self.current_config):
                # 更新状态显示
                self.update_client_status_display()

                # 重新创建客户端管理器
                if self.client_manager:
                    # 直接创建新的客户端管理器，让旧的自然清理
                    old_client_manager = self.client_manager
                    self.client_manager = None

                    # 在后台线程中安全地关闭旧客户端
                    def shutdown_sync():
                        try:
                            # 使用同步方式关闭客户端，避免事件循环冲突
                            for session_name, client in old_client_manager.clients.items():
                                try:
                                    if client.is_connected:
                                        # 直接停止客户端，不使用异步方法
                                        client.stop()
                                except Exception as e:
                                    self.logger.warning(f"关闭客户端 {session_name} 失败: {e}")
                            self.logger.info("旧客户端管理器已关闭")
                        except Exception as e:
                            self.logger.error(f"关闭客户端管理器失败: {e}")

                    import threading
                    threading.Thread(target=shutdown_sync, daemon=True).start()

                # 创建新的客户端管理器
                self.client_manager = ClientManager(self.current_config, self.on_client_manager_event)

                self.logger.info("API设置已保存并应用")
            else:
                self.logger.error("保存API设置失败")

        except Exception as e:
            self.logger.error(f"应用API设置失败: {e}")
    


    def load_config(self):
        """加载配置"""
        try:
            # 加载客户端配置
            self.current_config = self.config_manager.load_client_config()

            if self.current_config:
                # 设置账户类型
                self.account_type_var.set(self.current_config.account_type.value)

                # 更新状态显示
                self.update_client_status_display()

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



    def login_client(self, client_index: int):
        """登录指定客户端"""
        if not self.client_manager or client_index >= len(self.current_config.clients):
            return

        client_config = self.current_config.clients[client_index]

        # 简化登录逻辑，避免创建新的事件循环
        def login_sync():
            try:
                # 首先确保客户端已启用
                if not self.client_manager.enable_client(client_config.session_name):
                    self.logger.error(f"无法启用客户端 {client_config.session_name}")
                    return

                # 检查客户端是否已经登录
                client = self.client_manager.get_client(client_config.session_name)
                if client and client.is_connected:
                    self.logger.info(f"客户端 {client_config.session_name} 已经登录")
                    # 在主线程中更新UI
                    if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                        self.parent.after(0, self._update_ui_after_login_success)
                    return

                # 对于需要手动登录的情况，提示用户
                self.logger.info(f"客户端 {client_config.session_name} 需要手动登录，请检查会话文件或重新配置")

                # 在主线程中更新UI
                if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                    self.parent.after(0, self._update_ui_after_login_failure)

            except Exception as e:
                self.logger.error(f"客户端登录异常: {e}")
                # 在主线程中更新UI
                if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                    self.parent.after(0, self._update_ui_after_login_failure)

        import threading
        threading.Thread(target=login_sync, daemon=True).start()

    def _update_ui_after_login_success(self):
        """登录成功后更新UI"""
        try:
            # 更新状态显示
            self.update_client_status_display()
            # 更新按钮状态
            self.update_login_button_states()
        except Exception as e:
            self.logger.error(f"登录成功后更新UI失败: {e}")

    def _update_ui_after_login_failure(self):
        """登录失败后更新UI"""
        try:
            # 更新状态显示
            self.update_client_status_display()
            # 更新按钮状态
            self.update_login_button_states()
        except Exception as e:
            self.logger.error(f"登录失败后更新UI失败: {e}")

    def logout_client(self, client_index: int):
        """登出指定客户端"""
        if not self.client_manager or client_index >= len(self.current_config.clients):
            return

        client_config = self.current_config.clients[client_index]

        # 使用同步方式执行登出，避免事件循环冲突
        def logout_sync():
            try:
                client = self.client_manager.get_client(client_config.session_name)
                if client and client.is_connected:
                    # 直接停止客户端连接
                    client.stop()
                    self.logger.info(f"客户端 {client_config.session_name} 登出成功")

                    # 更新客户端状态
                    self.client_manager.client_status[client_config.session_name] = ClientStatus.NOT_LOGGED_IN

                    # 在主线程中更新UI
                    if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                        self.parent.after(0, self.update_client_status_display)
                else:
                    self.logger.warning(f"客户端 {client_config.session_name} 未连接或不存在")
            except Exception as e:
                self.logger.error(f"客户端登出异常: {e}")

        import threading
        threading.Thread(target=logout_sync, daemon=True).start()



    def test_connections(self):
        """测试连接 - 使用真实的API调用测试连接状态"""
        if not self.client_manager:
            self.show_error("请先保存配置")
            return

        # 禁用测试按钮，防止重复点击
        self.test_button.configure(state="disabled", text="测试中...")

        def test_real_connection():
            """真实连接测试 - 使用get_me API测试所有客户端"""
            try:
                results = {}  # 存储测试结果

                for client_config in self.current_config.clients:
                    if client_config.enabled:
                        session_name = client_config.session_name

                        # 使用API测试方法，真正调用get_me
                        success, message = self.client_manager.test_client_connection_with_api(session_name)
                        results[session_name] = (success, message)

                        # 记录测试结果
                        self.logger.info(f"客户端 {session_name}: {message}")
                    else:
                        # 未启用的客户端跳过测试
                        results[session_name] = (False, "客户端未启用")
                        self.logger.debug(f"客户端 {session_name}: 未启用，跳过测试")

                # 在主线程中更新UI显示和恢复按钮
                def update_ui():
                    try:
                        # 更新客户端状态显示
                        self.update_client_status_display()

                        # 恢复测试按钮
                        self.test_button.configure(state="normal", text="测试连接")

                        # 计算测试结果
                        enabled_results = {k: v for k, v in results.items()
                                         if any(c.session_name == k and c.enabled
                                               for c in self.current_config.clients)}
                        success_count = sum(1 for success, _ in enabled_results.values() if success)
                        total_enabled = len(enabled_results)

                        # 显示测试结果摘要
                        if total_enabled == 0:
                            self.show_info("没有启用的客户端需要测试")
                        elif success_count == total_enabled:
                            self.show_success(f"所有客户端连接正常 ({success_count}/{total_enabled})")
                        elif success_count > 0:
                            self.show_info(f"部分客户端连接正常 ({success_count}/{total_enabled})")
                        else:
                            self.show_error(f"所有客户端连接失败 ({success_count}/{total_enabled})")

                        # 更新主窗口状态栏中的客户端数量
                        if hasattr(self, 'parent') and hasattr(self.parent, 'update_client_count_status'):
                            self.parent.update_client_count_status()

                    except Exception as e:
                        self.logger.error(f"更新UI失败: {e}")
                        self.test_button.configure(state="normal", text="测试连接")

                if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                    self.parent.after(0, update_ui)

            except Exception as e:
                self.logger.error(f"测试连接异常: {e}")
                # 恢复按钮状态
                if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                    self.parent.after(0, lambda: self.test_button.configure(state="normal", text="测试连接"))

        import threading
        threading.Thread(target=test_real_connection, daemon=True).start()



    def update_client_status(self, client_index: int, status: ClientStatus):
        """更新客户端状态显示"""
        # 现在状态更新通过 update_client_status_display 方法统一处理
        # 这个方法主要用于记录状态变化
        try:
            if self.current_config and client_index < len(self.current_config.clients):
                client = self.current_config.clients[client_index]
                client.status = status
                self.logger.debug(f"客户端 {client_index + 1} 状态更新为: {status.value}")

                # 刷新整个状态显示
                self.update_client_status_display()
        except Exception as e:
            self.logger.error(f"更新客户端状态失败: {e}")

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
            if hasattr(event, 'client_name') and event.client_name:
                # 查找对应的客户端
                for i, client_config in enumerate(self.current_config.clients):
                    if client_config.session_name == event.client_name:
                        # 从客户端管理器获取最新状态，而不是依赖事件中的状态
                        if self.client_manager:
                            current_status = self.client_manager.get_client_status(event.client_name)
                            if current_status:
                                self.update_client_status(i, current_status)
                        break
        except Exception as e:
            self.logger.error(f"更新客户端UI失败: {e}")

    def on_client_manager_event(self, event: BaseEvent):
        """客户端管理器事件回调"""
        # 转发到事件管理器
        self.event_manager.emit(event)

    def show_success(self, message: str):
        """显示成功消息"""
        self.logger.info(message)
        # 可以在这里添加UI提示，比如状态栏消息或弹窗

    def show_error(self, message: str):
        """显示错误消息"""
        self.logger.error(message)
        # 可以在这里添加UI提示，比如状态栏消息或弹窗

    def show_info(self, message: str):
        """显示信息消息"""
        self.logger.info(message)
        # 可以在这里添加UI提示，比如状态栏消息或弹窗
