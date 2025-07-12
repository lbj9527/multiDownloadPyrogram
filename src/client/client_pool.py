"""
客户端池管理模块

负责管理多个Pyrogram客户端的并发操作、负载均衡和故障转移
"""

import asyncio
import random
from typing import List, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass
from pyrogram import Client
from pyrogram.errors import FloodWait

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import ClientError, ClientPoolError
from .client_factory import ClientFactory
from .client_manager import ClientManager, ClientStatus


@dataclass
class PoolMetrics:
    """客户端池性能指标"""
    total_clients: int = 0
    active_clients: int = 0
    failed_clients: int = 0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    load_balancing_decisions: int = 0
    failover_count: int = 0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    def get_client_availability(self) -> float:
        """获取客户端可用率"""
        if self.total_clients == 0:
            return 0.0
        return (self.active_clients / self.total_clients) * 100


class ClientPool:
    """客户端池管理器"""
    
    def __init__(self, config: Config, pool_size: Optional[int] = None):
        """
        初始化客户端池
        
        Args:
            config: 配置对象
            pool_size: 池大小，如果为None则使用配置中的max_clients
        """
        self.config = config
        self.pool_size = pool_size or config.download.max_clients
        self.logger = get_logger(f"{__name__}.ClientPool")
        
        # 客户端管理
        self.client_managers: List[ClientManager] = []
        self.client_factory = ClientFactory(config)
        
        # 负载均衡
        self._current_client_index = 0
        self._client_usage_count: Dict[str, int] = {}
        self._client_load_scores: Dict[str, float] = {}
        
        # 性能指标
        self.metrics = PoolMetrics()
        
        # 配置
        self.load_balancing_strategy = "round_robin"
        self.failover_enabled = True
        self.health_check_interval = 300.0
        self.max_retries_per_client = 3
        
        # 状态监控
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # 回调函数
        self.on_client_added: Optional[Callable] = None
        self.on_client_removed: Optional[Callable] = None
        self.on_client_failed: Optional[Callable] = None
        self.on_failover: Optional[Callable] = None
    
    async def initialize(self, session_strings: Optional[List[str]] = None) -> bool:
        """
        初始化客户端池
        
        Args:
            session_strings: 会话字符串列表
            
        Returns:
            是否初始化成功
        """
        self.logger.info(f"正在初始化客户端池 (大小: {self.pool_size})")
        
        try:
            # 创建客户端
            clients = self.client_factory.create_multiple_clients(
                count=self.pool_size,
                session_strings=session_strings
            )
            
            # 创建客户端管理器
            for i, client in enumerate(clients):
                client_id = f"client_{i}"
                client_manager = ClientManager(client, client_id)
                
                # 设置回调
                client_manager.set_callbacks(
                    on_status_change=self._on_client_status_change,
                    on_error=self._on_client_error,
                    on_reconnect=self._on_client_reconnect
                )
                
                self.client_managers.append(client_manager)
                self._client_usage_count[client_id] = 0
                self._client_load_scores[client_id] = 0.0
            
            # 初始化所有客户端
            successful_clients = []
            tasks = [manager.start() for manager in self.client_managers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for manager, result in zip(self.client_managers, results):
                if isinstance(result, bool) and result:
                    successful_clients.append(manager)
                else:
                    self.logger.error(f"客户端初始化失败: {manager.client_id}")
            
            # 更新指标
            self.metrics.total_clients = len(self.client_managers)
            self.metrics.active_clients = len(successful_clients)
            self.metrics.failed_clients = self.metrics.total_clients - self.metrics.active_clients
            
            if successful_clients:
                self.logger.info(f"客户端池初始化成功: {len(successful_clients)}/{self.pool_size}")
                return True
            else:
                self.logger.error("没有客户端成功初始化")
                return False
                
        except Exception as e:
            self.logger.error(f"客户端池初始化失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭客户端池"""
        self.logger.info("正在关闭客户端池...")
        
        # 停止所有客户端
        tasks = [manager.stop() for manager in self.client_managers]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 清理资源
        await self.client_factory.cleanup_clients()
        self.client_managers.clear()
        self._client_usage_count.clear()
        self._client_load_scores.clear()
        
        self.logger.info("客户端池已关闭")
    
    def get_available_clients(self) -> List[ClientManager]:
        """获取可用的客户端管理器"""
        return [manager for manager in self.client_managers if manager.is_available()]
    
    def get_client_by_id(self, client_id: str) -> Optional[ClientManager]:
        """根据ID获取客户端管理器"""
        for manager in self.client_managers:
            if manager.client_id == client_id:
                return manager
        return None
    
    def select_client(self, strategy: Optional[str] = None) -> Optional[ClientManager]:
        """
        选择一个客户端
        
        Args:
            strategy: 负载均衡策略
            
        Returns:
            选中的客户端管理器
        """
        available_clients = self.get_available_clients()
        
        if not available_clients:
            # 尝试重连可重试的客户端
            retryable_clients = [manager for manager in self.client_managers if manager.can_retry()]
            if retryable_clients:
                self.logger.info(f"尝试重连 {len(retryable_clients)} 个客户端...")
                # 选择第一个可重试的客户端
                return retryable_clients[0]
            
            self.logger.warning("没有可用的客户端")
            return None
        
        strategy = strategy or self.load_balancing_strategy
        
        if strategy == "round_robin":
            return self._select_round_robin(available_clients)
        elif strategy == "least_used":
            return self._select_least_used(available_clients)
        elif strategy == "random":
            return random.choice(available_clients)
        else:
            self.logger.warning(f"未知的负载均衡策略: {strategy}，使用轮询")
            return self._select_round_robin(available_clients)
    
    def _select_round_robin(self, clients: List[ClientManager]) -> ClientManager:
        """轮询选择客户端"""
        if not clients:
            return None
        
        client = clients[self._current_client_index % len(clients)]
        self._current_client_index += 1
        self.metrics.load_balancing_decisions += 1
        
        return client
    
    def _select_least_used(self, clients: List[ClientManager]) -> ClientManager:
        """选择使用次数最少的客户端"""
        if not clients:
            return None
        
        # 按使用次数排序
        sorted_clients = sorted(clients, key=lambda c: self._client_usage_count.get(c.client_id, 0))
        self.metrics.load_balancing_decisions += 1
        
        return sorted_clients[0]
    
    def _on_client_status_change(self, client_id: str, old_status: ClientStatus, 
                                new_status: ClientStatus, message: Optional[str] = None):
        """客户端状态变更回调"""
        self.logger.debug(f"客户端状态变更: {client_id} {old_status.value} -> {new_status.value}")
    
    def _on_client_error(self, client_id: str, error: Exception):
        """客户端错误回调"""
        self.logger.error(f"客户端错误: {client_id} - {error}")
    
    def _on_client_reconnect(self, client_id: str, attempt: int):
        """客户端重连回调"""
        self.logger.info(f"客户端重连: {client_id} (尝试 {attempt})")
    
    def get_pool_info(self) -> Dict[str, Any]:
        """获取池信息"""
        return {
            "pool_size": self.pool_size,
            "total_clients": len(self.client_managers),
            "available_clients": len(self.get_available_clients()),
            "metrics": {
                "total_clients": self.metrics.total_clients,
                "active_clients": self.metrics.active_clients,
                "failed_clients": self.metrics.failed_clients,
                "success_rate": self.metrics.get_success_rate(),
                "client_availability": self.metrics.get_client_availability()
            }
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.shutdown() 