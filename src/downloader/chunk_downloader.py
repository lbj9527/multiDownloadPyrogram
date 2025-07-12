"""
分片下载器模块

专门处理大文件的分片并发下载，提高下载效率和稳定性
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from utils.config import Config
from utils.logger import get_logger
from utils.exceptions import ChunkDownloadError, DownloadError
from client.client_manager import ClientManager


@dataclass
class ChunkInfo:
    """分片信息"""
    index: int
    start_offset: int
    end_offset: int
    size: int
    downloaded: int = 0
    completed: bool = False
    retry_count: int = 0
    
    @property
    def progress(self) -> float:
        """获取分片进度"""
        return (self.downloaded / self.size) * 100 if self.size > 0 else 0


@dataclass
class ChunkDownloadProgress:
    """分片下载进度"""
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    total_size: int
    downloaded_size: int
    speed: float = 0.0
    eta: float = 0.0
    start_time: float = 0.0
    file_name: str = ""
    
    def update(self):
        """更新进度信息"""
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.speed = self.downloaded_size / elapsed_time
            if self.speed > 0:
                remaining_bytes = self.total_size - self.downloaded_size
                self.eta = remaining_bytes / self.speed
    
    @property
    def percentage(self) -> float:
        """获取总进度百分比"""
        return (self.downloaded_size / self.total_size) * 100 if self.total_size > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "failed_chunks": self.failed_chunks,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "speed": self.speed,
            "eta": self.eta,
            "percentage": self.percentage,
            "file_name": self.file_name
        }


class ChunkDownloader:
    """分片下载器"""
    
    def __init__(self, config: Config, client_manager: Optional[ClientManager] = None):
        """
        初始化分片下载器
        
        Args:
            config: 配置对象
            client_manager: 客户端管理器
        """
        self.config = config
        self.client_manager = client_manager
        self.logger = get_logger(f"{__name__}.ChunkDownloader")
        
        # 分片配置
        self.chunk_size = config.download.chunk_size
        self.max_concurrent_chunks = 3  # 最大并发分片数
        self.max_retries = config.download.retry_count
        self.timeout = config.download.timeout
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        self.chunk_progress_callback: Optional[Callable] = None
        
        # 统计信息
        self.total_chunks_downloaded = 0
        self.total_chunks_failed = 0
        self.total_bytes_downloaded = 0
    
    def set_progress_callback(self, callback: Callable[[ChunkDownloadProgress], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_chunk_progress_callback(self, callback: Callable[[ChunkInfo], None]):
        """设置分片进度回调函数"""
        self.chunk_progress_callback = callback
    
    def _calculate_chunks(self, file_size: int, chunk_size: int) -> List[ChunkInfo]:
        """
        计算分片信息
        
        Args:
            file_size: 文件大小
            chunk_size: 分片大小
            
        Returns:
            分片信息列表
        """
        chunks = []
        for i in range(0, file_size, chunk_size):
            start_offset = i
            end_offset = min(i + chunk_size - 1, file_size - 1)
            chunk_size_actual = end_offset - start_offset + 1
            
            chunk = ChunkInfo(
                index=len(chunks),
                start_offset=start_offset,
                end_offset=end_offset,
                size=chunk_size_actual
            )
            chunks.append(chunk)
        
        return chunks
    
    async def _download_chunk(self, message: Message, chunk: ChunkInfo, 
                             file_handle, progress: ChunkDownloadProgress) -> bool:
        """
        下载单个分片
        
        Args:
            message: 消息对象
            chunk: 分片信息
            file_handle: 文件句柄
            progress: 下载进度
            
        Returns:
            是否下载成功
        """
        client = self.client_manager.client if self.client_manager else None
        if not client:
            raise ChunkDownloadError("没有可用的客户端", chunk_index=chunk.index)
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.logger.debug(f"开始下载分片 {chunk.index}: {chunk.start_offset}-{chunk.end_offset}")
                
                # 使用stream_media获取数据
                chunk_data = b''
                async for data in client.stream_media(
                    message, 
                    offset=chunk.start_offset, 
                    limit=chunk.size
                ):
                    chunk_data += data
                    chunk.downloaded = len(chunk_data)
                    
                    # 更新分片进度
                    if self.chunk_progress_callback:
                        await self.chunk_progress_callback(chunk)
                    
                    # 检查是否完成
                    if len(chunk_data) >= chunk.size:
                        break
                
                # 写入文件
                file_handle.seek(chunk.start_offset)
                file_handle.write(chunk_data)
                file_handle.flush()
                
                # 标记完成
                chunk.completed = True
                chunk.downloaded = len(chunk_data)
                
                # 更新总进度
                progress.completed_chunks += 1
                progress.downloaded_size += chunk.downloaded
                progress.update()
                
                self.logger.debug(f"分片 {chunk.index} 下载完成")
                self.total_chunks_downloaded += 1
                return True
                
            except FloodWait as e:
                self.logger.warning(f"分片 {chunk.index} 遇到FloodWait: {e.value}秒")
                await asyncio.sleep(e.value)
                retry_count += 1
                
            except Exception as e:
                self.logger.error(f"分片 {chunk.index} 下载失败: {e}")
                retry_count += 1
                chunk.retry_count = retry_count
                
                if retry_count < self.max_retries:
                    # 指数退避
                    await asyncio.sleep(2 ** retry_count)
                else:
                    break
        
        # 所有重试都失败了
        self.logger.error(f"分片 {chunk.index} 下载失败，已重试 {self.max_retries} 次")
        progress.failed_chunks += 1
        self.total_chunks_failed += 1
        return False
    
    async def download_file_chunks(self, message: Message, file_path: Path, 
                                  file_size: int) -> bool:
        """
        分片下载文件
        
        Args:
            message: 消息对象
            file_path: 文件路径
            file_size: 文件大小
            
        Returns:
            是否下载成功
        """
        # 计算分片
        chunks = self._calculate_chunks(file_size, self.chunk_size)
        
        self.logger.info(f"开始分片下载: {file_path.name}, 总大小: {file_size}, 分片数: {len(chunks)}")
        
        # 创建进度对象
        progress = ChunkDownloadProgress(
            total_chunks=len(chunks),
            completed_chunks=0,
            failed_chunks=0,
            total_size=file_size,
            downloaded_size=0,
            start_time=time.time(),
            file_name=file_path.name
        )
        
        # 创建文件
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'wb') as file_handle:
                # 预分配文件空间
                file_handle.seek(file_size - 1)
                file_handle.write(b'\0')
                file_handle.seek(0)
                
                # 创建并发下载任务
                semaphore = asyncio.Semaphore(self.max_concurrent_chunks)
                
                async def download_chunk_with_semaphore(chunk: ChunkInfo):
                    async with semaphore:
                        return await self._download_chunk(message, chunk, file_handle, progress)
                
                # 并发下载所有分片
                tasks = [download_chunk_with_semaphore(chunk) for chunk in chunks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 检查结果
                successful_chunks = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"分片 {i} 下载异常: {result}")
                    elif result:
                        successful_chunks += 1
                
                # 更新最终进度
                if self.progress_callback:
                    await self.progress_callback(progress)
                
                # 检查是否所有分片都成功
                if successful_chunks == len(chunks):
                    self.logger.info(f"分片下载完成: {file_path.name}")
                    self.total_bytes_downloaded += file_size
                    return True
                else:
                    self.logger.error(f"分片下载失败: {file_path.name}, 成功: {successful_chunks}/{len(chunks)}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"分片下载异常: {file_path.name}", exc_info=e)
            return False
    
    async def resume_download(self, message: Message, file_path: Path, 
                             file_size: int) -> bool:
        """
        恢复下载（断点续传）
        
        Args:
            message: 消息对象
            file_path: 文件路径
            file_size: 文件大小
            
        Returns:
            是否下载成功
        """
        if not file_path.exists():
            self.logger.info("文件不存在，开始新的下载")
            return await self.download_file_chunks(message, file_path, file_size)
        
        current_size = file_path.stat().st_size
        
        if current_size >= file_size:
            self.logger.info("文件已完整下载")
            return True
        
        self.logger.info(f"恢复下载: {file_path.name}, 已下载: {current_size}/{file_size}")
        
        # 计算需要下载的分片
        chunks = self._calculate_chunks(file_size, self.chunk_size)
        
        # 找出需要下载的分片
        incomplete_chunks = []
        for chunk in chunks:
            if chunk.start_offset >= current_size:
                # 完全未下载的分片
                incomplete_chunks.append(chunk)
            elif chunk.end_offset >= current_size:
                # 部分下载的分片
                chunk.start_offset = current_size
                chunk.size = chunk.end_offset - current_size + 1
                incomplete_chunks.append(chunk)
        
        if not incomplete_chunks:
            self.logger.info("文件已完整下载")
            return True
        
        # 创建进度对象
        progress = ChunkDownloadProgress(
            total_chunks=len(incomplete_chunks),
            completed_chunks=0,
            failed_chunks=0,
            total_size=file_size - current_size,
            downloaded_size=0,
            start_time=time.time(),
            file_name=file_path.name
        )
        
        # 以追加模式打开文件
        try:
            with open(file_path, 'r+b') as file_handle:
                # 创建并发下载任务
                semaphore = asyncio.Semaphore(self.max_concurrent_chunks)
                
                async def download_chunk_with_semaphore(chunk: ChunkInfo):
                    async with semaphore:
                        return await self._download_chunk(message, chunk, file_handle, progress)
                
                # 并发下载未完成的分片
                tasks = [download_chunk_with_semaphore(chunk) for chunk in incomplete_chunks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 检查结果
                successful_chunks = sum(1 for result in results if result is True)
                
                # 更新最终进度
                if self.progress_callback:
                    await self.progress_callback(progress)
                
                # 检查是否所有分片都成功
                if successful_chunks == len(incomplete_chunks):
                    self.logger.info(f"断点续传完成: {file_path.name}")
                    return True
                else:
                    self.logger.error(f"断点续传失败: {file_path.name}, 成功: {successful_chunks}/{len(incomplete_chunks)}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"断点续传异常: {file_path.name}", exc_info=e)
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        return {
            "total_chunks_downloaded": self.total_chunks_downloaded,
            "total_chunks_failed": self.total_chunks_failed,
            "total_bytes_downloaded": self.total_bytes_downloaded,
            "chunk_success_rate": (self.total_chunks_downloaded / 
                                  (self.total_chunks_downloaded + self.total_chunks_failed)) * 100
            if (self.total_chunks_downloaded + self.total_chunks_failed) > 0 else 0
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.total_chunks_downloaded = 0
        self.total_chunks_failed = 0
        self.total_bytes_downloaded = 0 