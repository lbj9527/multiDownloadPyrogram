"""
客户端工厂模块
负责创建和配置Pyrogram客户端实例，确保每个客户端使用独立的会话
"""

import os
from typing import List, Optional
from pyrogram import Client

from ..utils.config import AppConfig, get_config
from ..utils.logger import get_logger
from ..utils.exceptions import ClientError, ConfigurationError


class ClientFactory:
    """Pyrogram客户端工厂类"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger()
        self._ensure_session_directories()
    
    def _ensure_session_directories(self):
        """确保会话目录存在"""
        sessions_dir = "sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        
        # 为每个客户端创建独立的工作目录
        for i in range(self.config.download.client_count):
            client_dir = os.path.join(sessions_dir, f"client_{i}")
            os.makedirs(client_dir, exist_ok=True)
    
    def create_client(self, client_index: int) -> Client:
        """
        创建单个Pyrogram客户端
        
        Args:
            client_index: 客户端索引
            
        Returns:
            Client: 配置好的Pyrogram客户端
            
        Raises:
            ClientError: 客户端创建失败
            ConfigurationError: 配置错误
        """
        try:
            if client_index < 0 or client_index >= self.config.download.client_count:
                raise ClientError(f"客户端索引超出范围: {client_index}")
            
            client_name = f"client_{client_index}"
            workdir = os.path.join("sessions", client_name)
            
            # 创建客户端配置
            client = Client(
                name=client_name,
                api_id=self.config.api.api_id,
                api_hash=self.config.api.api_hash,
                proxy=self.config.proxy.to_dict(),
                workdir=workdir,
                sleep_threshold=self.config.download.sleep_threshold,
                no_updates=True,  # 禁用更新接收，专用于下载
                device_model=f"MultiDownload_Client_{client_index}",
                app_version="MultiDownloadPyrogram v1.0"
            )
            
            self.logger.debug(f"创建客户端 {client_name}，工作目录: {workdir}")
            return client
            
        except Exception as e:
            error_msg = f"创建客户端 {client_index} 失败: {str(e)}"
            self.logger.error(error_msg)
            raise ClientError(error_msg, f"client_{client_index}")
    
    def create_multiple_clients(self, count: Optional[int] = None) -> List[Client]:
        """
        创建多个Pyrogram客户端
        
        Args:
            count: 客户端数量，默认使用配置中的数量
            
        Returns:
            List[Client]: 客户端列表
            
        Raises:
            ClientError: 客户端创建失败
        """
        if count is None:
            count = self.config.download.client_count
        
        if count <= 0:
            raise ClientError("客户端数量必须大于0")
        
        clients = []
        created_count = 0
        
        try:
            for i in range(count):
                client = self.create_client(i)
                clients.append(client)
                created_count += 1
            
            self.logger.info(f"成功创建 {created_count} 个客户端")
            return clients
            
        except Exception as e:
            # 清理已创建的客户端
            for client in clients:
                try:
                    if hasattr(client, 'stop'):
                        client.stop()
                except:
                    pass
            
            error_msg = f"创建多个客户端失败，已创建 {created_count} 个: {str(e)}"
            self.logger.error(error_msg)
            raise ClientError(error_msg)
    
    def create_client_from_session_string(self, session_string: str, client_index: int) -> Client:
        """
        从会话字符串创建客户端（内存会话）
        
        Args:
            session_string: 会话字符串
            client_index: 客户端索引
            
        Returns:
            Client: 配置好的Pyrogram客户端
            
        Raises:
            ClientError: 客户端创建失败
        """
        try:
            client_name = f"memory_client_{client_index}"
            
            client = Client(
                name=client_name,
                api_id=self.config.api.api_id,
                api_hash=self.config.api.api_hash,
                session_string=session_string,
                proxy=self.config.proxy.to_dict(),
                sleep_threshold=self.config.download.sleep_threshold,
                no_updates=True,
                device_model=f"MultiDownload_Memory_{client_index}",
                app_version="MultiDownloadPyrogram v1.0"
            )
            
            self.logger.debug(f"从会话字符串创建内存客户端 {client_name}")
            return client
            
        except Exception as e:
            error_msg = f"从会话字符串创建客户端失败: {str(e)}"
            self.logger.error(error_msg)
            raise ClientError(error_msg, f"memory_client_{client_index}")
    
    def validate_client_config(self) -> bool:
        """
        验证客户端配置
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ConfigurationError: 配置错误
        """
        try:
            # 验证API配置
            if not self.config.api.api_id or not self.config.api.api_hash:
                raise ConfigurationError("API ID 和 API Hash 不能为空", "api")
            
            # 验证客户端数量
            if self.config.download.client_count <= 0:
                raise ConfigurationError("客户端数量必须大于0", "client_count")
            
            if self.config.download.client_count > 10:
                self.logger.warning("客户端数量过多可能导致频率限制")
            
            # 验证代理配置
            if self.config.proxy.port <= 0 or self.config.proxy.port > 65535:
                raise ConfigurationError("代理端口无效", "proxy_port")
            
            # 验证下载配置
            if self.config.download.max_concurrent_downloads <= 0:
                raise ConfigurationError("最大并发下载数必须大于0", "max_concurrent_downloads")
            
            self.logger.debug("客户端配置验证通过")
            return True
            
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(f"配置验证失败: {str(e)}")
    
    def cleanup_session_files(self, client_index: Optional[int] = None):
        """
        清理会话文件
        
        Args:
            client_index: 客户端索引，None表示清理所有
        """
        import shutil
        
        try:
            if client_index is not None:
                # 清理指定客户端的会话文件
                client_dir = os.path.join("sessions", f"client_{client_index}")
                if os.path.exists(client_dir):
                    shutil.rmtree(client_dir)
                    self.logger.info(f"清理客户端 {client_index} 的会话文件")
            else:
                # 清理所有会话文件
                sessions_dir = "sessions"
                if os.path.exists(sessions_dir):
                    shutil.rmtree(sessions_dir)
                    self.logger.info("清理所有会话文件")
                    # 重新创建目录
                    self._ensure_session_directories()
                    
        except Exception as e:
            self.logger.error(f"清理会话文件失败: {str(e)}")
    
    def get_session_info(self, client_index: int) -> dict:
        """
        获取客户端会话信息
        
        Args:
            client_index: 客户端索引
            
        Returns:
            dict: 会话信息
        """
        client_dir = os.path.join("sessions", f"client_{client_index}")
        session_file = os.path.join(client_dir, f"client_{client_index}.session")
        
        info = {
            "client_index": client_index,
            "client_name": f"client_{client_index}",
            "workdir": client_dir,
            "session_file": session_file,
            "session_exists": os.path.exists(session_file),
            "workdir_exists": os.path.exists(client_dir)
        }
        
        if info["session_exists"]:
            try:
                stat = os.stat(session_file)
                info["session_size"] = stat.st_size
                info["session_modified"] = stat.st_mtime
            except:
                pass
        
        return info 