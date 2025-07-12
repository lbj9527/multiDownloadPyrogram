#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代理管理窗口

提供代理连接管理和测试功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from typing import Optional, Dict, Any, List
import time

# 修改为绝对导入
from utils.proxy_manager import ProxyManager, ProxyConfig, get_proxy_manager
from utils.logger import get_logger


class ProxyWindow:
    """代理管理窗口类"""
    
    def __init__(self, parent: tk.Tk):
        """
        初始化代理管理窗口
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        self.logger = get_logger(f"{__name__}.ProxyWindow")
        self.proxy_manager = get_proxy_manager()  # 恢复正确的初始化方式
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("代理管理")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # 设置窗口图标
        try:
            # self.window.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        # 变量
        self.is_testing = False
        self.update_timer = None
        
        # 创建GUI
        self.create_widgets()
        self.setup_bindings()
        
        # 窗口居中
        self.center_window()
        
        # 加载代理列表
        self.refresh_proxy_list()
        
        # 启动定期更新
        self.start_update_timer()
        
        self.logger.info("代理管理窗口初始化完成")
    
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
        
        # 创建代理列表
        self.create_proxy_list(main_frame)
        
        # 创建代理配置区域
        self.create_proxy_config(main_frame)
        
        # 创建按钮区域
        self.create_buttons(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 添加按钮
        ttk.Button(toolbar, text="添加代理", command=self.add_proxy).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(toolbar, text="编辑代理", command=self.edit_proxy).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(toolbar, text="删除代理", command=self.delete_proxy).grid(row=0, column=2, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(toolbar, orient=tk.VERTICAL).grid(row=0, column=3, sticky=(tk.N, tk.S), padx=10)
        
        # 测试按钮
        ttk.Button(toolbar, text="测试选中", command=self.test_selected_proxy).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(toolbar, text="测试全部", command=self.test_all_proxies).grid(row=0, column=5, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(toolbar, orient=tk.VERTICAL).grid(row=0, column=6, sticky=(tk.N, tk.S), padx=10)
        
        # 刷新按钮
        ttk.Button(toolbar, text="刷新列表", command=self.refresh_proxy_list).grid(row=0, column=7, padx=(0, 5))
        
        # 当前代理显示
        ttk.Label(toolbar, text="当前代理:").grid(row=0, column=8, padx=(20, 5))
        self.current_proxy_label = ttk.Label(toolbar, text="无", foreground="red")
        self.current_proxy_label.grid(row=0, column=9, padx=(0, 5))
    
    def create_proxy_list(self, parent):
        """创建代理列表"""
        list_frame = ttk.LabelFrame(parent, text="代理列表", padding="10")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ("名称", "协议", "主机", "端口", "状态", "响应时间", "成功率", "最后检查")
        self.proxy_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        # 设置列头
        self.proxy_tree.heading("名称", text="名称")
        self.proxy_tree.heading("协议", text="协议")
        self.proxy_tree.heading("主机", text="主机")
        self.proxy_tree.heading("端口", text="端口")
        self.proxy_tree.heading("状态", text="状态")
        self.proxy_tree.heading("响应时间", text="响应时间(ms)")
        self.proxy_tree.heading("成功率", text="成功率")
        self.proxy_tree.heading("最后检查", text="最后检查")
        
        # 设置列宽
        self.proxy_tree.column("名称", width=100, minwidth=80)
        self.proxy_tree.column("协议", width=80, minwidth=60)
        self.proxy_tree.column("主机", width=120, minwidth=100)
        self.proxy_tree.column("端口", width=60, minwidth=50)
        self.proxy_tree.column("状态", width=80, minwidth=60)
        self.proxy_tree.column("响应时间", width=100, minwidth=80)
        self.proxy_tree.column("成功率", width=80, minwidth=60)
        self.proxy_tree.column("最后检查", width=120, minwidth=100)
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proxy_tree.yview)
        self.proxy_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.proxy_tree.xview)
        self.proxy_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.proxy_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="设为当前代理", command=self.set_current_proxy)
        self.context_menu.add_command(label="测试代理", command=self.test_selected_proxy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑代理", command=self.edit_proxy)
        self.context_menu.add_command(label="删除代理", command=self.delete_proxy)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="启用代理", command=self.enable_proxy)
        self.context_menu.add_command(label="禁用代理", command=self.disable_proxy)
        
        # 绑定右键菜单
        self.proxy_tree.bind("<Button-3>", self.show_context_menu)
    
    def create_proxy_config(self, parent):
        """创建代理配置区域"""
        config_frame = ttk.LabelFrame(parent, text="代理配置", padding="10")
        config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # 代理名称
        ttk.Label(config_frame, text="名称:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.name_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 协议
        ttk.Label(config_frame, text="协议:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=2)
        self.scheme_var = tk.StringVar()
        scheme_combo = ttk.Combobox(config_frame, textvariable=self.scheme_var, values=["socks5", "socks4", "http"], width=10)
        scheme_combo.grid(row=0, column=3, sticky=tk.W, pady=2)
        
        # 主机
        ttk.Label(config_frame, text="主机:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.hostname_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.hostname_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 端口
        ttk.Label(config_frame, text="端口:").grid(row=1, column=2, sticky=tk.W, padx=(20, 5), pady=2)
        self.port_var = tk.IntVar()
        ttk.Spinbox(config_frame, from_=1, to=65535, textvariable=self.port_var, width=10).grid(row=1, column=3, sticky=tk.W, pady=2)
        
        # 用户名
        ttk.Label(config_frame, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.username_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.username_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        
        # 密码
        ttk.Label(config_frame, text="密码:").grid(row=2, column=2, sticky=tk.W, padx=(20, 5), pady=2)
        self.password_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.password_var, width=20, show="*").grid(row=2, column=3, sticky=tk.W, pady=2)
        
        # 启用复选框
        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="启用代理", variable=self.enabled_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
    
    def create_buttons(self, parent):
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        # 配置按钮
        ttk.Button(button_frame, text="保存代理", command=self.save_proxy).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="清空配置", command=self.clear_config).grid(row=0, column=1, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(button_frame, orient=tk.VERTICAL).grid(row=0, column=2, sticky=(tk.N, tk.S), padx=10)
        
        # 导入导出按钮
        ttk.Button(button_frame, text="导入代理", command=self.import_proxies).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(button_frame, text="导出代理", command=self.export_proxies).grid(row=0, column=4, padx=(0, 5))
        
        # 右侧按钮
        ttk.Button(button_frame, text="关闭", command=self.window.destroy).grid(row=0, column=5, padx=(20, 0))
    
    def setup_bindings(self):
        """设置事件绑定"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 双击编辑
        self.proxy_tree.bind("<Double-1>", self.on_double_click)
        
        # 选择变化
        self.proxy_tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        
        # 键盘快捷键
        self.window.bind('<Delete>', lambda e: self.delete_proxy())
        self.window.bind('<F5>', lambda e: self.refresh_proxy_list())
        self.window.bind('<Control-s>', lambda e: self.save_proxy())
        self.window.bind('<Control-t>', lambda e: self.test_selected_proxy())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def refresh_proxy_list(self):
        """刷新代理列表"""
        # 清空列表
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        
        # 获取代理统计信息
        stats = self.proxy_manager.get_proxy_stats()
        
        # 添加代理到列表
        for name, proxy_info in self.proxy_manager.proxies.items():
            config = proxy_info.config
            stat = stats.get(name, {})
            
            # 格式化数据
            status = stat.get("status", "unknown")
            response_time = f"{stat.get('response_time', 0) * 1000:.0f}" if stat.get('response_time') else "0"
            success_rate = f"{stat.get('success_rate', 0) * 100:.1f}%"
            last_check = time.strftime("%H:%M:%S", time.localtime(stat.get('last_check', 0))) if stat.get('last_check') else "未检查"
            
            # 状态颜色
            status_color = self.get_status_color(status)
            
            # 插入行
            item = self.proxy_tree.insert("", "end", values=(
                name,
                config.scheme,
                config.hostname,
                config.port,
                status,
                response_time,
                success_rate,
                last_check
            ))
            
            # 设置状态颜色
            self.proxy_tree.set(item, "状态", status)
            if status_color:
                self.proxy_tree.tag_configure(status, foreground=status_color)
                self.proxy_tree.item(item, tags=(status,))
        
        # 更新当前代理显示
        current_proxy = self.proxy_manager.current_proxy
        if current_proxy:
            self.current_proxy_label.config(text=current_proxy, foreground="green")
        else:
            self.current_proxy_label.config(text="无", foreground="red")
    
    def get_status_color(self, status: str) -> str:
        """获取状态颜色"""
        colors = {
            "healthy": "green",
            "slow": "orange",
            "unhealthy": "red",
            "failed": "red",
            "unknown": "gray"
        }
        return colors.get(status, "black")
    
    def start_update_timer(self):
        """启动更新定时器"""
        self.update_timer = self.window.after(5000, self.update_loop)
    
    def update_loop(self):
        """更新循环"""
        try:
            self.refresh_proxy_list()
            self.update_timer = self.window.after(5000, self.update_loop)
        except:
            pass
    
    def stop_update_timer(self):
        """停止更新定时器"""
        if self.update_timer:
            self.window.after_cancel(self.update_timer)
            self.update_timer = None
    
    def add_proxy(self):
        """添加代理"""
        self.clear_config()
        messagebox.showinfo("添加代理", "请在下方配置区域填写代理信息，然后点击保存代理")
    
    def edit_proxy(self):
        """编辑代理"""
        selected = self.proxy_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = selected[0]
        values = self.proxy_tree.item(item, "values")
        name = values[0]
        
        if name in self.proxy_manager.proxies:
            proxy_info = self.proxy_manager.proxies[name]
            config = proxy_info.config
            
            # 加载配置到界面
            self.name_var.set(name)
            self.scheme_var.set(config.scheme)
            self.hostname_var.set(config.hostname)
            self.port_var.set(config.port)
            self.username_var.set(config.username or "")
            self.password_var.set(config.password or "")
            self.enabled_var.set(config.enabled)
    
    def delete_proxy(self):
        """删除代理"""
        selected = self.proxy_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = selected[0]
        values = self.proxy_tree.item(item, "values")
        name = values[0]
        
        if messagebox.askyesno("确认", f"确定要删除代理 '{name}' 吗？"):
            self.proxy_manager.remove_proxy(name)
            self.refresh_proxy_list()
    
    def save_proxy(self):
        """保存代理"""
        name = self.name_var.get().strip()
        scheme = self.scheme_var.get()
        hostname = self.hostname_var.get().strip()
        port = self.port_var.get()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        enabled = self.enabled_var.get()
        
        if not name:
            messagebox.showerror("错误", "代理名称不能为空")
            return
        
        if not hostname:
            messagebox.showerror("错误", "主机不能为空")
            return
        
        if not port or port <= 0 or port > 65535:
            messagebox.showerror("错误", "端口必须在1-65535之间")
            return
        
        try:
            # 创建代理配置
            config = ProxyConfig(
                scheme=scheme,
                hostname=hostname,
                port=port,
                username=username if username else None,
                password=password if password else None,
                enabled=enabled
            )
            
            # 添加到管理器
            self.proxy_manager.add_proxy(name, config)
            
            # 刷新列表
            self.refresh_proxy_list()
            
            # 清空配置
            self.clear_config()
            
            messagebox.showinfo("成功", f"代理 '{name}' 已保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存代理失败: {e}")
    
    def clear_config(self):
        """清空配置"""
        self.name_var.set("")
        self.scheme_var.set("socks5")
        self.hostname_var.set("")
        self.port_var.set(7890)
        self.username_var.set("")
        self.password_var.set("")
        self.enabled_var.set(True)
    
    def test_selected_proxy(self):
        """测试选中的代理"""
        selected = self.proxy_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = selected[0]
        values = self.proxy_tree.item(item, "values")
        name = values[0]
        
        if name not in self.proxy_manager.proxies:
            messagebox.showerror("错误", "代理不存在")
            return
        
        # 在新线程中测试
        def test_proxy():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                success, response_time = loop.run_until_complete(
                    self.proxy_manager.test_proxy(name)
                )
                
                # 更新UI
                self.window.after(0, lambda: self.on_test_complete(name, success, response_time))
                
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("错误", f"测试代理失败: {e}"))
            finally:
                loop.close()
        
        self.is_testing = True
        threading.Thread(target=test_proxy, daemon=True).start()
        
        # 显示测试中状态
        messagebox.showinfo("测试中", f"正在测试代理 '{name}'，请稍候...")
    
    def test_all_proxies(self):
        """测试所有代理"""
        if not self.proxy_manager.proxies:
            messagebox.showwarning("警告", "没有可测试的代理")
            return
        
        # 在新线程中测试
        def test_all():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(
                    self.proxy_manager.test_all_proxies()
                )
                
                # 更新UI
                self.window.after(0, lambda: self.on_test_all_complete(results))
                
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("错误", f"测试代理失败: {e}"))
            finally:
                loop.close()
        
        self.is_testing = True
        threading.Thread(target=test_all, daemon=True).start()
        
        # 显示测试中状态
        messagebox.showinfo("测试中", "正在测试所有代理，请稍候...")
    
    def on_test_complete(self, name: str, success: bool, response_time: float):
        """测试完成回调"""
        self.is_testing = False
        self.refresh_proxy_list()
        
        if success:
            messagebox.showinfo("测试成功", f"代理 '{name}' 测试成功\n响应时间: {response_time * 1000:.0f}ms")
        else:
            messagebox.showerror("测试失败", f"代理 '{name}' 测试失败")
    
    def on_test_all_complete(self, results: Dict[str, tuple]):
        """测试所有代理完成回调"""
        self.is_testing = False
        self.refresh_proxy_list()
        
        success_count = sum(1 for success, _ in results.values() if success)
        total_count = len(results)
        
        messagebox.showinfo("测试完成", f"代理测试完成\n成功: {success_count}/{total_count}")
    
    def set_current_proxy(self):
        """设置当前代理"""
        selected = self.proxy_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = selected[0]
        values = self.proxy_tree.item(item, "values")
        name = values[0]
        
        if name not in self.proxy_manager.proxies:
            messagebox.showerror("错误", "代理不存在")
            return
        
        old_proxy = self.proxy_manager.current_proxy
        self.proxy_manager.current_proxy = name
        
        self.refresh_proxy_list()
        messagebox.showinfo("成功", f"当前代理已设置为: {name}")
        
        self.logger.info(f"代理切换: {old_proxy} -> {name}")
    
    def enable_proxy(self):
        """启用代理"""
        self.set_proxy_enabled(True)
    
    def disable_proxy(self):
        """禁用代理"""
        self.set_proxy_enabled(False)
    
    def set_proxy_enabled(self, enabled: bool):
        """设置代理启用状态"""
        selected = self.proxy_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个代理")
            return
        
        item = selected[0]
        values = self.proxy_tree.item(item, "values")
        name = values[0]
        
        if name not in self.proxy_manager.proxies:
            messagebox.showerror("错误", "代理不存在")
            return
        
        proxy_info = self.proxy_manager.proxies[name]
        proxy_info.config.enabled = enabled
        
        self.refresh_proxy_list()
        
        status = "启用" if enabled else "禁用"
        messagebox.showinfo("成功", f"代理 '{name}' 已{status}")
    
    def import_proxies(self):
        """导入代理"""
        # 这里可以实现代理导入功能
        messagebox.showinfo("导入代理", "代理导入功能将在后续版本中实现")
    
    def export_proxies(self):
        """导出代理"""
        # 这里可以实现代理导出功能
        messagebox.showinfo("导出代理", "代理导出功能将在后续版本中实现")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择点击的项目
        item = self.proxy_tree.identify_row(event.y)
        if item:
            self.proxy_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_double_click(self, event):
        """双击事件"""
        self.edit_proxy()
    
    def on_selection_change(self, event):
        """选择变化事件"""
        pass
    
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