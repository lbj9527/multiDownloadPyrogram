"""
上传服务
负责将下载的消息上传到指定的Telegram频道
"""

import asyncio
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pyrogram import Client
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

from models import MediaInfo, FileInfo
from utils import get_logger, sanitize_filename
from config import app_settings

logger = get_logger(__name__)


class UploadService:
    """上传服务类"""

    def __init__(self):
        self.upload_config = app_settings.upload
        self.media_group_cache: Dict[str, List[Dict]] = {}
        self.current_media_group_id: Optional[str] = None  # 当前处理的媒体组ID
        self.upload_stats = {
            "total_uploaded": 0,
            "total_failed": 0,
            "media_groups_uploaded": 0
        }
    
    async def upload_message(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        上传单条消息到目标频道

        Args:
            client: Pyrogram客户端
            original_message: 原始消息对象
            media_data: 媒体文件的字节数据（内存模式）
            file_path: 文件路径（文件模式）

        Returns:
            是否上传成功
        """
        try:
            logger.info(f"🚀 开始上传消息: {original_message.id}")

            if not self.upload_config.enabled:
                logger.debug("上传功能未启用")
                return False

            if not self.upload_config.target_channel:
                logger.error("未配置上传目标频道")
                return False

            # 检查是否为媒体组消息
            if self._is_media_group_message(original_message):
                logger.info(f"📦 处理媒体组消息: {original_message.id}, 组ID: {original_message.media_group_id}")
                return await self._handle_media_group_message_sequential(
                    client, original_message, media_data, file_path
                )
            else:
                # 处理单条消息前，检查是否需要完成之前的媒体组
                await self._complete_current_media_group(client)

                logger.info(f"📄 处理单条消息: {original_message.id}")
                return await self._upload_single_message(
                    client, original_message, media_data, file_path
                )

        except Exception as e:
            logger.error(f"上传消息失败: {e}")
            self.upload_stats["total_failed"] += 1
            return False
    
    async def _upload_single_message(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """上传单条消息"""
        try:
            # 获取消息文本
            caption = self._get_message_caption(original_message)
            
            if self._has_media(original_message):
                # 上传媒体消息
                success = await self._upload_media_message(
                    client, original_message, media_data, file_path, caption
                )
            else:
                # 上传文本消息
                success = await self._upload_text_message(client, caption)
            
            if success:
                self.upload_stats["total_uploaded"] += 1
                logger.info(f"消息 {original_message.id} 上传成功")
            
            return success
            
        except Exception as e:
            logger.error(f"上传单条消息失败: {e}")
            return False
    
    async def _handle_media_group_message_sequential(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """顺序处理媒体组消息（基于媒体组感知分配）"""
        try:
            media_group_id = original_message.media_group_id

            # 检查是否是新的媒体组
            if self.current_media_group_id != media_group_id:
                # 如果有之前的媒体组未发送，先发送它
                if self.current_media_group_id and self.current_media_group_id in self.media_group_cache:
                    prev_group_size = len(self.media_group_cache[self.current_media_group_id])
                    logger.info(f"🚀 发送完整媒体组 {self.current_media_group_id}，包含 {prev_group_size} 个文件")
                    await self._upload_media_group(client, self.current_media_group_id)

                # 开始新的媒体组
                self.current_media_group_id = media_group_id
                if media_group_id not in self.media_group_cache:
                    self.media_group_cache[media_group_id] = []
                    logger.info(f"📦 开始新媒体组: {media_group_id}")

            # 将消息添加到当前媒体组缓存
            self.media_group_cache[media_group_id].append({
                'message': original_message,
                'media_data': media_data,
                'file_path': file_path,
                'client': client
            })

            current_count = len(self.media_group_cache[media_group_id])
            logger.info(f"媒体组 {media_group_id} 当前有 {current_count} 个文件")

            # 如果当前媒体组已经收集了预期数量的文件（通常是10个），立即发送
            # 这是基于媒体组感知分配的优化：每个客户端应该收到完整的媒体组
            if current_count >= 10:
                logger.info(f"🎯 媒体组 {media_group_id} 收集完整（{current_count}个文件），立即发送")
                await self._upload_media_group(client, media_group_id)
                self.current_media_group_id = None  # 重置当前媒体组ID

            return True

        except Exception as e:
            logger.error(f"处理媒体组消息失败: {e}")
            return False

    async def _complete_current_media_group(self, client: Client) -> bool:
        """完成当前媒体组的上传"""
        if self.current_media_group_id and self.current_media_group_id in self.media_group_cache:
            current_count = len(self.media_group_cache[self.current_media_group_id])
            logger.info(f"🚀 完成媒体组上传: {self.current_media_group_id}，包含 {current_count} 个文件")
            result = await self._upload_media_group(client, self.current_media_group_id)
            self.current_media_group_id = None  # 重置当前媒体组ID
            return result
        return True

    async def _handle_media_group_message(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """处理媒体组消息（旧的时间收集方式，保留作为备用）"""
        try:
            media_group_id = original_message.media_group_id

            # 将消息添加到媒体组缓存
            if media_group_id not in self.media_group_cache:
                self.media_group_cache[media_group_id] = []

            self.media_group_cache[media_group_id].append({
                'message': original_message,
                'media_data': media_data,
                'file_path': file_path,
                'timestamp': time.time(),
                'client': client  # 保存客户端引用
            })

            logger.info(f"媒体组 {media_group_id} 当前有 {len(self.media_group_cache[media_group_id])} 个文件")

            # 等待一段时间收集同组的其他消息
            await asyncio.sleep(3.0)

            # 检查是否应该发送媒体组（使用更短的超时时间）
            if await self._should_send_media_group(media_group_id):
                logger.info(f"准备发送媒体组 {media_group_id}")
                return await self._upload_media_group(client, media_group_id)

            return True

        except Exception as e:
            logger.error(f"处理媒体组消息失败: {e}")
            return False
    
    async def _should_send_media_group(self, media_group_id: str) -> bool:
        """判断是否应该发送媒体组"""
        if media_group_id not in self.media_group_cache:
            return False

        group_messages = self.media_group_cache[media_group_id]
        if not group_messages:
            return False

        # 检查最后一条消息的时间，如果超过2秒则发送
        last_timestamp = max(msg['timestamp'] for msg in group_messages)
        time_since_last = time.time() - last_timestamp

        logger.info(f"媒体组 {media_group_id} 最后消息时间差: {time_since_last:.1f}秒")

        # 如果超过2秒没有新消息，就发送
        return time_since_last > 2.0
    
    async def _upload_media_group(self, client: Client, media_group_id: str) -> bool:
        """上传媒体组"""
        try:
            if media_group_id not in self.media_group_cache:
                return False
            
            group_messages = self.media_group_cache[media_group_id]
            if not group_messages:
                return False
            
            # 准备媒体列表
            input_media_list = []
            
            for i, msg_data in enumerate(group_messages):
                original_message = msg_data['message']
                media_data = msg_data['media_data']
                file_path = msg_data['file_path']
                
                # 创建InputMedia对象
                input_media = await self._create_input_media(
                    original_message, media_data, file_path,
                    caption=self._get_message_caption(original_message) if i == 0 else None
                )
                
                if input_media:
                    input_media_list.append(input_media)
            
            if input_media_list:
                # 发送媒体组
                await client.send_media_group(
                    chat_id=self.upload_config.target_channel,
                    media=input_media_list
                )
                
                self.upload_stats["media_groups_uploaded"] += 1
                self.upload_stats["total_uploaded"] += len(input_media_list)
                logger.info(f"媒体组 {media_group_id} 上传成功，包含 {len(input_media_list)} 个文件")
                
                # 清理缓存
                del self.media_group_cache[media_group_id]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"上传媒体组失败: {e}")
            return False
    
    async def _upload_media_message(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None,
        caption: Optional[str] = None
    ) -> bool:
        """上传媒体消息"""
        try:
            # 准备媒体文件
            if media_data:
                # 内存模式
                memory_file = BytesIO(media_data)
                memory_file.name = self._generate_filename(original_message)
                memory_file.seek(0)
                media_source = memory_file
            elif file_path and file_path.exists():
                # 文件模式
                media_source = str(file_path)
            else:
                logger.error("没有可用的媒体数据或文件路径")
                return False

            # 根据媒体类型直接发送
            media_type = self._detect_media_type(original_message)

            logger.info(f"发送{media_type}到目标频道: {self.upload_config.target_channel}")

            if media_type == 'photo':
                await client.send_photo(
                    chat_id=self.upload_config.target_channel,
                    photo=media_source,
                    caption=caption or ""
                )
            elif media_type == 'video':
                await client.send_video(
                    chat_id=self.upload_config.target_channel,
                    video=media_source,
                    caption=caption or ""
                )
            elif media_type == 'audio':
                await client.send_audio(
                    chat_id=self.upload_config.target_channel,
                    audio=media_source,
                    caption=caption or ""
                )
            else:
                await client.send_document(
                    chat_id=self.upload_config.target_channel,
                    document=media_source,
                    caption=caption or ""
                )

            logger.info(f"✅ {media_type}发送成功")

            # 添加上传延迟
            await asyncio.sleep(self.upload_config.upload_delay)
            return True

        except Exception as e:
            logger.error(f"上传媒体消息失败: {e}")
            return False
    
    async def _upload_text_message(self, client: Client, text: str) -> bool:
        """上传文本消息"""
        try:
            if not text or not text.strip():
                return True  # 空文本消息跳过
            
            await client.send_message(
                chat_id=self.upload_config.target_channel,
                text=text
            )
            
            await asyncio.sleep(self.upload_config.upload_delay)
            return True
            
        except Exception as e:
            logger.error(f"上传文本消息失败: {e}")
            return False
    
    async def _create_input_media(
        self,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None,
        caption: Optional[str] = None
    ) -> Optional[Union[InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument]]:
        """创建InputMedia对象"""
        try:
            # 准备媒体文件
            if media_data:
                # 内存模式 - 直接使用BytesIO对象
                memory_file = BytesIO(media_data)
                memory_file.name = self._generate_filename(original_message)
                # 确保文件指针在开始位置
                memory_file.seek(0)

                logger.debug(f"准备创建InputMedia: {memory_file.name}, 大小: {len(media_data)} 字节")
                media_source = memory_file

            elif file_path and file_path.exists():
                # 文件模式 - 使用文件路径
                media_source = str(file_path)
            else:
                logger.error("没有可用的媒体数据或文件路径")
                return None

            # 根据媒体类型创建InputMedia
            media_type = self._detect_media_type(original_message)

            if media_type == 'photo':
                return InputMediaPhoto(media=media_source, caption=caption or "")
            elif media_type == 'video':
                return InputMediaVideo(media=media_source, caption=caption or "")
            elif media_type == 'audio':
                return InputMediaAudio(media=media_source, caption=caption or "")
            else:
                return InputMediaDocument(media=media_source, caption=caption or "")
                
        except Exception as e:
            logger.error(f"创建InputMedia失败: {e}")
            return None

    def _is_media_group_message(self, message: Any) -> bool:
        """检查消息是否属于媒体组"""
        return hasattr(message, 'media_group_id') and message.media_group_id is not None

    def _has_media(self, message: Any) -> bool:
        """检查消息是否包含媒体"""
        return hasattr(message, 'media') and message.media is not None

    def _detect_media_type(self, message: Any) -> str:
        """检测媒体类型"""
        if hasattr(message, 'photo') and message.photo:
            return 'photo'
        elif hasattr(message, 'video') and message.video:
            return 'video'
        elif hasattr(message, 'audio') and message.audio:
            return 'audio'
        elif hasattr(message, 'voice') and message.voice:
            return 'audio'
        elif hasattr(message, 'video_note') and message.video_note:
            return 'video'
        elif hasattr(message, 'animation') and message.animation:
            return 'video'
        elif hasattr(message, 'document') and message.document:
            return 'document'
        elif hasattr(message, 'sticker') and message.sticker:
            return 'document'
        else:
            return 'document'

    def _get_message_caption(self, message: Any) -> Optional[str]:
        """获取消息说明文字"""
        if not self.upload_config.preserve_captions:
            return None

        # 优先使用caption，其次使用text
        if hasattr(message, 'caption') and message.caption:
            return message.caption
        elif hasattr(message, 'text') and message.text:
            return message.text

        return None

    def _generate_filename(self, message: Any) -> str:
        """生成文件名"""
        # 检查是否为媒体组消息
        if self._is_media_group_message(message):
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
        """获取文件扩展名"""
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
        elif hasattr(message, 'photo') and message.photo:
            return '.jpg'
        elif hasattr(message, 'video') and message.video:
            return '.mp4'
        elif hasattr(message, 'audio') and message.audio:
            return '.mp3'
        elif hasattr(message, 'voice') and message.voice:
            return '.ogg'
        elif hasattr(message, 'video_note') and message.video_note:
            return '.mp4'
        elif hasattr(message, 'animation') and message.animation:
            return '.gif'
        elif hasattr(message, 'sticker') and message.sticker:
            return '.webp'
        else:
            return '.bin'

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """根据MIME类型获取扩展名"""
        mime_extensions = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/mkv': '.mkv',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg',
            'audio/wav': '.wav',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'text/plain': '.txt'
        }
        return mime_extensions.get(mime_type, '.bin')

    async def cleanup_expired_media_groups(self):
        """清理过期的媒体组缓存"""
        current_time = time.time()
        expired_groups = []

        for group_id, messages in self.media_group_cache.items():
            if messages:
                last_timestamp = max(msg['timestamp'] for msg in messages)
                if current_time - last_timestamp > 300:  # 5分钟过期
                    expired_groups.append(group_id)

        for group_id in expired_groups:
            logger.warning(f"清理过期媒体组缓存: {group_id}")
            del self.media_group_cache[group_id]

    def get_upload_stats(self) -> Dict[str, int]:
        """获取上传统计信息"""
        return self.upload_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.upload_stats = {
            "total_uploaded": 0,
            "total_failed": 0,
            "media_groups_uploaded": 0
        }

    async def finalize_upload(self):
        """完成上传，发送所有剩余的媒体组"""
        logger.info("🔄 开始发送剩余的媒体组...")

        # 首先完成当前正在处理的媒体组
        if self.current_media_group_id and self.current_media_group_id in self.media_group_cache:
            group_messages = self.media_group_cache[self.current_media_group_id]
            if group_messages:
                logger.info(f"发送当前媒体组 {self.current_media_group_id}，包含 {len(group_messages)} 个文件")
                client = group_messages[0].get('client')
                if client:
                    try:
                        await self._upload_media_group(client, self.current_media_group_id)
                    except Exception as e:
                        logger.error(f"发送当前媒体组失败: {e}")

        # 然后发送其他剩余的媒体组
        for media_group_id, group_messages in list(self.media_group_cache.items()):
            if group_messages and media_group_id != self.current_media_group_id:
                logger.info(f"发送剩余媒体组 {media_group_id}，包含 {len(group_messages)} 个文件")

                # 使用第一个消息的客户端
                client = group_messages[0].get('client')
                if client:
                    try:
                        await self._upload_media_group(client, media_group_id)
                    except Exception as e:
                        logger.error(f"发送剩余媒体组失败: {e}")

        # 重置状态
        self.current_media_group_id = None
        logger.info("✅ 剩余媒体组发送完成")
