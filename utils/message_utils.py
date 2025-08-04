"""
消息处理工具函数
提供消息相关的通用功能
"""
from typing import Any, Dict, Optional
from models.download_result import DownloadResult


class MessageUtils:
    """消息处理工具类"""
    
    @staticmethod
    def get_file_info(message: Any) -> Dict[str, Any]:
        """
        获取消息中媒体文件的信息
        
        Args:
            message: Pyrogram 消息对象
            
        Returns:
            dict: 包含文件名、大小、MIME类型等信息的字典
        """
        if not message.media:
            return {
                'file_name': f"file_{message.id}",
                'file_size': 0,
                'mime_type': None
            }
        
        media = message.media
        file_info = {
            'file_name': f"file_{message.id}",
            'file_size': 0,
            'mime_type': None
        }
        
        if hasattr(media, 'document') and media.document:
            doc = media.document
            file_info['file_name'] = getattr(doc, 'file_name', f"document_{message.id}")
            file_info['file_size'] = getattr(doc, 'file_size', 0)
            file_info['mime_type'] = getattr(doc, 'mime_type', None)
            
        elif hasattr(media, 'photo') and media.photo:
            photo = media.photo
            file_info['file_name'] = f"photo_{message.id}.jpg"
            file_info['file_size'] = getattr(photo, 'file_size', 0)
            file_info['mime_type'] = "image/jpeg"
            
        elif hasattr(media, 'video') and media.video:
            video = media.video
            file_info['file_name'] = getattr(video, 'file_name', f"video_{message.id}.mp4")
            file_info['file_size'] = getattr(video, 'file_size', 0)
            file_info['mime_type'] = getattr(video, 'mime_type', "video/mp4")
            
        elif hasattr(media, 'audio') and media.audio:
            audio = media.audio
            file_info['file_name'] = getattr(audio, 'file_name', f"audio_{message.id}.mp3")
            file_info['file_size'] = getattr(audio, 'file_size', 0)
            file_info['mime_type'] = getattr(audio, 'mime_type', "audio/mpeg")
            
        elif hasattr(media, 'voice') and media.voice:
            voice = media.voice
            file_info['file_name'] = f"voice_{message.id}.ogg"
            file_info['file_size'] = getattr(voice, 'file_size', 0)
            file_info['mime_type'] = "audio/ogg"
            
        elif hasattr(media, 'video_note') and media.video_note:
            video_note = media.video_note
            file_info['file_name'] = f"video_note_{message.id}.mp4"
            file_info['file_size'] = getattr(video_note, 'file_size', 0)
            file_info['mime_type'] = "video/mp4"
            
        elif hasattr(media, 'sticker') and media.sticker:
            sticker = media.sticker
            file_info['file_name'] = f"sticker_{message.id}.webp"
            file_info['file_size'] = getattr(sticker, 'file_size', 0)
            file_info['mime_type'] = "image/webp"
        
        return file_info
    
    @staticmethod
    def create_memory_download_result(message: Any, file_data: bytes, 
                                    client_name: str, file_info: Dict[str, Any] = None) -> DownloadResult:
        """
        创建内存下载结果
        
        Args:
            message: Pyrogram 消息对象
            file_data: 文件数据
            client_name: 客户端名称
            file_info: 文件信息字典（可选，如果不提供会自动获取）
            
        Returns:
            DownloadResult: 下载结果对象
        """
        if file_info is None:
            file_info = MessageUtils.get_file_info(message)
        
        return DownloadResult.create_memory_result(
            message_id=message.id,
            file_data=file_data,
            file_name=file_info['file_name'],
            client_name=client_name,
            mime_type=file_info.get('mime_type'),
            original_text=message.text,
            original_caption=message.caption,
            media_group_id=getattr(message, 'media_group_id', None)
        )
    
    @staticmethod
    def create_local_download_result(message: Any, file_path: str, 
                                   client_name: str, file_info: Dict[str, Any] = None) -> DownloadResult:
        """
        创建本地下载结果
        
        Args:
            message: Pyrogram 消息对象
            file_path: 本地文件路径
            client_name: 客户端名称
            file_info: 文件信息字典（可选，如果不提供会自动获取）
            
        Returns:
            DownloadResult: 下载结果对象
        """
        if file_info is None:
            file_info = MessageUtils.get_file_info(message)
        
        return DownloadResult.create_local_result(
            message_id=message.id,
            file_path=file_path,
            file_name=file_info['file_name'],
            file_size=file_info['file_size'],
            client_name=client_name,
            mime_type=file_info.get('mime_type'),
            original_text=message.text,
            original_caption=message.caption,
            media_group_id=getattr(message, 'media_group_id', None)
        )
    
    @staticmethod
    def get_media_type(message: Any) -> str:
        """
        获取媒体类型
        
        Args:
            message: Pyrogram 消息对象
            
        Returns:
            str: 媒体类型 (document, photo, video, audio, voice, video_note, sticker)
        """
        if not message.media:
            return "none"
        
        media = message.media
        
        if hasattr(media, 'document') and media.document:
            return "document"
        elif hasattr(media, 'photo') and media.photo:
            return "photo"
        elif hasattr(media, 'video') and media.video:
            return "video"
        elif hasattr(media, 'audio') and media.audio:
            return "audio"
        elif hasattr(media, 'voice') and media.voice:
            return "voice"
        elif hasattr(media, 'video_note') and media.video_note:
            return "video_note"
        elif hasattr(media, 'sticker') and media.sticker:
            return "sticker"
        
        return "unknown"
    
    @staticmethod
    def has_media(message: Any) -> bool:
        """
        检查消息是否包含媒体
        
        Args:
            message: Pyrogram 消息对象
            
        Returns:
            bool: 是否包含媒体
        """
        return message.media is not None
    
    @staticmethod
    def get_content_preview(message: Any, max_length: int = 50) -> str:
        """
        获取消息内容预览
        
        Args:
            message: Pyrogram 消息对象
            max_length: 最大长度
            
        Returns:
            str: 内容预览
        """
        content = ""
        if message.text:
            content = message.text
        elif message.caption:
            content = message.caption
        
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content
