#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理工具模块
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from .logger import get_logger


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        """初始化代理管理器"""
        self.logger = get_logger(__name__)
        self._proxy_config = None
    
    def set_proxy_config(self, config: Dict[str, Any]):
        """
        设置代理配置
        
        Args:
            config: 代理配置字典
        """
        self._proxy_config = config.copy() if config else None
        self.logger.debug(f"代理配置已更新: {self._proxy_config}")
    
    def get_proxy_url(self) -> Optional[str]:
        """
        获取代理URL
        
        Returns:
            Optional[str]: 代理URL，如果未启用代理则返回None
        """
        if not self._proxy_config or not self._proxy_config.get("enabled", False):
            return None
        
        try:
            proxy_type = self._proxy_config.get("type", "socks5")
            host = self._proxy_config.get("host", "127.0.0.1")
            port = self._proxy_config.get("port", 1080)
            username = self._proxy_config.get("username", "")
            password = self._proxy_config.get("password", "")
            
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{proxy_type}://{host}:{port}"
            
            return proxy_url
            
        except Exception as e:
            self.logger.error(f"构建代理URL失败: {e}")
            return None
    
    def get_pyrogram_proxy(self) -> Optional[Dict[str, Any]]:
        """
        获取Pyrogram格式的代理配置
        
        Returns:
            Optional[Dict[str, Any]]: Pyrogram代理配置，如果未启用代理则返回None
        """
        if not self._proxy_config or not self._proxy_config.get("enabled", False):
            return None
        
        try:
            proxy_type = self._proxy_config.get("type", "socks5")
            host = self._proxy_config.get("host", "127.0.0.1")
            port = self._proxy_config.get("port", 1080)
            username = self._proxy_config.get("username", "")
            password = self._proxy_config.get("password", "")
            
            # Pyrogram代理配置格式
            proxy_config = {
                "scheme": proxy_type,
                "hostname": host,
                "port": port
            }
            
            if username:
                proxy_config["username"] = username
            if password:
                proxy_config["password"] = password
            
            return proxy_config
            
        except Exception as e:
            self.logger.error(f"构建Pyrogram代理配置失败: {e}")
            return None
    
    async def test_proxy_connection(self, test_url: str = "https://api.telegram.org") -> Tuple[bool, str]:
        """
        测试代理连接
        
        Args:
            test_url: 测试URL
            
        Returns:
            Tuple[bool, str]: (是否成功, 结果消息)
        """
        if not self._proxy_config or not self._proxy_config.get("enabled", False):
            return False, "代理未启用"
        
        proxy_url = self.get_proxy_url()
        if not proxy_url:
            return False, "代理配置无效"
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector()
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                async with session.get(test_url, proxy=proxy_url) as response:
                    if response.status == 200:
                        return True, f"连接成功 (HTTP {response.status})"
                    else:
                        return False, f"HTTP {response.status}"
                        
        except aiohttp.ClientProxyConnectionError as e:
            return False, f"代理连接失败: {e}"
        except aiohttp.ClientConnectorError as e:
            return False, f"连接错误: {e}"
        except asyncio.TimeoutError:
            return False, "连接超时"
        except Exception as e:
            return False, f"测试失败: {e}"
    
    def validate_proxy_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证代理配置
        
        Args:
            config: 代理配置字典
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        try:
            if not config.get("enabled", False):
                return True, "代理未启用"
            
            # 检查必需字段
            host = config.get("host", "").strip()
            if not host:
                return False, "代理主机不能为空"
            
            port = config.get("port")
            if not isinstance(port, int) or port <= 0 or port > 65535:
                return False, "代理端口无效 (1-65535)"
            
            proxy_type = config.get("type", "").lower()
            if proxy_type not in ["socks5", "socks4", "http", "https"]:
                return False, "不支持的代理类型"
            
            # 检查主机名格式
            if not self._is_valid_hostname(host):
                return False, "代理主机名格式无效"
            
            return True, "配置有效"
            
        except Exception as e:
            return False, f"验证失败: {e}"
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """
        验证主机名格式
        
        Args:
            hostname: 主机名
            
        Returns:
            bool: 是否有效
        """
        try:
            import re
            import ipaddress
            
            # 尝试解析为IP地址
            try:
                ipaddress.ip_address(hostname)
                return True
            except ValueError:
                pass
            
            # 验证域名格式
            hostname_pattern = re.compile(
                r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
            )
            
            return bool(hostname_pattern.match(hostname))
            
        except Exception:
            return False
    
    def get_proxy_info(self) -> str:
        """
        获取代理信息字符串
        
        Returns:
            str: 代理信息
        """
        if not self._proxy_config or not self._proxy_config.get("enabled", False):
            return "未使用代理"
        
        try:
            proxy_type = self._proxy_config.get("type", "socks5")
            host = self._proxy_config.get("host", "127.0.0.1")
            port = self._proxy_config.get("port", 1080)
            username = self._proxy_config.get("username", "")
            
            if username:
                return f"{proxy_type.upper()}代理: {username}@{host}:{port}"
            else:
                return f"{proxy_type.upper()}代理: {host}:{port}"
                
        except Exception as e:
            return f"代理配置错误: {e}"


# 全局代理管理器实例
proxy_manager = ProxyManager()


def get_proxy_manager() -> ProxyManager:
    """
    获取代理管理器实例
    
    Returns:
        ProxyManager: 代理管理器实例
    """
    return proxy_manager


def update_proxy_config(config: Dict[str, Any]):
    """
    更新代理配置
    
    Args:
        config: 代理配置字典
    """
    proxy_manager.set_proxy_config(config)


def get_proxy_url() -> Optional[str]:
    """
    获取当前代理URL
    
    Returns:
        Optional[str]: 代理URL
    """
    return proxy_manager.get_proxy_url()


def get_pyrogram_proxy() -> Optional[Dict[str, Any]]:
    """
    获取Pyrogram格式的代理配置
    
    Returns:
        Optional[Dict[str, Any]]: Pyrogram代理配置
    """
    return proxy_manager.get_pyrogram_proxy()


async def test_proxy(test_url: str = "https://api.telegram.org") -> Tuple[bool, str]:
    """
    测试当前代理连接
    
    Args:
        test_url: 测试URL
        
    Returns:
        Tuple[bool, str]: (是否成功, 结果消息)
    """
    return await proxy_manager.test_proxy_connection(test_url)
