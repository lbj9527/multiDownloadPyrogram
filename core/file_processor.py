"""
文件处理器
负责文件的存储、去重等处理
"""

import time
from pathlib import Path
from typing import Dict, Optional, Set
from datetime import datetime

from models import FileInfo
from utils import get_logger, calculate_file_hash, ensure_directory, get_file_type_category
from config import app_settings

logger = get_logger(__name__)


class FileProcessor:
    """文件处理器"""
    
    def __init__(self, base_directory: Optional[Path] = None):
        self.base_directory = base_directory or app_settings.get_download_directory()
        self.storage_config = app_settings.storage
        
        # 文件哈希缓存（用于去重）
        self._file_hashes: Dict[str, Path] = {}
        
        # 频道目录缓存
        self._channel_directories: Dict[str, Path] = {}
    
    async def process_file(self, file_info: FileInfo) -> bool:
        """
        处理文件（存储、压缩、去重等）
        
        Args:
            file_info: 文件信息
            
        Returns:
            是否处理成功
        """
        try:
            start_time = time.time()
            
            # 检查文件是否存在
            if not file_info.file_path.exists():
                logger.error(f"文件不存在: {file_info.file_path}")
                return False
            
            # 更新文件大小
            file_info.file_size = file_info.file_path.stat().st_size
            
            # 检查是否需要去重
            if await self._check_and_handle_duplicate(file_info):
                logger.info(f"发现重复文件，跳过: {file_info.file_path.name}")
                return True
            
            # 根据存储模式处理文件
            success = await self._process_by_storage_mode(file_info)
            
            if success:
                # 标记为已下载
                download_duration = time.time() - start_time
                file_info.mark_downloaded(download_duration)
                
                # 添加到哈希缓存
                if file_info.file_hash:
                    self._file_hashes[file_info.file_hash] = file_info.file_path
            
            return success
            
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
            return False
    
    async def _check_and_handle_duplicate(self, file_info: FileInfo) -> bool:
        """
        检查并处理重复文件
        
        Args:
            file_info: 文件信息
            
        Returns:
            是否为重复文件
        """
        try:
            # 计算文件哈希
            file_hash = await calculate_file_hash(file_info.file_path)
            file_info.file_hash = file_hash
            
            # 检查是否重复
            if file_hash in self._file_hashes:
                original_path = self._file_hashes[file_hash]
                logger.info(f"发现重复文件: {file_info.file_path.name} -> {original_path.name}")
                
                # 标记为重复并删除当前文件
                file_info.mark_duplicate(file_hash)
                file_info.file_path.unlink()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查重复文件失败: {e}")
            return False
    
    async def _process_by_storage_mode(self, file_info: FileInfo) -> bool:
        """
        根据存储模式处理文件

        Args:
            file_info: 文件信息

        Returns:
            是否处理成功
        """
        # 只支持原始存储模式
        return await self._store_raw_file(file_info)
    
    async def _store_raw_file(self, file_info: FileInfo) -> bool:
        """
        原始存储文件
        
        Args:
            file_info: 文件信息
            
        Returns:
            是否存储成功
        """
        # 文件已经在正确位置，无需额外处理
        logger.debug(f"原始存储文件: {file_info.file_path.name}")
        return True
    




    
    async def get_channel_directory(self, channel: str, client=None) -> Path:
        """
        获取频道目录

        Args:
            channel: 频道名称
            client: Pyrogram客户端（用于获取频道信息）

        Returns:
            频道目录路径
        """
        # 如果有客户端，总是尝试获取最新的频道信息
        if client and channel not in self._channel_directories:
            # 获取频道信息
            channel_info = await self._get_channel_info(channel, client)
            folder_name = channel_info["folder_name"]
            channel_dir = self.base_directory / folder_name

            # 确保目录存在
            ensure_directory(channel_dir)

            # 缓存目录路径
            self._channel_directories[channel] = channel_dir
        elif channel not in self._channel_directories:
            # 没有客户端时使用默认逻辑
            safe_channel_name = channel.replace('@', '').replace('/', '_')
            folder_name = f"@{safe_channel_name}-Unknown"
            channel_dir = self.base_directory / folder_name
            ensure_directory(channel_dir)
            self._channel_directories[channel] = channel_dir

        return self._channel_directories[channel]

    async def _get_channel_info(self, channel: str, client=None) -> dict:
        """
        获取频道信息

        Args:
            channel: 频道名称
            client: Pyrogram客户端

        Returns:
            频道信息字典
        """
        try:
            if client:
                chat = await client.get_chat(channel)
                username = f"@{chat.username}" if chat.username else f"id_{chat.id}"
                title = chat.title or "Unknown"

                # 清理文件名中的非法字符
                from utils import sanitize_filename
                safe_title = sanitize_filename(title)
                folder_name = f"{username}-{safe_title}"

                return {
                    "username": username,
                    "title": title,
                    "folder_name": folder_name,
                    "chat_id": chat.id
                }
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")

        # 失败时返回默认信息
        safe_channel_name = channel.replace('@', '').replace('/', '_')
        return {
            "username": f"@{safe_channel_name}",
            "title": "Unknown",
            "folder_name": f"@{safe_channel_name}-Unknown",
            "chat_id": None
        }

    def close_compression_handles(self):
        """关闭压缩文件句柄（已移除压缩功能，保留方法以兼容性）"""
        pass
    
    def get_storage_stats(self) -> Dict[str, any]:
        """
        获取存储统计信息
        
        Returns:
            存储统计字典
        """
        total_files = len(self._file_hashes)
        total_size = 0
        duplicate_files = 0

        for file_path in self._file_hashes.values():
            if file_path.exists():
                total_size += file_path.stat().st_size

        return {
            "total_files": total_files,
            "total_size": total_size,
            "duplicate_files": duplicate_files,
            "storage_mode": self.storage_config.storage_mode
        }
