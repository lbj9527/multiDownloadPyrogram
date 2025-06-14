"""
认证管理器
处理多客户端认证策略，避免FLOOD_WAIT错误
"""

import asyncio
import time
from typing import List, Optional, Dict
from pyrogram import Client
from pyrogram.errors import FloodWait

from ..utils.config import AppConfig
from ..utils.logger import get_logger


class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger()
        self.last_auth_time = 0
        self.auth_interval = 30  # 30秒间隔（降低等待时间）
        
    async def authenticate_clients_safely(self, clients: List[Client]) -> List[Client]:
        """
        安全地认证多个客户端
        
        Args:
            clients: 客户端列表
            
        Returns:
            List[Client]: 成功认证的客户端列表
        """
        authenticated_clients = []
        
        for i, client in enumerate(clients):
            try:
                # 检查是否需要等待
                await self._wait_if_needed()
                
                self.logger.info(f"开始认证客户端 {i}")
                await client.start()
                
                authenticated_clients.append(client)
                self.logger.info(f"客户端 {i} 认证成功")
                
                # 更新最后认证时间
                self.last_auth_time = time.time()
                
                # 如果不是最后一个客户端，等待一段时间
                if i < len(clients) - 1:
                    wait_time = self.auth_interval
                    self.logger.info(f"等待 {wait_time} 秒后认证下一个客户端")
                    await asyncio.sleep(wait_time)
                    
            except FloodWait as e:
                self.logger.warning(f"客户端 {i} 认证遇到限流，等待 {e.value} 秒")
                await asyncio.sleep(e.value)
                
                # 重试认证
                try:
                    await client.start()
                    authenticated_clients.append(client)
                    self.logger.info(f"客户端 {i} 重试认证成功")
                except Exception as retry_error:
                    self.logger.error(f"客户端 {i} 重试认证失败: {retry_error}")
                    
            except Exception as e:
                self.logger.error(f"客户端 {i} 认证失败: {e}")
                
        return authenticated_clients
    
    async def _wait_if_needed(self):
        """如果需要，等待一段时间"""
        current_time = time.time()
        time_since_last_auth = current_time - self.last_auth_time
        
        if time_since_last_auth < self.auth_interval:
            wait_time = self.auth_interval - time_since_last_auth
            self.logger.info(f"距离上次认证时间过短，等待 {wait_time:.1f} 秒")
            await asyncio.sleep(wait_time)
    
    def create_session_strategy(self) -> str:
        """
        创建会话策略
        
        Returns:
            str: 推荐的策略
        """
        strategies = {
            "single_client": "使用单个客户端，避免多重认证",
            "different_phones": "使用不同手机号进行认证",
            "session_strings": "使用已有会话字符串",
            "staggered_auth": "分时段认证客户端"
        }
        
        # 根据配置推荐策略
        if self.config.download.client_count == 1:
            return strategies["single_client"]
        else:
            return strategies["staggered_auth"]
    
    async def export_session_string(self, client: Client) -> Optional[str]:
        """
        导出会话字符串
        
        Args:
            client: 已认证的客户端
            
        Returns:
            Optional[str]: 会话字符串
        """
        try:
            if client.is_connected:
                session_string = await client.export_session_string()
                self.logger.info("会话字符串导出成功")
                return session_string
            else:
                self.logger.warning("客户端未连接，无法导出会话字符串")
                return None
        except Exception as e:
            self.logger.error(f"导出会话字符串失败: {e}")
            return None
    
    def get_auth_recommendations(self) -> Dict[str, str]:
        """
        获取认证建议
        
        Returns:
            Dict[str, str]: 认证建议
        """
        return {
            "避免同号多认证": "不要用同一手机号同时认证多个客户端",
            "使用会话字符串": "导出已认证会话的字符串，用于创建新客户端",
            "分时段认证": "如必须多客户端，间隔5分钟以上进行认证",
            "减少客户端数": "临时使用单客户端，避免认证限流",
            "等待限流结束": "如遇FLOOD_WAIT，必须等待指定时间"
        } 