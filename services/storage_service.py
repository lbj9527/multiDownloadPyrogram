"""
存储服务
负责文件存储策略、压缩管理、存储优化
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import zipfile
import shutil

from models import FileInfo, CompressionInfo, CompressionType
from utils import get_logger, ensure_directory, get_file_size, format_file_size
from config import app_settings

logger = get_logger(__name__)


class StorageService:
    """存储服务"""
    
    def __init__(self, base_directory: Optional[Path] = None):
        self.base_directory = base_directory or app_settings.get_download_directory()
        self.storage_config = app_settings.storage
        
        # 存储统计
        self.storage_stats = {
            "total_files": 0,
            "total_size": 0,
            "compressed_files": 0,
            "compressed_size": 0,
            "duplicate_files": 0,
            "space_saved": 0
        }
        
        # 压缩任务队列
        self.compression_queue: List[FileInfo] = []
        self.compression_worker_running = False
    
    async def start_compression_worker(self):
        """启动压缩工作器"""
        if self.compression_worker_running:
            return
        
        self.compression_worker_running = True
        asyncio.create_task(self._compression_worker())
        logger.info("压缩工作器已启动")
    
    async def stop_compression_worker(self):
        """停止压缩工作器"""
        self.compression_worker_running = False
        logger.info("压缩工作器已停止")
    
    async def _compression_worker(self):
        """压缩工作器主循环"""
        try:
            while self.compression_worker_running:
                if self.compression_queue:
                    file_info = self.compression_queue.pop(0)
                    await self._compress_file_async(file_info)
                else:
                    await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"压缩工作器异常: {e}")
    
    async def store_file(self, file_info: FileInfo) -> bool:
        """
        存储文件
        
        Args:
            file_info: 文件信息
            
        Returns:
            是否存储成功
        """
        try:
            # 更新统计
            self._update_storage_stats(file_info)
            
            # 根据存储模式处理
            storage_mode = self.storage_config.storage_mode
            
            if storage_mode == "raw":
                return await self._store_raw(file_info)
            elif storage_mode == "compressed":
                return await self._store_compressed(file_info)
            elif storage_mode == "hybrid":
                return await self._store_hybrid(file_info)
            else:
                logger.error(f"未知存储模式: {storage_mode}")
                return False
                
        except Exception as e:
            logger.error(f"存储文件失败: {e}")
            return False
    
    async def _store_raw(self, file_info: FileInfo) -> bool:
        """原始存储"""
        # 文件已在正确位置，无需处理
        logger.debug(f"原始存储: {file_info.file_path.name}")
        return True
    
    async def _store_compressed(self, file_info: FileInfo) -> bool:
        """压缩存储"""
        # 添加到压缩队列
        self.compression_queue.append(file_info)
        logger.debug(f"已添加到压缩队列: {file_info.file_path.name}")
        return True
    
    async def _store_hybrid(self, file_info: FileInfo) -> bool:
        """混合存储"""
        if self._should_compress(file_info):
            return await self._store_compressed(file_info)
        else:
            return await self._store_raw(file_info)
    
    def _should_compress(self, file_info: FileInfo) -> bool:
        """判断是否应该压缩"""
        # 根据文件类型和大小决定
        file_type = file_info.file_type.value + "s"
        type_rule = self.storage_config.file_type_rules.get(file_type, {})
        
        # 检查类型规则
        if "compress" in type_rule:
            should_compress = type_rule["compress"]
            max_size_mb = type_rule.get("max_size_mb", float('inf'))
            
            if file_info.file_size_mb > max_size_mb:
                return True
            
            return should_compress
        
        # 默认规则
        return file_info.file_size_mb > self.storage_config.compress_threshold_mb
    
    async def _compress_file_async(self, file_info: FileInfo) -> bool:
        """异步压缩文件"""
        try:
            # 创建压缩包路径
            archive_path = self._get_archive_path(file_info)
            
            # 执行压缩
            compression_info = await self._perform_compression(file_info, archive_path)
            
            if compression_info:
                file_info.mark_compressed(compression_info)
                
                # 删除原文件
                if file_info.file_path.exists():
                    file_info.file_path.unlink()
                
                # 更新统计
                self.storage_stats["compressed_files"] += 1
                self.storage_stats["space_saved"] += compression_info.space_saved
                
                logger.info(f"文件压缩完成: {file_info.file_path.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"压缩文件失败: {e}")
            return False
    
    async def _perform_compression(
        self,
        file_info: FileInfo,
        archive_path: Path
    ) -> Optional[CompressionInfo]:
        """执行压缩操作"""
        try:
            import time
            start_time = time.time()
            
            # 确保目录存在
            ensure_directory(archive_path.parent)
            
            # 压缩文件
            with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED) as zf:
                zf.write(file_info.file_path, file_info.file_path.name)
            
            # 计算压缩信息
            original_size = file_info.file_size
            compressed_size = get_file_size(archive_path)
            compression_time = time.time() - start_time
            
            compression_info = CompressionInfo(
                compression_type=CompressionType.ZIP,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_time=compression_time
            )
            
            if original_size > 0:
                compression_info.compression_ratio = compressed_size / original_size
            
            return compression_info
            
        except Exception as e:
            logger.error(f"执行压缩失败: {e}")
            return None
    
    def _get_archive_path(self, file_info: FileInfo) -> Path:
        """获取压缩包路径"""
        # 按日期和类型组织压缩包
        date_str = datetime.now().strftime("%Y%m%d")
        file_type = file_info.file_type.value
        
        archive_dir = self.base_directory / "archives"
        archive_name = f"{file_type}_{date_str}.zip"
        
        return archive_dir / archive_name
    
    def _update_storage_stats(self, file_info: FileInfo):
        """更新存储统计"""
        self.storage_stats["total_files"] += 1
        self.storage_stats["total_size"] += file_info.file_size
    
    async def cleanup_old_files(self, days: int = 90) -> Dict[str, int]:
        """
        清理旧文件
        
        Args:
            days: 保留天数
            
        Returns:
            清理统计
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cleanup_stats = {
            "files_removed": 0,
            "space_freed": 0
        }
        
        try:
            for file_path in self.base_directory.rglob("*"):
                if file_path.is_file():
                    # 检查文件修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if mtime < cutoff_date:
                        file_size = get_file_size(file_path)
                        file_path.unlink()
                        
                        cleanup_stats["files_removed"] += 1
                        cleanup_stats["space_freed"] += file_size
            
            logger.info(f"清理完成: 删除 {cleanup_stats['files_removed']} 个文件，"
                       f"释放 {format_file_size(cleanup_stats['space_freed'])} 空间")
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
        
        return cleanup_stats
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        优化存储
        
        Returns:
            优化结果
        """
        optimization_results = {
            "compressed_files": 0,
            "space_saved": 0,
            "duplicates_removed": 0,
            "errors": []
        }
        
        try:
            # 压缩未压缩的大文件
            await self._compress_large_files(optimization_results)
            
            # 移除重复文件
            await self._remove_duplicates(optimization_results)
            
            # 整理目录结构
            await self._organize_directories(optimization_results)
            
        except Exception as e:
            logger.error(f"存储优化失败: {e}")
            optimization_results["errors"].append(str(e))
        
        return optimization_results
    
    async def _compress_large_files(self, results: Dict[str, Any]):
        """压缩大文件"""
        threshold_mb = self.storage_config.compress_threshold_mb
        
        for file_path in self.base_directory.rglob("*"):
            if file_path.is_file() and not file_path.suffix == '.zip':
                file_size_mb = get_file_size(file_path) / (1024 * 1024)
                
                if file_size_mb > threshold_mb:
                    # 创建文件信息并压缩
                    file_info = FileInfo(
                        file_path=file_path,
                        original_name=file_path.name,
                        file_type=file_info.get_file_type_from_extension()
                    )
                    
                    if await self._compress_file_async(file_info):
                        results["compressed_files"] += 1
                        results["space_saved"] += file_info.compression_info.space_saved
    
    async def _remove_duplicates(self, results: Dict[str, Any]):
        """移除重复文件"""
        # 这里应该实现重复文件检测和移除逻辑
        # 由于复杂性，这里只是占位符
        pass
    
    async def _organize_directories(self, results: Dict[str, Any]):
        """整理目录结构"""
        # 按文件类型整理目录
        type_dirs = {
            "images": self.base_directory / "images",
            "videos": self.base_directory / "videos",
            "audio": self.base_directory / "audio",
            "documents": self.base_directory / "documents",
            "archives": self.base_directory / "archives"
        }
        
        # 创建类型目录
        for type_dir in type_dirs.values():
            ensure_directory(type_dir)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        # 计算目录大小
        total_size = 0
        file_count = 0
        
        for file_path in self.base_directory.rglob("*"):
            if file_path.is_file():
                total_size += get_file_size(file_path)
                file_count += 1
        
        # 计算可用空间
        try:
            disk_usage = shutil.disk_usage(self.base_directory)
            free_space = disk_usage.free
            total_space = disk_usage.total
            used_space = disk_usage.used
        except Exception:
            free_space = total_space = used_space = 0
        
        return {
            "base_directory": str(self.base_directory),
            "storage_mode": self.storage_config.storage_mode,
            "file_count": file_count,
            "total_size": total_size,
            "total_size_formatted": format_file_size(total_size),
            "disk_usage": {
                "total": total_space,
                "used": used_space,
                "free": free_space,
                "total_formatted": format_file_size(total_space),
                "used_formatted": format_file_size(used_space),
                "free_formatted": format_file_size(free_space)
            },
            "compression_stats": self.storage_stats,
            "compression_queue_size": len(self.compression_queue)
        }
    
    async def export_storage_report(self, output_path: Path) -> bool:
        """
        导出存储报告
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            storage_info = self.get_storage_info()
            
            # 生成报告内容
            report_content = self._generate_storage_report(storage_info)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"存储报告已导出: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出存储报告失败: {e}")
            return False
    
    def _generate_storage_report(self, storage_info: Dict[str, Any]) -> str:
        """生成存储报告内容"""
        report = f"""
# 存储报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 基本信息
- 存储目录: {storage_info['base_directory']}
- 存储模式: {storage_info['storage_mode']}
- 文件总数: {storage_info['file_count']}
- 总大小: {storage_info['total_size_formatted']}

## 磁盘使用情况
- 总空间: {storage_info['disk_usage']['total_formatted']}
- 已使用: {storage_info['disk_usage']['used_formatted']}
- 可用空间: {storage_info['disk_usage']['free_formatted']}

## 压缩统计
- 压缩文件数: {storage_info['compression_stats']['compressed_files']}
- 节省空间: {format_file_size(storage_info['compression_stats']['space_saved'])}
- 重复文件数: {storage_info['compression_stats']['duplicate_files']}
"""
        return report
