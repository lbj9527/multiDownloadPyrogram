"""
客户端管理器模块
负责管理多个Pyrogram客户端的生命周期，使用独立会话文件确保稳定性
"""

import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager
from pyrogram import Client
from pyrogram.errors import FloodWait

from ..utils.config import AppConfig, get_config
from ..utils.logger import get_logger
from ..utils.exceptions import ClientError, MultiDownloadError
from .client_factory import ClientFactory
from .auth_manager import AuthManager


class ClientManager:
    """客户端管理器"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger()
        self.client_factory = ClientFactory(self.config)
        self.auth_manager = AuthManager(self.config)
        self.clients: List[Client] = []
    
    async def initialize_clients(self) -> List[Client]:
        """
        初始化客户端列表
        使用独立会话文件，确保多客户端稳定性
        
        Returns:
            List[Client]: 初始化的客户端列表
        """
        try:
            client_count = self.config.download.client_count
            self.logger.info(f"初始化 {client_count} 个客户端")
            
            if client_count == 1:
                # 单客户端模式
                return await self._create_single_client()
            else:
                # 多客户端模式，使用独立会话文件
                return await self._create_multiple_clients_with_independent_sessions()
                
        except Exception as e:
            self.logger.error(f"初始化客户端失败: {str(e)}")
            raise ClientError(f"初始化客户端失败: {str(e)}")
    
    async def _create_single_client(self) -> List[Client]:
        """创建单个客户端"""
        client = self.client_factory.create_client(0)
        return [client]
    
    async def _create_multiple_clients_with_independent_sessions(self) -> List[Client]:
        """
        使用独立会话文件创建多个客户端
        每个客户端都有自己的会话文件，避免认证问题
        
        Returns:
            List[Client]: 客户端列表
        """
        client_count = self.config.download.client_count
        clients = []
        
        self.logger.info("创建多个独立会话客户端...")
        self.logger.warning("注意: 每个客户端需要独立认证，请按提示完成每个客户端的登录")
        
        try:
            # 创建所有客户端实例
            for i in range(client_count):
                client = self.client_factory.create_client(i)
                clients.append(client)
            
            # 安全认证所有客户端（带间隔）
            authenticated_clients = await self.auth_manager.authenticate_clients_safely(clients)
            
            if not authenticated_clients:
                raise ClientError("没有成功认证的客户端")
            
            if len(authenticated_clients) < client_count:
                self.logger.warning(
                    f"部分客户端认证失败，预期 {client_count} 个，实际 {len(authenticated_clients)} 个"
                )
            
            self.logger.info(f"成功创建并认证 {len(authenticated_clients)} 个客户端")
            return authenticated_clients
            
        except Exception as e:
            # 清理已创建的客户端
            for client in clients:
                try:
                    if client.is_connected:
                        await client.stop()
                except:
                    pass
            
            self.logger.error(f"多客户端创建失败: {e}")
            raise ClientError(f"多客户端创建失败: {e}")
    
    async def start_clients(self, clients: List[Client]) -> List[Client]:
        """
        启动客户端列表
        
        Args:
            clients: 客户端列表
            
        Returns:
            List[Client]: 成功启动的客户端列表
        """
        if not clients:
            raise ClientError("客户端列表为空")
        
        # 如果使用独立认证，客户端应该已经启动
        started_clients = []
        for i, client in enumerate(clients):
            if client.is_connected:
                started_clients.append(client)
                self.logger.info(f"客户端 {i} 已连接")
            else:
                self.logger.warning(f"客户端 {i} 未连接，尝试启动...")
                try:
                    await client.start()
                    started_clients.append(client)
                    self.logger.info(f"客户端 {i} 启动成功")
                except Exception as e:
                    self.logger.error(f"启动客户端 {i} 失败: {e}")
        
        if not started_clients:
            raise ClientError("没有成功启动的客户端")
        
        self.logger.info(f"成功启动 {len(started_clients)}/{len(clients)} 个客户端")
        return started_clients
    
    async def stop_clients(self, clients: List[Client]):
        """
        停止客户端列表
        
        Args:
            clients: 客户端列表
        """
        if not clients:
            return
        
        stop_tasks = []
        for i, client in enumerate(clients):
            if client.is_connected:
                task = self._stop_single_client(client, i)
                stop_tasks.append(task)
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.logger.info("所有客户端已停止")
    
    async def _stop_single_client(self, client: Client, index: int):
        """停止单个客户端"""
        try:
            await client.stop()
            self.logger.debug(f"客户端 {index} 停止成功")
        except Exception as e:
            self.logger.error(f"停止客户端 {index} 失败: {e}")
    
    @asynccontextmanager
    async def managed_clients(self):
        """
        客户端上下文管理器
        自动管理客户端的创建、启动和清理
        
        Yields:
            List[Client]: 可用的客户端列表
        """
        clients = []
        try:
            # 初始化客户端
            clients = await self.initialize_clients()
            self.clients = clients
            
            # 启动客户端
            active_clients = await self.start_clients(clients)
            
            yield active_clients
            
        except Exception as e:
            self.logger.error(f"客户端管理器错误: {str(e)}")
            raise MultiDownloadError(f"客户端管理失败: {str(e)}")
        finally:
            # 清理资源
            await self.cleanup()
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 是否健康
        """
        try:
            if not self.clients:
                return False
            
            healthy_count = 0
            for client in self.clients:
                if client.is_connected:
                    healthy_count += 1
            
            health_ratio = healthy_count / len(self.clients)
            is_healthy = health_ratio >= 0.5  # 至少50%的客户端正常
            
            self.logger.info(f"健康检查: {healthy_count}/{len(self.clients)} 客户端正常 ({health_ratio:.1%})")
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.clients:
                await self.stop_clients(self.clients)
                self.clients.clear()
            
            self.logger.info("客户端管理器清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {str(e)}")
    
    def get_client_stats(self) -> dict:
        """
        获取客户端统计信息
        
        Returns:
            dict: 统计信息
        """
        if not self.clients:
            return {"total": 0, "connected": 0, "disconnected": 0}
        
        connected = sum(1 for client in self.clients if client.is_connected)
        disconnected = len(self.clients) - connected
        
        return {
            "total": len(self.clients),
            "connected": connected,
            "disconnected": disconnected,
            "health_ratio": connected / len(self.clients) if self.clients else 0
        } 