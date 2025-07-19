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

from pyrogram import Client
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
        
        # 会话文件目录
        self.session_dir = Path("sessions")
        self.session_dir.mkdir(exist_ok=True)
        
        # 初始化客户端
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化所有客户端"""
        for client_config in self.config.clients:
            self._create_client(client_config)
    
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

            # 创建客户端实例
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
                "sleep_threshold": 10,
                "hide_password": True,
                "max_concurrent_transmissions": 1
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
    
    async def login_client(self, session_name: str, phone_code: Optional[str] = None, 
                          password: Optional[str] = None) -> bool:
        """
        登录指定客户端
        
        Args:
            session_name: 会话名称
            phone_code: 验证码（如果需要）
            password: 双重验证密码（如果需要）
            
        Returns:
            bool: 登录是否成功
        """
        if session_name not in self.clients:
            self.logger.error(f"客户端 {session_name} 不存在")
            return False
        
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
            return False

        client = self.clients[session_name]

        try:
            if not client.is_connected:
                return False

            # 尝试获取用户信息来验证连接
            await client.get_me()
            self.last_active[session_name] = datetime.now()
            return True

        except Exception as e:
            self.logger.warning(f"客户端 {session_name} 连接检查失败: {e}")

            # 发送断连事件
            if self.event_callback:
                event = create_client_event(
                    EventType.CLIENT_DISCONNECTED,
                    session_name,
                    f"客户端 {session_name} 连接断开",
                    data={"error": str(e)}
                )
                self.event_callback(event)

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
