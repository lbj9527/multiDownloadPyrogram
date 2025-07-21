#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import customtkinter as ctk
import asyncio
import threading
import time

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
        try:
            window_config = self.app_config["app"]["window_size"]
            width = window_config.get("width", 1200)
            height = window_config.get("height", 800)

            # 验证窗口尺寸
            if width <= 0 or height <= 0:
                width, height = 1200, 800
                self.logger.warning("窗口尺寸配置无效，使用默认尺寸")

            # 计算居中位置
            if self.root:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()

                # 验证屏幕尺寸
                if screen_width <= 0 or screen_height <= 0:
                    self.logger.error("屏幕尺寸获取失败，使用默认位置")
                    x, y = 100, 100
                else:
                    # 确保窗口不超出屏幕边界
                    if width > screen_width:
                        width = int(screen_width * 0.9)
                    if height > screen_height:
                        height = int(screen_height * 0.9)

                    x = max(0, (screen_width - width) // 2)
                    y = max(0, (screen_height - height) // 2)

                self.root.geometry(f"{width}x{height}+{x}+{y}")
                self.root.minsize(800, 600)

                self.logger.debug(f"主窗口设置: {width}x{height}+{x}+{y}")
            else:
                self.logger.error("主窗口对象不存在")

        except Exception as e:
            self.logger.error(f"设置窗口大小和位置失败: {e}")
            # 使用默认设置
            try:
                if self.root:
                    self.root.geometry("1200x800+100+100")
                    self.root.minsize(800, 600)
            except Exception as fallback_error:
                self.logger.error(f"设置默认窗口配置失败: {fallback_error}")
        
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

        # 网络状态跟踪
        self._last_network_status = None  # 上次网络状态

        # 延迟更新连接状态，确保所有组件都已初始化
        self.root.after(1000, self.update_connection_status)

        # 延迟2秒后开始网络检测
        self.root.after(2000, self.update_network_status)

        # 延迟3秒后开始定时更新（心跳检测）
        self.root.after(3000, self.schedule_connection_status_update)

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

        # 客户端连接数量显示
        self.client_count_label = ctk.CTkLabel(
            self.status_frame,
            text="客户端: 0/0",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.client_count_label.pack(side="left", padx=(20, 10), pady=5)

        # 网络连接状态指示器
        self.network_indicator = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.network_indicator.pack(side="right", padx=10, pady=5)

        # 网络连接状态文本
        self.network_label = ctk.CTkLabel(
            self.status_frame,
            text="网络检测中",
            font=ctk.CTkFont(size=12)
        )
        self.network_label.pack(side="right", padx=(0, 5), pady=5)
    
    def setup_events(self):
        """设置事件处理"""
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 订阅事件管理器的事件
        event_manager.subscribe_all(self.on_event_received)
        
        # 定时更新状态
        self.update_status()

        # 定时更新连接状态
        self.schedule_connection_status_update()
    
    def on_event_received(self, event: BaseEvent):
        """处理接收到的事件"""
        try:
            # 在主线程中更新UI
            if self.root:
                self.root.after(0, self._update_ui_from_event, event)
            else:
                self.logger.warning("主窗口对象不存在，无法更新UI")
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")
    
    def _update_ui_from_event(self, event: BaseEvent):
        """从事件更新UI（在主线程中执行）"""
        try:
            # 处理配置更新事件
            if event.event_type == EventType.CONFIG_UPDATED:
                self.reload_app_config()
                self.update_status("配置已更新", "green")

                # 如果是代理配置更新，通知客户端管理器重新检查连接
                if hasattr(event, 'data') and event.data and event.data.get('config_type') == 'app_config':
                    self._handle_proxy_config_change()
                return

            # 更新状态栏
            if event.event_type in [EventType.CLIENT_LOGIN_SUCCESS, EventType.CLIENT_DISCONNECTED, EventType.CLIENT_STATUS_CHANGED]:
                self.logger.info(f"收到客户端状态事件: {event.event_type}, 更新连接状态")
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
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.configure(text=message, text_color=color)

            # 5秒后恢复默认状态
            if message != "就绪" and self.root:
                self.root.after(5000, lambda: self.update_status())
        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")

    def check_network_connection(self) -> tuple[bool, str]:
        """检测网络连接状态 - 使用代理连接Google"""
        try:
            # 获取代理配置
            from ..utils.proxy_utils import get_proxy_manager
            proxy_manager = get_proxy_manager()

            # 使用异步方式测试连接（通过代理）
            if self.loop and not self.loop.is_closed():
                try:
                    # 在异步事件循环中执行代理测试
                    future = asyncio.run_coroutine_threadsafe(
                        self._test_google_with_proxy(proxy_manager),
                        self.loop
                    )
                    is_connected, status_text = future.result(timeout=5.0)
                    return is_connected, status_text
                except Exception as e:
                    self.logger.debug(f"异步代理测试失败: {e}")
                    return False, "网络断开"
            else:
                self.logger.debug("异步事件循环不可用，无法进行代理测试")
                return False, "网络检测失败"

        except Exception as e:
            self.logger.error(f"网络检测异常: {e}")
            return False, "网络检测失败"

    async def _test_google_with_proxy(self, proxy_manager) -> tuple[bool, str]:
        """使用代理测试Google连接"""
        try:
            import aiohttp

            # 获取代理URL
            proxy_url = proxy_manager.get_proxy_url()

            # 设置超时
            timeout = aiohttp.ClientTimeout(total=3)

            start_time = time.time()

            # 创建HTTP会话
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 使用代理连接Google
                async with session.get(
                    "https://www.google.com",
                    proxy=proxy_url
                ) as response:
                    end_time = time.time()

                    if response.status == 200:
                        response_time = int((end_time - start_time) * 1000)
                        proxy_info = "使用代理" if proxy_url else "直连"
                        self.logger.debug(f"Google连接成功: {proxy_info} ({response_time}ms)")
                        return True, f"网络正常 ({response_time}ms)"
                    else:
                        self.logger.debug(f"Google连接失败: HTTP {response.status}")
                        return False, "网络断开"

        except asyncio.TimeoutError:
            self.logger.debug("Google连接超时")
            return False, "网络断开"
        except Exception as e:
            error_msg = str(e)
            if "ProxyConnectionError" in error_msg or "proxy" in error_msg.lower():
                self.logger.debug("代理连接失败")
                return False, "网络断开"
            elif "ConnectorError" in error_msg or "connection" in error_msg.lower():
                self.logger.debug("网络连接失败")
                return False, "网络断开"
            else:
                self.logger.debug(f"Google连接异常: {e}")
                return False, "网络断开"

    def update_network_status(self):
        """更新网络连接状态 - 心跳检测"""
        def check_network():
            try:
                is_connected, status_text = self.check_network_connection()

                # 在主线程中更新UI
                def update_ui():
                    try:
                        if is_connected:
                            self.network_indicator.configure(text_color="green")
                            self.network_label.configure(text=status_text)
                            # 记录网络恢复
                            if hasattr(self, '_last_network_status') and not self._last_network_status:
                                self.logger.info("网络连接已恢复")
                                self.update_status("网络连接已恢复", "green")
                        else:
                            self.network_indicator.configure(text_color="red")
                            self.network_label.configure(text=status_text)
                            # 记录网络断开
                            if not hasattr(self, '_last_network_status') or self._last_network_status:
                                self.logger.warning("网络连接已断开")
                                self.update_status("网络连接已断开", "red")

                        # 保存当前网络状态
                        self._last_network_status = is_connected

                    except Exception as e:
                        self.logger.error(f"更新网络状态UI失败: {e}")

                if self.root:
                    self.root.after(0, update_ui)

            except Exception as e:
                self.logger.error(f"网络心跳检测失败: {e}")
                # 网络检测失败时也要更新UI
                def update_error_ui():
                    try:
                        self.network_indicator.configure(text_color="gray")
                        self.network_label.configure(text="网络检测失败")
                    except Exception:
                        pass

                if self.root:
                    self.root.after(0, update_error_ui)

        # 在后台线程中执行网络检测
        threading.Thread(target=check_network, daemon=True).start()

    def update_client_count_status(self):
        """更新客户端连接数量状态"""
        try:
            if hasattr(self.client_config_frame, 'client_manager') and self.client_config_frame.client_manager:
                enabled_clients = self.client_config_frame.client_manager.get_enabled_clients()
                total_clients = len(self.client_config_frame.client_manager.config.clients)
                connected_count = len(enabled_clients)

                # 更新客户端数量显示
                self.client_count_label.configure(text=f"客户端: {connected_count}/{total_clients}")

                # 根据连接数量设置颜色
                if connected_count == 0:
                    self.client_count_label.configure(text_color="red")
                elif connected_count == total_clients:
                    self.client_count_label.configure(text_color="green")
                else:
                    self.client_count_label.configure(text_color="orange")

                self.logger.debug(f"客户端连接状态: {connected_count}/{total_clients}")
            else:
                self.client_count_label.configure(text="客户端: 0/0", text_color="gray")

        except Exception as e:
            self.logger.error(f"更新客户端数量状态失败: {e}")

    def update_connection_status(self):
        """更新连接状态（现在只更新客户端数量）"""
        self.update_client_count_status()

    def schedule_connection_status_update(self):
        """定时更新连接状态"""
        try:
            # 更新客户端连接数量
            self.update_connection_status()

            # 更新网络连接状态（心跳检测）
            self.update_network_status()

            # 每5秒更新一次状态（心跳检测需要更频繁）
            if self.root:
                self.root.after(5000, self.schedule_connection_status_update)
        except Exception as e:
            self.logger.error(f"定时更新连接状态失败: {e}")

    def _handle_proxy_config_change(self):
        """处理代理配置变更"""
        try:
            self.logger.info("检测到代理配置变更，重新检查客户端连接")

            # 重新初始化代理配置
            self._initialize_proxy_config()

            # 通知客户端配置框架重新检查连接
            if hasattr(self, 'client_config_frame') and self.client_config_frame:
                # 在后台线程中执行连接检查
                def check_connections():
                    try:
                        # 延迟一秒，确保代理配置已更新
                        import time
                        time.sleep(1)

                        # 触发连接测试
                        if hasattr(self.client_config_frame, 'test_connections'):
                            self.client_config_frame.test_connections()
                    except Exception as e:
                        self.logger.error(f"代理配置变更后检查连接失败: {e}")

                import threading
                threading.Thread(target=check_connections, daemon=True).start()

        except Exception as e:
            self.logger.error(f"处理代理配置变更失败: {e}")

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
    
    def reload_app_config(self):
        """重新加载应用配置"""
        try:
            self.app_config = self.config_manager.load_app_config()
            self.logger.debug("应用配置已重新加载")
        except Exception as e:
            self.logger.error(f"重新加载应用配置失败: {e}")

    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            self.logger.info("正在关闭应用...")

            # 停止事件管理器
            event_manager.stop_processing()

            # 停止异步循环
            self.stop_async_loop()

            # 重新加载最新配置，避免覆盖用户修改
            self.reload_app_config()

            # 关闭窗口（不再保存配置，因为配置已经在设置窗口中保存了）
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
