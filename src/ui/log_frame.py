#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志查看界面
"""

import tkinter as tk
import customtkinter as ctk
from typing import List
from datetime import datetime

from ..core.event_manager import EventManager
from ..models.events import BaseEvent, EventType, EventSeverity
from ..utils.logger import get_logger


class LogFrame:
    """日志框架"""
    
    def __init__(self, parent, event_manager: EventManager):
        """
        初始化日志框架
        
        Args:
            parent: 父窗口
            event_manager: 事件管理器
        """
        self.parent = parent
        self.event_manager = event_manager
        self.logger = get_logger(__name__)
        
        # 日志过滤设置
        self.filter_severity = None
        self.filter_event_type = None
        self.filter_source = None
        
        # 创建界面
        self.setup_ui()
        
        # 订阅所有事件
        self.event_manager.subscribe_all(self.on_event_received)
        
        # 加载历史日志
        self.load_history_logs()
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建日志显示区域
        self.create_log_display()
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar_frame = ctk.CTkFrame(self.main_frame)
        toolbar_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 标题
        title_label = ctk.CTkLabel(
            toolbar_frame,
            text="日志查看",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side="left", padx=10, pady=10)
        
        # 过滤器框架
        filter_frame = ctk.CTkFrame(toolbar_frame)
        filter_frame.pack(side="left", padx=20, pady=5)
        
        # 严重程度过滤
        severity_label = ctk.CTkLabel(filter_frame, text="级别:")
        severity_label.grid(row=0, column=0, padx=5, pady=5)
        
        self.severity_var = ctk.StringVar(value="全部")
        severity_values = ["全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.severity_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.severity_var,
            values=severity_values,
            command=self.on_filter_changed,
            width=100
        )
        self.severity_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # 事件类型过滤
        type_label = ctk.CTkLabel(filter_frame, text="类型:")
        type_label.grid(row=0, column=2, padx=5, pady=5)
        
        self.type_var = ctk.StringVar(value="全部")
        type_values = ["全部", "客户端", "下载", "错误", "系统"]
        self.type_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.type_var,
            values=type_values,
            command=self.on_filter_changed,
            width=100
        )
        self.type_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # 操作按钮框架
        button_frame = ctk.CTkFrame(toolbar_frame)
        button_frame.pack(side="right", padx=10, pady=5)
        
        # 刷新按钮
        refresh_button = ctk.CTkButton(
            button_frame,
            text="刷新",
            width=80,
            command=self.refresh_logs
        )
        refresh_button.pack(side="left", padx=5, pady=5)
        
        # 清空按钮
        clear_button = ctk.CTkButton(
            button_frame,
            text="清空",
            width=80,
            command=self.clear_logs
        )
        clear_button.pack(side="left", padx=5, pady=5)
        
        # 导出按钮
        export_button = ctk.CTkButton(
            button_frame,
            text="导出",
            width=80,
            command=self.export_logs
        )
        export_button.pack(side="left", padx=5, pady=5)
        
        # 自动滚动开关
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        auto_scroll_switch = ctk.CTkSwitch(
            button_frame,
            text="自动滚动",
            variable=self.auto_scroll_var
        )
        auto_scroll_switch.pack(side="left", padx=10, pady=5)
    
    def create_log_display(self):
        """创建日志显示区域"""
        # 日志显示框架
        log_frame = ctk.CTkFrame(self.main_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建文本框和滚动条
        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 配置文本标签样式
        self.configure_text_tags()
    
    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ctk.CTkFrame(self.main_frame)
        status_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # 日志统计
        self.log_count_label = ctk.CTkLabel(
            status_frame,
            text="日志: 0 条",
            font=ctk.CTkFont(size=12)
        )
        self.log_count_label.pack(side="left", padx=10, pady=5)
        
        # 过滤状态
        self.filter_status_label = ctk.CTkLabel(
            status_frame,
            text="过滤: 无",
            font=ctk.CTkFont(size=12)
        )
        self.filter_status_label.pack(side="left", padx=10, pady=5)
        
        # 最后更新时间
        self.last_update_label = ctk.CTkLabel(
            status_frame,
            text="最后更新: 从未",
            font=ctk.CTkFont(size=12)
        )
        self.last_update_label.pack(side="right", padx=10, pady=5)
    
    def configure_text_tags(self):
        """配置文本标签样式"""
        # 严重程度颜色
        severity_colors = {
            "DEBUG": "gray",
            "INFO": "white",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "darkred"
        }
        
        for severity, color in severity_colors.items():
            self.log_text.tag_config(severity, foreground=color)
        
        # 时间戳样式
        self.log_text.tag_config("timestamp", foreground="lightblue")
        
        # 事件类型样式
        self.log_text.tag_config("event_type", foreground="lightgreen")
        
        # 来源样式
        self.log_text.tag_config("source", foreground="yellow")
    
    def on_filter_changed(self, value=None):
        """过滤器改变事件"""
        # 更新过滤设置
        severity = self.severity_var.get()
        self.filter_severity = None if severity == "全部" else EventSeverity(severity.lower())
        
        event_type = self.type_var.get()
        self.filter_event_type = self.get_event_type_filter(event_type)
        
        # 重新加载日志
        self.refresh_logs()
        
        # 更新过滤状态
        filter_parts = []
        if self.filter_severity:
            filter_parts.append(f"级别:{severity}")
        if event_type != "全部":
            filter_parts.append(f"类型:{event_type}")
        
        filter_text = ", ".join(filter_parts) if filter_parts else "无"
        self.filter_status_label.configure(text=f"过滤: {filter_text}")
    
    def get_event_type_filter(self, type_name: str) -> List[EventType]:
        """获取事件类型过滤器"""
        if type_name == "全部":
            return None
        elif type_name == "客户端":
            return [
                EventType.CLIENT_LOGIN_START,
                EventType.CLIENT_LOGIN_SUCCESS,
                EventType.CLIENT_LOGIN_FAILED,
                EventType.CLIENT_DISCONNECTED,
                EventType.CLIENT_RECONNECTED,
                EventType.CLIENT_STATUS_CHANGED
            ]
        elif type_name == "下载":
            return [
                EventType.DOWNLOAD_STARTED,
                EventType.DOWNLOAD_PROGRESS,
                EventType.DOWNLOAD_FILE_COMPLETED,
                EventType.DOWNLOAD_COMPLETED,
                EventType.DOWNLOAD_FAILED,
                EventType.DOWNLOAD_CANCELLED,
                EventType.DOWNLOAD_PAUSED,
                EventType.DOWNLOAD_RESUMED
            ]
        elif type_name == "错误":
            return [
                EventType.ERROR_FLOOD_WAIT,
                EventType.ERROR_NETWORK,
                EventType.ERROR_AUTH,
                EventType.ERROR_PERMISSION,
                EventType.ERROR_UNKNOWN
            ]
        elif type_name == "系统":
            return [
                EventType.APP_STARTED,
                EventType.APP_SHUTDOWN,
                EventType.CONFIG_UPDATED
            ]
        return None
    
    def load_history_logs(self):
        """加载历史日志"""
        try:
            # 获取历史事件
            events = self.event_manager.get_recent_events(limit=1000)
            
            # 清空当前显示
            self.log_text.delete("1.0", tk.END)
            
            # 显示事件
            for event in events:
                self.add_log_entry(event)
            
            # 更新统计
            self.update_log_count(len(events))
            
        except Exception as e:
            self.logger.error(f"加载历史日志失败: {e}")
    
    def refresh_logs(self):
        """刷新日志"""
        try:
            # 获取过滤后的事件
            events = self.get_filtered_events()
            
            # 清空当前显示
            self.log_text.delete("1.0", tk.END)
            
            # 显示事件
            for event in events:
                self.add_log_entry(event)
            
            # 更新统计
            self.update_log_count(len(events))
            
            # 更新最后更新时间
            self.last_update_label.configure(
                text=f"最后更新: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            self.logger.error(f"刷新日志失败: {e}")
    
    def get_filtered_events(self) -> List[BaseEvent]:
        """获取过滤后的事件"""
        events = self.event_manager.get_recent_events(limit=1000)
        
        # 应用过滤器
        filtered_events = []
        for event in events:
            # 严重程度过滤
            if self.filter_severity and event.severity != self.filter_severity:
                continue
            
            # 事件类型过滤
            if self.filter_event_type and event.event_type not in self.filter_event_type:
                continue
            
            filtered_events.append(event)
        
        return filtered_events
    
    def add_log_entry(self, event: BaseEvent):
        """添加日志条目"""
        try:
            # 格式化时间戳
            timestamp = event.timestamp.strftime("%H:%M:%S")
            
            # 构建日志行
            log_line = f"[{timestamp}] [{event.severity.value.upper()}] [{event.event_type.value}]"
            
            if event.source:
                log_line += f" [{event.source}]"
            
            log_line += f" {event.message}\n"
            
            # 插入文本
            start_index = self.log_text.index(tk.END + "-1c")
            self.log_text.insert(tk.END, log_line)
            end_index = self.log_text.index(tk.END + "-1c")
            
            # 应用样式
            self.log_text.tag_add(event.severity.value.upper(), start_index, end_index)
            
            # 自动滚动到底部
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)
                
        except Exception as e:
            self.logger.error(f"添加日志条目失败: {e}")
    
    def clear_logs(self):
        """清空日志"""
        try:
            # 清空显示
            self.log_text.delete("1.0", tk.END)
            
            # 清空事件历史
            self.event_manager.clear_history()
            
            # 更新统计
            self.update_log_count(0)
            
            self.logger.info("日志已清空")
            
        except Exception as e:
            self.logger.error(f"清空日志失败: {e}")
    
    def export_logs(self):
        """导出日志"""
        try:
            from tkinter import filedialog
            
            # 选择保存文件
            file_path = filedialog.asksaveasfilename(
                title="导出日志",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if file_path:
                # 获取当前显示的日志
                log_content = self.log_text.get("1.0", tk.END)
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                
                self.logger.info(f"日志已导出到: {file_path}")
                
        except Exception as e:
            self.logger.error(f"导出日志失败: {e}")
    
    def update_log_count(self, count: int):
        """更新日志计数"""
        self.log_count_label.configure(text=f"日志: {count} 条")
    
    def on_event_received(self, event: BaseEvent):
        """处理接收到的事件"""
        try:
            # 在主线程中更新UI
            if self.parent:
                self.parent.after(0, self._add_new_event, event)
            else:
                self.logger.warning("父窗口对象不存在，无法更新UI")
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")
    
    def _add_new_event(self, event: BaseEvent):
        """添加新事件（在主线程中执行）"""
        try:
            # 检查是否符合过滤条件
            if self.filter_severity and event.severity != self.filter_severity:
                return
            
            if self.filter_event_type and event.event_type not in self.filter_event_type:
                return
            
            # 添加到显示
            self.add_log_entry(event)
            
            # 更新计数（简单递增）
            current_text = self.log_count_label.cget("text")
            if "日志: " in current_text:
                try:
                    current_count = int(current_text.split("日志: ")[1].split(" 条")[0])
                    self.update_log_count(current_count + 1)
                except:
                    pass
            
        except Exception as e:
            self.logger.error(f"添加新事件失败: {e}")
