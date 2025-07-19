"""
客户端工厂模块

负责创建和配置Pyrogram客户端，实现多客户端并发支持
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from pyrogram import Client

from utils.config import Config, TelegramConfig, ProxyConfig
from utils.logger import get_logger
from utils.exceptions import ClientError, ClientAuthError
from utils.proxy_manager import get_proxy_manager


class ClientFactory:
    """Pyrogram客户端工厂类"""
    
    def __init__(self, config: Config):
        """
        初始化客户端工厂
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.ClientFactory")
        self.created_clients: List[Client] = []
        
    def create_client(self, 
                     session_name: str,
                     api_id: Optional[int] = None,
                     api_hash: Optional[str] = None,
                     phone_number: Optional[str] = None,
                     session_string: Optional[str] = None,
                     proxy: Optional[Dict[str, Any]] = None,
                     workdir: Optional[str] = None) -> Client:
        """
        创建单个Pyrogram客户端
        
        Args:
            session_name: 会话名称
            api_id: API ID
            api_hash: API Hash
            phone_number: 电话号码
            session_string: 会话字符串
            proxy: 代理配置
            workdir: 工作目录
            
        Returns:
            配置好的Pyrogram客户端
        """
        # 使用配置中的参数作为默认值
        api_id = api_id or self.config.telegram.api_id
        api_hash = api_hash or self.config.telegram.api_hash
        phone_number = phone_number or self.config.telegram.phone_number
        
        # 处理会话字符串 - 只有在有有效值时才使用
        if not session_string:
            session_string = self.config.telegram.session_string
            
        # 验证会话字符串是否有效
        if session_string and len(session_string.strip()) < 50:
            # 会话字符串太短，可能无效，不使用
            self.logger.warning(f"会话字符串太短，可能无效，将使用电话号码认证: {session_name}")
            session_string = None
        
        # 如果没有有效的会话字符串，必须有电话号码
        if not session_string and not phone_number:
            raise ClientError("必须提供会话字符串或电话号码", error_code="MISSING_AUTH_INFO")
        
        # 获取代理配置
        if proxy is None:
            proxy = self.get_proxy_config()
        
        try:
            # 创建工作目录
            if workdir:
                Path(workdir).mkdir(parents=True, exist_ok=True)
            
            # 构建客户端参数
            client_params = {
                "name": session_name,
                "api_id": api_id,
                "api_hash": api_hash,
                "workdir": workdir,
                "max_concurrent_transmissions": self.config.telegram.max_concurrent_transmissions,
                "sleep_threshold": self.config.telegram.sleep_threshold,
                "no_updates": self.config.telegram.no_updates
            }
            
            # 添加代理配置
            if proxy:
                client_params["proxy"] = proxy
            
            # 添加认证信息
            if session_string:
                client_params["session_string"] = session_string
            elif phone_number:
                client_params["phone_number"] = phone_number
            
            # 创建客户端
            client = Client(**client_params)
            
            self.created_clients.append(client)
            self.logger.info(f"客户端创建成功: {session_name}")
            
            return client
            
        except Exception as e:
            self.logger.error(f"创建客户端失败: {session_name}", exc_info=e)
            raise ClientError(f"创建客户端失败: {e}", error_code="CLIENT_CREATION_FAILED")
    
    def get_proxy_config(self) -> Optional[Dict[str, Any]]:
        """
        获取代理配置
        
        Returns:
            代理配置字典
        """
        if not self.config.proxy.enabled:
            return None
        
        try:
            # 尝试使用代理管理器获取当前最佳代理
            proxy_manager = get_proxy_manager()
            proxy = proxy_manager.get_current_proxy_dict()
            
            # 如果代理管理器没有可用代理，使用配置文件中的默认代理
            if proxy is None:
                proxy = self.config.proxy.to_dict()
            
            return proxy
        except Exception as e:
            self.logger.error(f"获取代理配置失败: {e}")
            return None
    
    def create_multiple_clients(self, 
                              count: int,
                              base_session_name: str = "client",
                              session_strings: Optional[List[str]] = None,
                              workdir_base: Optional[str] = None) -> List[Client]:
        """
        创建多个Pyrogram客户端
        
        Args:
            count: 客户端数量
            base_session_name: 基础会话名称
            session_strings: 会话字符串列表
            workdir_base: 工作目录基础路径
            
        Returns:
            客户端列表
        """
        if count < 1:
            raise ClientError("客户端数量必须大于0", error_code="INVALID_CLIENT_COUNT")
        
        clients = []
        
        for i in range(count):
            session_name = f"{base_session_name}_{i}"
            workdir = f"{workdir_base}/{session_name}" if workdir_base else f"sessions/{session_name}"
            
            # 使用会话字符串（如果提供）
            session_string = None
            if session_strings and i < len(session_strings):
                session_string = session_strings[i]
            
            try:
                client = self.create_client(
                    session_name=session_name,
                    session_string=session_string,
                    workdir=workdir
                )
                clients.append(client)
                
            except Exception as e:
                self.logger.error(f"创建客户端失败: {session_name}", exc_info=e)
                # 清理已创建的客户端
                for created_client in clients:
                    try:
                        if created_client.is_connected:
                            asyncio.create_task(created_client.stop())
                    except:
                        pass
                raise ClientError(f"批量创建客户端失败: {e}", error_code="BATCH_CLIENT_CREATION_FAILED")
        
        self.logger.info(f"成功创建 {len(clients)} 个客户端")
        return clients
    
    def create_client_from_session_string(self, 
                                        session_string: str,
                                        session_name: str,
                                        workdir: Optional[str] = None) -> Client:
        """
        从会话字符串创建客户端
        
        Args:
            session_string: 会话字符串
            session_name: 会话名称
            workdir: 工作目录
            
        Returns:
            客户端对象
        """
        return self.create_client(
            session_name=session_name,
            session_string=session_string,
            workdir=workdir
        )
    
    def create_client_from_phone(self, 
                                phone_number: str,
                                session_name: str,
                                workdir: Optional[str] = None) -> Client:
        """
        从电话号码创建客户端
        
        Args:
            phone_number: 电话号码
            session_name: 会话名称
            workdir: 工作目录
            
        Returns:
            客户端对象
        """
        return self.create_client(
            session_name=session_name,
            phone_number=phone_number,
            workdir=workdir
        )
    
    async def test_client_connection(self, client: Client) -> bool:
        """
        测试客户端连接
        
        Args:
            client: 客户端对象
            
        Returns:
            是否连接成功
        """
        try:
            if not client.is_connected:
                await client.start()
            
            # 测试简单的API调用
            me = await client.get_me()
            self.logger.info(f"客户端连接测试成功: {me.first_name} (@{me.username})")
            return True
            
        except Exception as e:
            self.logger.error(f"客户端连接测试失败: {e}")
            return False
    
    async def initialize_client(self, client: Client) -> bool:
        """
        初始化客户端（启动并验证）
        
        Args:
            client: 客户端对象
            
        Returns:
            是否初始化成功
        """
        try:
            # 启动客户端
            await client.start()
            
            # 验证连接
            if await self.test_client_connection(client):
                self.logger.info(f"客户端初始化成功: {client.name}")
                return True
            else:
                self.logger.error(f"客户端初始化失败: {client.name}")
                return False
                
        except Exception as e:
            self.logger.error(f"客户端初始化失败: {client.name}", exc_info=e)
            return False
    
    async def initialize_multiple_clients(self, clients: List[Client]) -> List[Client]:
        """
        初始化多个客户端
        
        Args:
            clients: 客户端列表
            
        Returns:
            成功初始化的客户端列表
        """
        successful_clients = []
        
        # 并发初始化所有客户端
        tasks = [self.initialize_client(client) for client in clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for client, result in zip(clients, results):
            if isinstance(result, bool) and result:
                successful_clients.append(client)
            else:
                self.logger.error(f"客户端初始化失败: {client.name}")
                # 清理失败的客户端
                try:
                    if client.is_connected:
                        await client.stop()
                except:
                    pass
        
        self.logger.info(f"成功初始化 {len(successful_clients)}/{len(clients)} 个客户端")
        return successful_clients
    
    async def cleanup_clients(self, clients: Optional[List[Client]] = None) -> None:
        """
        清理客户端资源
        
        Args:
            clients: 要清理的客户端列表，如果为None则清理所有创建的客户端
        """
        clients_to_cleanup = clients or self.created_clients
        
        if not clients_to_cleanup:
            return
        
        self.logger.info(f"开始清理 {len(clients_to_cleanup)} 个客户端")
        
        # 并发停止所有客户端
        tasks = []
        for client in clients_to_cleanup:
            if client.is_connected:
                task = asyncio.create_task(client.stop())
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 从创建列表中移除
        if clients is None:
            self.created_clients.clear()
        else:
            for client in clients:
                if client in self.created_clients:
                    self.created_clients.remove(client)
        
        self.logger.info("客户端清理完成")
    
    def get_client_info(self, client: Client) -> Dict[str, Any]:
        """
        获取客户端信息
        
        Args:
            client: 客户端对象
            
        Returns:
            客户端信息字典
        """
        return {
            "name": client.name,
            "is_connected": client.is_connected,
            "max_concurrent_transmissions": client.max_concurrent_transmissions,
            "sleep_threshold": client.sleep_threshold,
            "no_updates": client.no_updates,
            "workdir": client.workdir
        }
    
    def get_all_clients_info(self) -> List[Dict[str, Any]]:
        """
        获取所有创建的客户端信息
        
        Returns:
            客户端信息列表
        """
        return [self.get_client_info(client) for client in self.created_clients]
    
    def get_created_clients_count(self) -> int:
        """
        获取已创建的客户端数量
        
        Returns:
            客户端数量
        """
        return len(self.created_clients)
    
    def get_connected_clients_count(self) -> int:
        """
        获取已连接的客户端数量
        
        Returns:
            已连接客户端数量
        """
        return sum(1 for client in self.created_clients if client.is_connected) 