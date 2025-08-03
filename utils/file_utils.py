"""
文件操作工具类
"""
import os
import re
from pathlib import Path
from typing import Optional, Any
from config.constants import VIDEO_EXTENSIONS, IMAGE_EXTENSIONS, DOCUMENT_EXTENSIONS

class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除非法字符
        """
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        # 限制长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename
    
    @staticmethod
    def generate_filename_by_type(message: Any) -> str:
        """
        根据消息类型生成文件名
        """
        message_id = message.id
        
        # 检查不同类型的媒体
        if message.document:
            # 文档类型
            if hasattr(message.document, 'file_name') and message.document.file_name:
                original_name = message.document.file_name
                name, ext = os.path.splitext(original_name)
                return FileUtils.sanitize_filename(f"{message_id}_{name}{ext}")
            else:
                return f"{message_id}_document.bin"
                
        elif message.video:
            # 视频类型
            if hasattr(message.video, 'file_name') and message.video.file_name:
                original_name = message.video.file_name
                name, ext = os.path.splitext(original_name)
                return FileUtils.sanitize_filename(f"{message_id}_{name}{ext}")
            else:
                return f"{message_id}_video.mp4"
                
        elif message.photo:
            # 图片类型
            return f"{message_id}_photo.jpg"
            
        elif message.audio:
            # 音频类型
            if hasattr(message.audio, 'file_name') and message.audio.file_name:
                original_name = message.audio.file_name
                name, ext = os.path.splitext(original_name)
                return FileUtils.sanitize_filename(f"{message_id}_{name}{ext}")
            else:
                return f"{message_id}_audio.mp3"
                
        elif message.voice:
            # 语音类型
            return f"{message_id}_voice.ogg"
            
        elif message.video_note:
            # 视频笔记
            return f"{message_id}_video_note.mp4"
            
        elif message.animation:
            # 动画/GIF
            return f"{message_id}_animation.gif"
            
        elif message.sticker:
            # 贴纸
            return f"{message_id}_sticker.webp"
            
        else:
            # 未知类型
            return f"{message_id}_unknown.bin"
    
    @staticmethod
    def get_file_size_bytes(message: Any) -> int:
        """
        获取消息文件大小（字节）
        从test_downloader_stream.py提取
        """
        media = (message.document or message.video or message.photo or 
                message.audio or message.voice or message.video_note or 
                message.animation or message.sticker)
        
        if media and hasattr(media, 'file_size'):
            return media.file_size or 0
        return 0
    
    @staticmethod
    def get_file_size_mb(message: Any) -> float:
        """获取消息文件大小（MB）"""
        size_bytes = FileUtils.get_file_size_bytes(message)
        return size_bytes / (1024 * 1024)
    
    @staticmethod
    def is_video_file(message: Any) -> bool:
        """判断是否为视频文件"""
        if message.video or message.video_note or message.animation:
            return True
        
        # 检查文档是否为视频格式
        if message.document and hasattr(message.document, 'file_name'):
            filename = message.document.file_name or ""
            ext = Path(filename).suffix.lower()
            return ext in VIDEO_EXTENSIONS
        
        return False
    
    @staticmethod
    def is_image_file(message: Any) -> bool:
        """判断是否为图片文件"""
        if message.photo:
            return True
            
        # 检查文档是否为图片格式
        if message.document and hasattr(message.document, 'file_name'):
            filename = message.document.file_name or ""
            ext = Path(filename).suffix.lower()
            return ext in IMAGE_EXTENSIONS
        
        return False
    
    @staticmethod
    def ensure_directory(directory: Path) -> Path:
        """确保目录存在"""
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    @staticmethod
    def get_channel_directory(base_dir: Path, folder_name: str) -> Path:
        """
        获取频道下载目录
        folder_name应该是已经处理过的文件夹名称
        """
        channel_dir = base_dir / folder_name
        return FileUtils.ensure_directory(channel_dir)
