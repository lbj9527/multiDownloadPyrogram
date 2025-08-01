"""
消息处理器
处理消息的验证、过滤、转换等功能
"""
from typing import List, Any, Optional, Dict
from utils.logging_utils import LoggerMixin
from utils.file_utils import FileUtils

class MessageProcessor(LoggerMixin):
    """消息处理器"""
    
    def __init__(self):
        pass
    
    def validate_messages(self, messages: List[Any]) -> List[Any]:
        """
        验证消息列表，过滤无效消息
        """
        valid_messages = []
        
        for message in messages:
            if self._is_valid_message(message):
                valid_messages.append(message)
            else:
                self.log_debug(f"消息 {getattr(message, 'id', 'unknown')} 验证失败，已过滤")
        
        self.log_info(f"消息验证完成: {len(valid_messages)}/{len(messages)} 条消息有效")
        return valid_messages
    
    def filter_by_file_type(self, messages: List[Any], file_types: List[str]) -> List[Any]:
        """
        根据文件类型过滤消息
        
        Args:
            messages: 消息列表
            file_types: 允许的文件类型 ['video', 'image', 'document', 'audio']
        """
        filtered_messages = []
        
        for message in messages:
            message_type = self._get_message_type(message)
            if message_type in file_types:
                filtered_messages.append(message)
        
        self.log_info(f"文件类型过滤完成: {len(filtered_messages)}/{len(messages)} 条消息符合类型要求")
        return filtered_messages
    
    def filter_by_size(
        self, 
        messages: List[Any], 
        min_size_mb: float = 0, 
        max_size_mb: float = float('inf')
    ) -> List[Any]:
        """
        根据文件大小过滤消息
        """
        filtered_messages = []
        
        for message in messages:
            size_mb = FileUtils.get_file_size_mb(message)
            if min_size_mb <= size_mb <= max_size_mb:
                filtered_messages.append(message)
        
        self.log_info(f"文件大小过滤完成: {len(filtered_messages)}/{len(messages)} 条消息符合大小要求")
        return filtered_messages
    
    def get_message_statistics(self, messages: List[Any]) -> Dict[str, Any]:
        """获取消息统计信息"""
        stats = {
            "total_count": len(messages),
            "by_type": {},
            "total_size_mb": 0.0,
            "average_size_mb": 0.0,
            "size_distribution": {
                "small": 0,    # < 10MB
                "medium": 0,   # 10MB - 100MB  
                "large": 0     # > 100MB
            }
        }
        
        total_size = 0.0
        
        for message in messages:
            # 统计类型
            msg_type = self._get_message_type(message)
            stats["by_type"][msg_type] = stats["by_type"].get(msg_type, 0) + 1
            
            # 统计大小
            size_mb = FileUtils.get_file_size_mb(message)
            total_size += size_mb
            
            # 大小分布
            if size_mb < 10:
                stats["size_distribution"]["small"] += 1
            elif size_mb < 100:
                stats["size_distribution"]["medium"] += 1
            else:
                stats["size_distribution"]["large"] += 1
        
        stats["total_size_mb"] = total_size
        stats["average_size_mb"] = total_size / len(messages) if messages else 0.0
        
        return stats
    
    def _is_valid_message(self, message: Any) -> bool:
        """检查消息是否有效 - 与原程序保持一致，只判断empty属性"""
        if not message:
            return False

        # 只判断empty属性，不判断是否有媒体文件（与原程序一致）
        return not getattr(message, 'empty', True)
    
    def _get_message_type(self, message: Any) -> str:
        """获取消息类型"""
        if message.video or message.video_note or message.animation:
            return "video"
        elif message.photo:
            return "image"
        elif message.document:
            return "document"
        elif message.audio or message.voice:
            return "audio"
        elif message.sticker:
            return "sticker"
        else:
            return "unknown"
