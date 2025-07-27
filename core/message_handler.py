"""
消息处理器
负责处理不同类型的Telegram消息
"""

from typing import Optional, Any
from pathlib import Path
from io import BytesIO
from pyrogram import Client

from models import MediaInfo, FileInfo, FileType
from utils import get_logger, sanitize_filename
from .file_processor import FileProcessor
from interfaces.core_interfaces import UploadHandlerInterface, NullUploadHandler
from config import app_settings

logger = get_logger(__name__)


class MessageHandler:
    """消息处理器"""

    def __init__(self, file_processor: FileProcessor, upload_handler: Optional[UploadHandlerInterface] = None):
        self.file_processor = file_processor
        self.upload_handler = upload_handler or NullUploadHandler()
        self.supported_media_types = {
            'photo', 'video', 'audio', 'voice',
            'video_note', 'animation', 'document', 'sticker'
        }
    
    async def process_message(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> bool:
        """
        处理单条消息

        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称

        Returns:
            是否处理成功
        """
        try:
            # 根据存储模式选择处理方式
            storage_mode = app_settings.storage.storage_mode

            if storage_mode == "upload":
                return await self._process_message_upload_mode(client, message, channel)
            elif storage_mode == "hybrid":
                return await self._process_message_hybrid_mode(client, message, channel)
            else:
                # 默认raw模式
                return await self._process_message_raw_mode(client, message, channel)

        except Exception as e:
            logger.error(f"处理消息 {message.id} 失败: {e}")
            return False

    async def _process_message_raw_mode(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> bool:
        """原始模式：下载到本地"""
        try:
            if self.has_media(message):
                return await self._process_media_message(client, message, channel)
            else:
                return await self._process_text_message(message, channel, client)
        except Exception as e:
            logger.error(f"原始模式处理消息失败: {e}")
            return False

    async def _process_message_upload_mode(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> bool:
        """上传模式：内存下载后上传"""
        try:
            logger.info(f"🔄 上传模式处理消息: {message.id}")

            if not self.upload_handler.is_enabled():
                logger.error("上传功能未启用")
                return False

            if self.has_media(message):
                logger.info(f"📥 内存下载媒体消息: {message.id}")
                # 内存下载媒体文件
                media_data = await self._download_media_to_memory(client, message)
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

    async def _process_message_hybrid_mode(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> bool:
        """混合模式：既下载到本地又上传"""
        try:
            # 先执行原始模式下载
            raw_success = await self._process_message_raw_mode(client, message, channel)

            # 再执行上传模式
            upload_success = False
            if self.upload_handler.is_enabled():
                if self.has_media(message):
                    # 使用已下载的文件进行上传
                    file_path = await self._get_downloaded_file_path(client, message, channel)
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
    
    def has_media(self, message: Any) -> bool:
        """
        检查消息是否包含媒体

        Args:
            message: 消息对象

        Returns:
            是否包含媒体
        """
        return (message and
                hasattr(message, 'media') and
                message.media)
    
    def is_media_group_message(self, message: Any) -> bool:
        """
        检查是否为媒体组消息
        
        Args:
            message: 消息对象
            
        Returns:
            是否为媒体组消息
        """
        return (hasattr(message, 'media_group_id') and 
                message.media_group_id is not None)
    
    async def _process_media_message(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> bool:
        """
        处理媒体消息
        
        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称
            
        Returns:
            是否处理成功
        """
        try:
            # 创建媒体信息
            media_info = self._create_media_info(message)
            
            # 检查是否为媒体组消息
            is_media_group = self.is_media_group_message(message)
            if is_media_group:
                logger.info(f"检测到媒体组消息: {message.id} (组ID: {media_info.media_group_id})")
            
            # 下载媒体文件
            file_path = await self._download_media_file(client, message, channel)
            if not file_path:
                return False
            
            # 创建文件信息
            file_info = self._create_file_info(file_path, message, media_info)
            
            # 处理文件
            success = await self.file_processor.process_file(file_info)
            
            if success:
                if is_media_group:
                    logger.info(f"媒体组文件处理成功: {file_path.name}")
                else:
                    logger.info(f"媒体文件处理成功: {file_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"处理媒体消息 {message.id} 失败: {e}")
            return False
    
    async def _process_text_message(self, message: Any, channel: str, client: Client = None) -> bool:
        """
        处理文本消息

        Args:
            message: 消息对象
            channel: 频道名称
            client: Pyrogram客户端

        Returns:
            是否处理成功
        """
        try:
            # 保存文本消息到文件
            await self._save_text_message(message, channel, client)
            return True
        except Exception as e:
            logger.error(f"处理文本消息 {message.id} 失败: {e}")
            return False
    
    def _create_media_info(self, message: Any) -> MediaInfo:
        """
        创建媒体信息对象

        Args:
            message: 消息对象

        Returns:
            媒体信息对象
        """
        # 检测媒体类型
        media_type = self._detect_media_type(message)

        media_info = MediaInfo(
            message_id=message.id,
            media_type=media_type,
            media_group_id=getattr(message, 'media_group_id', None)
        )

        # 获取媒体对象
        if media_type:
            media = getattr(message, media_type, None)
            if media:
                media_info.file_name = getattr(media, 'file_name', None)
                media_info.file_size = getattr(media, 'file_size', None)
                media_info.mime_type = getattr(media, 'mime_type', None)
                media_info.duration = getattr(media, 'duration', None)
                media_info.width = getattr(media, 'width', None)
                media_info.height = getattr(media, 'height', None)

        return media_info

    def _detect_media_type(self, message: Any) -> Optional[str]:
        """
        检测消息的媒体类型

        Args:
            message: 消息对象

        Returns:
            媒体类型字符串
        """
        for media_type in self.supported_media_types:
            if hasattr(message, media_type) and getattr(message, media_type):
                return media_type
        return None
    
    def _create_file_info(
        self,
        file_path: Path,
        message: Any,
        media_info: MediaInfo
    ) -> FileInfo:
        """
        创建文件信息对象
        
        Args:
            file_path: 文件路径
            message: 消息对象
            media_info: 媒体信息
            
        Returns:
            文件信息对象
        """
        # 确定文件类型
        file_type = self._determine_file_type(media_info.media_type)
        
        # 创建文件信息
        file_info = FileInfo(
            file_path=file_path,
            original_name=media_info.file_name or f"message_{message.id}",
            file_type=file_type,
            media_info=media_info
        )
        
        # 设置文件大小
        if file_path.exists():
            file_info.file_size = file_path.stat().st_size
        
        return file_info
    
    def _determine_file_type(self, media_type: Optional[str]) -> FileType:
        """
        根据媒体类型确定文件类型

        Args:
            media_type: 媒体类型

        Returns:
            文件类型
        """
        if not media_type:
            return FileType.OTHER

        type_mapping = {
            'photo': FileType.IMAGE,
            'video': FileType.VIDEO,
            'video_note': FileType.VIDEO,
            'animation': FileType.VIDEO,
            'audio': FileType.AUDIO,
            'voice': FileType.AUDIO,
            'document': FileType.DOCUMENT,
            'sticker': FileType.IMAGE
        }

        return type_mapping.get(media_type, FileType.OTHER)
    
    async def _download_media_file(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> Optional[Path]:
        """
        下载媒体文件

        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称

        Returns:
            下载的文件路径
        """
        try:
            # 获取频道目录（传递客户端以获取频道信息）
            channel_dir = await self.file_processor.get_channel_directory(channel, client)

            # 生成文件名
            file_name = self._generate_filename(message)

            # 下载文件
            file_path = await client.download_media(
                message,
                file_name=str(channel_dir / file_name)
            )

            return Path(file_path) if file_path else None

        except Exception as e:
            logger.error(f"下载媒体文件失败: {e}")
            return None

    async def _download_media_to_memory(
        self,
        client: Client,
        message: Any
    ) -> Optional[bytes]:
        """
        下载媒体文件到内存

        Args:
            client: Pyrogram客户端
            message: 消息对象

        Returns:
            文件字节数据
        """
        try:
            # 使用Pyrogram的in_memory参数直接下载到内存
            file_like_object = await client.download_media(message, in_memory=True)

            if file_like_object:
                # 获取字节数据
                media_data = file_like_object.getvalue()
                file_like_object.close()

                logger.debug(f"消息 {message.id} 媒体文件已下载到内存，大小: {len(media_data)} 字节")
                return media_data

            return None

        except Exception as e:
            logger.error(f"内存下载媒体文件失败: {e}")
            return None

    async def _get_downloaded_file_path(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> Optional[Path]:
        """
        获取已下载文件的路径

        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称

        Returns:
            文件路径
        """
        try:
            # 获取频道目录
            channel_dir = await self.file_processor.get_channel_directory(channel, client)

            # 生成文件名
            file_name = self._generate_filename(message)

            # 构建文件路径
            file_path = channel_dir / file_name

            return file_path if file_path.exists() else None

        except Exception as e:
            logger.error(f"获取下载文件路径失败: {e}")
            return None
    
    def _generate_filename(self, message: Any) -> str:
        """
        生成文件名（与原始程序保持一致）

        Args:
            message: 消息对象

        Returns:
            生成的文件名
        """
        # 检查是否为媒体组消息
        if self.is_media_group_message(message):
            # 媒体组消息：媒体组ID-消息ID.扩展名
            base_name = f"{message.media_group_id}-{message.id}"
        else:
            # 单条消息：msg-消息ID.扩展名
            base_name = f"msg-{message.id}"

        # 获取文件扩展名
        extension = self._get_file_extension(message)
        filename = f"{base_name}{extension}"

        return sanitize_filename(filename)
    
    def _get_file_extension(self, message: Any) -> str:
        """
        获取消息媒体的文件扩展名（与原始程序保持一致）

        Args:
            message: 消息对象

        Returns:
            文件扩展名
        """
        import os

        # 检查不同类型的媒体
        if hasattr(message, 'document') and message.document:
            # 文档类型
            if hasattr(message.document, 'file_name') and message.document.file_name:
                # 从原文件名提取扩展名
                _, ext = os.path.splitext(message.document.file_name)
                return ext if ext else self._get_extension_from_mime(message.document.mime_type)
            else:
                # 根据MIME类型推断扩展名
                return self._get_extension_from_mime(getattr(message.document, 'mime_type', ''))

        elif hasattr(message, 'video') and message.video:
            return '.mp4'
        elif hasattr(message, 'photo') and message.photo:
            return '.jpg'
        elif hasattr(message, 'audio') and message.audio:
            if hasattr(message.audio, 'file_name') and message.audio.file_name:
                _, ext = os.path.splitext(message.audio.file_name)
                return ext if ext else '.mp3'
            return '.mp3'
        elif hasattr(message, 'voice') and message.voice:
            return '.ogg'
        elif hasattr(message, 'video_note') and message.video_note:
            return '.mp4'
        elif hasattr(message, 'animation') and message.animation:
            if hasattr(message.animation, 'file_name') and message.animation.file_name:
                _, ext = os.path.splitext(message.animation.file_name)
                return ext if ext else '.gif'
            return '.gif'
        elif hasattr(message, 'sticker') and message.sticker:
            return '.webp'
        else:
            return '.bin'

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """
        根据MIME类型获取文件扩展名

        Args:
            mime_type: MIME类型

        Returns:
            文件扩展名
        """
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/mov': '.mov',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'text/plain': '.txt'
        }

        return mime_to_ext.get(mime_type, '.bin')
    
    async def _save_text_message(self, message: Any, channel: str, client: Client = None):
        """
        保存文本消息

        Args:
            message: 消息对象
            channel: 频道名称
            client: Pyrogram客户端
        """
        try:
            channel_dir = await self.file_processor.get_channel_directory(channel, client)
            text_file = channel_dir / "messages.txt"

            # 确保目录存在
            channel_dir.mkdir(parents=True, exist_ok=True)

            # 使用同步文件操作（简化处理）
            with open(text_file, "a", encoding="utf-8") as f:
                # 检查是否为媒体组消息
                if self.is_media_group_message(message):
                    f.write(f"消息ID: {message.id} (媒体组: {message.media_group_id})\n")
                else:
                    f.write(f"消息ID: {message.id}\n")

                f.write(f"时间: {message.date}\n")
                f.write(f"内容: {message.text or '无文本内容'}\n")
                f.write("-" * 50 + "\n")

        except Exception as e:
            logger.error(f"保存文本消息失败: {e}")
            raise
