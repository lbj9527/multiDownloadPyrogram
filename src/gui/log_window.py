#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志窗口

提供日志显示和管理功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import threading
import queue
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

# 修改为绝对导入
from utils.logger import get_logger


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到GUI"""
    
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录"""
        try:
            log_entry = self.format(record)
            self.log_queue.put((record.levelname, log_entry, record.created))
        except Exception:
            self.handleError(record)


class LogWindow:
    """日志窗口类"""
    
    def __init__(self, parent: tk.Tk):
        """
        初始化日志窗口
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        self.logger = get_logger(f"{__name__}.LogWindow")
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("日志窗口")
        self.window.geometry("900x600")
        self.window.resizable(True, True)
        
        # 设置窗口图标
        try:
            # self.window.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # 日志队列和处理器
        self.log_queue = queue.Queue()
        self.log_handler = LogHandler(self.log_queue)
        self.log_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # 日志记录
        self.log_records: List[Dict[str, Any]] = []
        self.max_log_records = 1000
        self.auto_scroll = True
        self.filter_level = "DEBUG"
        
        # 创建GUI
        self.create_widgets()
        self.setup_bindings()
        
        # 窗口居中
        self.center_window()
        
        # 启动日志处理
        self.start_log_processing()
        
        # 添加日志处理器
        self.add_log_handler()
        
        self.logger.info("日志窗口初始化完成")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置窗口的权重
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 创建工具栏
        self.create_toolbar(main_frame)
        
        # 创建日志显示区域
        self.create_log_display(main_frame)
        
        # 创建状态栏
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 日志级别过滤
        ttk.Label(toolbar, text="日志级别:").grid(row=0, column=0, padx=(0, 5))
        self.level_var = tk.StringVar(value="DEBUG")
        level_combo = ttk.Combobox(toolbar, textvariable=self.level_var, 
                                  values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                  width=10)
        level_combo.grid(row=0, column=1, padx=(0, 10))
        level_combo.bind("<<ComboboxSelected>>", self.on_level_change)
        
        # 搜索框
        ttk.Label(toolbar, text="搜索:").grid(row=0, column=2, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        search_entry.grid(row=0, column=3, padx=(0, 5))
        search_entry.bind("<KeyRelease>", self.on_search_change)
        
        # 按钮
        ttk.Button(toolbar, text="清空日志", command=self.clear_logs).grid(row=0, column=4, padx=(10, 5))
        ttk.Button(toolbar, text="刷新", command=self.refresh_logs).grid(row=0, column=5, padx=(0, 5))
        ttk.Button(toolbar, text="保存日志", command=self.save_logs).grid(row=0, column=6, padx=(0, 5))
        
        # 自动滚动复选框
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="自动滚动", variable=self.auto_scroll_var,
                       command=self.on_auto_scroll_change).grid(row=0, column=7, padx=(10, 0))
    
    def create_log_display(self, parent):
        """创建日志显示区域"""
        log_frame = ttk.Frame(parent)
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ("时间", "级别", "模块", "消息")
        self.log_tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=20)
        
        # 设置列头
        self.log_tree.heading("时间", text="时间")
        self.log_tree.heading("级别", text="级别")
        self.log_tree.heading("模块", text="模块")
        self.log_tree.heading("消息", text="消息")
        
        # 设置列宽
        self.log_tree.column("时间", width=150, minwidth=120)
        self.log_tree.column("级别", width=80, minwidth=60)
        self.log_tree.column("模块", width=200, minwidth=150)
        self.log_tree.column("消息", width=400, minwidth=300)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_tree.xview)
        self.log_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.log_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置级别颜色
        self.log_tree.tag_configure("DEBUG", foreground="gray")
        self.log_tree.tag_configure("INFO", foreground="black")
        self.log_tree.tag_configure("WARNING", foreground="orange")
        self.log_tree.tag_configure("ERROR", foreground="red")
        self.log_tree.tag_configure("CRITICAL", foreground="darkred", background="lightpink")
        
        # 右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="复制消息", command=self.copy_message)
        self.context_menu.add_command(label="复制行", command=self.copy_line)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="查看详情", command=self.show_details)
        self.context_menu.add_command(label="过滤此模块", command=self.filter_module)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="清空日志", command=self.clear_logs)
        
        # 绑定右键菜单
        self.log_tree.bind("<Button-3>", self.show_context_menu)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 状态标签
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 日志统计
        self.log_count_var = tk.StringVar()
        self.log_count_var.set("日志数量: 0")
        self.log_count_label = ttk.Label(status_frame, textvariable=self.log_count_var)
        self.log_count_label.grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
        
        # 配置状态栏权重
        status_frame.columnconfigure(1, weight=1)
    
    def setup_bindings(self):
        """设置事件绑定"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 双击查看详情
        self.log_tree.bind("<Double-1>", self.on_double_click)
        
        # 键盘快捷键
        self.window.bind('<Control-c>', lambda e: self.copy_line())
        self.window.bind('<Control-s>', lambda e: self.save_logs())
        self.window.bind('<Control-f>', lambda e: self.focus_search())
        self.window.bind('<Delete>', lambda e: self.clear_logs())
        self.window.bind('<F5>', lambda e: self.refresh_logs())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def start_log_processing(self):
        """启动日志处理"""
        self.process_logs()
    
    def process_logs(self):
        """处理日志队列"""
        try:
            while True:
                try:
                    level, message, timestamp = self.log_queue.get_nowait()
                    self.add_log_record(level, message, timestamp)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"处理日志时发生错误: {e}")
        
        # 定期调用
        self.window.after(100, self.process_logs)
    
    def add_log_record(self, level: str, message: str, timestamp: float):
        """添加日志记录"""
        # 解析消息
        parts = message.split(" - ", 3)
        if len(parts) >= 4:
            time_str = parts[0]
            module = parts[1]
            level = parts[2]
            content = parts[3]
        else:
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            module = "unknown"
            content = message
        
        # 添加到记录列表
        record = {
            "timestamp": timestamp,
            "time_str": time_str,
            "level": level,
            "module": module,
            "content": content,
            "full_message": message
        }
        
        self.log_records.append(record)
        
        # 限制记录数量
        if len(self.log_records) > self.max_log_records:
            self.log_records.pop(0)
        
        # 检查是否需要显示
        if self.should_show_record(record):
            self.add_log_to_tree(record)
        
        # 更新状态
        self.update_status()
    
    def should_show_record(self, record: Dict[str, Any]) -> bool:
        """检查是否应该显示记录"""
        # 级别过滤
        level_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        current_level_index = level_order.index(self.filter_level)
        record_level_index = level_order.index(record["level"])
        
        if record_level_index < current_level_index:
            return False
        
        # 搜索过滤
        search_text = self.search_var.get().lower()
        if search_text:
            if (search_text not in record["content"].lower() and
                search_text not in record["module"].lower()):
                return False
        
        return True
    
    def add_log_to_tree(self, record: Dict[str, Any]):
        """添加日志到树形视图"""
        item = self.log_tree.insert("", "end", values=(
            record["time_str"],
            record["level"],
            record["module"],
            record["content"]
        ))
        
        # 设置颜色
        self.log_tree.item(item, tags=(record["level"],))
        
        # 自动滚动
        if self.auto_scroll_var.get():
            self.log_tree.see(item)
    
    def update_status(self):
        """更新状态"""
        total_count = len(self.log_records)
        visible_count = len(self.log_tree.get_children())
        
        self.log_count_var.set(f"日志数量: {visible_count}/{total_count}")
        
        # 更新状态消息
        if visible_count != total_count:
            self.status_var.set(f"已过滤显示 {visible_count}/{total_count} 条日志")
        else:
            self.status_var.set("就绪")
    
    def refresh_logs(self):
        """刷新日志显示"""
        # 清空树形视图
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        
        # 重新添加符合条件的记录
        for record in self.log_records:
            if self.should_show_record(record):
                self.add_log_to_tree(record)
        
        self.update_status()
    
    def clear_logs(self):
        """清空日志"""
        if messagebox.askyesno("确认", "确定要清空所有日志吗？"):
            self.log_records.clear()
            
            # 清空树形视图
            for item in self.log_tree.get_children():
                self.log_tree.delete(item)
            
            self.update_status()
            self.status_var.set("日志已清空")
    
    def save_logs(self):
        """保存日志"""
        file_path = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for record in self.log_records:
                        f.write(f"{record['full_message']}\n")
                
                messagebox.showinfo("成功", f"日志已保存到: {file_path}")
                self.status_var.set(f"日志已保存: {file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def add_log_handler(self):
        """添加日志处理器"""
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        self.log_handler.setLevel(logging.DEBUG)
    
    def remove_log_handler(self):
        """移除日志处理器"""
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)
    
    def on_level_change(self, event):
        """日志级别改变事件"""
        self.filter_level = self.level_var.get()
        self.refresh_logs()
    
    def on_search_change(self, event):
        """搜索内容改变事件"""
        self.refresh_logs()
    
    def on_auto_scroll_change(self):
        """自动滚动改变事件"""
        self.auto_scroll = self.auto_scroll_var.get()
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择点击的项目
        item = self.log_tree.identify_row(event.y)
        if item:
            self.log_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_double_click(self, event):
        """双击事件"""
        self.show_details()
    
    def copy_message(self):
        """复制消息"""
        selected = self.log_tree.selection()
        if selected:
            item = selected[0]
            values = self.log_tree.item(item, "values")
            message = values[3]  # 消息内容
            
            self.window.clipboard_clear()
            self.window.clipboard_append(message)
            self.status_var.set("消息已复制到剪贴板")
    
    def copy_line(self):
        """复制整行"""
        selected = self.log_tree.selection()
        if selected:
            item = selected[0]
            values = self.log_tree.item(item, "values")
            line = " - ".join(values)
            
            self.window.clipboard_clear()
            self.window.clipboard_append(line)
            self.status_var.set("日志行已复制到剪贴板")
    
    def show_details(self):
        """显示详情"""
        selected = self.log_tree.selection()
        if selected:
            item = selected[0]
            values = self.log_tree.item(item, "values")
            
            details = f"""时间: {values[0]}
级别: {values[1]}
模块: {values[2]}
消息: {values[3]}"""
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.window)
            detail_window.title("日志详情")
            detail_window.geometry("600x400")
            
            # 文本框
            text_widget = tk.Text(detail_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(tk.END, details)
            text_widget.config(state=tk.DISABLED)
            
            # 滚动条
            scrollbar = ttk.Scrollbar(detail_window, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def filter_module(self):
        """过滤模块"""
        selected = self.log_tree.selection()
        if selected:
            item = selected[0]
            values = self.log_tree.item(item, "values")
            module = values[2]
            
            # 设置搜索框
            self.search_var.set(module)
            self.refresh_logs()
            self.status_var.set(f"已过滤模块: {module}")
    
    def focus_search(self):
        """聚焦搜索框"""
        # 这里可以聚焦搜索框
        pass
    
    def on_closing(self):
        """窗口关闭事件"""
        self.remove_log_handler()
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