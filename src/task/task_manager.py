"""
任务管理器模块

协调客户端池、下载器和任务队列，实现高效的并发下载管理
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from pyrogram.types import Message

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import TaskError, TaskTimeoutError
from client.client_pool import ClientPool, ClientManager, ClientStatus
from downloader.media_downloader import MediaDownloader
from downloader.chunk_downloader import ChunkDownloader
from downloader.group_downloader import GroupDownloader
from .task_queue import TaskQueue, DownloadTask, TaskStatus, TaskPriority


class TaskManager:
    """任务管理器"""
    
    def __init__(self, config: Config):
        """
        初始化任务管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.TaskManager")
        
        # 初始化组件
        self.client_pool = ClientPool(config)
        self.task_queue = TaskQueue(config)
        
        # 下载器
        self.media_downloader = MediaDownloader(config)
        self.chunk_downloader = ChunkDownloader(config)
        self.group_downloader = GroupDownloader(config)
        
        # 任务执行控制
        self.max_concurrent_tasks = config.download.max_concurrent_downloads
        self.task_timeout = config.download.timeout
        self.is_running = False
        
        # 工作任务
        self._worker_tasks: List[asyncio.Task] = []
        self._main_task: Optional[asyncio.Task] = None
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        self.task_status_callback: Optional[Callable] = None
        
        # 设置回调
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置回调函数"""
        # 任务队列回调
        self.task_queue.set_callbacks(
            task_added=self._on_task_added,
            task_started=self._on_task_started,
            task_completed=self._on_task_completed,
            task_failed=self._on_task_failed
        )
        
        # 下载器回调
        self.media_downloader.set_progress_callback(self._on_download_progress)
        self.chunk_downloader.set_progress_callback(self._on_chunk_progress)
        self.group_downloader.set_progress_callback(self._on_group_progress)
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self.progress_callback = callback
    
    def set_task_status_callback(self, callback: Callable):
        """设置任务状态回调"""
        self.task_status_callback = callback
    
    async def initialize(self, session_strings: Optional[List[str]] = None) -> bool:
        """
        初始化任务管理器
        
        Args:
            session_strings: 会话字符串列表
            
        Returns:
            是否初始化成功
        """
        self.logger.info("正在初始化任务管理器...")
        
        try:
            # 初始化客户端池
            if not await self.client_pool.initialize(session_strings):
                self.logger.error("客户端池初始化失败")
                return False
            
            # 启动任务队列清理
            self.task_queue.start_cleanup_task()
            
            self.logger.info("任务管理器初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"任务管理器初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭任务管理器"""
        self.logger.info("正在关闭任务管理器...")
        
        # 停止工作器
        await self.stop()
        
        # 关闭客户端池
        await self.client_pool.shutdown()
        
        # 停止任务队列清理
        self.task_queue.stop_cleanup_task()
        
        self.logger.info("任务管理器已关闭")
    
    async def start(self):
        """启动任务管理器"""
        if self.is_running:
            self.logger.warning("任务管理器已经在运行")
            return
        
        self.is_running = True
        self.logger.info("启动任务管理器...")
        
        # 创建工作器任务
        self._worker_tasks = [
            asyncio.create_task(self._worker(i)) 
            for i in range(self.max_concurrent_tasks)
        ]
        
        # 创建主任务
        self._main_task = asyncio.create_task(self._main_loop())
        
        self.logger.info(f"任务管理器已启动，工作器数量: {len(self._worker_tasks)}")
    
    async def stop(self):
        """停止任务管理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("正在停止任务管理器...")
        
        # 取消所有工作器任务
        for task in self._worker_tasks:
            task.cancel()
        
        # 取消主任务
        if self._main_task:
            self._main_task.cancel()
        
        # 等待所有任务完成
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        if self._main_task:
            await asyncio.gather(self._main_task, return_exceptions=True)
        
        self._worker_tasks.clear()
        self._main_task = None
        
        self.logger.info("任务管理器已停止")
    
    async def _main_loop(self):
        """主循环"""
        while self.is_running:
            try:
                # 定期检查任务状态
                await asyncio.sleep(10)
                
                # 检查超时任务
                await self._check_timeout_tasks()
                
                # 记录统计信息
                stats = self.get_statistics()
                if stats["running_count"] > 0:
                    self.logger.debug(f"运行中任务: {stats['running_count']}, 队列大小: {stats['queue_size']}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _worker(self, worker_id: int):
        """工作器任务"""
        self.logger.debug(f"工作器 {worker_id} 启动")
        
        while self.is_running:
            try:
                # 获取下一个任务
                task = self.task_queue.get_next_task()
                if not task:
                    await asyncio.sleep(1)
                    continue
                
                # 开始执行任务
                if not self.task_queue.start_task(task):
                    await asyncio.sleep(1)
                    continue
                
                self.logger.debug(f"工作器 {worker_id} 开始执行任务: {task.task_id}")
                
                # 执行任务
                success = await self._execute_task(task)
                
                if success:
                    self.logger.debug(f"工作器 {worker_id} 完成任务: {task.task_id}")
                else:
                    self.logger.error(f"工作器 {worker_id} 任务失败: {task.task_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"工作器 {worker_id} 异常: {e}")
                await asyncio.sleep(5)
        
        self.logger.debug(f"工作器 {worker_id} 停止")
    
    async def _execute_task(self, task: DownloadTask) -> bool:
        """
        执行任务
        
        Args:
            task: 下载任务
            
        Returns:
            是否执行成功
        """
        try:
            # 获取客户端
            client_manager = self._get_available_client()
            if not client_manager:
                self.task_queue.fail_task(task.task_id, "没有可用的客户端")
                return False
            
            # 设置下载器的客户端
            self.media_downloader.client_manager = client_manager
            self.chunk_downloader.client_manager = client_manager
            self.group_downloader.client_manager = client_manager
            
            # 根据任务类型执行下载
            if task.task_type == "group_download":
                result = await self._execute_group_download(task)
            elif task.task_type == "chunk_download":
                result = await self._execute_chunk_download(task)
            else:
                result = await self._execute_media_download(task)
            
            if result:
                # 获取文件信息
                file_path = result if isinstance(result, str) else None
                file_size = 0
                
                if file_path and Path(file_path).exists():
                    file_size = Path(file_path).stat().st_size
                
                self.task_queue.complete_task(task.task_id, file_path, file_size)
                return True
            else:
                self.task_queue.fail_task(task.task_id, "下载失败")
                return False
                
        except Exception as e:
            self.task_queue.fail_task(task.task_id, str(e))
            return False
    
    async def _execute_media_download(self, task: DownloadTask) -> Optional[str]:
        """执行媒体下载"""
        return await self.media_downloader.download_media(
            task.message,
            custom_path=task.custom_path,
            chat_title=task.chat_title
        )
    
    async def _execute_chunk_download(self, task: DownloadTask) -> Optional[str]:
        """执行分片下载"""
        # 获取文件信息
        file_info = self.media_downloader._get_file_info(task.message)
        if not file_info["file_name"]:
            return None
        
        # 确定文件路径
        if task.custom_path:
            file_path = Path(task.custom_path)
            if file_path.is_dir():
                file_path = file_path / file_info["file_name"]
        else:
            file_path = self.media_downloader._get_download_path(file_info, task.chat_title)
        
        # 执行分片下载
        success = await self.chunk_downloader.download_file_chunks(
            task.message,
            file_path,
            file_info["file_size"]
        )
        
        return str(file_path) if success else None
    
    async def _execute_group_download(self, task: DownloadTask) -> Optional[List[str]]:
        """执行媒体组下载"""
        return await self.group_downloader.download_media_group(
            task.message,
            chat_title=task.chat_title
        )
    
    async def _check_timeout_tasks(self):
        """检查超时任务"""
        current_time = time.time()
        
        for task in self.task_queue.running_tasks.values():
            if task.started_at and (current_time - task.started_at) > self.task_timeout:
                self.logger.warning(f"任务超时: {task.task_id}")
                self.task_queue.fail_task(task.task_id, "任务超时")
    
    def add_download_task(self, message: Message, 
                         chat_title: Optional[str] = None,
                         custom_path: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """
        添加下载任务
        
        Args:
            message: 消息对象
            chat_title: 聊天标题
            custom_path: 自定义路径
            priority: 任务优先级
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        task = DownloadTask(
            task_id=task_id,
            message=message,
            chat_title=chat_title,
            custom_path=custom_path,
            priority=priority
        )
        
        if self.task_queue.add_task(task):
            self.logger.info(f"添加下载任务: {task_id}")
            return task_id
        else:
            raise TaskError(f"添加任务失败: {task_id}")
    
    def add_batch_download_tasks(self, messages: List[Message], 
                               chat_title: Optional[str] = None,
                               custom_path: Optional[str] = None,
                               priority: TaskPriority = TaskPriority.NORMAL) -> List[str]:
        """
        批量添加下载任务
        
        Args:
            messages: 消息列表
            chat_title: 聊天标题
            custom_path: 自定义路径
            priority: 任务优先级
            
        Returns:
            任务ID列表
        """
        task_ids = []
        
        for message in messages:
            if message.media:
                try:
                    task_id = self.add_download_task(message, chat_title, custom_path, priority)
                    task_ids.append(task_id)
                except Exception as e:
                    self.logger.error(f"添加任务失败: {e}")
        
        self.logger.info(f"批量添加任务: {len(task_ids)} 个")
        return task_ids
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.task_queue.cancel_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.task_queue.get_task(task_id)
        return task.to_dict() if task else None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        queue_stats = self.task_queue.get_statistics()
        pool_stats = self.client_pool.get_pool_info()
        
        return {
            "queue_size": queue_stats["queue_size"],
            "running_count": queue_stats["running_count"],
            "completed_count": queue_stats["completed_count"],
            "failed_count": queue_stats["failed_count"],
            "success_rate": queue_stats["success_rate"],
            "total_tasks": queue_stats["total_tasks"],
            "client_pool": {
                "total_clients": pool_stats["total_clients"],
                "available_clients": pool_stats["available_clients"],
                "client_availability": pool_stats["metrics"]["client_availability"]
            },
            "downloader_stats": {
                "media_downloader": self.media_downloader.get_statistics(),
                "chunk_downloader": self.chunk_downloader.get_statistics(),
                "group_downloader": self.group_downloader.get_statistics()
            }
        }
    
    # 回调方法
    def _on_task_added(self, task: DownloadTask):
        """任务添加回调"""
        if self.task_status_callback:
            try:
                self.task_status_callback("task_added", task.to_dict())
            except Exception as e:
                self.logger.error(f"任务状态回调失败: {e}")
    
    def _on_task_started(self, task: DownloadTask):
        """任务开始回调"""
        if self.task_status_callback:
            try:
                self.task_status_callback("task_started", task.to_dict())
            except Exception as e:
                self.logger.error(f"任务状态回调失败: {e}")
    
    def _on_task_completed(self, task: DownloadTask):
        """任务完成回调"""
        if self.task_status_callback:
            try:
                self.task_status_callback("task_completed", task.to_dict())
            except Exception as e:
                self.logger.error(f"任务状态回调失败: {e}")
    
    def _on_task_failed(self, task: DownloadTask):
        """任务失败回调"""
        if self.task_status_callback:
            try:
                self.task_status_callback("task_failed", task.to_dict())
            except Exception as e:
                self.logger.error(f"任务状态回调失败: {e}")
    
    async def _on_download_progress(self, progress):
        """下载进度回调"""
        if self.progress_callback:
            try:
                await self.progress_callback("download_progress", progress.to_dict())
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    async def _on_chunk_progress(self, progress):
        """分片进度回调"""
        if self.progress_callback:
            try:
                await self.progress_callback("chunk_progress", progress.to_dict())
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    async def _on_group_progress(self, progress):
        """媒体组进度回调"""
        if self.progress_callback:
            try:
                await self.progress_callback("group_progress", progress.to_dict())
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    def _get_available_client(self) -> Optional[ClientManager]:
        """获取可用的客户端"""
        client_manager = self.client_pool.select_client()
        
        if client_manager is None:
            self.logger.error("没有可用的客户端")
            return None
        
        # 如果客户端状态为ERROR但已连接，尝试重连
        if (client_manager.get_status() == ClientStatus.ERROR and 
            client_manager.client.is_connected):
            self.logger.info(f"尝试重连客户端: {client_manager.client_id}")
            try:
                # 在后台重连
                asyncio.create_task(client_manager.reconnect())
            except Exception as e:
                self.logger.error(f"重连客户端失败: {e}")
        
        return client_manager
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.shutdown() 