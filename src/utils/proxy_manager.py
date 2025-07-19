"""
代理管理模块

提供代理连接测试、自动切换、代理池管理等功能
"""

import asyncio
import aiohttp
import socket
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .config import ProxyConfig
from .logger import get_logger
from .exceptions import ProxyError, NetworkError


class ProxyType(Enum):
    """代理类型枚举"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    """代理状态枚举"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    SLOW = "slow"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


@dataclass
class ProxyInfo:
    """代理信息"""
    config: ProxyConfig
    status: ProxyStatus = ProxyStatus.UNKNOWN
    last_check: float = 0
    response_time: float = 0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return self.success_count / total


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        """初始化代理管理器"""
        self.logger = get_logger(f"{__name__}.ProxyManager")
        self.proxies: Dict[str, ProxyInfo] = {}
        self.current_proxy: Optional[str] = None
        self.check_interval = 300.0  # 5分钟检查一次
        self.timeout = 10.0
        self.test_urls = [
            "https://httpbin.org/ip",
            "https://api.ipify.org",
            "https://checkip.amazonaws.com"
        ]
        
        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
    def add_proxy(self, name: str, config: ProxyConfig) -> None:
        """
        添加代理
        
        Args:
            name: 代理名称
            config: 代理配置
        """
        self.proxies[name] = ProxyInfo(config=config)
        self.logger.info(f"添加代理: {name} ({config.scheme}://{config.hostname}:{config.port})")
        
        # 如果是第一个代理，设置为当前代理
        if self.current_proxy is None:
            self.current_proxy = name
    
    def remove_proxy(self, name: str) -> None:
        """
        移除代理
        
        Args:
            name: 代理名称
        """
        if name in self.proxies:
            del self.proxies[name]
            self.logger.info(f"移除代理: {name}")
            
            # 如果移除的是当前代理，切换到下一个
            if self.current_proxy == name:
                self.current_proxy = self.get_best_proxy()
    
    def get_proxy_config(self, name: Optional[str] = None) -> Optional[ProxyConfig]:
        """
        获取代理配置
        
        Args:
            name: 代理名称，如果为None则返回当前代理
            
        Returns:
            代理配置
        """
        proxy_name = name or self.current_proxy
        if proxy_name and proxy_name in self.proxies:
            return self.proxies[proxy_name].config
        return None
    
    def get_current_proxy_dict(self) -> Optional[Dict[str, Any]]:
        """
        获取当前代理的字典格式配置
        
        Returns:
            代理配置字典
        """
        config = self.get_proxy_config()
        if config and config.enabled:
            return config.to_dict()
        return None
    
    async def test_proxy(self, name: str) -> Tuple[bool, float]:
        """
        测试代理连接
        
        Args:
            name: 代理名称
            
        Returns:
            (是否成功, 响应时间)
        """
        if name not in self.proxies:
            return False, 0.0
        
        proxy_info = self.proxies[name]
        config = proxy_info.config
        
        self.logger.debug(f"测试代理连接: {name}")
        
        start_time = time.time()
        
        try:
            # 构建代理URL
            if config.username and config.password:
                proxy_url = f"{config.scheme}://{config.username}:{config.password}@{config.hostname}:{config.port}"
            else:
                proxy_url = f"{config.scheme}://{config.hostname}:{config.port}"
            
            # 创建连接器
            connector = aiohttp.TCPConnector(
                connector_timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            # 测试连接
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                for test_url in self.test_urls:
                    try:
                        async with session.get(
                            test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=self.timeout)
                        ) as response:
                            if response.status == 200:
                                response_time = time.time() - start_time
                                proxy_info.response_time = response_time
                                proxy_info.last_check = time.time()
                                proxy_info.success_count += 1
                                
                                # 根据响应时间判断状态
                                if response_time < 2.0:
                                    proxy_info.status = ProxyStatus.HEALTHY
                                elif response_time < 5.0:
                                    proxy_info.status = ProxyStatus.SLOW
                                else:
                                    proxy_info.status = ProxyStatus.UNHEALTHY
                                
                                self.logger.debug(f"代理 {name} 测试成功，响应时间: {response_time:.2f}s")
                                return True, response_time
                    except Exception as e:
                        self.logger.debug(f"代理 {name} 测试URL {test_url} 失败: {e}")
                        continue
                
                # 所有测试URL都失败
                raise Exception("所有测试URL都失败")
                
        except Exception as e:
            response_time = time.time() - start_time
            proxy_info.response_time = response_time
            proxy_info.last_check = time.time()
            proxy_info.error_count += 1
            proxy_info.status = ProxyStatus.FAILED
            
            self.logger.error(f"代理 {name} 测试失败: {e}")
            return False, response_time
    
    async def test_all_proxies(self) -> Dict[str, Tuple[bool, float]]:
        """
        测试所有代理
        
        Returns:
            测试结果字典
        """
        self.logger.info("开始测试所有代理...")
        
        results = {}
        tasks = []
        
        for name in self.proxies:
            task = asyncio.create_task(self.test_proxy(name))
            tasks.append((name, task))
        
        for name, task in tasks:
            try:
                success, response_time = await task
                results[name] = (success, response_time)
            except Exception as e:
                self.logger.error(f"测试代理 {name} 时发生异常: {e}")
                results[name] = (False, 0.0)
        
        self.logger.info("代理测试完成")
        return results
    
    def get_best_proxy(self) -> Optional[str]:
        """
        获取最佳代理
        
        Returns:
            最佳代理名称
        """
        if not self.proxies:
            return None
        
        # 按优先级排序：健康 > 慢速 > 未知 > 不健康 > 失败
        priority_order = [
            ProxyStatus.HEALTHY,
            ProxyStatus.SLOW,
            ProxyStatus.UNKNOWN,
            ProxyStatus.UNHEALTHY,
            ProxyStatus.FAILED
        ]
        
        best_proxy = None
        best_score = float('inf')
        
        for name, proxy_info in self.proxies.items():
            if not proxy_info.config.enabled:
                continue
                
            # 计算分数（越小越好）
            status_score = priority_order.index(proxy_info.status)
            time_score = proxy_info.response_time
            success_rate = proxy_info.success_rate
            
            # 综合分数
            score = status_score * 100 + time_score * 10 + (1 - success_rate) * 50
            
            if score < best_score:
                best_score = score
                best_proxy = name
        
        return best_proxy
    
    async def switch_to_best_proxy(self) -> bool:
        """
        切换到最佳代理
        
        Returns:
            是否成功切换
        """
        best_proxy = self.get_best_proxy()
        if best_proxy and best_proxy != self.current_proxy:
            old_proxy = self.current_proxy
            self.current_proxy = best_proxy
            self.logger.info(f"代理切换: {old_proxy} -> {best_proxy}")
            return True
        return False
    
    async def auto_switch_proxy(self) -> bool:
        """
        自动切换代理（当前代理不可用时）
        
        Returns:
            是否成功切换
        """
        if not self.current_proxy:
            return False
        
        # 测试当前代理
        success, _ = await self.test_proxy(self.current_proxy)
        if success:
            return False  # 当前代理正常，不需要切换
        
        # 当前代理不可用，切换到最佳代理
        return await self.switch_to_best_proxy()
    
    def get_proxy_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取代理统计信息
        
        Returns:
            代理统计信息
        """
        stats = {}
        for name, proxy_info in self.proxies.items():
            stats[name] = {
                "status": proxy_info.status.value,
                "response_time": proxy_info.response_time,
                "success_rate": proxy_info.success_rate,
                "last_check": proxy_info.last_check,
                "error_count": proxy_info.error_count,
                "success_count": proxy_info.success_count,
                "enabled": proxy_info.config.enabled
            }
        return stats
    
    async def start_monitoring(self) -> None:
        """启动代理监控"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_proxies())
        self.logger.info("代理监控已启动")
    
    async def stop_monitoring(self) -> None:
        """停止代理监控"""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("代理监控已停止")
    
    async def _monitor_proxies(self) -> None:
        """代理监控任务"""
        while self._is_monitoring:
            try:
                # 测试所有代理
                await self.test_all_proxies()
                
                # 自动切换到最佳代理
                await self.switch_to_best_proxy()
                
                # 等待下次检查
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"代理监控任务异常: {e}")
                await asyncio.sleep(10)  # 发生异常时短暂等待
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ProxyManager(proxies={len(self.proxies)}, current={self.current_proxy})"


# 全局代理管理器实例
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """获取全局代理管理器实例"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def setup_proxy_manager(proxy_configs: List[Tuple[str, ProxyConfig]]) -> ProxyManager:
    """
    设置代理管理器
    
    Args:
        proxy_configs: 代理配置列表 [(名称, 配置)]
        
    Returns:
        代理管理器实例
    """
    manager = get_proxy_manager()
    
    for name, config in proxy_configs:
        manager.add_proxy(name, config)
    
    return manager


async def test_proxy_connection(config: ProxyConfig) -> bool:
    """
    测试单个代理连接
    
    Args:
        config: 代理配置
        
    Returns:
        是否连接成功
    """
    manager = ProxyManager()
    manager.add_proxy("test", config)
    success, _ = await manager.test_proxy("test")
    return success 