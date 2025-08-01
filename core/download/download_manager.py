"""
下载管理器
协调不同的下载策略，从test_downloader_stream.py提取的智能下载选择逻辑
"""
from pathlib import Path
from typing import Optional, Any, List, Dict
from pyrogram.client import Client

from config.settings import DownloadConfig
from utils.logging_utils import LoggerMixin
from utils.file_utils import FileUtils
from .stream_downloader import StreamDownloader
from .raw_downloader import RawDownloader

class DownloadManager(LoggerMixin):
    """下载管理器 - 智能选择下载方法"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.stream_downloader = StreamDownloader(config.download_dir)
        self.raw_downloader = RawDownloader(config.download_dir)
        self.download_stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "stream_downloads": 0,
            "raw_downloads": 0,
            "total_size_mb": 0.0
        }
    
    async def download_media(
        self,
        client: Client,
        message: Any,
        folder_name: str
    ) -> Optional[Path]:
        """
        智能选择下载方法
        从test_downloader_stream.py提取的决策逻辑
        """
        try:
            self.download_stats["total_downloads"] += 1

            # 获取文件信息
            file_size_mb = FileUtils.get_file_size_mb(message)
            is_video = FileUtils.is_video_file(message)

            # 决策逻辑：小于阈值且非视频文件使用RAW API，其他使用stream_media
            use_raw_api = file_size_mb < self.config.stream_threshold_mb and not is_video

            if use_raw_api:
                self.log_info(
                    f"消息 {message.id}: 使用RAW API下载 "
                    f"(大小: {file_size_mb:.2f} MB, 视频: {is_video})"
                )
                result = await self.raw_downloader.download(client, message, folder_name)
                if result:
                    self.download_stats["raw_downloads"] += 1
            else:
                self.log_info(
                    f"消息 {message.id}: 使用Stream下载 "
                    f"(大小: {file_size_mb:.2f} MB, 视频: {is_video})"
                )
                result = await self.stream_downloader.download(client, message, folder_name)
                if result:
                    self.download_stats["stream_downloads"] += 1
            
            # 更新统计
            if result:
                self.download_stats["successful_downloads"] += 1
                self.download_stats["total_size_mb"] += file_size_mb
            else:
                self.download_stats["failed_downloads"] += 1
            
            return result
            
        except Exception as e:
            self.log_error(f"下载消息 {message.id} 失败: {e}")
            self.download_stats["failed_downloads"] += 1
            return None
    
    async def batch_download(
        self,
        client: Client,
        messages: List[Any],
        folder_name: str
    ) -> Dict[str, Any]:
        """
        批量下载消息

        Returns:
            下载结果统计
        """
        results = {
            "successful": [],
            "failed": [],
            "total_count": len(messages),
            "success_count": 0,
            "fail_count": 0
        }

        self.log_info(f"开始批量下载 {len(messages)} 个文件...")

        for i, message in enumerate(messages, 1):
            self.log_info(f"进度: {i}/{len(messages)} - 下载消息 {message.id}")

            result = await self.download_media(client, message, folder_name)
            
            if result:
                results["successful"].append({
                    "message_id": message.id,
                    "file_path": str(result),
                    "file_size_mb": FileUtils.get_file_size_mb(message)
                })
                results["success_count"] += 1
            else:
                results["failed"].append({
                    "message_id": message.id,
                    "error": "下载失败"
                })
                results["fail_count"] += 1
        
        self.log_info(
            f"批量下载完成: {results['success_count']}/{results['total_count']} 成功"
        )
        
        return results
    
    def get_download_stats(self) -> Dict[str, Any]:
        """获取下载统计信息"""
        stats = self.download_stats.copy()
        
        # 计算成功率
        if stats["total_downloads"] > 0:
            stats["success_rate"] = stats["successful_downloads"] / stats["total_downloads"]
        else:
            stats["success_rate"] = 0.0
        
        # 计算平均文件大小
        if stats["successful_downloads"] > 0:
            stats["average_file_size_mb"] = stats["total_size_mb"] / stats["successful_downloads"]
        else:
            stats["average_file_size_mb"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.download_stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "stream_downloads": 0,
            "raw_downloads": 0,
            "total_size_mb": 0.0
        }
        self.log_info("下载统计已重置")
    
    def get_channel_directory(self, folder_name: str) -> Path:
        """获取频道下载目录"""
        return FileUtils.get_channel_directory(Path(self.config.download_dir), folder_name)
