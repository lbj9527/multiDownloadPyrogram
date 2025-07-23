"""
文件操作工具函数
"""

import re
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Set
import aiofiles
import asyncio

from config.constants import FILE_EXTENSIONS, FILE_TYPE_CATEGORIES


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度限制
        
    Returns:
        清理后的安全文件名
    """
    # 移除或替换Windows文件名中的非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    safe_name = re.sub(illegal_chars, '_', filename)
    
    # 移除首尾空格和点
    safe_name = safe_name.strip('. ')
    
    # 限制长度
    if len(safe_name) > max_length:
        name_part, ext_part = Path(safe_name).stem, Path(safe_name).suffix
        max_name_length = max_length - len(ext_part)
        safe_name = name_part[:max_name_length] + ext_part
    
    # 确保不为空
    if not safe_name:
        safe_name = "unnamed_file"
    
    return safe_name


def get_file_extension(mime_type: str, fallback: str = ".bin") -> str:
    """
    根据MIME类型获取文件扩展名
    
    Args:
        mime_type: MIME类型
        fallback: 默认扩展名
        
    Returns:
        文件扩展名
    """
    return FILE_EXTENSIONS.get(mime_type, fallback)


def get_file_type_category(file_path: Path) -> str:
    """
    根据文件扩展名获取文件类型分类
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件类型分类 (images, videos, audio, documents, archives, other)
    """
    extension = file_path.suffix.lower()
    
    for category, extensions in FILE_TYPE_CATEGORIES.items():
        if extension in extensions:
            return category
    
    return "other"


def ensure_directory(directory: Path) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        目录路径
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def calculate_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    异步计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha1, sha256)
        
    Returns:
        文件哈希值
    """
    if not file_path.exists():
        return ""
    
    hash_func = getattr(hashlib, algorithm)()
    
    async with aiofiles.open(file_path, 'rb') as f:
        while chunk := await f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def get_file_size(file_path: Path) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小（字节）
    """
    try:
        return file_path.stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def is_file_exists(file_path: Path) -> bool:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件是否存在
    """
    return file_path.exists() and file_path.is_file()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化的文件大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def get_mime_type(file_path: Path) -> Optional[str]:
    """
    获取文件的MIME类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        MIME类型
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type


async def copy_file_async(src: Path, dst: Path) -> bool:
    """
    异步复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        
    Returns:
        是否复制成功
    """
    try:
        # 确保目标目录存在
        ensure_directory(dst.parent)
        
        async with aiofiles.open(src, 'rb') as src_file:
            async with aiofiles.open(dst, 'wb') as dst_file:
                while chunk := await src_file.read(8192):
                    await dst_file.write(chunk)
        
        return True
    except Exception:
        return False


async def move_file_async(src: Path, dst: Path) -> bool:
    """
    异步移动文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        
    Returns:
        是否移动成功
    """
    try:
        # 确保目标目录存在
        ensure_directory(dst.parent)
        
        # 尝试直接重命名（同一文件系统）
        try:
            src.rename(dst)
            return True
        except OSError:
            # 跨文件系统，需要复制后删除
            if await copy_file_async(src, dst):
                src.unlink()
                return True
            return False
    except Exception:
        return False


def generate_unique_filename(directory: Path, base_name: str) -> Path:
    """
    生成唯一的文件名（避免重名）
    
    Args:
        directory: 目录路径
        base_name: 基础文件名
        
    Returns:
        唯一的文件路径
    """
    file_path = directory / base_name
    
    if not file_path.exists():
        return file_path
    
    # 文件已存在，生成新名称
    stem = file_path.stem
    suffix = file_path.suffix
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = directory / new_name
        
        if not new_path.exists():
            return new_path
        
        counter += 1


class FileManager:
    """文件管理器类"""
    
    def __init__(self, base_directory: Path):
        self.base_directory = ensure_directory(base_directory)
        self._file_hashes: Dict[str, Path] = {}
    
    async def add_file(self, file_path: Path, calculate_hash: bool = True) -> str:
        """
        添加文件到管理器
        
        Args:
            file_path: 文件路径
            calculate_hash: 是否计算哈希值
            
        Returns:
            文件哈希值
        """
        if calculate_hash:
            file_hash = await calculate_file_hash(file_path)
            self._file_hashes[file_hash] = file_path
            return file_hash
        return ""
    
    def find_duplicate(self, file_hash: str) -> Optional[Path]:
        """
        查找重复文件
        
        Args:
            file_hash: 文件哈希值
            
        Returns:
            重复文件路径（如果存在）
        """
        return self._file_hashes.get(file_hash)
    
    def get_file_stats(self) -> Dict[str, int]:
        """
        获取文件统计信息
        
        Returns:
            文件统计字典
        """
        total_files = 0
        total_size = 0
        type_counts = {}
        
        for file_path in self.base_directory.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += get_file_size(file_path)
                
                file_type = get_file_type_category(file_path)
                type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "total_size_formatted": format_file_size(total_size),
            "type_counts": type_counts
        }
