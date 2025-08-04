"""
RAW API下载器
使用Telegram RAW API进行下载
"""
from pathlib import Path
from typing import Optional, Any, Union
from pyrogram.client import Client
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import InputDocumentFileLocation, InputPhotoFileLocation
from pyrogram.file_id import FileId, FileType
from .base import BaseDownloader
from models.download_result import DownloadResult
from utils.message_utils import MessageUtils

class RawDownloader(BaseDownloader):
    """RAW API下载器 - 使用Telegram RAW API"""
    
    async def download(self, client: Client, message: Any, folder_name: str) -> Optional[Path]:
        """本地下载方法（保持向后兼容）"""
        return await self._download_to_file(client, message, folder_name)

    async def download_to_memory(self, client: Client, message: Any) -> Optional[DownloadResult]:
        """内存下载方法"""
        return await self._download_to_memory(client, message)

    async def _download_to_file(self, client: Client, message: Any, folder_name: str) -> Optional[Path]:
        """
        使用RAW API方法下载媒体文件到本地
        """
        try:
            # 验证消息
            if not self.validate_message(message):
                self.log_error(f"消息 {message.id} 无有效媒体")
                return None
            
            # 生成文件路径
            file_path = self.generate_file_path(message, folder_name)
            
            # 获取文件大小信息
            size_info = self.get_file_size_info(message)
            expected_size = size_info["size_bytes"]
            
            # 记录下载开始
            self.log_download_start(message, file_path, "RAW API")
            
            # 获取媒体对象
            media = (message.document or message.video or message.photo or 
                    message.audio or message.voice or message.video_note or 
                    message.animation or message.sticker)
            
            if not media:
                self.log_error(f"消息 {message.id} 无有效媒体对象")
                return None
            
            # 解析文件ID
            file_id_obj = FileId.decode(media.file_id)
            
            # 根据文件类型创建输入位置 - 修复thumb_size参数
            if file_id_obj.file_type == FileType.PHOTO:
                input_location = InputPhotoFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )
            else:
                input_location = InputDocumentFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )
            
            # 检查数据中心迁移
            dc_id = file_id_obj.dc_id
            current_dc_id = await client.storage.dc_id()
            
            if dc_id != current_dc_id:
                self.log_info(f"消息 {message.id} 文件位于数据中心 {dc_id}，当前连接到 {current_dc_id}")
                # 使用Pyrogram的内置下载方法处理数据中心迁移
                try:
                    downloaded_path = await client.download_media(message, file_name=str(file_path))
                    if downloaded_path:
                        self.log_download_success(file_path, file_path.stat().st_size)
                        return Path(downloaded_path)
                    else:
                        self.log_error(f"内置方法下载失败")
                        return None
                except Exception as e:
                    self.log_error(f"内置方法下载异常: {e}")
                    return None
            
            # 分片下载
            offset = 0
            chunk_size = 1024 * 1024  # 1MB，Telegram API最大值

            with open(file_path, 'wb') as f:
                while offset < expected_size or expected_size == 0:
                    try:
                        # 调用RAW API获取文件块 - 使用与原程序相同的逻辑
                        result = await client.invoke(
                            GetFile(
                                location=input_location,
                                offset=offset,
                                limit=chunk_size
                            )
                        )

                        # 检查返回结果
                        if not hasattr(result, 'bytes') or not result.bytes:
                            break

                        # 写入文件
                        f.write(result.bytes)
                        offset += len(result.bytes)

                        # 显示进度（每10MB显示一次）
                        if offset % (10 * 1024 * 1024) == 0:
                            progress_mb = offset / (1024 * 1024)
                            self.log_info(f"消息 {message.id} 已下载: {progress_mb:.1f} MB")

                    except Exception as e:
                        self.log_error(f"RAW API下载消息 {message.id} 分片失败: {e}")
                        return None
            
            # 验证下载完整性
            actual_size = file_path.stat().st_size
            if not self.verify_download(file_path, expected_size):
                self.log_warning(
                    f"消息 {message.id} 文件大小不匹配: "
                    f"期望 {expected_size}, 实际 {actual_size}"
                )
            
            # 记录下载成功
            self.log_download_success(file_path, actual_size)
            return file_path
            
        except Exception as e:
            self.log_download_error(message, e, "RAW API")
            # 清理失败的文件
            if 'file_path' in locals() and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            return None

    async def _download_to_memory(self, client: Client, message: Any) -> Optional[DownloadResult]:
        """
        使用RAW API方法下载媒体文件到内存
        """
        try:
            # 验证消息
            if not self.validate_message(message):
                self.log_error(f"消息 {message.id} 无有效媒体")
                return None

            # 使用统一的工具函数获取文件信息
            file_info = MessageUtils.get_file_info(message)
            file_name = file_info['file_name']

            # 获取文件大小信息 - 使用原函数的方法
            size_info = self.get_file_size_info(message)
            expected_size = size_info["size_bytes"]

            # 获取MIME类型
            mime_type = file_info.get('mime_type')

            # 记录下载开始
            self.log_info(f"开始RAW API内存下载消息 {message.id}: {file_name}")

            # 获取媒体对象
            media = (message.document or message.video or message.photo or
                    message.audio or message.voice or message.video_note or
                    message.animation or message.sticker)

            if not media:
                self.log_error(f"消息 {message.id} 无有效媒体对象")
                return None

            # 解析文件ID
            file_id_obj = FileId.decode(media.file_id)

            # 根据文件类型创建输入位置 - 与原函数完全相同
            if file_id_obj.file_type == FileType.PHOTO:
                input_location = InputPhotoFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )
            else:
                input_location = InputDocumentFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )

            # 检查数据中心迁移
            dc_id = file_id_obj.dc_id
            current_dc_id = await client.storage.dc_id()

            if dc_id != current_dc_id:
                self.log_error(f"消息 {message.id} 文件位于数据中心 {dc_id}，当前连接到 {current_dc_id}，RAW API不支持跨数据中心")
                return None

            # 分片下载到内存 - 使用与原函数完全相同的逻辑
            file_data = bytearray()
            offset = 0
            chunk_size = 1024 * 1024  # 1MB，Telegram API最大值

            while offset < expected_size or expected_size == 0:
                try:
                    # 调用RAW API获取文件块
                    result = await client.invoke(
                        GetFile(
                            location=input_location,
                            offset=offset,
                            limit=chunk_size
                        )
                    )

                    # 检查返回结果
                    if not hasattr(result, 'bytes') or not result.bytes:
                        break

                    # 添加到内存
                    file_data.extend(result.bytes)
                    offset += len(result.bytes)

                    # 显示进度（每10MB显示一次）
                    if offset % (10 * 1024 * 1024) == 0:
                        progress_mb = offset / (1024 * 1024)
                        self.log_info(f"消息 {message.id} 已下载到内存: {progress_mb:.1f} MB")

                except Exception as e:
                    self.log_error(f"RAW API内存下载消息 {message.id} 分片失败: {e}")
                    return None

            # 转换为bytes
            file_bytes = bytes(file_data)
            actual_size = len(file_bytes)

            # 验证下载完整性
            if expected_size > 0 and actual_size != expected_size:
                self.log_warning(
                    f"消息 {message.id} 文件大小不匹配: "
                    f"期望 {expected_size}, 实际 {actual_size}"
                )

            # 创建下载结果
            result = MessageUtils.create_memory_download_result(message, file_bytes, client.name, file_info)

            # 记录下载成功
            self.log_info(f"RAW API内存下载完成: {file_name} ({result.get_size_formatted()})")
            return result

        except Exception as e:
            self.log_error(f"RAW API内存下载消息 {message.id} 失败: {e}")
            return None




