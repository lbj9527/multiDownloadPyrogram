"""
上传策略
根据文件类型和大小选择最佳上传方式
"""
from typing import Dict, Any, Optional, Callable, List
from models.upload_task import UploadTask, UploadType
from utils.logging_utils import LoggerMixin


class UploadStrategy(LoggerMixin):
    """上传策略管理器"""
    
    def __init__(self):
        """初始化上传策略"""
        # 文件大小阈值 (字节)
        self.size_thresholds = {
            "small": 10 * 1024 * 1024,      # 10MB
            "medium": 50 * 1024 * 1024,     # 50MB
            "large": 200 * 1024 * 1024,     # 200MB
        }
        
        # 文件类型映射
        self.mime_type_mapping = {
            # 图片类型
            "image/jpeg": UploadType.PHOTO,
            "image/jpg": UploadType.PHOTO,
            "image/png": UploadType.PHOTO,
            "image/gif": UploadType.PHOTO,
            "image/webp": UploadType.PHOTO,
            
            # 视频类型
            "video/mp4": UploadType.VIDEO,
            "video/avi": UploadType.VIDEO,
            "video/mkv": UploadType.VIDEO,
            "video/mov": UploadType.VIDEO,
            "video/wmv": UploadType.VIDEO,
            "video/webm": UploadType.VIDEO,
            
            # 音频类型
            "audio/mp3": UploadType.AUDIO,
            "audio/wav": UploadType.AUDIO,
            "audio/flac": UploadType.AUDIO,
            "audio/aac": UploadType.AUDIO,
            "audio/ogg": UploadType.AUDIO,
            "audio/mpeg": UploadType.AUDIO,
            
            # 语音类型
            "audio/ogg; codecs=opus": UploadType.VOICE,
            
            # 文档类型 (默认)
            "application/pdf": UploadType.DOCUMENT,
            "application/zip": UploadType.DOCUMENT,
            "application/rar": UploadType.DOCUMENT,
            "text/plain": UploadType.DOCUMENT,
        }
        
        # 上传方法配置
        self.upload_methods = {
            UploadType.PHOTO: self._get_photo_upload_config,
            UploadType.VIDEO: self._get_video_upload_config,
            UploadType.AUDIO: self._get_audio_upload_config,
            UploadType.VOICE: self._get_voice_upload_config,
            UploadType.DOCUMENT: self._get_document_upload_config,
            UploadType.VIDEO_NOTE: self._get_video_note_upload_config,
            UploadType.STICKER: self._get_sticker_upload_config,
        }
    
    def determine_upload_type(self, task: UploadTask) -> UploadType:
        """
        确定上传类型
        
        Args:
            task: 上传任务
            
        Returns:
            UploadType: 上传类型
        """
        # 优先使用已设置的类型
        if task.upload_type != UploadType.DOCUMENT:
            return task.upload_type
        
        # 根据MIME类型判断
        if task.mime_type:
            upload_type = self.mime_type_mapping.get(task.mime_type)
            if upload_type:
                return upload_type
        
        # 根据文件扩展名判断
        if task.file_name:
            ext = task.file_name.lower().split('.')[-1]
            upload_type = self._get_type_by_extension(ext)
            if upload_type:
                return upload_type
        
        # 默认为文档类型
        return UploadType.DOCUMENT
    
    def _get_type_by_extension(self, extension: str) -> Optional[UploadType]:
        """根据文件扩展名确定类型"""
        extension_mapping = {
            # 图片
            'jpg': UploadType.PHOTO, 'jpeg': UploadType.PHOTO,
            'png': UploadType.PHOTO, 'gif': UploadType.PHOTO,
            'webp': UploadType.PHOTO, 'bmp': UploadType.PHOTO,
            
            # 视频
            'mp4': UploadType.VIDEO, 'avi': UploadType.VIDEO,
            'mkv': UploadType.VIDEO, 'mov': UploadType.VIDEO,
            'wmv': UploadType.VIDEO, 'webm': UploadType.VIDEO,
            'flv': UploadType.VIDEO, '3gp': UploadType.VIDEO,
            
            # 音频
            'mp3': UploadType.AUDIO, 'wav': UploadType.AUDIO,
            'flac': UploadType.AUDIO, 'aac': UploadType.AUDIO,
            'ogg': UploadType.AUDIO, 'm4a': UploadType.AUDIO,
            
            # 文档
            'pdf': UploadType.DOCUMENT, 'doc': UploadType.DOCUMENT,
            'docx': UploadType.DOCUMENT, 'txt': UploadType.DOCUMENT,
            'zip': UploadType.DOCUMENT, 'rar': UploadType.DOCUMENT,
            '7z': UploadType.DOCUMENT, 'tar': UploadType.DOCUMENT,
        }
        
        return extension_mapping.get(extension)
    
    def get_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """
        获取上传配置
        
        Args:
            task: 上传任务
            
        Returns:
            Dict[str, Any]: 上传配置
        """
        upload_type = self.determine_upload_type(task)
        task.upload_type = upload_type  # 更新任务类型
        
        # 获取对应的配置方法
        config_method = self.upload_methods.get(upload_type, self._get_document_upload_config)
        
        return config_method(task)
    
    def _get_photo_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取图片上传配置"""
        config = {
            "method": "send_photo",
            "supports_caption": True,
            "max_caption_length": 1024,
            "compress": True,  # 图片默认压缩
        }

        # 保持原始媒体类型，不降级为文档
        # 大图片仍然使用 send_photo，让 Telegram 处理大小限制
        if task.file_size > self.size_thresholds["medium"]:
            self.log_info(f"大图片 {task.file_name} ({task.get_file_size_formatted()}) 保持图片格式上传")

        return config
    
    def _get_video_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取视频上传配置"""
        config = {
            "method": "send_video",
            "supports_caption": True,
            "max_caption_length": 1024,
            "supports_streaming": True,
        }

        # 保持原始媒体类型，不降级为文档
        # 大视频仍然使用 send_video，让 Telegram 处理大小限制
        if task.file_size > self.size_thresholds["large"]:
            self.log_info(f"大视频 {task.file_name} ({task.get_file_size_formatted()}) 保持视频格式上传")

        return config
    
    def _get_audio_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取音频上传配置"""
        return {
            "method": "send_audio",
            "supports_caption": True,
            "max_caption_length": 1024,
            "supports_metadata": True,  # 支持音频元数据
        }
    
    def _get_voice_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取语音上传配置"""
        return {
            "method": "send_voice",
            "supports_caption": False,  # 语音消息不支持说明
            "max_duration": 60,  # 最大60秒
        }
    
    def _get_document_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取文档上传配置"""
        return {
            "method": "send_document",
            "supports_caption": True,
            "max_caption_length": 1024,
            "force_document": True,  # 强制作为文档发送
        }
    
    def _get_video_note_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取视频消息上传配置"""
        return {
            "method": "send_video_note",
            "supports_caption": False,  # 视频消息不支持说明
            "max_duration": 60,  # 最大60秒
            "required_format": "mp4",  # 必须是MP4格式
        }
    
    def _get_sticker_upload_config(self, task: UploadTask) -> Dict[str, Any]:
        """获取贴纸上传配置"""
        return {
            "method": "send_sticker",
            "supports_caption": False,  # 贴纸不支持说明
            "required_format": "webp",  # 必须是WebP格式
            "max_size": 512 * 1024,  # 最大512KB
        }
    
    def get_size_category(self, file_size: int) -> str:
        """
        获取文件大小分类
        
        Args:
            file_size: 文件大小（字节）
            
        Returns:
            str: 大小分类 (small/medium/large/huge)
        """
        if file_size <= self.size_thresholds["small"]:
            return "small"
        elif file_size <= self.size_thresholds["medium"]:
            return "medium"
        elif file_size <= self.size_thresholds["large"]:
            return "large"
        else:
            return "huge"
    
    def estimate_upload_time(self, task: UploadTask, 
                           upload_speed: float = 1024 * 1024) -> float:
        """
        估算上传时间
        
        Args:
            task: 上传任务
            upload_speed: 上传速度 (bytes/s)，默认1MB/s
            
        Returns:
            float: 预计上传时间（秒）
        """
        if upload_speed <= 0:
            return 0.0
        
        base_time = task.file_size / upload_speed
        
        # 根据文件类型和大小调整
        size_category = self.get_size_category(task.file_size)
        
        # 大文件需要额外的处理时间
        if size_category == "large":
            base_time *= 1.2
        elif size_category == "huge":
            base_time *= 1.5
        
        # 视频文件可能需要额外的处理时间
        if task.upload_type == UploadType.VIDEO:
            base_time *= 1.1
        
        return base_time
    
    def should_compress(self, task: UploadTask) -> bool:
        """
        是否应该压缩文件
        
        Args:
            task: 上传任务
            
        Returns:
            bool: 是否压缩
        """
        # 图片默认压缩（除非明确指定不压缩）
        if task.upload_type == UploadType.PHOTO:
            return task.metadata.get("compress", True)
        
        # 其他类型默认不压缩
        return False
    
    def validate_upload_task(self, task: UploadTask) -> List[str]:
        """
        验证上传任务
        
        Args:
            task: 上传任务
            
        Returns:
            List[str]: 错误列表
        """
        errors = []
        
        # 基础验证
        if not task.target_channel:
            errors.append("目标频道不能为空")
        
        if not task.file_data:
            errors.append("文件数据不能为空")
        
        if task.file_size <= 0:
            errors.append("文件大小必须大于0")
        
        # Telegram限制验证
        max_file_size = 2 * 1024 * 1024 * 1024  # 2GB
        if task.file_size > max_file_size:
            errors.append(f"文件大小超过Telegram限制 (2GB)")
        
        # 说明文字长度验证
        config = self.get_upload_config(task)
        if config.get("supports_caption") and task.caption:
            max_length = config.get("max_caption_length", 1024)
            if len(task.caption) > max_length:
                errors.append(f"说明文字超过最大长度 ({max_length})")
        
        return errors
