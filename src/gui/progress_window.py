#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
进度窗口

提供实时下载进度和任务状态显示
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# 修改为绝对导入
from utils.logger import get_logger


class ProgressWindow:
    """进度窗口类"""
    
    def __init__(self, parent: tk.Tk):
        """
        初始化进度窗口
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        self.logger = get_logger(f"{__name__}.ProgressWindow")
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("下载进度")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # 设置窗口图标
        try:
            # self.window.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # 进度数据
        self.progress_data: Dict[str, Dict[str, Any]] = {}
        self.overall_stats = {
            "total_files": 0,
            "completed_files": 0,
            "failed_files": 0,
            "total_size": 0,
            "downloaded_size": 0,
            "download_speed": 0.0,
            "start_time": time.time(),
            "estimated_time": 0
        }
        
        # 更新定时器
        self.update_timer = None
        self.update_interval = 1000  # 1秒
        
        # 创建GUI
        self.create_widgets()
        self.setup_bindings()
        
        # 窗口居中
        self.center_window()
        
        # 启动更新
        self.start_update_timer()
        
        self.logger.info("进度窗口初始化完成")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置窗口的权重
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 创建总体进度区域
        self.create_overall_progress(main_frame)
        
        # 创建统计信息区域
        self.create_statistics(main_frame)
        
        # 创建任务进度列表
        self.create_progress_list(main_frame)
        
        # 创建控制按钮
        self.create_control_buttons(main_frame)
    
    def create_overall_progress(self, parent):
        """创建总体进度区域"""
        progress_frame = ttk.LabelFrame(parent, text="总体进度", padding="10")
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        # 总体进度条
        self.overall_progress_var = tk.DoubleVar()
        self.overall_progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.overall_progress_var,
            maximum=100,
            length=400
        )
        self.overall_progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 进度文本
        self.overall_progress_text = ttk.Label(progress_frame, text="0% (0/0)")
        self.overall_progress_text.grid(row=1, column=0, sticky=tk.W)
        
        # 速度和时间信息
        info_frame = ttk.Frame(progress_frame)
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        info_frame.columnconfigure(2, weight=1)
        
        # 下载速度
        ttk.Label(info_frame, text="下载速度:").grid(row=0, column=0, sticky=tk.W)
        self.speed_label = ttk.Label(info_frame, text="0 KB/s")
        self.speed_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        # 剩余时间
        ttk.Label(info_frame, text="剩余时间:").grid(row=0, column=2, sticky=tk.W)
        self.eta_label = ttk.Label(info_frame, text="计算中...")
        self.eta_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        # 已用时间
        ttk.Label(info_frame, text="已用时间:").grid(row=0, column=4, sticky=tk.W)
        self.elapsed_label = ttk.Label(info_frame, text="00:00:00")
        self.elapsed_label.grid(row=0, column=5, sticky=tk.W, padx=(5, 0))
    
    def create_statistics(self, parent):
        """创建统计信息区域"""
        stats_frame = ttk.LabelFrame(parent, text="统计信息", padding="10")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建两列布局
        left_frame = ttk.Frame(stats_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.N))
        
        right_frame = ttk.Frame(stats_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.N), padx=(50, 0))
        
        # 左列统计
        ttk.Label(left_frame, text="总文件数:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.total_files_label = ttk.Label(left_frame, text="0")
        self.total_files_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(left_frame, text="已完成:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.completed_files_label = ttk.Label(left_frame, text="0")
        self.completed_files_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(left_frame, text="失败:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.failed_files_label = ttk.Label(left_frame, text="0")
        self.failed_files_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 右列统计
        ttk.Label(right_frame, text="总大小:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.total_size_label = ttk.Label(right_frame, text="0 B")
        self.total_size_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(right_frame, text="已下载:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.downloaded_size_label = ttk.Label(right_frame, text="0 B")
        self.downloaded_size_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        ttk.Label(right_frame, text="成功率:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.success_rate_label = ttk.Label(right_frame, text="0%")
        self.success_rate_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
    
    def create_progress_list(self, parent):
        """创建任务进度列表"""
        list_frame = ttk.LabelFrame(parent, text="任务进度", padding="10")
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ("任务ID", "文件名", "状态", "进度", "大小", "速度", "剩余时间")
        self.progress_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列头
        self.progress_tree.heading("任务ID", text="任务ID")
        self.progress_tree.heading("文件名", text="文件名")
        self.progress_tree.heading("状态", text="状态")
        self.progress_tree.heading("进度", text="进度")
        self.progress_tree.heading("大小", text="大小")
        self.progress_tree.heading("速度", text="速度")
        self.progress_tree.heading("剩余时间", text="剩余时间")
        
        # 设置列宽
        self.progress_tree.column("任务ID", width=80, minwidth=60)
        self.progress_tree.column("文件名", width=200, minwidth=150)
        self.progress_tree.column("状态", width=80, minwidth=60)
        self.progress_tree.column("进度", width=80, minwidth=60)
        self.progress_tree.column("大小", width=80, minwidth=60)
        self.progress_tree.column("速度", width=80, minwidth=60)
        self.progress_tree.column("剩余时间", width=80, minwidth=60)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.progress_tree.yview)
        self.progress_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.progress_tree.xview)
        self.progress_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.progress_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置状态颜色
        self.progress_tree.tag_configure("PENDING", foreground="gray")
        self.progress_tree.tag_configure("RUNNING", foreground="blue")
        self.progress_tree.tag_configure("COMPLETED", foreground="green")
        self.progress_tree.tag_configure("FAILED", foreground="red")
        self.progress_tree.tag_configure("CANCELLED", foreground="orange")
        
        # 右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="查看详情", command=self.show_task_details)
        self.context_menu.add_command(label="重试任务", command=self.retry_task)
        self.context_menu.add_command(label="取消任务", command=self.cancel_task)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制任务ID", command=self.copy_task_id)
        self.context_menu.add_command(label="复制文件名", command=self.copy_filename)
        
        # 绑定右键菜单
        self.progress_tree.bind("<Button-3>", self.show_context_menu)
    
    def create_control_buttons(self, parent):
        """创建控制按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        # 按钮
        ttk.Button(button_frame, text="刷新", command=self.refresh_progress).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="暂停全部", command=self.pause_all).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="恢复全部", command=self.resume_all).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="重试失败", command=self.retry_failed).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(button_frame, text="清空完成", command=self.clear_completed).grid(row=0, column=4, padx=(0, 5))
        
        # 右侧按钮
        ttk.Button(button_frame, text="导出报告", command=self.export_report).grid(row=0, column=5, padx=(20, 5))
        ttk.Button(button_frame, text="关闭", command=self.window.destroy).grid(row=0, column=6, padx=(0, 0))
    
    def setup_bindings(self):
        """设置事件绑定"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 双击查看详情
        self.progress_tree.bind("<Double-1>", self.on_double_click)
        
        # 键盘快捷键
        self.window.bind('<F5>', lambda e: self.refresh_progress())
        self.window.bind('<Control-r>', lambda e: self.retry_failed())
        self.window.bind('<Control-c>', lambda e: self.copy_task_id())
        self.window.bind('<Delete>', lambda e: self.clear_completed())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def start_update_timer(self):
        """启动更新定时器"""
        self.update_timer = self.window.after(self.update_interval, self.update_loop)
    
    def update_loop(self):
        """更新循环"""
        try:
            self.update_progress()
            self.update_overall_stats()
            self.update_timer = self.window.after(self.update_interval, self.update_loop)
        except:
            pass
    
    def stop_update_timer(self):
        """停止更新定时器"""
        if self.update_timer:
            self.window.after_cancel(self.update_timer)
            self.update_timer = None
    
    def update_progress(self):
        """更新进度显示"""
        # 这里可以从任务管理器获取真实的进度数据
        # 目前使用模拟数据
        pass
    
    def update_overall_stats(self):
        """更新总体统计"""
        # 计算总体进度
        if self.overall_stats["total_files"] > 0:
            progress = (self.overall_stats["completed_files"] / self.overall_stats["total_files"]) * 100
            self.overall_progress_var.set(progress)
            self.overall_progress_text.config(
                text=f"{progress:.1f}% ({self.overall_stats['completed_files']}/{self.overall_stats['total_files']})"
            )
        else:
            self.overall_progress_var.set(0)
            self.overall_progress_text.config(text="0% (0/0)")
        
        # 更新统计标签
        self.total_files_label.config(text=str(self.overall_stats["total_files"]))
        self.completed_files_label.config(text=str(self.overall_stats["completed_files"]))
        self.failed_files_label.config(text=str(self.overall_stats["failed_files"]))
        
        self.total_size_label.config(text=self.format_size(self.overall_stats["total_size"]))
        self.downloaded_size_label.config(text=self.format_size(self.overall_stats["downloaded_size"]))
        
        # 成功率
        if self.overall_stats["total_files"] > 0:
            success_rate = (self.overall_stats["completed_files"] / self.overall_stats["total_files"]) * 100
            self.success_rate_label.config(text=f"{success_rate:.1f}%")
        else:
            self.success_rate_label.config(text="0%")
        
        # 下载速度
        speed_text = self.format_speed(self.overall_stats["download_speed"])
        self.speed_label.config(text=speed_text)
        
        # 已用时间
        elapsed = time.time() - self.overall_stats["start_time"]
        elapsed_text = self.format_time(elapsed)
        self.elapsed_label.config(text=elapsed_text)
        
        # 剩余时间
        if self.overall_stats["download_speed"] > 0:
            remaining_size = self.overall_stats["total_size"] - self.overall_stats["downloaded_size"]
            eta = remaining_size / self.overall_stats["download_speed"]
            eta_text = self.format_time(eta)
            self.eta_label.config(text=eta_text)
        else:
            self.eta_label.config(text="计算中...")
    
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
    
    def format_speed(self, speed_bytes_per_sec: float) -> str:
        """格式化下载速度"""
        if speed_bytes_per_sec == 0:
            return "0 B/s"
        
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        unit_index = 0
        speed = float(speed_bytes_per_sec)
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    def format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 0:
            return "00:00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def add_task_progress(self, task_id: str, filename: str, status: str, progress: float = 0.0, 
                         total_size: int = 0, downloaded_size: int = 0, speed: float = 0.0):
        """添加任务进度"""
        # 计算剩余时间
        if speed > 0:
            remaining_size = total_size - downloaded_size
            eta = remaining_size / speed
            eta_text = self.format_time(eta)
        else:
            eta_text = "未知"
        
        # 检查是否已存在
        existing_item = None
        for item in self.progress_tree.get_children():
            if self.progress_tree.item(item, "values")[0] == task_id:
                existing_item = item
                break
        
        values = (
            task_id,
            filename,
            status,
            f"{progress:.1f}%",
            self.format_size(total_size),
            self.format_speed(speed),
            eta_text
        )
        
        if existing_item:
            # 更新现有项目
            self.progress_tree.item(existing_item, values=values)
            self.progress_tree.item(existing_item, tags=(status,))
        else:
            # 添加新项目
            item = self.progress_tree.insert("", "end", values=values)
            self.progress_tree.item(item, tags=(status,))
        
        # 更新进度数据
        self.progress_data[task_id] = {
            "filename": filename,
            "status": status,
            "progress": progress,
            "total_size": total_size,
            "downloaded_size": downloaded_size,
            "speed": speed,
            "eta": eta_text
        }
    
    def update_task_progress(self, task_id: str, **kwargs):
        """更新任务进度"""
        if task_id in self.progress_data:
            self.progress_data[task_id].update(kwargs)
            
            # 更新显示
            data = self.progress_data[task_id]
            self.add_task_progress(
                task_id,
                data["filename"],
                data["status"],
                data["progress"],
                data["total_size"],
                data["downloaded_size"],
                data["speed"]
            )
    
    def remove_task_progress(self, task_id: str):
        """移除任务进度"""
        if task_id in self.progress_data:
            del self.progress_data[task_id]
        
        # 从树形视图中移除
        for item in self.progress_tree.get_children():
            if self.progress_tree.item(item, "values")[0] == task_id:
                self.progress_tree.delete(item)
                break
    
    def refresh_progress(self):
        """刷新进度"""
        # 这里可以从任务管理器重新获取进度数据
        pass
    
    def pause_all(self):
        """暂停全部任务"""
        messagebox.showinfo("暂停全部", "暂停全部任务功能将在后续版本中实现")
    
    def resume_all(self):
        """恢复全部任务"""
        messagebox.showinfo("恢复全部", "恢复全部任务功能将在后续版本中实现")
    
    def retry_failed(self):
        """重试失败任务"""
        failed_count = sum(1 for data in self.progress_data.values() if data["status"] == "FAILED")
        if failed_count > 0:
            if messagebox.askyesno("重试失败", f"确定要重试 {failed_count} 个失败任务吗？"):
                messagebox.showinfo("重试失败", "重试失败任务功能将在后续版本中实现")
        else:
            messagebox.showinfo("重试失败", "没有失败的任务")
    
    def clear_completed(self):
        """清空已完成任务"""
        completed_count = sum(1 for data in self.progress_data.values() if data["status"] == "COMPLETED")
        if completed_count > 0:
            if messagebox.askyesno("清空完成", f"确定要清空 {completed_count} 个已完成任务吗？"):
                # 移除已完成的任务
                completed_tasks = [task_id for task_id, data in self.progress_data.items() if data["status"] == "COMPLETED"]
                for task_id in completed_tasks:
                    self.remove_task_progress(task_id)
        else:
            messagebox.showinfo("清空完成", "没有已完成的任务")
    
    def export_report(self):
        """导出报告"""
        messagebox.showinfo("导出报告", "导出报告功能将在后续版本中实现")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择点击的项目
        item = self.progress_tree.identify_row(event.y)
        if item:
            self.progress_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_double_click(self, event):
        """双击事件"""
        self.show_task_details()
    
    def show_task_details(self):
        """显示任务详情"""
        selected = self.progress_tree.selection()
        if selected:
            item = selected[0]
            values = self.progress_tree.item(item, "values")
            task_id = values[0]
            
            if task_id in self.progress_data:
                data = self.progress_data[task_id]
                
                details = f"""任务ID: {task_id}
文件名: {data['filename']}
状态: {data['status']}
进度: {data['progress']:.1f}%
总大小: {self.format_size(data['total_size'])}
已下载: {self.format_size(data['downloaded_size'])}
下载速度: {self.format_speed(data['speed'])}
剩余时间: {data['eta']}"""
                
                # 创建详情窗口
                detail_window = tk.Toplevel(self.window)
                detail_window.title("任务详情")
                detail_window.geometry("400x300")
                
                # 文本框
                text_widget = tk.Text(detail_window, wrap=tk.WORD, padx=10, pady=10)
                text_widget.pack(fill=tk.BOTH, expand=True)
                text_widget.insert(tk.END, details)
                text_widget.config(state=tk.DISABLED)
    
    def retry_task(self):
        """重试任务"""
        selected = self.progress_tree.selection()
        if selected:
            item = selected[0]
            values = self.progress_tree.item(item, "values")
            task_id = values[0]
            
            messagebox.showinfo("重试任务", f"重试任务 {task_id} 功能将在后续版本中实现")
    
    def cancel_task(self):
        """取消任务"""
        selected = self.progress_tree.selection()
        if selected:
            item = selected[0]
            values = self.progress_tree.item(item, "values")
            task_id = values[0]
            
            if messagebox.askyesno("取消任务", f"确定要取消任务 {task_id} 吗？"):
                messagebox.showinfo("取消任务", f"取消任务 {task_id} 功能将在后续版本中实现")
    
    def copy_task_id(self):
        """复制任务ID"""
        selected = self.progress_tree.selection()
        if selected:
            item = selected[0]
            values = self.progress_tree.item(item, "values")
            task_id = values[0]
            
            self.window.clipboard_clear()
            self.window.clipboard_append(task_id)
            messagebox.showinfo("复制任务ID", f"任务ID {task_id} 已复制到剪贴板")
    
    def copy_filename(self):
        """复制文件名"""
        selected = self.progress_tree.selection()
        if selected:
            item = selected[0]
            values = self.progress_tree.item(item, "values")
            filename = values[1]
            
            self.window.clipboard_clear()
            self.window.clipboard_append(filename)
            messagebox.showinfo("复制文件名", f"文件名 {filename} 已复制到剪贴板")
    
    def on_closing(self):
        """窗口关闭事件"""
        self.stop_update_timer()
        self.window.destroy()
    
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