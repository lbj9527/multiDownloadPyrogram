"""
存储策略模式实现
将不同的存储模式抽象为独立的策略类
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pathlib import Path
from pyrogram import Client

from utils import get_logger
from interfaces.core_interfaces import UploadHandlerInterface, NullUploadHandler

logger = get_logger(__name__)


class StorageStrategyInterface(ABC):
    """存储策略接口"""
    
    @abstractmethod
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """
        处理消息的存储策略
        
        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称
            message_handler: 消息处理器实例（用于调用其方法）
            
        Returns:
            是否处理成功
        """
        pass


class RawStorageStrategy(StorageStrategyInterface):
    """原始存储策略：仅下载到本地"""
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """原始模式：下载到本地"""
        try:
            if message_handler.has_media(message):
                return await message_handler._process_media_message(client, message, channel)
            else:
                return await message_handler._process_text_message(message, channel, client)
        except Exception as e:
            logger.error(f"原始模式处理消息失败: {e}")
            return False


class UploadStorageStrategy(StorageStrategyInterface):
    """上传存储策略：客户端内部并发处理"""

    def __init__(self, upload_handler: UploadHandlerInterface):
        self.upload_handler = upload_handler

        # 添加简单的异步队列
        self.upload_queue = None  # 延迟初始化
        self.upload_task = None

        # 复用现有媒体组处理状态
        self.current_media_group_id = None
        self.media_group_cache = []
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """下载完成后立即入队，不等待上传"""
        try:
            logger.info(f"🔄 上传模式处理消息: {message.id}")

            if not self.upload_handler.is_enabled():
                logger.error("上传功能未启用")
                return False

            # 初始化队列（如果还没有）
            if self.upload_queue is None:
                import asyncio
                self.upload_queue = asyncio.Queue(maxsize=100)

            # 下载消息（复用现有逻辑）
            if message_handler.has_media(message):
                logger.info(f"📥 内存下载媒体消息: {message.id}")
                media_data = await message_handler._download_media_to_memory(client, message)
                if not media_data:
                    logger.error(f"❌ 内存下载失败: {message.id}")
                    return False
            else:
                media_data = None

            # 创建上传任务
            upload_task = {
                'message': message,
                'media_data': media_data,
                'client': client
            }

            # 立即入队，不等待上传
            await self.upload_queue.put(upload_task)
            logger.info(f"📤 消息已入队: {message.id}")

            # 启动上传消费者（如果还没启动）
            if not self.upload_task:
                import asyncio
                self.upload_task = asyncio.create_task(self._upload_consumer())
                logger.info("🚀 上传消费者已启动")

            return True  # 立即返回，上传在后台进行

        except Exception as e:
            logger.error(f"上传模式处理消息失败: {e}")
            return False

    async def _upload_consumer(self):
        """上传消费者 - 复用现有媒体组处理逻辑"""
        logger.info("📤 上传消费者开始工作")
        while True:
            try:
                # 从队列获取任务
                task = await self.upload_queue.get()
                if task is None:  # 停止信号
                    break

                # 直接调用现有的媒体组处理逻辑
                await self._handle_media_group_upload(task)

            except Exception as e:
                logger.error(f"上传消费者异常: {e}")

    async def _handle_media_group_upload(self, task):
        """复用现有的媒体组处理逻辑"""
        message = task['message']
        media_group_id = getattr(message, 'media_group_id', None)

        # 完全复用现有逻辑
        if media_group_id:
            # 检查媒体组ID变化
            if self.current_media_group_id != media_group_id:
                # 上传当前缓存的媒体组
                if self.current_media_group_id and self.media_group_cache:
                    await self._upload_current_media_group()

                # 开始新媒体组
                self.current_media_group_id = media_group_id
                self.media_group_cache = []
                logger.info(f"🆕 开始新媒体组: {media_group_id}")

            # 缓存当前消息
            self.media_group_cache.append(task)
            logger.info(f"📦 媒体组 {media_group_id} 当前有 {len(self.media_group_cache)} 个文件")
        else:
            # 单条消息，先上传缓存的媒体组
            if self.media_group_cache:
                await self._upload_current_media_group()

            # 直接上传单条消息
            await self.upload_handler.handle_upload(
                task['client'], message, media_data=task['media_data']
            )
            logger.info(f"✅ 单条消息上传完成: {message.id}")

    async def _upload_current_media_group(self):
        """上传当前缓存的媒体组 - 调用现有函数"""
        if not self.media_group_cache:
            return

        try:
            logger.info(f"📤 开始上传媒体组 {self.current_media_group_id}，包含 {len(self.media_group_cache)} 个文件")

            # 准备媒体组数据
            media_group_data = []
            for task in self.media_group_cache:
                media_group_data.append({
                    'message': task['message'],
                    'media_data': task['media_data'],
                    'client': task['client']
                })

            # 调用上传处理器的媒体组上传功能
            # 这里需要上传服务支持批量上传
            success = await self._upload_media_group_batch(media_group_data)

            if success:
                logger.info(f"✅ 媒体组 {self.current_media_group_id} 上传成功")
            else:
                logger.error(f"❌ 媒体组 {self.current_media_group_id} 上传失败")

        except Exception as e:
            logger.error(f"❌ 上传媒体组失败: {e}")
        finally:
            # 清理缓存
            self.current_media_group_id = None
            self.media_group_cache = []

    async def _upload_media_group_batch(self, media_group_data):
        """批量上传媒体组"""
        try:
            # 逐个上传媒体组中的文件
            # 注意：这里简化处理，实际应该使用send_media_group API
            for data in media_group_data:
                success = await self.upload_handler.handle_upload(
                    data['client'],
                    data['message'],
                    media_data=data['media_data']
                )
                if not success:
                    return False
            return True
        except Exception as e:
            logger.error(f"批量上传失败: {e}")
            return False

    async def cleanup(self):
        """程序结束时清理剩余缓存"""
        try:
            # 停止接收新任务
            if self.upload_task:
                # 发送停止信号
                if self.upload_queue:
                    await self.upload_queue.put(None)
                # 等待任务完成
                await self.upload_task
                logger.info("🛑 上传消费者已停止")

            # 上传剩余的媒体组
            if self.media_group_cache:
                logger.info("🔄 上传剩余的媒体组...")
                await self._upload_current_media_group()

        except Exception as e:
            logger.error(f"清理失败: {e}")


class HybridStorageStrategy(StorageStrategyInterface):
    """混合存储策略：既下载到本地又并发上传"""

    def __init__(self, upload_handler: UploadHandlerInterface):
        self.upload_handler = upload_handler
        self.raw_strategy = RawStorageStrategy()

        # 添加简单的异步队列（类似UploadStorageStrategy）
        self.upload_queue = None  # 延迟初始化
        self.upload_task = None

        # 复用现有媒体组处理状态
        self.current_media_group_id = None
        self.media_group_cache = []
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """混合模式：先下载到本地，然后并发上传"""
        try:
            # 先执行原始模式下载
            raw_success = await self.raw_strategy.process_message(
                client, message, channel, message_handler
            )

            if not raw_success:
                return False

            # 如果上传功能启用，则并发上传
            if self.upload_handler.is_enabled():
                # 初始化队列（如果还没有）
                if self.upload_queue is None:
                    import asyncio
                    self.upload_queue = asyncio.Queue(maxsize=100)

                # 准备上传任务
                if message_handler.has_media(message):
                    # 使用已下载的文件进行上传
                    file_path = await message_handler._get_downloaded_file_path(client, message, channel)
                    if file_path and file_path.exists():
                        upload_task = {
                            'message': message,
                            'file_path': file_path,
                            'media_data': None,
                            'client': client
                        }
                    else:
                        logger.warning(f"文件不存在，跳过上传: {message.id}")
                        return raw_success
                else:
                    upload_task = {
                        'message': message,
                        'file_path': None,
                        'media_data': None,
                        'client': client
                    }

                # 立即入队，不等待上传
                await self.upload_queue.put(upload_task)
                logger.info(f"📤 混合模式消息已入队: {message.id}")

                # 启动上传消费者（如果还没启动）
                if not self.upload_task:
                    import asyncio
                    self.upload_task = asyncio.create_task(self._upload_consumer())
                    logger.info("🚀 混合模式上传消费者已启动")

            # 本地下载成功就返回True，上传在后台进行
            return raw_success

        except Exception as e:
            logger.error(f"混合模式处理消息失败: {e}")
            return False

    async def _upload_consumer(self):
        """上传消费者 - 复用UploadStorageStrategy的逻辑"""
        logger.info("📤 混合模式上传消费者开始工作")
        while True:
            try:
                # 从队列获取任务
                task = await self.upload_queue.get()
                if task is None:  # 停止信号
                    break

                # 处理上传任务
                await self._handle_hybrid_upload(task)

            except Exception as e:
                logger.error(f"混合模式上传消费者异常: {e}")

    async def _handle_hybrid_upload(self, task):
        """处理混合模式的上传任务"""
        message = task['message']
        file_path = task['file_path']

        try:
            if file_path:
                # 使用文件路径上传
                success = await self.upload_handler.handle_upload(
                    task['client'], message, file_path=file_path
                )
            else:
                # 文本消息直接上传
                success = await self.upload_handler.handle_upload(
                    task['client'], message
                )

            if success:
                logger.info(f"✅ 混合模式上传完成: {message.id}")
            else:
                logger.error(f"❌ 混合模式上传失败: {message.id}")

        except Exception as e:
            logger.error(f"混合模式上传异常: {e}")

    async def cleanup(self):
        """程序结束时清理"""
        try:
            # 停止接收新任务
            if self.upload_task:
                # 发送停止信号
                if self.upload_queue:
                    await self.upload_queue.put(None)
                # 等待任务完成
                await self.upload_task
                logger.info("🛑 混合模式上传消费者已停止")

        except Exception as e:
            logger.error(f"混合模式清理失败: {e}")


class StorageStrategyFactory:
    """存储策略工厂"""
    
    @staticmethod
    def create_strategy(
        storage_mode: str, 
        upload_handler: UploadHandlerInterface
    ) -> StorageStrategyInterface:
        """
        根据存储模式创建对应的策略
        
        Args:
            storage_mode: 存储模式 (raw/upload/hybrid)
            upload_handler: 上传处理器
            
        Returns:
            对应的存储策略实例
        """
        if storage_mode == "upload":
            return UploadStorageStrategy(upload_handler)
        elif storage_mode == "hybrid":
            return HybridStorageStrategy(upload_handler)
        else:
            # 默认raw模式
            return RawStorageStrategy()
