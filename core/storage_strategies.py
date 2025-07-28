"""
存储策略模式实现
将不同的存储模式抽象为独立的策略类
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pathlib import Path
from pyrogram import Client

from utils import get_logger
from config.constants import STORAGE_MODES

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
    """上传存储策略：下载后立即提交到UploadCoordinator，实现真正的并发"""

    def __init__(self, upload_coordinator):
        """
        初始化上传存储策略

        Args:
            upload_coordinator: 上传协调器实例
        """
        self.upload_coordinator = upload_coordinator

    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """下载后立即提交到UploadCoordinator，实现真正的下载上传并发"""
        try:
            logger.info(f"🔄 [UploadStorageStrategy] 上传模式处理消息: {message.id}")

            if not self.upload_coordinator:
                logger.error("[UploadStorageStrategy] 上传协调器未设置")
                return False

            if not self.upload_coordinator.running:
                logger.error("[UploadStorageStrategy] 上传协调器未启动")
                return False

            # 下载消息
            if message_handler.has_media(message):
                logger.info(f"📥 内存下载媒体消息: {message.id}")
                media_data = await message_handler._download_media_to_memory(client, message)
                if not media_data:
                    logger.error(f"❌ 内存下载失败: {message.id}")
                    return False
            else:
                media_data = b""  # 文本消息使用空字节

            # 立即提交到UploadCoordinator，实现真正的并发
            logger.info(f"📤 [UploadStorageStrategy] 提交消息到协调器: {message.id} (客户端: {client.name})")
            await self.upload_coordinator.handle_message(
                message, media_data, client.name
            )

            logger.info(f"✅ [UploadStorageStrategy] 上传模式消息已提交: {message.id}")
            return True

        except Exception as e:
            logger.error(f"上传模式处理消息失败: {e}")
            return False




class HybridStorageStrategy(StorageStrategyInterface):
    """混合存储策略：先下载到本地，然后提交到UploadCoordinator，实现真正的并发"""

    def __init__(self, upload_coordinator):
        """
        初始化混合存储策略

        Args:
            upload_coordinator: 上传协调器实例
        """
        self.upload_coordinator = upload_coordinator
        self.raw_strategy = RawStorageStrategy()

    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """混合模式：先下载到本地，然后提交到UploadCoordinator，实现真正的并发"""
        try:
            logger.info(f"🔄 混合模式处理消息: {message.id}")

            # 先执行原始模式下载
            raw_success = await self.raw_strategy.process_message(
                client, message, channel, message_handler
            )

            if not raw_success or not self.upload_coordinator or not self.upload_coordinator.running:
                return raw_success

            # 获取已下载的文件数据并提交到UploadCoordinator
            if message_handler.has_media(message):
                # 读取已下载的文件数据
                file_path = await message_handler._get_downloaded_file_path(
                    client, message, channel
                )
                if file_path and file_path.exists():
                    # 读取文件数据
                    with open(file_path, 'rb') as f:
                        media_data = f.read()

                    # 提交到UploadCoordinator，实现真正的并发
                    await self.upload_coordinator.handle_message(
                        message, media_data, client.name
                    )
                    logger.info(f"✅ 混合模式文件上传已提交: {message.id}")
                else:
                    logger.warning(f"文件不存在，跳过上传: {message.id}")
            else:
                # 文本消息提交上传任务
                await self.upload_coordinator.handle_message(
                    message, b"", client.name
                )
                logger.info(f"✅ 混合模式文本上传已提交: {message.id}")

            return raw_success

        except Exception as e:
            logger.error(f"混合模式处理消息失败: {e}")
            return False




class StorageStrategyFactory:
    """存储策略工厂"""

    @staticmethod
    def create_strategy(
        storage_mode: str,
        upload_coordinator=None
    ) -> StorageStrategyInterface:
        """
        根据存储模式创建对应的策略

        Args:
            storage_mode: 存储模式 (raw/upload/hybrid)
            upload_coordinator: 上传协调器实例

        Returns:
            对应的存储策略实例
        """
        # 验证存储模式
        if storage_mode not in STORAGE_MODES:
            logger.warning(f"未知的存储模式: {storage_mode}，使用默认的raw模式")
            storage_mode = "raw"

        if storage_mode == "upload":
            return UploadStorageStrategy(upload_coordinator)
        elif storage_mode == "hybrid":
            return HybridStorageStrategy(upload_coordinator)
        else:
            # 默认raw模式
            return RawStorageStrategy()
