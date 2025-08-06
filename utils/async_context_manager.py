"""
异步上下文管理器工具
用于更好地管理Pyrogram客户端的生命周期，避免数据库操作错误
"""

import asyncio
import logging
from typing import List, Optional
from contextlib import asynccontextmanager
from pyrogram.client import Client

logger = logging.getLogger(__name__)

class SafeClientManager:
    """安全的客户端管理器，确保正确的清理"""
    
    def __init__(self, clients: List[Client]):
        self.clients = clients
        self._cleanup_timeout = 10.0  # 清理超时时间
        
    async def safe_stop_all(self):
        """安全地停止所有客户端"""
        if not self.clients:
            return
            
        logger.info(f"安全停止 {len(self.clients)} 个客户端...")
        
        # 第一步：尝试正常停止所有客户端
        stop_tasks = []
        for client in self.clients:
            if client.is_connected:
                task = self._safe_stop_client(client)
                stop_tasks.append(task)
        
        if stop_tasks:
            # 等待所有客户端停止，但设置超时
            try:
                await asyncio.wait_for(
                    asyncio.gather(*stop_tasks, return_exceptions=True),
                    timeout=self._cleanup_timeout
                )
            except asyncio.TimeoutError:
                logger.warning("客户端停止超时，进行强制清理")
                await self._force_cleanup()
        
        # 第二步：等待后台任务完成
        await self._wait_for_background_tasks()
        
        logger.info("所有客户端已安全停止")
    
    async def _safe_stop_client(self, client: Client):
        """安全地停止单个客户端"""
        try:
            # 给客户端一些时间完成当前操作
            await asyncio.sleep(0.1)
            
            # 停止客户端
            await client.stop()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 忽略预期的数据库清理错误
            if any(keyword in error_msg for keyword in [
                'database', 'sqlite', 'connection', 'closed',
                'cannot operate on a closed database',
                'session is closed', 'connection lost',
                'event loop is closed'
            ]):
                logger.debug(f"客户端 {client.name} 正常清理: {e}")
            else:
                logger.error(f"客户端 {client.name} 停止时出现意外错误: {e}")
    
    async def _force_cleanup(self):
        """强制清理客户端连接"""
        for client in self.clients:
            try:
                if hasattr(client, 'session') and client.session:
                    await client.session.stop()
                if hasattr(client, 'storage') and client.storage:
                    await client.storage.close()
            except Exception as e:
                logger.debug(f"强制清理客户端 {client.name}: {e}")
    
    async def _wait_for_background_tasks(self):
        """等待后台任务完成"""
        try:
            # 等待一段时间让Pyrogram的后台任务完成
            await asyncio.sleep(1.0)
            
            # 获取当前任务
            current_task = asyncio.current_task()
            
            # 查找可能的Pyrogram相关任务
            pyrogram_tasks = []
            for task in asyncio.all_tasks():
                if task != current_task and not task.done():
                    # 检查任务名称或协程名称是否与Pyrogram相关
                    task_name = getattr(task, 'get_name', lambda: '')()
                    coro_name = getattr(task.get_coro(), '__name__', '')
                    
                    if any(keyword in f"{task_name} {coro_name}".lower() for keyword in [
                        'handle_updates', 'fetch_peers', 'pyrogram', 'client'
                    ]):
                        pyrogram_tasks.append(task)
            
            if pyrogram_tasks:
                logger.debug(f"等待 {len(pyrogram_tasks)} 个Pyrogram后台任务完成...")
                
                # 取消这些任务
                for task in pyrogram_tasks:
                    if not task.done():
                        task.cancel()
                
                # 等待任务取消完成
                await asyncio.gather(*pyrogram_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.debug(f"等待后台任务时的预期错误: {e}")

@asynccontextmanager
async def managed_clients(clients: List[Client]):
    """
    异步上下文管理器，用于安全管理客户端生命周期
    
    使用示例:
    async with managed_clients(clients) as safe_clients:
        # 使用客户端进行操作
        pass
    # 客户端会被安全清理
    """
    manager = SafeClientManager(clients)
    try:
        yield clients
    finally:
        await manager.safe_stop_all()

def suppress_pyrogram_errors():
    """抑制Pyrogram的常见清理错误"""
    import warnings
    
    # 抑制特定的警告
    warnings.filterwarnings('ignore', message='.*Cannot operate on a closed database.*')
    warnings.filterwarnings('ignore', message='.*Event loop is closed.*')
    warnings.filterwarnings('ignore', message='.*Session is closed.*')
    
    # 设置asyncio日志级别，减少噪音
    asyncio_logger = logging.getLogger('asyncio')
    if asyncio_logger.level < logging.WARNING:
        asyncio_logger.setLevel(logging.WARNING)

class AsyncTaskCleaner:
    """异步任务清理器"""
    
    @staticmethod
    async def cancel_remaining_tasks(exclude_current: bool = True):
        """取消所有剩余的异步任务"""
        try:
            current_task = asyncio.current_task() if exclude_current else None
            all_tasks = [task for task in asyncio.all_tasks() if task != current_task]
            
            if all_tasks:
                logger.debug(f"取消 {len(all_tasks)} 个剩余任务...")
                
                # 取消所有任务
                for task in all_tasks:
                    if not task.done():
                        task.cancel()
                
                # 等待任务取消完成
                await asyncio.gather(*all_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.debug(f"取消任务时的预期错误: {e}")
    
    @staticmethod
    async def graceful_shutdown(timeout: float = 5.0):
        """优雅关闭，等待任务完成或超时取消"""
        try:
            current_task = asyncio.current_task()
            pending_tasks = [task for task in asyncio.all_tasks() if task != current_task and not task.done()]
            
            if pending_tasks:
                logger.debug(f"等待 {len(pending_tasks)} 个任务完成...")
                
                try:
                    # 等待任务完成，但设置超时
                    await asyncio.wait_for(
                        asyncio.gather(*pending_tasks, return_exceptions=True),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    logger.debug("任务完成超时，强制取消...")
                    await AsyncTaskCleaner.cancel_remaining_tasks()
                    
        except Exception as e:
            logger.debug(f"优雅关闭时的预期错误: {e}")
