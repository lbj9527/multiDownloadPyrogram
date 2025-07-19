#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息下载管理器
"""

import asyncio
import os
import re
import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from pathlib import Path
from datetime import datetime
import uuid

from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired, MessageNotModified

from ..models.download_config import DownloadConfig, DownloadProgress, DownloadStatus, DownloadTask, MessageType
from ..models.events import EventType, create_download_event, create_error_event
from ..utils.logger import get_logger
from ..utils.file_utils import sanitize_filename, get_file_extension


class DownloadManager:
    """消息下载管理器"""
    
    def __init__(self, client_manager, event_callback: Optional[Callable] = None):
        """
        初始化下载管理器
        
        Args:
            client_manager: 客户端管理器实例
            event_callback: 事件回调函数
        """
        self.client_manager = client_manager
        self.event_callback = event_callback
        self.logger = get_logger(__name__)
        
        # 当前下载任务
        self.current_tasks: Dict[str, DownloadTask] = {}
        # 下载队列
        self.download_queue: List[DownloadTask] = []
        # 是否正在下载
        self.is_downloading = False
        
        # 下载统计
        self.download_stats = {
            "total_downloaded": 0,
            "total_size": 0,
            "start_time": None,
            "errors": []
        }
    
    async def start_download(self, config: DownloadConfig) -> str:
        """
        开始下载任务
        
        Args:
            config: 下载配置
            
        Returns:
            str: 任务ID
        """
        # 创建任务
        task_id = str(uuid.uuid4())
        task = DownloadTask(
            task_id=task_id,
            config=config,
            created_at=datetime.now().isoformat()
        )
        
        # 验证配置
        if not await self._validate_download_config(config):
            task.progress.status = DownloadStatus.FAILED
            task.progress.error_message = "下载配置验证失败"
            return task_id
        
        # 添加到任务列表
        self.current_tasks[task_id] = task
        
        # 发送下载开始事件
        if self.event_callback:
            event = create_download_event(
                EventType.DOWNLOAD_STARTED,
                task_id,
                f"开始下载任务: {config.channel_id}",
                channel_id=config.channel_id,
                data={"config": config.dict()}
            )
            self.event_callback(event)
        
        # 启动下载
        asyncio.create_task(self._execute_download(task))
        
        return task_id
    
    async def _validate_download_config(self, config: DownloadConfig) -> bool:
        """验证下载配置"""
        try:
            # 检查是否有可用的客户端
            enabled_clients = self.client_manager.get_enabled_clients()
            if not enabled_clients:
                self.logger.error("没有可用的客户端")
                return False
            
            # 检查下载路径
            download_path = Path(config.download_path)
            download_path.mkdir(parents=True, exist_ok=True)
            
            # 测试频道访问权限
            client_name = enabled_clients[0]
            client = self.client_manager.get_client(client_name)
            
            if client and client.is_connected:
                try:
                    # 尝试获取频道信息
                    chat = await client.get_chat(config.channel_id)
                    self.logger.info(f"频道验证成功: {chat.title}")
                    return True
                except ChannelPrivate:
                    self.logger.error(f"频道 {config.channel_id} 为私有频道或无访问权限")
                    return False
                except Exception as e:
                    self.logger.error(f"频道验证失败: {e}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    async def _execute_download(self, task: DownloadTask):
        """执行下载任务"""
        try:
            task.progress.status = DownloadStatus.DOWNLOADING
            task.started_at = datetime.now().isoformat()
            
            # 获取可用客户端
            enabled_clients = self.client_manager.get_enabled_clients()
            if not enabled_clients:
                raise Exception("没有可用的客户端")
            
            # 获取消息列表
            messages = await self._get_messages(task, enabled_clients[0])
            if not messages:
                raise Exception("未找到消息")
            
            task.progress.total_messages = len(messages)
            
            # 分配任务给多个客户端
            client_tasks = self._distribute_tasks(messages, enabled_clients)
            task.client_assignments = {client: [msg.id for msg in msgs] for client, msgs in client_tasks.items()}
            
            # 并发下载
            download_tasks = []
            for client_name, client_messages in client_tasks.items():
                download_tasks.append(
                    self._download_messages_with_client(task, client_name, client_messages)
                )
            
            # 等待所有下载任务完成
            await asyncio.gather(*download_tasks, return_exceptions=True)
            
            # 检查下载结果
            if task.progress.downloaded_messages == task.progress.total_messages:
                task.progress.status = DownloadStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                
                # 发送完成事件
                if self.event_callback:
                    event = create_download_event(
                        EventType.DOWNLOAD_COMPLETED,
                        task.task_id,
                        f"下载任务完成: {task.config.channel_id}",
                        channel_id=task.config.channel_id,
                        progress_data=task.progress.dict()
                    )
                    self.event_callback(event)
            else:
                task.progress.status = DownloadStatus.FAILED
                task.progress.error_message = "部分消息下载失败"
                
        except Exception as e:
            self.logger.error(f"下载任务执行失败: {e}")
            task.progress.status = DownloadStatus.FAILED
            task.progress.error_message = str(e)
            
            # 发送失败事件
            if self.event_callback:
                event = create_download_event(
                    EventType.DOWNLOAD_FAILED,
                    task.task_id,
                    f"下载任务失败: {e}",
                    channel_id=task.config.channel_id,
                    data={"error": str(e)}
                )
                self.event_callback(event)
    
    async def _get_messages(self, task: DownloadTask, client_name: str) -> List[Message]:
        """获取消息列表"""
        client = self.client_manager.get_client(client_name)
        if not client or not client.is_connected:
            raise Exception(f"客户端 {client_name} 不可用")
        
        try:
            messages = []
            config = task.config
            
            # 获取消息
            async for message in client.get_chat_history(
                chat_id=config.channel_id,
                limit=config.message_count,
                offset_id=config.start_message_id + config.message_count
            ):
                if message.id >= config.start_message_id:
                    # 过滤消息类型
                    if self._should_download_message(message, config):
                        messages.append(message)
                
                if len(messages) >= config.message_count:
                    break
            
            # 按消息ID排序
            messages.sort(key=lambda x: x.id)
            
            self.logger.info(f"获取到 {len(messages)} 条消息")
            return messages
            
        except FloodWait as e:
            self.logger.warning(f"获取消息时触发限流，等待 {e.value} 秒")
            await asyncio.sleep(e.value)
            return await self._get_messages(task, client_name)
            
        except Exception as e:
            self.logger.error(f"获取消息失败: {e}")
            raise
    
    def _should_download_message(self, message: Message, config: DownloadConfig) -> bool:
        """判断是否应该下载该消息"""
        # 检查是否包含文本消息
        if message.text and config.include_text:
            return True
        
        # 检查是否包含媒体文件
        if not config.include_media:
            return False
        
        # 检查媒体类型
        if message.photo and MessageType.PHOTO in config.media_types:
            return True
        elif message.video and MessageType.VIDEO in config.media_types:
            return True
        elif message.document and MessageType.DOCUMENT in config.media_types:
            return True
        elif message.audio and MessageType.AUDIO in config.media_types:
            return True
        elif message.voice and MessageType.VOICE in config.media_types:
            return True
        elif message.sticker and MessageType.STICKER in config.media_types:
            return True
        elif message.animation and MessageType.ANIMATION in config.media_types:
            return True
        elif message.video_note and MessageType.VIDEO_NOTE in config.media_types:
            return True
        
        return False
    
    def _distribute_tasks(self, messages: List[Message], clients: List[str]) -> Dict[str, List[Message]]:
        """将消息分配给多个客户端"""
        if not clients:
            return {}
        
        # 平均分配消息
        client_tasks = {client: [] for client in clients}
        
        for i, message in enumerate(messages):
            client_index = i % len(clients)
            client_name = clients[client_index]
            client_tasks[client_name].append(message)
        
        self.logger.info(f"消息分配完成，共 {len(clients)} 个客户端")
        for client, msgs in client_tasks.items():
            self.logger.info(f"客户端 {client}: {len(msgs)} 条消息")
        
        return client_tasks

    async def _download_messages_with_client(self, task: DownloadTask, client_name: str, messages: List[Message]):
        """使用指定客户端下载消息"""
        client = self.client_manager.get_client(client_name)
        if not client or not client.is_connected:
            self.logger.error(f"客户端 {client_name} 不可用")
            return

        try:
            for message in messages:
                if task.progress.status == DownloadStatus.CANCELLED:
                    break

                await self._download_single_message(task, client, message, client_name)

                # 更新进度
                task.progress.downloaded_messages += 1

                # 发送进度事件
                if self.event_callback:
                    event = create_download_event(
                        EventType.DOWNLOAD_PROGRESS,
                        task.task_id,
                        f"下载进度: {task.progress.downloaded_messages}/{task.progress.total_messages}",
                        channel_id=task.config.channel_id,
                        progress_data=task.progress.dict()
                    )
                    self.event_callback(event)

                # 避免过快请求
                await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"客户端 {client_name} 下载失败: {e}")

    async def _download_single_message(self, task: DownloadTask, client: Client, message: Message, client_name: str):
        """下载单条消息"""
        try:
            config = task.config
            download_path = Path(config.download_path)

            # 处理文本消息
            if message.text and config.include_text:
                await self._save_text_message(message, download_path, task.config.channel_id)

            # 处理媒体文件
            if config.include_media:
                await self._download_media_file(task, client, message, download_path, client_name)

        except FloodWait as e:
            self.logger.warning(f"下载消息 {message.id} 时触发限流，等待 {e.value} 秒")

            # 发送FloodWait事件
            if self.event_callback:
                error_event = create_error_event(
                    EventType.ERROR_FLOOD_WAIT,
                    f"客户端 {client_name} 触发限流",
                    error_details={"wait_time": e.value, "message_id": message.id},
                    source="download_manager"
                )
                self.event_callback(error_event)

            await asyncio.sleep(e.value)
            # 重试下载
            await self._download_single_message(task, client, message, client_name)

        except Exception as e:
            self.logger.error(f"下载消息 {message.id} 失败: {e}")
            task.progress.error_message = f"下载消息 {message.id} 失败: {e}"

    async def _save_text_message(self, message: Message, download_path: Path, channel_id: str):
        """保存文本消息"""
        try:
            # 创建文本文件名
            timestamp = datetime.fromtimestamp(message.date.timestamp()).strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{message.id}_{sanitize_filename(channel_id)}_text.txt"
            file_path = download_path / filename

            # 保存文本内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"消息ID: {message.id}\n")
                f.write(f"时间: {message.date}\n")
                f.write(f"频道: {channel_id}\n")
                f.write(f"内容:\n{message.text}\n")

            self.logger.debug(f"保存文本消息: {filename}")

        except Exception as e:
            self.logger.error(f"保存文本消息失败: {e}")

    async def _download_media_file(self, task: DownloadTask, client: Client, message: Message,
                                 download_path: Path, client_name: str):
        """下载媒体文件"""
        try:
            media = None
            media_type = None

            # 确定媒体类型和对象
            if message.photo:
                media = message.photo
                media_type = "photo"
            elif message.video:
                media = message.video
                media_type = "video"
            elif message.document:
                media = message.document
                media_type = "document"
            elif message.audio:
                media = message.audio
                media_type = "audio"
            elif message.voice:
                media = message.voice
                media_type = "voice"
            elif message.sticker:
                media = message.sticker
                media_type = "sticker"
            elif message.animation:
                media = message.animation
                media_type = "animation"
            elif message.video_note:
                media = message.video_note
                media_type = "video_note"

            if not media:
                return

            # 检查文件大小限制
            file_size = getattr(media, 'file_size', 0)
            if task.config.max_file_size and file_size > task.config.max_file_size:
                self.logger.warning(f"文件 {message.id} 大小超过限制: {file_size} > {task.config.max_file_size}")
                return

            # 生成文件名
            filename = self._generate_filename(message, media, media_type, task.config.channel_id)
            file_path = download_path / filename

            # 更新当前下载文件
            task.progress.current_file = filename
            task.progress.total_files += 1

            # 下载文件
            start_time = time.time()
            await client.download_media(
                message,
                file_name=str(file_path),
                progress=lambda current, total: self._update_download_progress(
                    task, current, total, start_time, filename
                )
            )

            # 更新统计
            task.progress.downloaded_files += 1
            task.progress.downloaded_size += file_size
            task.progress.total_size += file_size

            self.logger.info(f"下载完成: {filename}")

            # 发送文件完成事件
            if self.event_callback:
                event = create_download_event(
                    EventType.DOWNLOAD_FILE_COMPLETED,
                    task.task_id,
                    f"文件下载完成: {filename}",
                    channel_id=task.config.channel_id,
                    data={"filename": filename, "size": file_size, "client": client_name}
                )
                self.event_callback(event)

        except Exception as e:
            self.logger.error(f"下载媒体文件失败: {e}")

    def _generate_filename(self, message: Message, media, media_type: str, channel_id: str) -> str:
        """生成文件名"""
        try:
            # 获取时间戳
            timestamp = datetime.fromtimestamp(message.date.timestamp()).strftime("%Y%m%d_%H%M%S")

            # 获取原始文件名
            original_name = ""
            if hasattr(media, 'file_name') and media.file_name:
                original_name = media.file_name
            elif hasattr(media, 'title') and media.title:
                original_name = media.title

            # 获取文件扩展名
            extension = get_file_extension(media, media_type)

            # 清理频道名称
            clean_channel = sanitize_filename(channel_id)

            # 构建文件名
            if original_name:
                # 移除原始文件名的扩展名
                name_without_ext = os.path.splitext(original_name)[0]
                clean_name = sanitize_filename(name_without_ext)
                filename = f"{timestamp}_{message.id}_{clean_channel}_{clean_name}{extension}"
            else:
                filename = f"{timestamp}_{message.id}_{clean_channel}_{media_type}{extension}"

            return filename

        except Exception as e:
            self.logger.error(f"生成文件名失败: {e}")
            return f"{message.id}_{media_type}.bin"

    def _update_download_progress(self, task: DownloadTask, current: int, total: int,
                                start_time: float, filename: str):
        """更新下载进度"""
        try:
            # 计算下载速度
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                speed = current / elapsed_time
                task.progress.download_speed = speed

                # 计算预计剩余时间
                if speed > 0:
                    remaining_bytes = total - current
                    eta = int(remaining_bytes / speed)
                    task.progress.eta = eta

            # 更新当前文件进度
            task.progress.current_file = f"{filename} ({current}/{total})"

        except Exception as e:
            self.logger.error(f"更新进度失败: {e}")

    def get_task_progress(self, task_id: str) -> Optional[DownloadProgress]:
        """获取任务进度"""
        task = self.current_tasks.get(task_id)
        return task.progress if task else None

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self.current_tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.current_tasks.get(task_id)
        if task and task.is_active():
            task.progress.status = DownloadStatus.CANCELLED
            self.logger.info(f"任务 {task_id} 已取消")

            # 发送取消事件
            if self.event_callback:
                event = create_download_event(
                    EventType.DOWNLOAD_CANCELLED,
                    task_id,
                    f"下载任务已取消",
                    channel_id=task.config.channel_id
                )
                self.event_callback(event)

            return True
        return False

    def get_active_tasks(self) -> List[DownloadTask]:
        """获取活跃任务列表"""
        return [task for task in self.current_tasks.values() if task.is_active()]

    def get_completed_tasks(self) -> List[DownloadTask]:
        """获取已完成任务列表"""
        return [task for task in self.current_tasks.values() if task.is_completed()]
