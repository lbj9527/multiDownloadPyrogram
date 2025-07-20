#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载界面
"""

import tkinter as tk
import customtkinter as ctk
import asyncio
import threading
from typing import Optional, List

from ..models.download_config import DownloadConfig, DownloadStatus, MessageType
from ..core.download_manager import DownloadManager
from ..core.event_manager import EventManager
from ..models.events import BaseEvent, EventType
from ..utils.config_manager import ConfigManager
from ..utils.logger import get_logger


class DownloadFrame:
    """下载框架"""
    
    def __init__(self, parent, config_manager: ConfigManager, event_manager: EventManager):
        """
        初始化下载框架
        
        Args:
            parent: 父窗口
            config_manager: 配置管理器
            event_manager: 事件管理器
        """
        self.parent = parent
        self.config_manager = config_manager
        self.event_manager = event_manager
        self.logger = get_logger(__name__)
        
        # 下载管理器
        self.download_manager: Optional[DownloadManager] = None
        
        # 当前任务ID
        self.current_task_id: Optional[str] = None

        # 主窗口引用
        self.main_window = None
        
        # 创建界面
        self.setup_ui()
        
        # 加载配置
        self.load_config()
        
        # 订阅事件
        self.event_manager.subscribe(EventType.DOWNLOAD_STARTED, self.on_download_event)
        self.event_manager.subscribe(EventType.DOWNLOAD_PROGRESS, self.on_download_event)
        self.event_manager.subscribe(EventType.DOWNLOAD_COMPLETED, self.on_download_event)
        self.event_manager.subscribe(EventType.DOWNLOAD_FAILED, self.on_download_event)
        self.event_manager.subscribe(EventType.DOWNLOAD_FILE_COMPLETED, self.on_download_event)
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建下载配置区域
        self.create_download_config_section()
        
        # 创建进度显示区域
        self.create_progress_section()
        
        # 创建操作按钮区域
        self.create_action_buttons()
    
    def create_download_config_section(self):
        """创建下载配置区域"""
        # 配置框架
        config_frame = ctk.CTkFrame(self.main_frame)
        config_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        # 标题
        title_label = ctk.CTkLabel(
            config_frame,
            text="下载配置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # 配置输入区域
        input_frame = ctk.CTkFrame(config_frame)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # 频道ID
        channel_label = ctk.CTkLabel(input_frame, text="频道ID/用户名:")
        channel_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.channel_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="输入频道ID或@用户名"
        )
        self.channel_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 最近使用的频道下拉框
        self.recent_channel_var = ctk.StringVar()
        self.recent_channel_combo = ctk.CTkComboBox(
            input_frame,
            variable=self.recent_channel_var,
            command=self.on_recent_channel_selected
        )
        self.recent_channel_combo.grid(row=0, column=2, padx=5, pady=5)
        
        # 起始消息ID
        start_id_label = ctk.CTkLabel(input_frame, text="起始消息ID:")
        start_id_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.start_id_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="默认为1"
        )
        self.start_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # 消息数量
        count_label = ctk.CTkLabel(input_frame, text="消息数量:")
        count_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.count_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="最多1000条"
        )
        self.count_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # 下载路径
        path_label = ctk.CTkLabel(input_frame, text="下载路径:")
        path_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        
        self.path_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="下载文件保存路径"
        )
        self.path_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        # 浏览按钮
        browse_button = ctk.CTkButton(
            input_frame,
            text="浏览",
            width=80,
            command=self.browse_download_path
        )
        browse_button.grid(row=3, column=2, padx=5, pady=5)
        
        # 设置列权重
        input_frame.grid_columnconfigure(1, weight=1)
        
        # 选项区域
        options_frame = ctk.CTkFrame(config_frame)
        options_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 包含选项
        include_frame = ctk.CTkFrame(options_frame)
        include_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        include_label = ctk.CTkLabel(include_frame, text="包含内容:")
        include_label.pack(pady=(5, 0))
        
        self.include_media_var = ctk.BooleanVar(value=True)
        include_media_check = ctk.CTkCheckBox(
            include_frame,
            text="媒体文件",
            variable=self.include_media_var
        )
        include_media_check.pack(pady=2)
        
        self.include_text_var = ctk.BooleanVar(value=True)
        include_text_check = ctk.CTkCheckBox(
            include_frame,
            text="文本消息",
            variable=self.include_text_var
        )
        include_text_check.pack(pady=2)
        
        # 媒体类型选择
        media_frame = ctk.CTkFrame(options_frame)
        media_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        media_label = ctk.CTkLabel(media_frame, text="媒体类型:")
        media_label.pack(pady=(5, 0))
        
        # 创建媒体类型复选框
        self.media_type_vars = {}
        media_types = [
            ("图片", MessageType.PHOTO),
            ("视频", MessageType.VIDEO),
            ("文档", MessageType.DOCUMENT),
            ("音频", MessageType.AUDIO),
            ("语音", MessageType.VOICE),
            ("贴纸", MessageType.STICKER),
            ("动画", MessageType.ANIMATION),
            ("视频笔记", MessageType.VIDEO_NOTE)
        ]
        
        media_grid_frame = ctk.CTkFrame(media_frame)
        media_grid_frame.pack(fill="x", padx=5, pady=5)
        
        for i, (name, media_type) in enumerate(media_types):
            var = ctk.BooleanVar(value=True)
            self.media_type_vars[media_type] = var
            
            check = ctk.CTkCheckBox(
                media_grid_frame,
                text=name,
                variable=var
            )
            check.grid(row=i // 4, column=i % 4, padx=5, pady=2, sticky="w")
        
        # 高级选项
        advanced_frame = ctk.CTkFrame(options_frame)
        advanced_frame.pack(side="right", fill="y", padx=5, pady=5)
        
        advanced_label = ctk.CTkLabel(advanced_frame, text="高级选项:")
        advanced_label.pack(pady=(5, 0))
        
        # 最大文件大小
        max_size_label = ctk.CTkLabel(advanced_frame, text="最大文件大小(MB):")
        max_size_label.pack(pady=(5, 0))

        self.max_size_entry = ctk.CTkEntry(
            advanced_frame,
            placeholder_text="留空表示无限制（最大50GB）",
            width=150
        )
        self.max_size_entry.pack(pady=2)

        # 添加文件大小限制提示
        size_hint_label = ctk.CTkLabel(
            advanced_frame,
            text="提示：最大支持50GB（51200MB）",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        size_hint_label.pack(pady=(0, 5))
    
    def create_progress_section(self):
        """创建进度显示区域"""
        # 进度框架
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 标题
        title_label = ctk.CTkLabel(
            progress_frame,
            text="下载进度",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # 进度信息框架
        info_frame = ctk.CTkFrame(progress_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # 总体进度
        self.overall_progress = ctk.CTkProgressBar(info_frame)
        self.overall_progress.pack(fill="x", padx=10, pady=(10, 5))
        self.overall_progress.set(0)
        
        # 进度文本
        self.progress_label = ctk.CTkLabel(
            info_frame,
            text="等待开始下载...",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(pady=5)
        
        # 详细信息框架
        details_frame = ctk.CTkFrame(info_frame)
        details_frame.pack(fill="x", padx=10, pady=5)
        
        # 左侧信息
        left_info = ctk.CTkFrame(details_frame)
        left_info.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.message_count_label = ctk.CTkLabel(left_info, text="消息: 0/0")
        self.message_count_label.pack(pady=2)
        
        self.file_count_label = ctk.CTkLabel(left_info, text="文件: 0/0")
        self.file_count_label.pack(pady=2)
        
        self.current_file_label = ctk.CTkLabel(left_info, text="当前文件: 无")
        self.current_file_label.pack(pady=2)
        
        # 右侧信息
        right_info = ctk.CTkFrame(details_frame)
        right_info.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.download_size_label = ctk.CTkLabel(right_info, text="大小: 0 B / 0 B")
        self.download_size_label.pack(pady=2)
        
        self.speed_label = ctk.CTkLabel(right_info, text="速度: 0 B/s")
        self.speed_label.pack(pady=2)
        
        self.eta_label = ctk.CTkLabel(right_info, text="剩余时间: 未知")
        self.eta_label.pack(pady=2)

    def create_action_buttons(self):
        """创建操作按钮区域"""
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=5, pady=(5, 0))

        # 开始下载按钮
        self.start_button = ctk.CTkButton(
            button_frame,
            text="开始下载",
            command=self.start_download
        )
        self.start_button.pack(side="left", padx=10, pady=10)

        # 暂停/恢复按钮
        self.pause_button = ctk.CTkButton(
            button_frame,
            text="暂停",
            command=self.pause_download,
            state="disabled"
        )
        self.pause_button.pack(side="left", padx=5, pady=10)

        # 取消按钮
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.cancel_download,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=5, pady=10)

        # 清空配置按钮
        clear_button = ctk.CTkButton(
            button_frame,
            text="清空配置",
            command=self.clear_config
        )
        clear_button.pack(side="left", padx=5, pady=10)

        # 打开下载文件夹按钮
        open_folder_button = ctk.CTkButton(
            button_frame,
            text="打开文件夹",
            command=self.open_download_folder
        )
        open_folder_button.pack(side="right", padx=10, pady=10)

    def load_config(self):
        """加载配置"""
        try:
            # 加载下载配置
            download_config = self.config_manager.load_download_config()

            # 加载最近使用的频道
            recent_channels = self.config_manager.get_recent_channels()
            if recent_channels:
                channel_values = [f"{ch['name']} ({ch['id']})" for ch in recent_channels]
                self.recent_channel_combo.configure(values=channel_values)

            # 加载默认设置
            default_settings = download_config.get("default_settings", {})

            if default_settings.get("start_message_id"):
                self.start_id_entry.insert(0, str(default_settings["start_message_id"]))

            if default_settings.get("message_count"):
                self.count_entry.insert(0, str(default_settings["message_count"]))

            # 加载下载路径（优先使用下载配置中的路径）
            download_path = default_settings.get("download_path")
            if not download_path:
                # 如果下载配置中没有路径，则使用应用配置中的路径
                app_config = self.config_manager.load_app_config()
                download_path = app_config.get("download", {}).get("default_path", "./downloads")
            self.path_entry.insert(0, download_path)

            # 设置媒体类型
            media_types = default_settings.get("media_types", [])
            for media_type, var in self.media_type_vars.items():
                var.set(media_type.value in media_types)

            self.include_media_var.set(default_settings.get("include_media", True))
            self.include_text_var.set(default_settings.get("include_text", True))

            self.logger.info("下载配置加载完成")

        except Exception as e:
            self.logger.error(f"加载下载配置失败: {e}")

    def on_recent_channel_selected(self, value: str):
        """选择最近使用的频道"""
        try:
            # 解析频道ID
            if "(" in value and ")" in value:
                channel_id = value.split("(")[-1].split(")")[0]
                self.channel_entry.delete(0, tk.END)
                self.channel_entry.insert(0, channel_id)
        except Exception as e:
            self.logger.error(f"选择频道失败: {e}")

    def browse_download_path(self):
        """浏览下载路径"""
        try:
            from tkinter import filedialog

            folder_path = filedialog.askdirectory(
                title="选择下载文件夹",
                initialdir=self.path_entry.get() or "./downloads"
            )

            if folder_path:
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, folder_path)

        except Exception as e:
            self.logger.error(f"浏览文件夹失败: {e}")

    def start_download(self):
        """开始下载"""
        try:
            # 验证输入
            if not self.validate_input():
                return

            # 创建下载配置
            config = self.create_download_config()
            if not config:
                return

            # 检查客户端管理器
            if not self.get_client_manager():
                self.show_error("请先配置并登录客户端")
                return

            # 创建下载管理器
            if not self.download_manager:
                client_manager = self.get_client_manager()
                self.download_manager = DownloadManager(client_manager, self.on_download_manager_event)

            # 更新UI状态
            self.start_button.configure(state="disabled")
            self.pause_button.configure(state="normal")
            self.cancel_button.configure(state="normal")

            # 保存到最近使用的频道
            channel_id = config.channel_id
            self.config_manager.add_recent_channel(channel_id)

            # 保存当前设置为默认设置
            self.save_current_settings()

            # 简化下载启动逻辑，避免创建新的事件循环
            def start_download_task():
                try:
                    # 生成任务ID
                    import uuid
                    self.current_task_id = str(uuid.uuid4())
                    self.logger.info(f"下载任务已创建: {self.current_task_id}")

                    # 下载管理器会在自己的异步环境中处理下载
                    # 这里只是启动下载任务，不需要等待完成
                    self.logger.info("下载任务已提交给下载管理器")

                except Exception as e:
                    self.logger.error(f"启动下载任务失败: {e}")
                    # 在主线程中显示错误
                    if hasattr(self, 'parent') and hasattr(self.parent, 'after'):
                        self.parent.after(0, lambda: self.show_error(f"启动下载失败: {e}"))

            # 在后台线程中启动下载任务
            threading.Thread(target=start_download_task, daemon=True).start()

        except Exception as e:
            self.logger.error(f"开始下载失败: {e}")
            self.show_error(f"开始下载失败: {e}")

    def pause_download(self):
        """暂停/恢复下载"""
        # TODO: 实现暂停/恢复功能
        pass

    def cancel_download(self):
        """取消下载"""
        try:
            if self.download_manager and self.current_task_id:
                success = self.download_manager.cancel_task(self.current_task_id)
                if success:
                    self.logger.info("下载任务已取消")
                    self.reset_ui_state()
                else:
                    self.show_error("取消下载失败")
        except Exception as e:
            self.logger.error(f"取消下载失败: {e}")
            self.show_error(f"取消下载失败: {e}")

    def clear_config(self):
        """清空配置"""
        try:
            self.channel_entry.delete(0, tk.END)
            self.start_id_entry.delete(0, tk.END)
            self.count_entry.delete(0, tk.END)
            self.max_size_entry.delete(0, tk.END)

            # 重置复选框
            for var in self.media_type_vars.values():
                var.set(True)

            self.include_media_var.set(True)
            self.include_text_var.set(True)

            # 重置进度
            self.reset_progress_display()

        except Exception as e:
            self.logger.error(f"清空配置失败: {e}")

    def save_current_settings(self):
        """保存当前设置为默认设置"""
        try:
            # 获取当前设置
            settings = {
                "start_message_id": int(self.start_id_entry.get().strip() or "1"),
                "message_count": int(self.count_entry.get().strip() or "100"),
                "download_path": self.path_entry.get().strip() or "./downloads",
                "include_media": self.include_media_var.get(),
                "include_text": self.include_text_var.get(),
                "media_types": [
                    media_type.value for media_type, var in self.media_type_vars.items()
                    if var.get()
                ],
                "max_file_size": None
            }

            # 处理最大文件大小
            max_size_text = self.max_size_entry.get().strip()
            if max_size_text:
                try:
                    settings["max_file_size"] = int(max_size_text)
                except ValueError:
                    pass  # 忽略无效的文件大小

            # 保存设置
            success = self.config_manager.save_download_settings(settings)
            if success:
                self.logger.info("下载设置已保存")
            else:
                self.logger.warning("保存下载设置失败")

        except Exception as e:
            self.logger.error(f"保存当前设置失败: {e}")

    def open_download_folder(self):
        """打开下载文件夹"""
        try:
            import os
            import subprocess
            import platform

            folder_path = self.path_entry.get() or "./downloads"

            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)

            # 根据操作系统打开文件夹
            system = platform.system()
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])

        except Exception as e:
            self.logger.error(f"打开文件夹失败: {e}")
            self.show_error(f"打开文件夹失败: {e}")

    def validate_input(self) -> bool:
        """验证输入"""
        try:
            # 验证频道ID
            channel_id = self.channel_entry.get().strip()
            if not channel_id:
                self.show_error("请输入频道ID")
                return False

            # 验证起始消息ID
            start_id_text = self.start_id_entry.get().strip()
            if start_id_text:
                try:
                    start_id = int(start_id_text)
                    if start_id < 1:
                        self.show_error("起始消息ID必须大于0")
                        return False
                except ValueError:
                    self.show_error("起始消息ID必须为数字")
                    return False

            # 验证消息数量
            count_text = self.count_entry.get().strip()
            if not count_text:
                self.show_error("请输入消息数量")
                return False

            try:
                count = int(count_text)
                if count < 1 or count > 1000:
                    self.show_error("消息数量必须在1-1000之间")
                    return False
            except ValueError:
                self.show_error("消息数量必须为数字")
                return False

            # 验证下载路径
            download_path = self.path_entry.get().strip()
            if not download_path:
                self.show_error("请选择下载路径")
                return False

            # 验证最大文件大小
            max_size_text = self.max_size_entry.get().strip()
            if max_size_text:
                try:
                    max_size_mb = float(max_size_text)
                    if max_size_mb <= 0:
                        self.show_error("最大文件大小必须大于0")
                        return False

                    # 检查是否超过50GB限制（51200MB）
                    max_allowed_mb = 50 * 1024  # 50GB = 51200MB
                    if max_size_mb > max_allowed_mb:
                        self.show_error(f"最大文件大小不能超过50GB（{max_allowed_mb}MB），您输入了{max_size_mb:.1f}MB")
                        return False

                except ValueError:
                    self.show_error("最大文件大小必须为数字")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"验证输入失败: {e}")
            self.show_error(f"验证输入失败: {e}")
            return False

    def create_download_config(self) -> Optional[DownloadConfig]:
        """创建下载配置"""
        try:
            # 获取基本配置
            channel_id = self.channel_entry.get().strip()
            start_id = int(self.start_id_entry.get().strip() or "1")
            count = int(self.count_entry.get().strip())
            download_path = self.path_entry.get().strip()

            # 获取媒体类型
            selected_media_types = []
            for media_type, var in self.media_type_vars.items():
                if var.get():
                    selected_media_types.append(media_type)

            # 获取最大文件大小
            max_size = None
            max_size_text = self.max_size_entry.get().strip()
            if max_size_text:
                try:
                    max_size_mb = float(max_size_text)
                    max_size = int(max_size_mb * 1024 * 1024)  # 转换为字节

                    # 检查是否超过50GB限制
                    max_allowed_gb = 50
                    max_allowed_bytes = max_allowed_gb * 1024 * 1024 * 1024
                    if max_size > max_allowed_bytes:
                        self.show_error(f"最大文件大小不能超过{max_allowed_gb}GB（您输入了{max_size_mb:.1f}MB）")
                        return None

                except ValueError:
                    self.show_error("最大文件大小必须为有效数字")
                    return None

            # 创建配置对象
            config = DownloadConfig(
                channel_id=channel_id,
                start_message_id=start_id,
                message_count=count,
                download_path=download_path,
                include_media=self.include_media_var.get(),
                include_text=self.include_text_var.get(),
                media_types=selected_media_types,
                max_file_size=max_size
            )

            return config

        except ValueError as e:
            # 处理Pydantic验证错误
            error_msg = str(e)
            if "最大文件大小不能超过" in error_msg:
                self.show_error("文件大小超出限制：最大支持50GB，请输入较小的值")
            else:
                self.show_error(f"配置验证失败: {error_msg}")
            self.logger.error(f"配置验证失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"创建下载配置失败: {e}")
            self.show_error(f"创建下载配置失败: {e}")
            return None

    def get_client_manager(self):
        """获取客户端管理器"""
        try:
            # 从主窗口引用获取客户端管理器
            if self.main_window and hasattr(self.main_window, 'client_config_frame'):
                return self.main_window.client_config_frame.client_manager
            return None
        except Exception as e:
            self.logger.error(f"获取客户端管理器失败: {e}")
            return None

    def reset_ui_state(self):
        """重置UI状态"""
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.current_task_id = None

    def reset_progress_display(self):
        """重置进度显示"""
        self.overall_progress.set(0)
        self.progress_label.configure(text="等待开始下载...")
        self.message_count_label.configure(text="消息: 0/0")
        self.file_count_label.configure(text="文件: 0/0")
        self.current_file_label.configure(text="当前文件: 无")
        self.download_size_label.configure(text="大小: 0 B / 0 B")
        self.speed_label.configure(text="速度: 0 B/s")
        self.eta_label.configure(text="剩余时间: 未知")

    def update_progress_display(self, progress_data: dict):
        """更新进度显示"""
        try:
            # 更新总体进度条
            progress_percentage = progress_data.get("progress_percentage", 0)
            self.overall_progress.set(progress_percentage / 100)

            # 更新进度文本
            downloaded = progress_data.get("downloaded_messages", 0)
            total = progress_data.get("total_messages", 0)
            self.progress_label.configure(text=f"进度: {progress_percentage:.1f}% ({downloaded}/{total})")

            # 更新消息计数
            self.message_count_label.configure(text=f"消息: {downloaded}/{total}")

            # 更新文件计数
            downloaded_files = progress_data.get("downloaded_files", 0)
            total_files = progress_data.get("total_files", 0)
            self.file_count_label.configure(text=f"文件: {downloaded_files}/{total_files}")

            # 更新当前文件
            current_file = progress_data.get("current_file", "无")
            if len(current_file) > 50:
                current_file = "..." + current_file[-47:]
            self.current_file_label.configure(text=f"当前文件: {current_file}")

            # 更新下载大小
            downloaded_size = progress_data.get("downloaded_size", 0)
            total_size = progress_data.get("total_size", 0)

            def format_size(size_bytes):
                if size_bytes == 0:
                    return "0 B"
                units = ["B", "KB", "MB", "GB"]
                unit_index = 0
                size = float(size_bytes)
                while size >= 1024 and unit_index < len(units) - 1:
                    size /= 1024
                    unit_index += 1
                return f"{size:.2f} {units[unit_index]}"

            self.download_size_label.configure(
                text=f"大小: {format_size(downloaded_size)} / {format_size(total_size)}"
            )

            # 更新下载速度
            speed = progress_data.get("download_speed", 0)
            self.speed_label.configure(text=f"速度: {format_size(speed)}/s")

            # 更新剩余时间
            eta = progress_data.get("eta")
            if eta is not None:
                if eta < 60:
                    eta_text = f"{eta}秒"
                elif eta < 3600:
                    minutes = eta // 60
                    seconds = eta % 60
                    eta_text = f"{minutes}分{seconds}秒"
                else:
                    hours = eta // 3600
                    minutes = (eta % 3600) // 60
                    eta_text = f"{hours}小时{minutes}分钟"
            else:
                eta_text = "未知"

            self.eta_label.configure(text=f"剩余时间: {eta_text}")

        except Exception as e:
            self.logger.error(f"更新进度显示失败: {e}")

    def on_download_event(self, event: BaseEvent):
        """处理下载事件"""
        try:
            # 在主线程中更新UI
            if self.parent:
                self.parent.after(0, self._update_ui_from_download_event, event)
            else:
                self.logger.warning("父窗口对象不存在，无法更新UI")
        except Exception as e:
            self.logger.error(f"处理下载事件失败: {e}")

    def _update_ui_from_download_event(self, event: BaseEvent):
        """从下载事件更新UI"""
        try:
            if event.event_type == EventType.DOWNLOAD_STARTED:
                self.progress_label.configure(text="开始下载...")

            elif event.event_type == EventType.DOWNLOAD_PROGRESS:
                if hasattr(event, 'progress_data') and event.progress_data:
                    self.update_progress_display(event.progress_data)

            elif event.event_type == EventType.DOWNLOAD_COMPLETED:
                self.progress_label.configure(text="下载完成！")
                self.reset_ui_state()
                self.show_success("下载完成")

            elif event.event_type == EventType.DOWNLOAD_FAILED:
                self.progress_label.configure(text="下载失败")
                self.reset_ui_state()
                error_msg = event.data.get("error", "未知错误") if event.data else "未知错误"
                self.show_error(f"下载失败: {error_msg}")

            elif event.event_type == EventType.DOWNLOAD_FILE_COMPLETED:
                if event.data:
                    filename = event.data.get("filename", "")
                    self.logger.info(f"文件下载完成: {filename}")

        except Exception as e:
            self.logger.error(f"更新下载UI失败: {e}")

    def on_download_manager_event(self, event: BaseEvent):
        """下载管理器事件回调"""
        # 转发到事件管理器
        self.event_manager.emit(event)

    def show_success(self, message: str):
        """显示成功消息"""
        self.logger.info(message)
        # TODO: 可以实现一个消息提示框

    def show_error(self, message: str):
        """显示错误消息"""
        self.logger.error(message)
        # TODO: 可以实现一个错误提示框
