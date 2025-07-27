"""
上传服务
负责将下载的消息上传到指定的Telegram频道
"""

import asyncio
import time
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pyrogram import Client
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument

from models import MediaInfo, FileInfo
from utils import get_logger, sanitize_filename
from config import app_settings
from interfaces.core_interfaces import UploadHandlerInterface
from core.media_group_utils import MediaGroupUtils

logger = get_logger(__name__)


@dataclass
class ClientUploadState:
    """客户端上传状态"""
    client_name: str
    current_media_group_id: Optional[str] = None
    media_group_cache: List[Dict] = field(default_factory=list)
    upload_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue())
    is_uploading: bool = False
    upload_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class UploadService(UploadHandlerInterface):
    """优化的上传服务类"""

    def __init__(self):
        self.upload_config = app_settings.upload
        # 每个客户端的上传状态
        self.client_upload_states: Dict[str, ClientUploadState] = {}
        # 为每个客户端启动的上传处理任务
        self.upload_tasks: Dict[str, asyncio.Task] = {}
        self.upload_stats = {
            "total_uploaded": 0,
            "total_failed": 0,
            "media_groups_uploaded": 0
        }
        self._shutdown = False

    # 实现UploadHandlerInterface接口
    async def handle_upload(
        self,
        client: Client,
        message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        处理上传请求 - 实现UploadHandlerInterface接口

        Args:
            client: Pyrogram客户端
            message: 原始消息对象
            media_data: 媒体数据（内存中）
            file_path: 文件路径（本地文件）

        Returns:
            是否上传成功
        """
        return await self.upload_message(
            client=client,
            original_message=message,
            media_data=media_data,
            file_path=file_path
        )

    def is_enabled(self) -> bool:
        """检查上传功能是否启用 - 实现UploadHandlerInterface接口"""
        return self.upload_config.enabled

    async def upload_message(
        self,
        client: Client,
        original_message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        上传消息的主入口（优化版本）

        Args:
            client: Pyrogram客户端
            original_message: 原始消息对象
            media_data: 媒体文件的字节数据（内存模式）
            file_path: 文件路径（文件模式）

        Returns:
            是否成功添加到上传队列
        """
        try:
            if not self.upload_config.enabled:
                logger.debug("上传功能未启用")
                return False

            if not self.upload_config.target_channel:
                logger.error("未配置上传目标频道")
                return False

            client_name = self._get_client_name(client)

            # 确保客户端状态存在
            if client_name not in self.client_upload_states:
                await self._initialize_client_state(client_name)

            # 创建上传任务
            upload_task = {
                'type': 'media_group' if MediaGroupUtils.is_media_group_message(original_message) else 'single',
                'message': original_message,
                'media_data': media_data,
                'file_path': file_path,
                'client': client,
                'timestamp': time.time()
            }

            # 添加到客户端上传队列
            await self.client_upload_states[client_name].upload_queue.put(upload_task)

            logger.debug(f"📝 消息 {original_message.id} 已添加到 {client_name} 的上传队列")
            return True

        except Exception as e:
            logger.error(f"添加上传任务失败: {e}")
            self.upload_stats["total_failed"] += 1
            return False

    def _get_client_name(self, client: Client) -> str:
        """获取客户端名称"""
        return getattr(client, 'name', f'client_{id(client)}')

    async def _initialize_client_state(self, client_name: str):
        """初始化客户端状态"""
        if client_name not in self.client_upload_states:
            self.client_upload_states[client_name] = ClientUploadState(client_name=client_name)

            # 启动客户端上传处理协程
            task = asyncio.create_task(self._client_upload_processor(client_name))
            self.upload_tasks[client_name] = task

            logger.info(f"🔧 初始化客户端 {client_name} 的上传状态")

    async def _client_upload_processor(self, client_name: str):
        """
        客户端上传处理器 - 每个客户端一个独立的处理协程
        """
        state = self.client_upload_states[client_name]
        logger.info(f"🚀 启动客户端 {client_name} 的上传处理器")

        while not self._shutdown:
            try:
                # 从队列获取上传任务，设置超时避免无限等待
                try:
                    upload_task = await asyncio.wait_for(
                        state.upload_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if upload_task is None:  # 停止信号
                    break

                async with state.upload_lock:
                    await self._process_upload_task(state, upload_task)

            except Exception as e:
                logger.error(f"客户端 {client_name} 上传处理失败: {e}")

            finally:
                if not state.upload_queue.empty():
                    state.upload_queue.task_done()

        logger.info(f"🛑 客户端 {client_name} 的上传处理器已停止")

    async def _process_upload_task(self, state: ClientUploadState, task: Dict):
        """
        处理单个上传任务
        """
        try:
            if task['type'] == 'media_group':
                await self._handle_media_group_task(state, task)
            else:
                await self._handle_single_message_task(state, task)
        except Exception as e:
            logger.error(f"处理上传任务失败: {e}")
            self.upload_stats["total_failed"] += 1

    async def _handle_media_group_task(self, state: ClientUploadState, task: Dict):
        """
        处理媒体组任务
        """
        message = task['message']
        media_group_id = message.media_group_id

        # 检查媒体组ID是否发生变化
        if state.current_media_group_id != media_group_id:
            # 媒体组ID变化，先上传当前缓存的媒体组
            if state.current_media_group_id and state.media_group_cache:
                logger.info(f"📤 媒体组ID变化，上传缓存的媒体组: {state.current_media_group_id}")
                await self._upload_cached_media_group(state)

            # 开始新的媒体组
            state.current_media_group_id = media_group_id
            state.media_group_cache = []
            logger.info(f"📦 开始新媒体组: {media_group_id}")

        # 添加消息到当前媒体组缓存
        state.media_group_cache.append({
            'message': message,
            'media_data': task['media_data'],
            'file_path': task['file_path'],
            'client': task['client'],
            'timestamp': task['timestamp']
        })

        logger.info(f"媒体组 {media_group_id} 当前有 {len(state.media_group_cache)} 个文件")

    async def _handle_single_message_task(self, state: ClientUploadState, task: Dict):
        """
        处理单条消息任务
        """
        # 单条消息出现，表示当前媒体组已完整，先上传缓存的媒体组
        if state.current_media_group_id and state.media_group_cache:
            logger.info(f"📤 遇到单条消息，上传缓存的媒体组: {state.current_media_group_id}")
            await self._upload_cached_media_group(state)

        # 立即上传单条消息
        logger.info(f"📄 立即上传单条消息: {task['message'].id}")
        await self._upload_single_message(
            task['client'],
            task['message'],
            task['media_data'],
            task['file_path']
        )

    async def _upload_cached_media_group(self, state: ClientUploadState):
        """
        上传缓存的媒体组
        """
        if not state.media_group_cache:
            return

        try:
            # 准备媒体列表
            input_media_list = []
            client = None

            for i, msg_data in enumerate(state.media_group_cache):
                client = msg_data['client']

                # 创建InputMedia对象
                input_media = await self._create_input_media(
                    msg_data['message'],
                    msg_data['media_data'],
                    msg_data['file_path'],
                    caption=self._get_message_caption(msg_data['message']) if i == 0 else None
                )

                if input_media:
                    input_media_list.append(input_media)

            if input_media_list and client:
                # 发送媒体组
                await client.send_media_group(
                    chat_id=self.upload_config.target_channel,
                    media=input_media_list
                )

                self.upload_stats["media_groups_uploaded"] += 1
                self.upload_stats["total_uploaded"] += len(input_media_list)

                logger.info(f"✅ 媒体组 {state.current_media_group_id} 上传成功，包含 {len(input_media_list)} 个文件")

        except Exception as e:
            logger.error(f"❌ 上传媒体组失败: {e}")
            self.upload_stats["total_failed"] += len(state.media_group_cache)

        finally:
            # 清理缓存
            state.current_media_group_id = None
            state.media_group_cache = []

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
    
    async def shutdown(self):
        """关闭上传服务"""
        logger.info("🛑 开始关闭上传服务...")

        # 只等待队列中的任务完成（不等待缓存，因为缓存需要手动处理）
        await self._wait_for_queue_complete()

        # 并发完成所有客户端的剩余媒体组上传
        upload_tasks = []
        for client_name, state in self.client_upload_states.items():
            if state.current_media_group_id and state.media_group_cache:
                logger.info(f"📤 准备上传客户端 {client_name} 的剩余媒体组")
                task = self._upload_cached_media_group(state)
                upload_tasks.append(task)

        # 并发等待所有上传完成
        if upload_tasks:
            logger.info(f"🚀 开始并发上传 {len(upload_tasks)} 个客户端的媒体组")
            await asyncio.gather(*upload_tasks)
            logger.info("✅ 所有客户端的媒体组上传完成")
        else:
            logger.info("📋 没有剩余的媒体组需要上传")

        # 设置关闭标志并停止所有上传处理任务
        self._shutdown = True
        for client_name, task in self.upload_tasks.items():
            if not task.done():
                # 发送停止信号
                await self.client_upload_states[client_name].upload_queue.put(None)
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"客户端 {client_name} 的上传任务超时，强制取消")
                    task.cancel()

        logger.info("✅ 上传服务已关闭")

    async def _wait_for_queue_complete(self):
        """等待所有队列中的任务完成（不包括缓存的媒体组）"""
        logger.info("⏳ 等待队列中的上传任务完成...")

        # 只统计队列中的任务数
        total_queue = sum(state.upload_queue.qsize() for state in self.client_upload_states.values())
        total_cached = sum(len(state.media_group_cache) for state in self.client_upload_states.values())

        if total_queue == 0:
            if total_cached > 0:
                logger.info(f"📋 队列已空，还有 {total_cached} 个缓存的媒体组待处理")
            else:
                logger.info("📋 没有待处理的队列任务")
            return

        logger.info(f"📋 队列中有 {total_queue} 个任务待处理，缓存中有 {total_cached} 个媒体组")

        # 只等待队列清空，设置超时防止无限等待
        last_queue_size = total_queue
        start_time = asyncio.get_event_loop().time()
        timeout = 300  # 5分钟超时

        while True:
            current_queue = sum(state.upload_queue.qsize() for state in self.client_upload_states.values())

            if current_queue == 0:
                logger.info("✅ 所有队列任务已完成")
                break

            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.warning(f"⚠️ 等待队列完成超时（{timeout}秒），强制继续，剩余任务: {current_queue}")
                break

            # 如果队列大小有变化，显示进度
            if current_queue != last_queue_size:
                completed = total_queue - current_queue
                progress = (completed / total_queue) * 100
                logger.info(f"📊 队列处理进度: {completed}/{total_queue} ({progress:.1f}%) - 剩余: {current_queue}")
                last_queue_size = current_queue

            await asyncio.sleep(0.5)  # 每0.5秒检查一次

    async def get_upload_stats(self) -> Dict[str, Any]:
        """获取上传统计信息"""
        stats = self.upload_stats.copy()

        # 添加客户端状态信息
        client_stats = {}
        for client_name, state in self.client_upload_states.items():
            client_stats[client_name] = {
                'current_media_group_id': state.current_media_group_id,
                'cached_messages': len(state.media_group_cache),
                'queue_size': state.upload_queue.qsize(),
                'is_uploading': state.is_uploading
            }

        stats['client_states'] = client_stats
        return stats


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
        return MediaGroupUtils.is_media_group_message(message)

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
        return MediaGroupUtils.get_message_caption(message)

    def _generate_filename(self, message: Any) -> str:
        """生成文件名"""
        extension = self._get_file_extension(message)
        filename = MediaGroupUtils.generate_filename_for_message(message, extension)
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

    def reset_stats(self):
        """重置统计信息"""
        self.upload_stats = {
            "total_uploaded": 0,
            "total_failed": 0,
            "media_groups_uploaded": 0
        }
