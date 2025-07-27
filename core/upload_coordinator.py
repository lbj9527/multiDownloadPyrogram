#!/usr/bin/env python3
"""
上传协调器 - 专门负责协调下载完成后的上传任务
符合SOLID原则的设计：单一职责，专注于上传任务的协调和队列管理
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UploadTask:
    """上传任务数据结构"""
    message: Any
    media_data: bytes
    client_name: str
    timestamp: float


class UploadCoordinator:
    """
    上传协调器 - 负责协调下载完成后的上传任务
    
    职责：
    1. 接收下载完成的消息
    2. 维护上传任务队列
    3. 管理消费者协程，实现真正的下载上传并发
    4. 协调上传时机和流程
    """
    
    def __init__(self, upload_service, client_manager, max_queue_size: int = 1000, consumer_count: int = 1):
        """
        初始化上传协调器

        Args:
            upload_service: 上传服务实例
            client_manager: 客户端管理器实例
            max_queue_size: 队列最大大小
            consumer_count: 消费者协程数量
        """
        self.upload_service = upload_service
        self.client_manager = client_manager
        self.max_queue_size = max_queue_size
        self.consumer_count = consumer_count
        
        # 上传任务队列
        self.upload_queue = asyncio.Queue(maxsize=max_queue_size)
        
        # 消费者协程列表
        self.consumers = []
        self.running = False
        self._shutdown = False
        
        logger.info(f"🔧 上传协调器初始化完成，队列大小: {max_queue_size}, 消费者数量: {consumer_count}")
    
    async def start(self):
        """启动上传协调器"""
        if self.running:
            logger.warning("上传协调器已经在运行中")
            return
            
        self.running = True
        self._shutdown = False
        
        # 启动消费者协程
        for i in range(self.consumer_count):
            consumer = asyncio.create_task(self._upload_consumer(i))
            self.consumers.append(consumer)
            
        logger.info(f"🚀 上传协调器已启动，{self.consumer_count} 个消费者协程开始工作")
    
    async def handle_message(self, message, media_data: bytes, client_name: str):
        """
        处理下载完成的消息 - 立即入队进行上传处理
        
        Args:
            message: 消息对象
            media_data: 媒体数据
            client_name: 客户端名称
        """
        if self._shutdown:
            logger.warning("上传协调器已关闭，忽略新的上传任务")
            return
            
        # 创建上传任务
        import time
        task = UploadTask(
            message=message,
            media_data=media_data,
            client_name=client_name,
            timestamp=time.time()
        )
        
        try:
            # 立即入队，实现真正的并发
            await asyncio.wait_for(self.upload_queue.put(task), timeout=1.0)
            logger.info(f"📤 [UploadCoordinator] 消息 {message.id} 已入队等待上传")
        except asyncio.TimeoutError:
            logger.error(f"❌ [UploadCoordinator] 上传队列已满，消息 {message.id} 入队失败")
        except Exception as e:
            logger.error(f"❌ [UploadCoordinator] 消息 {message.id} 入队异常: {e}")
    
    async def _upload_consumer(self, consumer_id: int):
        """
        上传消费者协程 - 持续处理队列中的上传任务
        
        Args:
            consumer_id: 消费者ID
        """
        logger.info(f"🔄 上传消费者 #{consumer_id} 开始工作")
        
        while not self._shutdown:
            try:
                # 从队列获取上传任务
                try:
                    task = await asyncio.wait_for(
                        self.upload_queue.get(), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    continue
                
                if task is None:  # 停止信号
                    break
                
                # 立即处理上传任务
                await self._process_upload_task(task, consumer_id)
                
                # 标记任务完成
                self.upload_queue.task_done()
                
            except Exception as e:
                logger.error(f"消费者 #{consumer_id} 处理上传任务失败: {e}")
                # 确保即使出错也要标记任务完成
                try:
                    self.upload_queue.task_done()
                except ValueError:
                    pass  # 队列可能已经空了
        
        logger.info(f"🛑 上传消费者 #{consumer_id} 已停止")
    
    async def _process_upload_task(self, task: UploadTask, consumer_id: int):
        """
        处理单个上传任务

        Args:
            task: 上传任务
            consumer_id: 消费者ID
        """
        try:
            # 获取真实的客户端实例
            try:
                # 直接使用传入的客户端名称（已经是ClientManager的键名）
                client = self.client_manager.get_client(task.client_name)

                if not client:
                    logger.error(f"❌ 找不到客户端: {task.client_name}")
                    return

            except Exception as e:
                logger.error(f"❌ 获取客户端失败: {e}")
                return

            # 调用上传服务处理
            logger.debug(f"🔄 消费者 #{consumer_id} 开始处理消息 {task.message.id}")
            await self.upload_service.upload_message(client, task.message, task.media_data)
            logger.debug(f"✅ 消费者 #{consumer_id} 完成处理消息 {task.message.id}")

        except Exception as e:
            logger.error(f"❌ 消费者 #{consumer_id} 处理消息 {task.message.id} 失败: {e}")
    
    async def shutdown(self):
        """关闭上传协调器"""
        if not self.running:
            return
            
        logger.info("🛑 开始关闭上传协调器...")
        self._shutdown = True
        
        # 等待队列中的任务完成
        if not self.upload_queue.empty():
            logger.info(f"⏳ 等待队列中的 {self.upload_queue.qsize()} 个任务完成...")
            try:
                await asyncio.wait_for(self.upload_queue.join(), timeout=30.0)
                logger.info("✅ 队列中的任务已全部完成")
            except asyncio.TimeoutError:
                logger.warning("⚠️ 等待队列任务完成超时")
        
        # 发送停止信号给所有消费者
        for _ in range(len(self.consumers)):
            await self.upload_queue.put(None)
        
        # 等待所有消费者停止
        if self.consumers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.consumers, return_exceptions=True), 
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ 等待消费者停止超时，强制取消")
                for consumer in self.consumers:
                    if not consumer.done():
                        consumer.cancel()
        
        self.consumers.clear()
        self.running = False
        
        logger.info("✅ 上传协调器已关闭")
    
    def get_status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        return {
            "running": self.running,
            "queue_size": self.upload_queue.qsize(),
            "consumer_count": len(self.consumers),
            "active_consumers": sum(1 for c in self.consumers if not c.done())
        }
