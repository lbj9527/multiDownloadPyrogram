"""
存储服务
负责文件存储管理
"""

from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from models import FileInfo
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
            "duplicate_files": 0
        }

    
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

            # 只支持原始存储模式
            return await self._store_raw(file_info)

        except Exception as e:
            logger.error(f"存储文件失败: {e}")
            return False
    
    async def _store_raw(self, file_info: FileInfo) -> bool:
        """原始存储"""
        # 文件已在正确位置，无需处理
        logger.debug(f"原始存储: {file_info.file_path.name}")
        return True



    
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
            "duplicates_removed": 0,
            "errors": []
        }

        try:
            # 移除重复文件
            await self._remove_duplicates(optimization_results)
            
            # 整理目录结构
            await self._organize_directories(optimization_results)
            
        except Exception as e:
            logger.error(f"存储优化失败: {e}")
            optimization_results["errors"].append(str(e))
        
        return optimization_results

    
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
            "storage_stats": self.storage_stats
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

## 存储统计
- 文件总数: {storage_info['storage_stats']['total_files']}
- 总大小: {format_file_size(storage_info['storage_stats']['total_size'])}
- 重复文件数: {storage_info['storage_stats']['duplicate_files']}
"""
        return report
