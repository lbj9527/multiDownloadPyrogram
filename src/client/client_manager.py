"""
单客户端管理模块

负责管理单个Pyrogram客户端的生命周期、状态监控和异常处理
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass
from pyrogram import Client
from pyrogram.errors import FloodWait, AuthBytesInvalid, SessionPasswordNeeded

from utils.logger import get_logger
from utils.exceptions import ClientError, ClientConnectionError, ClientAuthError, handle_pyrogram_exception, NetworkError


class ClientStatus(Enum):
    """客户端状态枚举"""
    CREATED = "created"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ClientMetrics:
    """客户端性能指标"""
    connection_time: float = 0.0
    last_activity: float = 0.0
    total_downloads: int = 0
    total_uploads: int = 0
    bytes_downloaded: int = 0
    bytes_uploaded: int = 0
    error_count: int = 0
    flood_wait_count: int = 0
    total_flood_wait_time: int = 0
    reconnect_count: int = 0
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = time.time()
    
    def record_download(self, bytes_count: int):
        """记录下载"""
        self.total_downloads += 1
        self.bytes_downloaded += bytes_count
        self.update_activity()
    
    def record_upload(self, bytes_count: int):
        """记录上传"""
        self.total_uploads += 1
        self.bytes_uploaded += bytes_count
        self.update_activity()
    
    def record_error(self):
        """记录错误"""
        self.error_count += 1
        self.update_activity()
    
    def record_flood_wait(self, wait_time: int):
        """记录FloodWait"""
        self.flood_wait_count += 1
        self.total_flood_wait_time += wait_time
        self.update_activity()
    
    def record_reconnect(self):
        """记录重连"""
        self.reconnect_count += 1
        self.update_activity()


class ClientManager:
    """单客户端管理器"""
    
    def __init__(self, client: Client, client_id: Optional[str] = None):
        """
        初始化客户端管理器
        
        Args:
            client: Pyrogram客户端对象
            client_id: 客户端ID
        """
        self.client = client
        self.client_id = client_id or client.name
        self.logger = get_logger(f"{__name__}.ClientManager.{self.client_id}")
        
        # 状态管理
        self.status = ClientStatus.CREATED
        self.status_history: List[tuple] = []
        self.last_status_change = time.time()
        
        # 性能指标
        self.metrics = ClientMetrics()
        
        # 配置
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        self.health_check_interval = 300.0  # 5分钟
        self.connection_timeout = 60.0  # 增加到60秒
        
        # 状态监控
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # 回调函数
        self.on_status_change: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_reconnect: Optional[Callable] = None
    
    def _update_status(self, new_status: ClientStatus, message: Optional[str] = None):
        """更新客户端状态"""
        old_status = self.status
        self.status = new_status
        self.last_status_change = time.time()
        self.status_history.append((old_status, new_status, time.time(), message))
        
        # 保持状态历史不超过100条
        if len(self.status_history) > 100:
            self.status_history = self.status_history[-100:]
        
        self.logger.info(f"客户端状态变更: {old_status.value} -> {new_status.value}")
        
        # 触发回调
        if self.on_status_change:
            try:
                self.on_status_change(self.client_id, old_status, new_status, message)
            except Exception as e:
                self.logger.error(f"状态变更回调失败: {e}")
    
    async def start(self, timeout: Optional[float] = None) -> bool:
        """
        启动客户端
        
        Args:
            timeout: 连接超时时间
            
        Returns:
            是否启动成功
        """
        if self.status == ClientStatus.CONNECTED:
            self.logger.info("客户端已经连接")
            return True
        
        self._update_status(ClientStatus.CONNECTING, "正在连接...")
        timeout = timeout or self.connection_timeout
        
        try:
            # 设置连接超时
            await asyncio.wait_for(self.client.start(), timeout=timeout)
            
            # 验证连接
            if await self._verify_connection():
                self._update_status(ClientStatus.CONNECTED, "连接成功")
                self.metrics.connection_time = time.time()
                
                # 启动监控
                if not self._is_monitoring:
                    self._start_health_monitoring()
                
                return True
            else:
                self._update_status(ClientStatus.ERROR, "连接验证失败")
                return False
                
        except asyncio.TimeoutError:
            self._update_status(ClientStatus.ERROR, f"连接超时 ({timeout}s)")
            self.logger.error(f"客户端连接超时: {timeout}s")
            return False
            
        except (AuthBytesInvalid, SessionPasswordNeeded) as e:
            self._update_status(ClientStatus.ERROR, f"认证失败: {e}")
            self.logger.error(f"客户端认证失败: {e}")
            if self.on_error:
                self.on_error(self.client_id, e)
            return False
            
        except Exception as e:
            self._update_status(ClientStatus.ERROR, f"启动失败: {e}")
            self.logger.error(f"客户端启动失败: {e}")
            self.metrics.record_error()
            if self.on_error:
                self.on_error(self.client_id, e)
            return False
    
    async def stop(self) -> bool:
        """
        停止客户端
        
        Returns:
            是否停止成功
        """
        if self.status == ClientStatus.DISCONNECTED:
            self.logger.info("客户端已经断开")
            return True
        
        self._update_status(ClientStatus.DISCONNECTING, "正在断开连接...")
        
        try:
            # 停止监控
            self._stop_health_monitoring()
            
            # 停止客户端
            if self.client.is_connected:
                await self.client.stop()
            
            self._update_status(ClientStatus.DISCONNECTED, "断开连接成功")
            return True
            
        except Exception as e:
            self._update_status(ClientStatus.ERROR, f"断开连接失败: {e}")
            self.logger.error(f"客户端断开失败: {e}")
            self.metrics.record_error()
            return False
    
    async def restart(self) -> bool:
        """
        重启客户端
        
        Returns:
            是否重启成功
        """
        self.logger.info("正在重启客户端...")
        
        # 停止客户端
        await self.stop()
        
        # 等待一段时间
        await asyncio.sleep(1.0)
        
        # 重新启动
        return await self.start()
    
    async def _verify_connection(self) -> bool:
        """验证客户端连接"""
        try:
            # 简单的API调用测试
            me = await self.client.get_me()
            self.logger.debug(f"连接验证成功: {me.first_name} (@{me.username})")
            return True
        except Exception as e:
            self.logger.error(f"连接验证失败: {e}")
            return False
    
    async def reconnect(self, max_attempts: Optional[int] = None) -> bool:
        """
        重连客户端
        
        Args:
            max_attempts: 最大重连尝试次数
            
        Returns:
            是否重连成功
        """
        max_attempts = max_attempts or self.max_reconnect_attempts
        
        for attempt in range(max_attempts):
            self._update_status(ClientStatus.RECONNECTING, f"重连尝试 {attempt + 1}/{max_attempts}")
            self.logger.info(f"尝试重连: {attempt + 1}/{max_attempts}")
            
            try:
                # 先停止
                if self.client.is_connected:
                    await self.client.stop()
                
                # 等待重连延迟
                await asyncio.sleep(self.reconnect_delay * (attempt + 1))
                
                # 重新启动
                if await self.start():
                    self.metrics.record_reconnect()
                    self.logger.info("重连成功")
                    if self.on_reconnect:
                        self.on_reconnect(self.client_id, attempt + 1)
                    return True
                    
            except Exception as e:
                self.logger.error(f"重连失败 (尝试 {attempt + 1}): {e}")
                continue
        
        self._update_status(ClientStatus.ERROR, "重连失败")
        self.logger.error("所有重连尝试都失败了")
        return False
    
    def _start_health_monitoring(self):
        """启动健康监控"""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._is_monitoring = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("健康监控已启动")
    
    def _stop_health_monitoring(self):
        """停止健康监控"""
        self._is_monitoring = False
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
        self.logger.info("健康监控已停止")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self._is_monitoring:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not self._is_monitoring:
                    break
                
                # 检查连接状态
                if not await self._verify_connection():
                    self.logger.warning("健康检查失败，尝试重连...")
                    await self.reconnect()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"健康检查异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟
    
    async def execute_with_retry(self, func: Callable, *args, 
                                max_retries: int = 3, **kwargs) -> Any:
        """
        执行函数并处理重试
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"重试成功 (尝试 {attempt + 1})")
                return result
                
            except FloodWait as e:
                self.logger.warning(f"遇到FloodWait: 等待 {e.value} 秒")
                self.metrics.record_flood_wait(e.value)
                await asyncio.sleep(e.value)
                last_exception = e
                
            except NetworkError as e:
                self.logger.warning(f"网络错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                self.metrics.record_error()
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    
                    # 检查连接状态
                    if not self.client.is_connected:
                        self.logger.info("检测到连接断开，尝试重连...")
                        await self.reconnect()
                
                last_exception = e
                
            except Exception as e:
                self.logger.error(f"执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                self.metrics.record_error()
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
                
                last_exception = e
        
        # 所有重试都失败了
        if last_exception:
            raise last_exception
        
        return None
    
    def get_status(self) -> ClientStatus:
        """获取当前状态"""
        return self.status
    
    def get_metrics(self) -> ClientMetrics:
        """获取性能指标"""
        return self.metrics
    
    def get_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "client_id": self.client_id,
            "client_name": self.client.name,
            "status": self.status.value,
            "is_connected": self.client.is_connected,
            "last_status_change": self.last_status_change,
            "metrics": {
                "connection_time": self.metrics.connection_time,
                "last_activity": self.metrics.last_activity,
                "total_downloads": self.metrics.total_downloads,
                "total_uploads": self.metrics.total_uploads,
                "bytes_downloaded": self.metrics.bytes_downloaded,
                "bytes_uploaded": self.metrics.bytes_uploaded,
                "error_count": self.metrics.error_count,
                "flood_wait_count": self.metrics.flood_wait_count,
                "total_flood_wait_time": self.metrics.total_flood_wait_time,
                "reconnect_count": self.metrics.reconnect_count
            }
        }
    
    def get_status_history(self) -> List[tuple]:
        """获取状态历史"""
        return self.status_history.copy()
    
    def is_healthy(self) -> bool:
        """检查客户端是否健康"""
        return (self.status == ClientStatus.CONNECTED and 
                self.client.is_connected and
                time.time() - self.metrics.last_activity < 3600)  # 1小时内有活动
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        # 如果客户端已连接且状态为CONNECTED，则可用
        if self.status == ClientStatus.CONNECTED and self.client.is_connected:
            return True
        
        # 如果状态为ERROR但客户端已连接，也认为可用（可能是临时错误）
        if self.status == ClientStatus.ERROR and self.client.is_connected:
            return True
            
        return False
    
    def can_retry(self) -> bool:
        """检查客户端是否可以重试"""
        # ERROR状态的客户端可以重试
        if self.status == ClientStatus.ERROR:
            return True
        
        # DISCONNECTED状态的客户端可以重试
        if self.status == ClientStatus.DISCONNECTED:
            return True
            
        return False
    
    def set_callbacks(self, 
                     on_status_change: Optional[Callable] = None,
                     on_error: Optional[Callable] = None,
                     on_reconnect: Optional[Callable] = None):
        """
        设置回调函数
        
        Args:
            on_status_change: 状态变更回调
            on_error: 错误回调
            on_reconnect: 重连回调
        """
        self.on_status_change = on_status_change
        self.on_error = on_error
        self.on_reconnect = on_reconnect
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop() 