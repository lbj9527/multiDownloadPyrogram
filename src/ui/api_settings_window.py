#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API设置窗口
"""

import tkinter as tk
import tkinter.messagebox
import customtkinter as ctk
from typing import Optional, List, Callable

from ..models.client_config import ClientConfig, ClientStatus, AccountType
from ..utils.logger import get_logger


class APISettingsWindow:
    """API设置窗口"""
    
    def __init__(self, parent, account_type: AccountType, clients: List[ClientConfig], 
                 on_save_callback: Optional[Callable] = None):
        """
        初始化API设置窗口
        
        Args:
            parent: 父窗口
            account_type: 账户类型
            clients: 客户端配置列表
            on_save_callback: 保存回调函数
        """
        self.parent = parent
        self.account_type = account_type
        self.clients = clients.copy() if clients else []
        self.on_save_callback = on_save_callback
        self.logger = get_logger(__name__)
        
        # 确保客户端数量正确，但不创建无效的ClientConfig对象
        # 而是使用字典来存储临时数据
        max_clients = 3 if account_type == AccountType.NORMAL else 4
        self.client_data = []

        # 从现有clients复制数据
        for i, client in enumerate(self.clients):
            if i < max_clients:
                self.client_data.append({
                    'api_id': client.api_id if client.api_id > 0 else '',
                    'api_hash': client.api_hash,
                    'phone_number': client.phone_number,
                    'session_name': client.session_name,
                    'enabled': client.enabled
                })

        # 填充剩余的空槽位
        while len(self.client_data) < max_clients:
            self.client_data.append({
                'api_id': '',
                'api_hash': '',
                'phone_number': '',
                'session_name': f'session_{len(self.client_data) + 1}',
                'enabled': False
            })
        
        # 创建窗口
        self.window = None
        self.client_widgets = []
        
    def show(self):
        """显示API设置窗口"""
        if self.window is not None:
            # 如果窗口已存在，将其置顶并获得焦点
            self.window.lift()
            self.window.focus_force()
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))
            return

        # 创建API设置窗口
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("API 设置")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        self.window.minsize(600, 500)

        # 设置窗口属性
        self.window.transient(self.parent)  # 设置为父窗口的子窗口
        self.window.grab_set()  # 设置为模态窗口

        # 设置窗口图标
        try:
            self.window.iconbitmap("assets/icon.ico")
        except:
            pass

        # 居中显示
        self.center_window()

        # 设置窗口置顶和焦点
        self.window.lift()
        self.window.focus_force()
        self.window.attributes('-topmost', True)

        # 短暂置顶后恢复正常状态，但保持在前台
        self.window.after(200, lambda: self.window.attributes('-topmost', False))

        # 设置窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建界面
        self.setup_ui()

        # 加载当前配置
        self.load_settings()

        self.logger.info("API设置窗口已打开")
    
    def center_window(self):
        """居中显示窗口（相对于父窗口）"""
        try:
            # 更新窗口以获取准确的尺寸
            self.window.update_idletasks()

            # 获取API设置窗口大小
            dialog_width = self.window.winfo_width()
            dialog_height = self.window.winfo_height()

            # 如果窗口尺寸无效，使用默认尺寸
            if dialog_width <= 1 or dialog_height <= 1:
                dialog_width = 700
                dialog_height = 600
                self.logger.warning("API设置窗口尺寸获取失败，使用默认尺寸")

            # 获取父窗口位置和大小
            try:
                self.parent.update_idletasks()
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()

                # 验证父窗口信息
                if parent_width <= 1 or parent_height <= 1:
                    raise ValueError("父窗口尺寸无效")

            except Exception as parent_error:
                self.logger.warning(f"获取父窗口信息失败: {parent_error}，使用屏幕居中")
                # 如果无法获取父窗口信息，则使用屏幕居中
                screen_width = self.window.winfo_screenwidth()
                screen_height = self.window.winfo_screenheight()
                parent_x = 0
                parent_y = 0
                parent_width = screen_width
                parent_height = screen_height

            # 计算相对于父窗口的居中位置
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2

            # 获取屏幕大小，确保窗口不会超出屏幕边界
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()

            # 调整位置，确保窗口完全在屏幕内
            if x < 0:
                x = 10
            elif x + dialog_width > screen_width:
                x = screen_width - dialog_width - 10

            if y < 0:
                y = 10
            elif y + dialog_height > screen_height:
                y = screen_height - dialog_height - 10

            # 设置窗口位置
            geometry = f"{dialog_width}x{dialog_height}+{x}+{y}"
            self.window.geometry(geometry)

            self.logger.debug(f"API设置窗口居中: {geometry} (相对于父窗口 {parent_x},{parent_y} {parent_width}x{parent_height})")

        except Exception as e:
            self.logger.warning(f"居中窗口失败: {e}")
            # 如果居中失败，使用默认位置
            try:
                self.window.geometry("700x600+100+100")
            except Exception as fallback_error:
                self.logger.error(f"设置默认窗口位置失败: {fallback_error}")
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ctk.CTkLabel(
            main_frame,
            text=f"API 设置 - {self.account_type.value.title()}账户",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # 说明文本
        max_clients = 3 if self.account_type == AccountType.NORMAL else 4
        info_text = f"配置您的Telegram API凭据，最多支持{max_clients}个客户端"
        info_label = ctk.CTkLabel(
            main_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(pady=(0, 10))
        
        # 创建滚动框架
        self.scroll_frame = ctk.CTkScrollableFrame(main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建客户端配置区域
        self.create_client_configs()
        
        # 创建按钮区域
        self.create_buttons()
    
    def create_client_configs(self):
        """创建客户端配置区域"""
        max_clients = 3 if self.account_type == AccountType.NORMAL else 4
        
        for i in range(max_clients):
            client_frame = self.create_client_widget(i + 1)
            self.client_widgets.append(client_frame)
    
    def create_client_widget(self, client_number: int) -> dict:
        """
        创建单个客户端配置组件
        
        Args:
            client_number: 客户端编号
            
        Returns:
            dict: 包含所有输入控件的字典
        """
        # 客户端框架
        client_frame = ctk.CTkFrame(self.scroll_frame)
        client_frame.pack(fill="x", padx=5, pady=5)
        
        # 标题和启用开关
        header_frame = ctk.CTkFrame(client_frame)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"客户端 {client_number}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(side="left", padx=5, pady=5)
        
        # 启用开关
        enabled_var = ctk.BooleanVar()
        enabled_switch = ctk.CTkSwitch(
            header_frame,
            text="启用",
            variable=enabled_var,
            command=lambda: self.on_client_enabled_changed(client_number - 1, enabled_var.get())
        )
        enabled_switch.pack(side="right", padx=5, pady=5)
        
        # 配置输入区域
        config_frame = ctk.CTkFrame(client_frame)
        config_frame.pack(fill="x", padx=10, pady=(0, 10))
        
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
        
        # 返回控件字典
        return {
            'frame': client_frame,
            'enabled_var': enabled_var,
            'enabled_switch': enabled_switch,
            'api_id_entry': api_id_entry,
            'api_hash_entry': api_hash_entry,
            'phone_entry': phone_entry,
            'session_entry': session_entry,
            'config_frame': config_frame
        }
    
    def create_buttons(self):
        """创建按钮区域"""
        button_frame = ctk.CTkFrame(self.window)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # 取消按钮
        cancel_button = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.on_closing,
            width=100
        )
        cancel_button.pack(side="right", padx=(5, 10), pady=10)
        
        # 保存按钮
        save_button = ctk.CTkButton(
            button_frame,
            text="保存",
            command=self.save_settings,
            width=100
        )
        save_button.pack(side="right", padx=5, pady=10)
        
        # 重置按钮
        reset_button = ctk.CTkButton(
            button_frame,
            text="重置",
            command=self.reset_settings,
            width=100
        )
        reset_button.pack(side="left", padx=10, pady=10)
    
    def on_client_enabled_changed(self, client_index: int, enabled: bool):
        """客户端启用状态改变"""
        if client_index < len(self.client_data):
            # 如果要禁用客户端，检查强制启用约束
            if not enabled:
                # 统计当前启用的客户端数量（不包括当前要禁用的）
                enabled_count = 0
                for i, data in enumerate(self.client_data):
                    if i != client_index and data['enabled']:
                        enabled_count += 1

                # 如果禁用后没有启用的客户端，阻止操作
                if enabled_count == 0:
                    tk.messagebox.showerror(
                        "禁用失败",
                        "系统要求至少保持一个客户端处于启用状态，无法禁用最后一个启用的客户端"
                    )
                    # 重新设置开关状态
                    widget = self.client_widgets[client_index]
                    widget['enabled_var'].set(True)
                    return

            self.client_data[client_index]['enabled'] = enabled

            # 更新UI状态
            widget = self.client_widgets[client_index]

            # 根据启用状态设置输入框的状态
            state = "normal" if enabled else "disabled"
            for entry in [widget['api_id_entry'], widget['api_hash_entry'],
                         widget['phone_entry'], widget['session_entry']]:
                entry.configure(state=state)
    
    def load_settings(self):
        """加载设置"""
        try:
            for i, client_data in enumerate(self.client_data):
                if i < len(self.client_widgets):
                    widget = self.client_widgets[i]

                    # 设置启用状态
                    widget['enabled_var'].set(client_data['enabled'])

                    # 设置输入值
                    if client_data['api_id']:
                        widget['api_id_entry'].insert(0, str(client_data['api_id']))
                    if client_data['api_hash']:
                        widget['api_hash_entry'].insert(0, client_data['api_hash'])
                    if client_data['phone_number']:
                        widget['phone_entry'].insert(0, client_data['phone_number'])
                    if client_data['session_name']:
                        widget['session_entry'].delete(0, tk.END)
                        widget['session_entry'].insert(0, client_data['session_name'])

                    # 更新UI状态
                    self.on_client_enabled_changed(i, client_data['enabled'])

        except Exception as e:
            self.logger.error(f"加载设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            # 收集所有客户端配置
            updated_clients = []

            for i, widget in enumerate(self.client_widgets):
                enabled = widget['enabled_var'].get()
                api_id_text = widget['api_id_entry'].get().strip()
                api_hash = widget['api_hash_entry'].get().strip()
                phone_number = widget['phone_entry'].get().strip()
                session_name = widget['session_entry'].get().strip()

                # 只处理启用的客户端
                if enabled:
                    # 验证必填字段
                    if not api_id_text or not api_hash or not phone_number:
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 启用时，API ID、API Hash和电话号码不能为空"
                        )
                        return

                    try:
                        api_id = int(api_id_text)
                    except ValueError:
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 的API ID必须是数字"
                        )
                        return

                    # 验证API ID范围
                    if not (10000 <= api_id <= 9999999999):
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 的API ID必须为5-10位数字"
                        )
                        return

                    # 验证API Hash格式
                    if len(api_hash) != 32:
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 的API Hash必须为32位字符串"
                        )
                        return

                    # 验证电话号码格式
                    import re
                    if not re.match(r'^\+\d{1,4}\d{6,15}$', phone_number):
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 的电话号码格式错误，必须包含国家代码（如+86、+1等）"
                        )
                        return

                    # 验证会话名称
                    if not session_name:
                        session_name = f"session_{i + 1}"

                    try:
                        # 创建客户端配置
                        client_config = ClientConfig(
                            api_id=api_id,
                            api_hash=api_hash,
                            phone_number=phone_number,
                            session_name=session_name,
                            enabled=enabled
                        )

                        updated_clients.append(client_config)

                    except Exception as validation_error:
                        tk.messagebox.showerror(
                            "验证错误",
                            f"客户端 {i + 1} 配置验证失败: {validation_error}"
                        )
                        return

            # 调用保存回调
            if self.on_save_callback:
                self.on_save_callback(updated_clients)

            self.logger.info("API设置已保存")
            self.on_closing()

        except Exception as e:
            self.logger.error(f"保存设置失败: {e}")
            tk.messagebox.showerror("保存失败", f"保存设置时发生错误: {e}")
    
    def reset_settings(self):
        """重置设置"""
        try:
            # 清空所有输入框
            for widget in self.client_widgets:
                widget['enabled_var'].set(False)
                widget['api_id_entry'].delete(0, tk.END)
                widget['api_hash_entry'].delete(0, tk.END)
                widget['phone_entry'].delete(0, tk.END)
                widget['session_entry'].delete(0, tk.END)
                
                # 更新UI状态
                self.on_client_enabled_changed(
                    self.client_widgets.index(widget), 
                    False
                )
            
            self.logger.info("API设置已重置")
            
        except Exception as e:
            self.logger.error(f"重置设置失败: {e}")
    
    def on_closing(self):
        """窗口关闭事件"""
        try:
            if self.window:
                # 释放模态状态
                try:
                    self.window.grab_release()
                except:
                    pass

                # 销毁窗口
                self.window.destroy()
                self.window = None
                self.logger.info("API设置窗口已关闭")
        except Exception as e:
            self.logger.error(f"关闭API设置窗口失败: {e}")
