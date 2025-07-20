#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多客户端池管理器
"""

import asyncio
import os
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from datetime import datetime

from pyrogram import Client, compose
from pyrogram.errors import (
    FloodWait, AuthKeyUnregistered, Unauthorized,
    PhoneNumberInvalid, PhoneCodeInvalid, PasswordHashInvalid,
    SessionPasswordNeeded, BadRequest
)

from ..models.client_config import ClientConfig, ClientStatus, MultiClientConfig
from ..models.events import EventType, create_client_event, create_error_event
from ..utils.logger import get_logger
from ..utils.proxy_utils import get_pyrogram_proxy


class ClientManager:
    """多客户端池管理器"""
    
    def __init__(self, config: MultiClientConfig, event_callback: Optional[Callable] = None):
        """
        初始化客户端管理器
        
        Args:
            config: 多客户端配置
            event_callback: 事件回调函数
        """
        self.config = config
        self.event_callback = event_callback
        self.logger = get_logger(__name__)
        
        # 客户端实例字典
        self.clients: Dict[str, Client] = {}
        # 客户端状态字典
        self.client_status: Dict[str, ClientStatus] = {}
        # 客户端最后活跃时间
        self.last_active: Dict[str, datetime] = {}
        # 客户端错误信息
        self.client_errors: Dict[str, str] = {}

        # 顺序登录控制
        self.login_queue: List[str] = []  # 登录队列
        self.current_logging_client: Optional[str] = None  # 当前正在登录的客户端
        self.login_lock = asyncio.Lock()  # 登录锁，确保顺序登录

        # 多客户端compose管理
        self.compose_task: Optional[asyncio.Task] = None  # compose任务
        self.is_compose_running = False  # compose是否正在运行

        # API调用频率监控（用于限流防护）
        self.api_call_counts: Dict[str, int] = {}  # 每个客户端的API调用计数
        self.api_call_timestamps: Dict[str, List[datetime]] = {}  # API调用时间戳
        
        # 会话文件目录
        self.session_dir = Path("sessions")
        self.session_dir.mkdir(exist_ok=True)
        
        # 初始化客户端
        self._initialize_clients()

        # 检查并自动登录已有会话
        self._check_and_auto_login_sessions()

        # 启动连接监控
        self._start_connection_monitor()

        # 添加客户端活跃时间更新机制
        self._setup_activity_tracking()
    
    def _initialize_clients(self):
        """初始化所有启用的客户端"""
        for client_config in self.config.clients:
            if client_config.enabled:
                self._create_client(client_config)
            else:
                # 为禁用的客户端设置状态
                self.client_status[client_config.session_name] = ClientStatus.DISABLED
                self.logger.info(f"客户端 {client_config.session_name} 已禁用，跳过初始化")

    def _check_and_auto_login_sessions(self):
        """检查现有会话文件并自动登录"""
        try:
            for client_config in self.config.clients:
                if not client_config.enabled:
                    continue

                session_name = client_config.session_name
                session_file = self.session_dir / f"{session_name}.session"

                # 检查会话文件是否存在
                if session_file.exists():
                    self.logger.info(f"发现会话文件: {session_file}")

                    # 启动自动登录任务
                    import threading
                    threading.Thread(
                        target=self._auto_login_with_session,
                        args=(session_name,),
                        daemon=True
                    ).start()
                else:
                    self.logger.debug(f"会话文件不存在: {session_file}")

        except Exception as e:
            self.logger.error(f"检查会话文件失败: {e}")

    def _auto_login_with_session(self, session_name: str):
        """使用会话文件自动登录"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 检查客户端是否存在
                if session_name not in self.clients:
                    self.logger.warning(f"客户端 {session_name} 不存在，无法自动登录")
                    return

                client = self.clients[session_name]

                # 设置登录状态
                self.client_status[session_name] = ClientStatus.LOGGING_IN
                self._send_status_event(session_name, ClientStatus.LOGGING_IN, "正在使用会话文件自动登录")

                # 尝试连接
                success = loop.run_until_complete(self._try_auto_connect(client, session_name))

                if success:
                    self.client_status[session_name] = ClientStatus.LOGGED_IN
                    self.last_active[session_name] = datetime.now()
                    self.logger.info(f"客户端 {session_name} 会话自动登录成功")
                    self._send_status_event(session_name, ClientStatus.LOGGED_IN, "会话自动登录成功")
                else:
                    self.client_status[session_name] = ClientStatus.LOGIN_FAILED
                    self.logger.warning(f"客户端 {session_name} 会话自动登录失败")
                    self._send_status_event(session_name, ClientStatus.LOGIN_FAILED, "会话自动登录失败")

            finally:
                loop.close()

        except Exception as e:
            self.logger.error(f"自动登录异常: {e}")
            if session_name in self.client_status:
                self.client_status[session_name] = ClientStatus.ERROR
                self._send_status_event(session_name, ClientStatus.ERROR, f"自动登录异常: {e}")

    def _start_connection_monitor(self):
        """启动连接监控"""
        def monitor_connections():
            import time
            while True:
                try:
                    # 每60秒检查一次连接状态（减少频率）
                    time.sleep(60)

                    # 检查所有已登录的客户端
                    for session_name, status in self.client_status.items():
                        if status == ClientStatus.LOGGED_IN:
                            # 直接在当前线程中检查，避免创建过多线程
                            self._check_single_client_connection(session_name)

                except Exception as e:
                    self.logger.error(f"连接监控异常: {e}")

        import threading
        monitor_thread = threading.Thread(target=monitor_connections, daemon=True)
        monitor_thread.start()
        self.logger.info("连接监控已启动（每60秒检查一次）")

    def _check_single_client_connection(self, session_name: str):
        """检查单个客户端的连接状态"""
        try:
            if session_name not in self.clients:
                return

            client = self.clients[session_name]

            # 使用简单的连接状态检查，避免创建新的事件循环
            try:
                if not client.is_connected:
                    self._handle_connection_lost(session_name, "客户端未连接")
                    return

                # 检查最后活跃时间，如果超过5分钟没有活动，标记为可能断连
                if session_name in self.last_active:
                    last_active = self.last_active[session_name]
                    now = datetime.now()
                    if (now - last_active).total_seconds() > 300:  # 5分钟
                        self.logger.warning(f"客户端 {session_name} 超过5分钟无活动，可能已断连")
                        # 不立即标记为断连，只是记录警告
                else:
                    # 如果没有最后活跃时间记录，设置当前时间
                    self.last_active[session_name] = datetime.now()

            except Exception as e:
                self._handle_connection_lost(session_name, str(e))

        except Exception as e:
            self.logger.error(f"检查客户端 {session_name} 连接状态失败: {e}")

    def _handle_connection_lost(self, session_name: str, reason: str):
        """处理连接丢失"""
        self.logger.warning(f"客户端 {session_name} 连接丢失: {reason}")

        # 更新状态
        self.client_status[session_name] = ClientStatus.ERROR
        self.client_errors[session_name] = f"连接丢失: {reason}"

        # 发送断连事件
        if self.event_callback:
            event = create_client_event(
                EventType.CLIENT_DISCONNECTED,
                session_name,
                f"客户端 {session_name} 连接丢失: {reason}",
                data={"error": reason}
            )
            self.event_callback(event)

    def _setup_activity_tracking(self):
        """设置活跃时间跟踪"""
        # 为每个客户端设置消息处理器来跟踪活跃时间
        for session_name, client in self.clients.items():
            try:
                # 添加消息处理器来更新活跃时间
                @client.on_message()
                async def update_activity(client, message):
                    # 更新对应客户端的活跃时间
                    for name, c in self.clients.items():
                        if c == client:
                            self.last_active[name] = datetime.now()
                            break

            except Exception as e:
                self.logger.debug(f"为客户端 {session_name} 设置活跃时间跟踪失败: {e}")

    def update_client_activity(self, session_name: str):
        """手动更新客户端活跃时间"""
        if session_name in self.clients:
            self.last_active[session_name] = datetime.now()
            self.logger.debug(f"更新客户端 {session_name} 活跃时间")

    def _send_status_event(self, session_name: str, status: ClientStatus, message: str):
        """发送状态变更事件"""
        if self.event_callback:
            from ..models.events import create_client_event, EventType
            event = create_client_event(
                EventType.CLIENT_STATUS_CHANGED,
                session_name,
                message,
                data={"status": status.value}
            )
            self.event_callback(event)

    def test_client_connection_sync(self, session_name: str) -> tuple[bool, str]:
        """
        同步方式测试客户端连接状态

        Args:
            session_name: 会话名称

        Returns:
            tuple[bool, str]: (是否连接成功, 状态描述)
        """
        try:
            if session_name not in self.clients:
                return False, "客户端不存在"

            client = self.clients[session_name]
            current_status = self.client_status.get(session_name)

            # 1. 首先检查基本连接状态
            if not client.is_connected:
                # 客户端未连接到Telegram服务器
                if current_status == ClientStatus.LOGGED_IN:
                    self.client_status[session_name] = ClientStatus.ERROR
                    self._send_status_event(session_name, ClientStatus.ERROR, "连接已断开")
                return False, "客户端未连接"

            # 2. 检查客户端是否有缓存的用户信息
            if hasattr(client, 'me') and client.me:
                # 有用户信息，说明之前成功登录过
                if current_status != ClientStatus.LOGGED_IN:
                    self.client_status[session_name] = ClientStatus.LOGGED_IN
                    self._send_status_event(session_name, ClientStatus.LOGGED_IN, "连接验证成功")

                self.last_active[session_name] = datetime.now()
                return True, f"连接正常 (用户: {client.me.first_name})"

            # 3. 检查当前状态
            if current_status == ClientStatus.LOGGED_IN:
                # 状态显示已登录，但没有用户信息缓存
                # 这种情况下认为连接正常，但可能需要重新获取用户信息
                self.last_active[session_name] = datetime.now()
                return True, "连接正常 (已登录状态)"

            # 4. 其他状态检查
            if current_status == ClientStatus.LOGGING_IN:
                return True, "正在登录中"
            elif current_status == ClientStatus.NOT_LOGGED_IN:
                return False, "未登录"
            elif current_status == ClientStatus.LOGIN_FAILED:
                return False, "登录失败"
            elif current_status == ClientStatus.ERROR:
                return False, "连接错误"
            else:
                # 未知状态，但客户端显示已连接
                return True, f"连接状态未知 (状态: {current_status})"

        except Exception as e:
            self.logger.error(f"测试客户端 {session_name} 连接失败: {e}")
            if session_name in self.client_status:
                self.client_status[session_name] = ClientStatus.ERROR
            return False, f"测试异常: {e}"

    def test_client_connection_with_api(self, session_name: str) -> tuple[bool, str]:
        """
        使用API调用测试客户端连接状态（更强的测试）

        Args:
            session_name: 会话名称

        Returns:
            tuple[bool, str]: (是否连接成功, 状态描述)
        """
        try:
            if session_name not in self.clients:
                return False, "客户端不存在"

            client = self.clients[session_name]

            # 检查基本连接状态
            if not client.is_connected:
                return False, "客户端未连接"

            # 尝试真正的API调用测试
            try:
                import concurrent.futures
                import asyncio

                async def test_get_me():
                    """异步测试get_me"""
                    try:
                        # 设置3秒超时，比较短的超时时间
                        me = await asyncio.wait_for(client.get_me(), timeout=3.0)
                        return me
                    except asyncio.TimeoutError:
                        return None
                    except Exception as e:
                        self.logger.debug(f"get_me调用失败: {e}")
                        return None

                # 尝试检测客户端的事件循环
                client_loop = None

                # 尝试多种方式获取客户端的事件循环
                if hasattr(client, '_loop') and client._loop and not client._loop.is_closed():
                    client_loop = client._loop
                elif hasattr(client, 'loop') and client.loop and not client.loop.is_closed():
                    client_loop = client.loop

                if client_loop:
                    try:
                        # 在客户端的事件循环中执行测试
                        future = asyncio.run_coroutine_threadsafe(test_get_me(), client_loop)
                        me = future.result(timeout=4.0)  # 比内部超时稍长
                        if me:
                            # API调用成功
                            self.client_status[session_name] = ClientStatus.LOGGED_IN
                            self.last_active[session_name] = datetime.now()
                            self._send_status_event(session_name, ClientStatus.LOGGED_IN, "API测试成功")
                            return True, f"连接正常 (API验证: {me.first_name})"
                        else:
                            # API调用失败
                            self.client_status[session_name] = ClientStatus.ERROR
                            self._send_status_event(session_name, ClientStatus.ERROR, "API调用失败")
                            return False, "连接失败 (API调用超时或失败)"
                    except concurrent.futures.TimeoutError:
                        self.client_status[session_name] = ClientStatus.ERROR
                        self._send_status_event(session_name, ClientStatus.ERROR, "API测试超时")
                        return False, "连接失败 (API测试超时)"
                    except Exception as e:
                        self.logger.debug(f"API测试异常: {e}")
                        return False, f"API测试异常: {e}"
                else:
                    return False, "无法获取客户端事件循环"

            except Exception as e:
                self.logger.debug(f"API测试异常: {e}")
                return False, f"API测试异常: {e}"

        except Exception as e:
            self.logger.error(f"API测试客户端 {session_name} 连接失败: {e}")
            return False, f"测试异常: {e}"

    async def _try_auto_connect(self, client: Client, session_name: str) -> bool:
        """尝试自动连接客户端"""
        try:
            # 启动客户端
            await client.start()

            # 检查是否成功连接
            if client.is_connected:
                # 获取用户信息验证登录状态
                me = await client.get_me()
                if me:
                    self.logger.info(f"客户端 {session_name} 自动登录成功，用户: {me.username or me.first_name}")
                    return True
                else:
                    self.logger.warning(f"客户端 {session_name} 连接成功但无法获取用户信息")
                    return False
            else:
                self.logger.warning(f"客户端 {session_name} 连接失败")
                return False

        except Exception as e:
            self.logger.error(f"客户端 {session_name} 自动连接失败: {e}")
            return False
    
    def _create_client(self, client_config: ClientConfig) -> Client:
        """
        创建单个客户端实例
        
        Args:
            client_config: 客户端配置
            
        Returns:
            Client: Pyrogram客户端实例
        """
        try:
            # 获取代理配置
            proxy_config = get_pyrogram_proxy()

            # 创建客户端实例 - 按照需求文档1.4.1节的完整参数
            client_kwargs = {
                "name": client_config.session_name,
                "api_id": client_config.api_id,
                "api_hash": client_config.api_hash,
                "phone_number": client_config.phone_number,
                "app_version": "TG-Manager 1.0",
                "device_model": "Desktop",
                "system_version": "Windows 10",
                "lang_code": "zh",
                "ipv6": False,
                "workers": min(32, os.cpu_count() + 4),
                "workdir": str(self.session_dir),
                "sleep_threshold": 10,  # FloodWait自动重试的睡眠阈值
                "hide_password": True,
                "max_concurrent_transmissions": 1,  # 最大并发传输数
                "in_memory": False,  # 使用文件存储
                "takeout": False,  # 不使用takeout会话
            }

            # 如果有代理配置，添加到客户端参数中
            if proxy_config:
                client_kwargs["proxy"] = proxy_config
                self.logger.info(f"客户端 {client_config.session_name} 将使用代理: {proxy_config['hostname']}:{proxy_config['port']}")

            client = Client(**client_kwargs)
            
            # 存储客户端实例
            self.clients[client_config.session_name] = client
            self.client_status[client_config.session_name] = ClientStatus.NOT_LOGGED_IN
            
            self.logger.info(f"客户端 {client_config.session_name} 初始化成功")
            
            # 发送事件
            if self.event_callback:
                event = create_client_event(
                    EventType.CLIENT_STATUS_CHANGED,
                    client_config.session_name,
                    f"客户端 {client_config.session_name} 初始化成功",
                    ClientStatus.NOT_LOGGED_IN.value
                )
                self.event_callback(event)
            
            return client
            
        except Exception as e:
            self.logger.error(f"创建客户端 {client_config.session_name} 失败: {e}")
            self.client_status[client_config.session_name] = ClientStatus.ERROR
            self.client_errors[client_config.session_name] = str(e)
            
            # 发送错误事件
            if self.event_callback:
                error_event = create_error_event(
                    EventType.ERROR_UNKNOWN,
                    f"创建客户端 {client_config.session_name} 失败: {e}",
                    error_details={"client_name": client_config.session_name, "error": str(e)},
                    source="client_manager"
                )
                self.event_callback(error_event)
            
            raise

    def enable_client(self, session_name: str) -> bool:
        """
        启用指定的客户端

        Args:
            session_name: 会话名称

        Returns:
            bool: 是否成功启用
        """
        try:
            # 查找对应的客户端配置
            client_config = None
            for config in self.config.clients:
                if config.session_name == session_name:
                    client_config = config
                    break

            if not client_config:
                self.logger.error(f"找不到客户端配置: {session_name}")
                return False

            # 如果客户端已经存在，直接返回
            if session_name in self.clients:
                self.logger.info(f"客户端 {session_name} 已经启用")
                return True

            # 创建客户端实例
            self._create_client(client_config)
            self.logger.info(f"客户端 {session_name} 已启用")
            return True

        except Exception as e:
            self.logger.error(f"启用客户端 {session_name} 失败: {e}")
            return False

    async def start_compose_clients(self, sequential: bool = False) -> bool:
        """
        使用Pyrogram compose()方法启动多客户端（按照需求文档1.4.3节）

        Args:
            sequential: 是否顺序运行客户端，默认False（并发运行）

        Returns:
            bool: 是否成功启动
        """
        try:
            if self.is_compose_running:
                self.logger.warning("compose已经在运行中")
                return True

            # 获取所有已登录的客户端
            logged_in_clients = []
            for session_name, client in self.clients.items():
                if (session_name in self.client_status and
                    self.client_status[session_name] == ClientStatus.LOGGED_IN):
                    logged_in_clients.append(client)

            if not logged_in_clients:
                self.logger.warning("没有已登录的客户端可以启动compose")
                return False

            self.logger.info(f"启动compose，包含 {len(logged_in_clients)} 个客户端")

            # 使用compose并发运行多个客户端
            self.compose_task = asyncio.create_task(
                compose(logged_in_clients, sequential=sequential)
            )
            self.is_compose_running = True

            return True

        except Exception as e:
            self.logger.error(f"启动compose失败: {e}")
            return False

    async def stop_compose_clients(self) -> bool:
        """
        停止compose多客户端运行

        Returns:
            bool: 是否成功停止
        """
        try:
            if not self.is_compose_running or not self.compose_task:
                return True

            self.logger.info("停止compose多客户端运行")

            # 取消compose任务
            self.compose_task.cancel()

            try:
                await self.compose_task
            except asyncio.CancelledError:
                pass

            self.compose_task = None
            self.is_compose_running = False

            return True

        except Exception as e:
            self.logger.error(f"停止compose失败: {e}")
            return False

    def _send_status_event(self, session_name: str, status: ClientStatus, message: str):
        """发送客户端状态变化事件"""
        try:
            if self.event_callback:
                from ..models.events import create_client_event, EventType
                event = create_client_event(
                    EventType.CLIENT_STATUS_CHANGED,
                    session_name,
                    message,
                    client_status=status.value
                )
                self.event_callback(event)
        except Exception as e:
            self.logger.error(f"发送状态事件失败: {e}")

    def can_disable_client(self, session_name: str) -> tuple[bool, str]:
        """
        检查是否可以禁用指定客户端（强制启用约束）

        Args:
            session_name: 会话名称

        Returns:
            tuple[bool, str]: (是否可以禁用, 错误信息)
        """
        # 统计当前启用的客户端数量
        enabled_count = 0
        for client_config in self.config.clients:
            if client_config.enabled and client_config.session_name != session_name:
                enabled_count += 1

        # 如果禁用该客户端后没有启用的客户端，则不允许禁用
        if enabled_count == 0:
            return False, "系统要求至少保持一个客户端处于启用状态，无法禁用最后一个启用的客户端"

        return True, ""

    def get_enabled_clients_count(self) -> int:
        """
        获取当前启用的客户端数量

        Returns:
            int: 启用的客户端数量
        """
        count = 0
        for client_config in self.config.clients:
            if client_config.enabled:
                count += 1
        return count

    def get_next_client_to_login(self) -> Optional[str]:
        """
        获取下一个应该登录的客户端（按照需求文档的顺序登录机制）

        Returns:
            Optional[str]: 下一个应该登录的客户端会话名称，如果没有则返回None
        """
        # 按照配置顺序查找第一个未登录且启用的客户端
        for client_config in self.config.clients:
            if (client_config.enabled and
                client_config.session_name in self.client_status and
                self.client_status[client_config.session_name] in [
                    ClientStatus.NOT_LOGGED_IN,
                    ClientStatus.LOGIN_FAILED,
                    ClientStatus.ERROR
                ]):
                return client_config.session_name
        return None

    def can_login_client(self, session_name: str) -> bool:
        """
        检查指定客户端是否可以登录（顺序登录控制）

        Args:
            session_name: 会话名称

        Returns:
            bool: 是否可以登录
        """
        # 如果有客户端正在登录，则不能登录其他客户端
        if self.current_logging_client is not None:
            return False

        # 检查是否轮到该客户端登录
        next_client = self.get_next_client_to_login()
        return next_client == session_name

    def get_login_button_states(self) -> Dict[str, bool]:
        """
        获取所有客户端登录按钮的启用状态

        Returns:
            Dict[str, bool]: 客户端会话名称到按钮启用状态的映射
        """
        states = {}
        next_client = self.get_next_client_to_login()

        for client_config in self.config.clients:
            session_name = client_config.session_name

            if not client_config.enabled:
                states[session_name] = False
            elif self.current_logging_client is not None:
                # 有客户端正在登录时，所有按钮都禁用
                states[session_name] = False
            elif session_name == next_client:
                # 轮到该客户端登录
                states[session_name] = True
            else:
                # 不是轮到该客户端登录
                states[session_name] = False

        return states

    async def login_client(self, session_name: str, phone_code: Optional[str] = None,
                          password: Optional[str] = None) -> bool:
        """
        登录指定客户端（实现顺序登录机制）

        Args:
            session_name: 会话名称
            phone_code: 验证码（如果需要）
            password: 双重验证密码（如果需要）

        Returns:
            bool: 登录是否成功
        """
        # 使用登录锁确保顺序登录
        async with self.login_lock:
            # 检查是否可以登录该客户端
            if not self.can_login_client(session_name):
                self.logger.error(f"客户端 {session_name} 当前不能登录，请按顺序登录")
                return False

            # 检查客户端是否存在
            if session_name not in self.clients:
                # 检查是否是禁用的客户端
                if session_name in self.client_status and self.client_status[session_name] == ClientStatus.DISABLED:
                    self.logger.error(f"客户端 {session_name} 已禁用，无法登录")
                    return False
                else:
                    self.logger.error(f"客户端 {session_name} 不存在")
                    return False

            # 设置当前正在登录的客户端
            self.current_logging_client = session_name
        
        client = self.clients[session_name]
        
        try:
            # 更新状态为登录中
            self.client_status[session_name] = ClientStatus.LOGGING_IN
            
            # 发送登录开始事件
            if self.event_callback:
                event = create_client_event(
                    EventType.CLIENT_LOGIN_START,
                    session_name,
                    f"开始登录客户端 {session_name}",
                    ClientStatus.LOGGING_IN.value
                )
                self.event_callback(event)
            
            # 启动客户端
            await client.start()
            
            # 验证登录状态
            me = await client.get_me()
            if me:
                # 登录成功
                self.client_status[session_name] = ClientStatus.LOGGED_IN
                self.last_active[session_name] = datetime.now()
                self.client_errors.pop(session_name, None)
                
                self.logger.info(f"客户端 {session_name} 登录成功，用户: {me.username or me.phone_number}")
                
                # 发送登录成功事件
                if self.event_callback:
                    event = create_client_event(
                        EventType.CLIENT_LOGIN_SUCCESS,
                        session_name,
                        f"客户端 {session_name} 登录成功",
                        ClientStatus.LOGGED_IN.value,
                        data={"user_id": me.id, "username": me.username, "phone": me.phone_number}
                    )
                    self.event_callback(event)
                
                # 登录成功，清理登录状态
                self.current_logging_client = None
                return True
            else:
                raise Exception("无法获取用户信息")

        except SessionPasswordNeeded:
            # 需要双重验证密码
            self.logger.warning(f"客户端 {session_name} 需要双重验证密码")
            if password:
                try:
                    await client.check_password(password)
                    return await self.login_client(session_name)
                except PasswordHashInvalid:
                    error_msg = "双重验证密码错误"
                    self.logger.error(f"客户端 {session_name} {error_msg}")
                    self._handle_login_error(session_name, error_msg)
                    return False
            else:
                error_msg = "需要双重验证密码"
                self._handle_login_error(session_name, error_msg)
                return False
                
        except PhoneCodeInvalid:
            error_msg = "验证码无效"
            self.logger.error(f"客户端 {session_name} {error_msg}")
            self._handle_login_error(session_name, error_msg)
            return False
            
        except PhoneNumberInvalid:
            error_msg = "电话号码无效"
            self.logger.error(f"客户端 {session_name} {error_msg}")
            self._handle_login_error(session_name, error_msg)
            return False
            
        except (AuthKeyUnregistered, Unauthorized):
            error_msg = "认证失败，需要重新登录"
            self.logger.error(f"客户端 {session_name} {error_msg}")
            self._handle_login_error(session_name, error_msg)
            return False
            
        except FloodWait as e:
            error_msg = f"触发限流，需要等待 {e.value} 秒"
            self.logger.warning(f"客户端 {session_name} {error_msg}")
            self._handle_login_error(session_name, error_msg)
            
            # 发送FloodWait事件
            if self.event_callback:
                error_event = create_error_event(
                    EventType.ERROR_FLOOD_WAIT,
                    f"客户端 {session_name} 触发限流",
                    error_details={"wait_time": e.value, "client_name": session_name},
                    source="client_manager"
                )
                self.event_callback(error_event)
            
            return False
            
        except Exception as e:
            error_msg = f"登录失败: {e}"
            self.logger.error(f"客户端 {session_name} {error_msg}")
            self._handle_login_error(session_name, error_msg)
            return False
    
    def _handle_login_error(self, session_name: str, error_msg: str):
        """处理登录错误"""
        self.client_status[session_name] = ClientStatus.LOGIN_FAILED
        self.client_errors[session_name] = error_msg

        # 清理登录状态
        if self.current_logging_client == session_name:
            self.current_logging_client = None

        # 发送登录失败事件
        if self.event_callback:
            event = create_client_event(
                EventType.CLIENT_LOGIN_FAILED,
                session_name,
                f"客户端 {session_name} 登录失败: {error_msg}",
                ClientStatus.LOGIN_FAILED.value,
                data={"error": error_msg}
            )
            self.event_callback(event)
    
    async def logout_client(self, session_name: str) -> bool:
        """
        登出指定客户端
        
        Args:
            session_name: 会话名称
            
        Returns:
            bool: 登出是否成功
        """
        if session_name not in self.clients:
            return False
        
        try:
            client = self.clients[session_name]
            if client.is_connected:
                await client.stop()
            
            self.client_status[session_name] = ClientStatus.NOT_LOGGED_IN
            self.client_errors.pop(session_name, None)
            
            self.logger.info(f"客户端 {session_name} 登出成功")
            
            # 发送状态变更事件
            if self.event_callback:
                event = create_client_event(
                    EventType.CLIENT_STATUS_CHANGED,
                    session_name,
                    f"客户端 {session_name} 已登出",
                    ClientStatus.NOT_LOGGED_IN.value
                )
                self.event_callback(event)
            
            return True
            
        except Exception as e:
            self.logger.error(f"客户端 {session_name} 登出失败: {e}")
            return False

    async def enable_client(self, session_name: str) -> bool:
        """
        启用指定客户端

        Args:
            session_name: 会话名称

        Returns:
            bool: 启用是否成功
        """
        # 更新配置中的客户端状态
        for client_config in self.config.clients:
            if client_config.session_name == session_name:
                client_config.enabled = True
                self.logger.info(f"客户端 {session_name} 已启用")

                # 发送状态变更事件
                if self.event_callback:
                    event = create_client_event(
                        EventType.CLIENT_STATUS_CHANGED,
                        session_name,
                        f"客户端 {session_name} 已启用",
                        data={"enabled": True}
                    )
                    self.event_callback(event)

                return True

        return False

    async def disable_client(self, session_name: str) -> bool:
        """
        禁用指定客户端

        Args:
            session_name: 会话名称

        Returns:
            bool: 禁用是否成功
        """
        # 检查是否可以禁用
        if not self.config.can_disable_client(session_name):
            self.logger.warning(f"无法禁用客户端 {session_name}，至少需要保持一个客户端启用")
            return False

        # 先登出客户端
        await self.logout_client(session_name)

        # 更新配置中的客户端状态
        for client_config in self.config.clients:
            if client_config.session_name == session_name:
                client_config.enabled = False
                self.client_status[session_name] = ClientStatus.DISABLED
                self.logger.info(f"客户端 {session_name} 已禁用")

                # 发送状态变更事件
                if self.event_callback:
                    event = create_client_event(
                        EventType.CLIENT_STATUS_CHANGED,
                        session_name,
                        f"客户端 {session_name} 已禁用",
                        ClientStatus.DISABLED.value,
                        data={"enabled": False}
                    )
                    self.event_callback(event)

                return True

        return False

    def get_enabled_clients(self) -> List[str]:
        """获取启用的客户端名称列表"""
        enabled_clients = []
        for client_config in self.config.clients:
            if client_config.enabled and self.client_status.get(client_config.session_name) == ClientStatus.LOGGED_IN:
                enabled_clients.append(client_config.session_name)
        return enabled_clients

    def get_client_status(self, session_name: str) -> Optional[ClientStatus]:
        """获取客户端状态"""
        return self.client_status.get(session_name)

    def get_client_error(self, session_name: str) -> Optional[str]:
        """获取客户端错误信息"""
        return self.client_errors.get(session_name)

    def get_client_last_active(self, session_name: str) -> Optional[datetime]:
        """获取客户端最后活跃时间"""
        return self.last_active.get(session_name)

    def get_client(self, session_name: str) -> Optional[Client]:
        """获取客户端实例"""
        return self.clients.get(session_name)

    async def check_client_connection(self, session_name: str) -> bool:
        """
        检查客户端连接状态

        Args:
            session_name: 会话名称

        Returns:
            bool: 连接是否正常
        """
        if session_name not in self.clients:
            self.logger.debug(f"客户端 {session_name} 不存在")
            return False

        client = self.clients[session_name]

        try:
            # 首先检查基本连接状态
            if not client.is_connected:
                self.logger.debug(f"客户端 {session_name} 未连接")
                self._handle_connection_lost(session_name, "客户端未连接")
                return False

            # 检查客户端状态和最后活跃时间
            current_status = self.client_status.get(session_name)
            if current_status == ClientStatus.LOGGED_IN:
                # 更新最后活跃时间
                self.last_active[session_name] = datetime.now()
                return True
            else:
                self.logger.debug(f"客户端 {session_name} 状态不是已登录: {current_status}")
                return False

        except Exception as e:
            self.logger.warning(f"客户端 {session_name} 连接检查失败: {e}")
            self._handle_connection_lost(session_name, str(e))
            return False

    async def reconnect_client(self, session_name: str) -> bool:
        """
        重连指定客户端

        Args:
            session_name: 会话名称

        Returns:
            bool: 重连是否成功
        """
        if session_name not in self.clients:
            return False

        try:
            # 先停止客户端
            await self.logout_client(session_name)

            # 等待一段时间
            await asyncio.sleep(2)

            # 重新登录
            success = await self.login_client(session_name)

            if success:
                self.logger.info(f"客户端 {session_name} 重连成功")

                # 发送重连成功事件
                if self.event_callback:
                    event = create_client_event(
                        EventType.CLIENT_RECONNECTED,
                        session_name,
                        f"客户端 {session_name} 重连成功"
                    )
                    self.event_callback(event)

            return success

        except Exception as e:
            self.logger.error(f"客户端 {session_name} 重连失败: {e}")
            return False

    def track_api_call(self, session_name: str):
        """
        跟踪API调用（用于限流防护）

        Args:
            session_name: 会话名称
        """
        now = datetime.now()

        # 初始化计数器
        if session_name not in self.api_call_counts:
            self.api_call_counts[session_name] = 0
            self.api_call_timestamps[session_name] = []

        # 增加调用计数
        self.api_call_counts[session_name] += 1
        self.api_call_timestamps[session_name].append(now)

        # 清理1分钟前的时间戳
        one_minute_ago = now.timestamp() - 60
        self.api_call_timestamps[session_name] = [
            ts for ts in self.api_call_timestamps[session_name]
            if ts.timestamp() > one_minute_ago
        ]

    def get_api_call_rate(self, session_name: str) -> int:
        """
        获取指定客户端的API调用频率（每分钟调用次数）

        Args:
            session_name: 会话名称

        Returns:
            int: 每分钟API调用次数
        """
        if session_name not in self.api_call_timestamps:
            return 0

        return len(self.api_call_timestamps[session_name])

    def is_approaching_rate_limit(self, session_name: str, threshold: int = 20) -> bool:
        """
        检查是否接近API调用限制

        Args:
            session_name: 会话名称
            threshold: 阈值（每分钟调用次数）

        Returns:
            bool: 是否接近限制
        """
        return self.get_api_call_rate(session_name) >= threshold

    def get_least_used_client(self) -> Optional[str]:
        """
        获取API调用最少的客户端（用于负载均衡）

        Returns:
            Optional[str]: 最少使用的客户端会话名称
        """
        min_calls = float('inf')
        least_used_client = None

        for session_name in self.clients:
            if (session_name in self.client_status and
                self.client_status[session_name] == ClientStatus.LOGGED_IN):
                calls = self.get_api_call_rate(session_name)
                if calls < min_calls:
                    min_calls = calls
                    least_used_client = session_name

        return least_used_client

    async def shutdown_all_clients(self):
        """关闭所有客户端"""
        self.logger.info("开始关闭所有客户端...")

        tasks = []
        for session_name in self.clients.keys():
            if self.client_status.get(session_name) == ClientStatus.LOGGED_IN:
                tasks.append(self.logout_client(session_name))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.logger.info("所有客户端已关闭")

    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        stats = {
            "total_clients": len(self.clients),
            "enabled_clients": len(self.get_enabled_clients()),
            "logged_in_clients": len([s for s in self.client_status.values() if s == ClientStatus.LOGGED_IN]),
            "failed_clients": len([s for s in self.client_status.values() if s == ClientStatus.LOGIN_FAILED]),
            "status_breakdown": {}
        }

        # 统计各状态的客户端数量
        for status in ClientStatus:
            count = len([s for s in self.client_status.values() if s == status])
            stats["status_breakdown"][status.value] = count

        return stats
