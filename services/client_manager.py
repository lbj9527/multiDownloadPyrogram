"""
客户端管理服务
负责Pyrogram客户端的创建、连接、管理
"""

import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
from pyrogram.client import Client

from models import ClientInfo, ClientStatus
from config import app_settings
from utils import get_logger, retry_async

logger = get_logger(__name__)


class ClientManager:
    """客户端管理器"""
    
    def __init__(self):
        self.clients: Dict[str, Client] = {}
        self.client_infos: Dict[str, ClientInfo] = {}
        self.telegram_config = app_settings.telegram
        self.download_config = app_settings.download
    
    async def initialize_clients(self) -> List[ClientInfo]:
        """
        初始化所有客户端
        
        Returns:
            客户端信息列表
        """
        logger.info("开始初始化客户端...")
        
        session_files = app_settings.get_session_files()
        
        if not session_files:
            raise ValueError("未找到会话文件")
        
        client_infos = []
        
        for i, session_file in enumerate(session_files, 1):
            client_name = f"client_{i}"
            
            try:
                # 创建客户端信息
                client_info = ClientInfo(
                    name=client_name,
                    session_file=session_file
                )
                
                # 创建Pyrogram客户端
                client = self._create_client(client_name, session_file)
                
                # 存储客户端和信息
                self.clients[client_name] = client
                self.client_infos[client_name] = client_info
                
                client_infos.append(client_info)
                
                logger.info(f"客户端 {client_name} 初始化完成")
                
            except Exception as e:
                logger.error(f"初始化客户端 {client_name} 失败: {e}")
        
        logger.info(f"客户端初始化完成，共 {len(client_infos)} 个客户端")
        return client_infos
    
    def _create_client(self, name: str, session_file: str) -> Client:
        """
        创建Pyrogram客户端
        
        Args:
            name: 客户端名称
            session_file: 会话文件路径
            
        Returns:
            Pyrogram客户端
        """
        client_config = {
            "name": session_file,
            "api_id": self.telegram_config.api_id,
            "api_hash": self.telegram_config.api_hash,
            "workdir": "sessions",
            "workers": 4,
            "sleep_threshold": 10
        }

        # 添加代理配置
        if self.telegram_config.proxy:
            client_config["proxy"] = self.telegram_config.proxy

        return Client(**client_config)
    
    async def connect_all_clients(self) -> List[str]:
        """
        连接所有客户端
        
        Returns:
            成功连接的客户端名称列表
        """
        logger.info("开始连接所有客户端...")
        
        connected_clients = []
        connection_tasks = []
        
        for client_name in self.clients.keys():
            task = self._connect_client_with_info(client_name)
            connection_tasks.append(task)
        
        # 并发连接所有客户端
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        for client_name, result in zip(self.clients.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"连接客户端 {client_name} 失败: {result}")
                self.client_infos[client_name].report_error(str(result))
            elif result:
                connected_clients.append(client_name)
                logger.info(f"客户端 {client_name} 连接成功")
        
        logger.info(f"客户端连接完成，成功连接 {len(connected_clients)} 个客户端")
        return connected_clients
    
    @retry_async(max_retries=3, delay=2.0)
    async def _connect_client_with_info(self, client_name: str) -> bool:
        """
        连接单个客户端并更新信息
        
        Args:
            client_name: 客户端名称
            
        Returns:
            是否连接成功
        """
        try:
            client = self.clients[client_name]
            client_info = self.client_infos[client_name]
            
            # 更新状态为连接中
            client_info.status = ClientStatus.CONNECTING
            
            # 连接客户端
            await client.start()
            
            # 更新连接信息
            client_info.connect()
            
            return True
            
        except Exception as e:
            logger.error(f"连接客户端 {client_name} 失败: {e}")
            self.client_infos[client_name].report_error(str(e))
            return False
    
    async def disconnect_all_clients(self):
        """断开所有客户端连接"""
        logger.info("开始断开所有客户端连接...")
        
        disconnect_tasks = []
        
        for client_name in self.clients.keys():
            task = self._disconnect_client_with_info(client_name)
            disconnect_tasks.append(task)
        
        # 并发断开所有客户端
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        logger.info("所有客户端已断开连接")
    
    async def _disconnect_client_with_info(self, client_name: str):
        """
        断开单个客户端并更新信息
        
        Args:
            client_name: 客户端名称
        """
        try:
            client = self.clients[client_name]
            client_info = self.client_infos[client_name]
            
            # 断开连接
            await client.stop()
            
            # 更新断开信息
            client_info.disconnect()
            
            logger.debug(f"客户端 {client_name} 已断开连接")
            
        except Exception as e:
            logger.error(f"断开客户端 {client_name} 失败: {e}")
    
    def get_client(self, client_name: str) -> Optional[Client]:
        """
        获取客户端实例
        
        Args:
            client_name: 客户端名称
            
        Returns:
            客户端实例
        """
        return self.clients.get(client_name)
    
    def get_client_info(self, client_name: str) -> Optional[ClientInfo]:
        """
        获取客户端信息
        
        Args:
            client_name: 客户端名称
            
        Returns:
            客户端信息
        """
        return self.client_infos.get(client_name)
    
    def get_available_clients(self) -> List[str]:
        """
        获取可用的客户端列表
        
        Returns:
            可用客户端名称列表
        """
        available_clients = []
        
        for client_name, client_info in self.client_infos.items():
            if client_info.is_available:
                available_clients.append(client_name)
        
        return available_clients
    
    def get_busy_clients(self) -> List[str]:
        """
        获取忙碌的客户端列表
        
        Returns:
            忙碌客户端名称列表
        """
        busy_clients = []
        
        for client_name, client_info in self.client_infos.items():
            if client_info.is_busy:
                busy_clients.append(client_name)
        
        return busy_clients
    
    def update_client_task(self, client_name: str, task_id: Optional[str]):
        """
        更新客户端任务信息
        
        Args:
            client_name: 客户端名称
            task_id: 任务ID
        """
        client_info = self.client_infos.get(client_name)
        if client_info:
            if task_id:
                client_info.start_task(task_id)
            else:
                # 任务完成，更新状态
                client_info.status = ClientStatus.CONNECTED
                client_info.current_task_id = None
                client_info.update_activity()
    
    def report_client_error(self, client_name: str, error_message: str):
        """
        报告客户端错误
        
        Args:
            client_name: 客户端名称
            error_message: 错误消息
        """
        client_info = self.client_infos.get(client_name)
        if client_info:
            client_info.report_error(error_message)
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        获取客户端统计信息
        
        Returns:
            统计信息字典
        """
        total_clients = len(self.client_infos)
        connected_clients = sum(1 for info in self.client_infos.values() if info.is_connected)
        available_clients = len(self.get_available_clients())
        busy_clients = len(self.get_busy_clients())
        error_clients = sum(1 for info in self.client_infos.values() if info.status == ClientStatus.ERROR)
        
        return {
            "total_clients": total_clients,
            "connected_clients": connected_clients,
            "available_clients": available_clients,
            "busy_clients": busy_clients,
            "error_clients": error_clients,
            "client_details": {
                name: info.to_dict() 
                for name, info in self.client_infos.items()
            }
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """
        健康检查所有客户端
        
        Returns:
            客户端健康状态字典
        """
        health_status = {}
        
        for client_name, client in self.clients.items():
            try:
                # 简单的健康检查：获取自己的信息
                if client.is_connected:
                    me = await client.get_me()
                    health_status[client_name] = me is not None
                else:
                    health_status[client_name] = False
                    
            except Exception as e:
                logger.error(f"客户端 {client_name} 健康检查失败: {e}")
                health_status[client_name] = False
                self.report_client_error(client_name, str(e))
        
        return health_status
