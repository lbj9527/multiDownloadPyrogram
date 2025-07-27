"""
核心业务接口抽象
定义系统中各组件的标准接口
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from pathlib import Path
from dataclasses import dataclass
from pyrogram import Client


@dataclass
class ProcessResult:
    """处理结果统一格式"""
    success: bool
    error_message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class MessageProcessorInterface(ABC):
    """消息处理器接口"""
    
    @abstractmethod
    async def process_message(
        self, 
        client: Client, 
        message: Any, 
        channel: str
    ) -> bool:
        """
        处理单条消息
        
        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称
            
        Returns:
            是否处理成功
        """
        pass


class UploadHandlerInterface(ABC):
    """上传处理器接口"""
    
    @abstractmethod
    async def handle_upload(
        self,
        client: Client,
        message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """
        处理上传请求
        
        Args:
            client: Pyrogram客户端
            message: 原始消息对象
            media_data: 媒体数据（内存中）
            file_path: 文件路径（本地文件）
            
        Returns:
            是否上传成功
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """检查上传功能是否启用"""
        pass


class FileProcessorInterface(ABC):
    """文件处理器接口"""
    
    @abstractmethod
    async def process_media_message(
        self,
        client: Client,
        message: Any,
        channel: str
    ) -> Optional[Path]:
        """
        处理媒体消息，下载文件
        
        Args:
            client: Pyrogram客户端
            message: 消息对象
            channel: 频道名称
            
        Returns:
            下载的文件路径
        """
        pass
    
    @abstractmethod
    async def process_text_message(
        self,
        message: Any,
        channel: str,
        client: Client
    ) -> bool:
        """
        处理文本消息
        
        Args:
            message: 消息对象
            channel: 频道名称
            client: Pyrogram客户端
            
        Returns:
            是否处理成功
        """
        pass


class NullUploadHandler(UploadHandlerInterface):
    """空上传处理器 - 用于禁用上传功能时"""
    
    async def handle_upload(
        self,
        client: Client,
        message: Any,
        media_data: Optional[bytes] = None,
        file_path: Optional[Path] = None
    ) -> bool:
        """不执行任何上传操作"""
        return True
    
    def is_enabled(self) -> bool:
        """上传功能未启用"""
        return False
