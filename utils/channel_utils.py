"""
频道工具类
处理频道信息获取和文件夹名称生成
"""
import re
from typing import Dict, Any
from pyrogram.client import Client
from utils.logging_utils import LoggerMixin


class ChannelUtils(LoggerMixin):
    """频道工具类"""
    
    @staticmethod
    async def get_channel_info(client: Client, channel: str) -> Dict[str, Any]:
        """
        获取频道信息并生成文件夹名称
        
        Args:
            client: Pyrogram客户端
            channel: 频道名称
            
        Returns:
            包含频道信息的字典
        """
        try:
            chat = await client.get_chat(channel)
            username = f"@{chat.username}" if chat.username else f"id_{chat.id}"
            title = chat.title or "Unknown"

            # 使用统一的文件夹名称清理方法
            safe_title = ChannelUtils.sanitize_folder_name(title)
            folder_name = f"{username}-{safe_title}"

            return {
                "username": username,
                "title": title,
                "folder_name": folder_name,
                "chat_id": chat.id,
                "chat_type": str(chat.type) if hasattr(chat, 'type') else "unknown"
            }
        except Exception as e:
            # 使用静态方法记录错误
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"获取频道信息失败: {e}")

            # 回退到简单的文件夹名，也使用统一的清理方法
            clean_channel = ChannelUtils.sanitize_folder_name(channel)
            return {
                "username": channel,
                "title": channel,
                "folder_name": clean_channel,
                "chat_id": None,
                "chat_type": "unknown"
            }
    
    @staticmethod
    def sanitize_folder_name(name: str) -> str:
        """
        清理文件夹名称，移除非法字符

        Args:
            name: 原始名称

        Returns:
            清理后的名称
        """
        if not name:
            return "unknown_channel"

        # 移除非法字符（包括@符号，因为它在某些情况下可能导致问题）
        clean_name = re.sub(r'[<>:"/\\|?*@]', '_', name)
        # 移除控制字符
        clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)
        # 去除首尾空格和点
        clean_name = clean_name.strip('. ')
        # 限制长度
        if len(clean_name) > 100:
            clean_name = clean_name[:100]

        return clean_name or "unknown_channel"
