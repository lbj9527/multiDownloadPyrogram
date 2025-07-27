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
    """上传存储策略：内存下载后上传"""
    
    def __init__(self, upload_handler: UploadHandlerInterface):
        self.upload_handler = upload_handler
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """上传模式：内存下载后上传"""
        try:
            logger.info(f"🔄 上传模式处理消息: {message.id}")

            if not self.upload_handler.is_enabled():
                logger.error("上传功能未启用")
                return False

            if message_handler.has_media(message):
                logger.info(f"📥 内存下载媒体消息: {message.id}")
                # 内存下载媒体文件
                media_data = await message_handler._download_media_to_memory(client, message)
                if media_data:
                    logger.info(f"📤 上传媒体消息: {message.id}, 大小: {len(media_data)} 字节")
                    return await self.upload_handler.handle_upload(
                        client, message, media_data=media_data
                    )
                else:
                    logger.error(f"❌ 内存下载失败: {message.id}")
                    return False
            else:
                logger.info(f"📤 上传文本消息: {message.id}")
                # 直接上传文本消息
                return await self.upload_handler.handle_upload(client, message)

        except Exception as e:
            logger.error(f"上传模式处理消息失败: {e}")
            return False


class HybridStorageStrategy(StorageStrategyInterface):
    """混合存储策略：既下载到本地又上传"""
    
    def __init__(self, upload_handler: UploadHandlerInterface):
        self.upload_handler = upload_handler
        self.raw_strategy = RawStorageStrategy()
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str,
        message_handler: 'MessageHandler'
    ) -> bool:
        """混合模式：既下载到本地又上传"""
        try:
            # 先执行原始模式下载
            raw_success = await self.raw_strategy.process_message(
                client, message, channel, message_handler
            )

            # 再执行上传模式
            upload_success = False
            if self.upload_handler.is_enabled():
                if message_handler.has_media(message):
                    # 使用已下载的文件进行上传
                    file_path = await message_handler._get_downloaded_file_path(client, message, channel)
                    if file_path and file_path.exists():
                        upload_success = await self.upload_handler.handle_upload(
                            client, message, file_path=file_path
                        )
                else:
                    upload_success = await self.upload_handler.handle_upload(client, message)

            # 只要有一个成功就算成功
            return raw_success or upload_success

        except Exception as e:
            logger.error(f"混合模式处理消息失败: {e}")
            return False


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
