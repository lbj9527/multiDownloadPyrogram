"""
客户端管理器
从test_downloader_stream.py提取的客户端管理逻辑
"""
import asyncio
from typing import List, Dict, Any, Optional
from pyrogram.client import Client
from pyrogram.errors import FloodWait

from config.settings import TelegramConfig
from utils.logging_utils import LoggerMixin
from utils.network_utils import NetworkUtils
from .session_manager import SessionManager

class ClientManager(LoggerMixin):
    """客户端管理器"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.session_manager = SessionManager(config.session_directory)
        self.clients: List[Client] = []
        self.client_stats: Dict[str, Any] = {}
        self._proxy_config = None
    
    async def initialize_clients(self, session_names: Optional[List[str]] = None) -> List[Client]:
        """
        初始化多个客户端
        从test_downloader_stream.py提取的逻辑
        """
        if session_names is None:
            session_names = self.config.session_names
        
        # 验证会话文件
        available_sessions = self.session_manager.get_available_sessions(session_names)
        if not available_sessions:
            raise RuntimeError("没有可用的会话文件")
        
        self.log_info(f"初始化 {len(available_sessions)} 个客户端...")
        
        # 创建代理配置
        self._proxy_config = NetworkUtils.create_proxy_config(
            self.config.proxy_host, 
            self.config.proxy_port
        )
        
        # 创建客户端
        clients = []
        for session_name in available_sessions:
            try:
                client = self._create_client(session_name)
                clients.append(client)
                self.log_info(f"创建客户端: {session_name}")
            except Exception as e:
                self.log_error(f"创建客户端失败 {session_name}: {e}")
        
        self.clients = clients
        return clients
    
    def _create_client(self, session_name: str) -> Client:
        """
        创建单个客户端
        从test_downloader_stream.py提取的逻辑
        """
        session_file = self.session_manager.get_session_file_path(session_name)
        
        client = Client(
            name=session_name,
            api_id=self.config.api_id,
            api_hash=self.config.api_hash,
            workdir=str(self.config.session_directory),
            proxy=self._proxy_config
        )
        
        return client
    
    async def start_all_clients(self) -> None:
        """
        启动所有客户端
        从test_downloader_stream.py提取的逻辑
        """
        if not self.clients:
            raise RuntimeError("没有可用的客户端")
        
        self.log_info(f"启动 {len(self.clients)} 个客户端...")
        
        start_tasks = []
        for client in self.clients:
            task = self._start_single_client(client)
            start_tasks.append(task)
        
        # 并发启动所有客户端
        results = await asyncio.gather(*start_tasks, return_exceptions=True)
        
        # 检查启动结果
        successful_clients = []
        for i, (client, result) in enumerate(zip(self.clients, results)):
            if isinstance(result, Exception):
                self.log_error(f"客户端 {client.name} 启动失败: {result}")
            else:
                successful_clients.append(client)
                self.log_info(f"客户端 {client.name} 启动成功")
        
        self.clients = successful_clients
        
        if not self.clients:
            raise RuntimeError("所有客户端启动失败")
        
        self.log_info(f"成功启动 {len(self.clients)} 个客户端")
    
    async def _start_single_client(self, client: Client) -> None:
        """启动单个客户端"""
        try:
            await client.start()
            
            # 获取客户端信息
            me = await client.get_me()
            self.client_stats[client.name] = {
                "user_id": me.id,
                "username": me.username,
                "phone": me.phone_number,
                "first_name": me.first_name,
                "last_name": me.last_name
            }
            
        except FloodWait as e:
            self.log_warning(f"客户端 {client.name} 遇到频率限制，等待 {e.value} 秒...")
            await asyncio.sleep(e.value)
            await client.start()
        except Exception as e:
            self.log_error(f"启动客户端 {client.name} 失败: {e}")
            raise
    
    async def stop_all_clients(self) -> None:
        """停止所有客户端"""
        if not self.clients:
            return
        
        self.log_info(f"停止 {len(self.clients)} 个客户端...")
        
        stop_tasks = []
        for client in self.clients:
            if client.is_connected:
                task = client.stop()
                stop_tasks.append(task)
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.log_info("所有客户端已停止")
    
    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "total_clients": len(self.clients),
            "active_clients": len([c for c in self.clients if c.is_connected]),
            "client_details": self.client_stats.copy()
        }
    
    def get_clients(self) -> List[Client]:
        """获取客户端列表"""
        return self.clients.copy()
    
    def get_client_names(self) -> List[str]:
        """获取客户端名称列表"""
        return [client.name for client in self.clients]
