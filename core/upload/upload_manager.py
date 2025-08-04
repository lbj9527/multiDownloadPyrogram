"""
上传管理器
负责单个文件的上传操作和进度跟踪
"""
import asyncio
import time
from typing import Optional, Dict, Any, Callable
from io import BytesIO
from pyrogram.client import Client
from pyrogram.types import Message
from models.upload_task import UploadTask, UploadStatus, UploadType
from .upload_strategy import UploadStrategy
from utils.logging_utils import LoggerMixin


class UploadManager(LoggerMixin):
    """上传管理器"""
    
    def __init__(self):
        """初始化上传管理器"""
        self.strategy = UploadStrategy()
        self.upload_stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_bytes": 0,
            "upload_speed_avg": 0.0
        }
    
    async def upload_task(self, client: Client, task: UploadTask,
                         progress_callback: Optional[Callable] = None) -> bool:
        """
        上传单个任务
        
        Args:
            client: Pyrogram客户端
            task: 上传任务
            progress_callback: 进度回调函数
            
        Returns:
            bool: 上传是否成功
        """
        try:
            # 验证任务
            errors = self.strategy.validate_upload_task(task)
            if errors:
                error_msg = "; ".join(errors)
                self.log_error(f"任务验证失败: {error_msg}")
                task.fail_upload(error_msg)
                return False
            
            # 开始上传
            task.start_upload()
            self.log_info(f"开始上传任务: {task.file_name} -> {task.target_channel}")
            
            # 获取上传配置
            upload_config = self.strategy.get_upload_config(task)
            
            # 创建进度回调
            def progress_wrapper(current: int, total: int):
                self._update_progress(task, current, total)
                if progress_callback:
                    progress_callback(task, current, total)
            
            # 执行上传
            message = await self._execute_upload(client, task, upload_config, progress_wrapper)
            
            if message:
                task.complete_upload(message.id)
                self.log_info(f"上传成功: {task.file_name} (消息ID: {message.id})")
                self.upload_stats["successful_uploads"] += 1
                return True
            else:
                task.fail_upload("上传返回空消息")
                self.upload_stats["failed_uploads"] += 1
                return False
                
        except Exception as e:
            error_msg = f"上传异常: {str(e)}"
            self.log_error(error_msg)
            task.fail_upload(error_msg)
            self.upload_stats["failed_uploads"] += 1
            return False
        
        finally:
            self.upload_stats["total_uploads"] += 1
            self.upload_stats["total_bytes"] += task.file_size
    
    async def _execute_upload(self, client: Client, task: UploadTask,
                            config: Dict[str, Any], progress_callback: Callable) -> Optional[Message]:
        """
        执行具体的上传操作
        
        Args:
            client: Pyrogram客户端
            task: 上传任务
            config: 上传配置
            progress_callback: 进度回调
            
        Returns:
            Optional[Message]: 上传后的消息对象
        """
        method_name = config["method"]
        
        # 准备文件数据
        file_data = BytesIO(task.file_data)
        file_data.name = task.file_name
        
        # 准备说明文字
        caption = self._prepare_caption(task, config)
        
        # 根据上传方法执行不同的上传操作
        if method_name == "send_photo":
            return await client.send_photo(
                chat_id=task.target_channel,
                photo=file_data,
                caption=caption,
                progress=progress_callback
            )
        
        elif method_name == "send_video":
            return await client.send_video(
                chat_id=task.target_channel,
                video=file_data,
                caption=caption,
                progress=progress_callback,
                supports_streaming=config.get("supports_streaming", True)
            )
        
        elif method_name == "send_audio":
            return await client.send_audio(
                chat_id=task.target_channel,
                audio=file_data,
                caption=caption,
                progress=progress_callback
            )
        
        elif method_name == "send_voice":
            return await client.send_voice(
                chat_id=task.target_channel,
                voice=file_data,
                progress=progress_callback
            )
        
        elif method_name == "send_document":
            return await client.send_document(
                chat_id=task.target_channel,
                document=file_data,
                caption=caption,
                progress=progress_callback,
                force_document=config.get("force_document", False)
            )
        
        elif method_name == "send_video_note":
            return await client.send_video_note(
                chat_id=task.target_channel,
                video_note=file_data,
                progress=progress_callback
            )
        
        elif method_name == "send_sticker":
            return await client.send_sticker(
                chat_id=task.target_channel,
                sticker=file_data
            )
        
        else:
            raise ValueError(f"不支持的上传方法: {method_name}")
    
    def _prepare_caption(self, task: UploadTask, config: Dict[str, Any]) -> Optional[str]:
        """
        准备说明文字
        
        Args:
            task: 上传任务
            config: 上传配置
            
        Returns:
            Optional[str]: 处理后的说明文字
        """
        if not config.get("supports_caption", True):
            return None
        
        # 优先使用格式化内容
        caption = task.formatted_content or task.caption
        
        if not caption:
            return None
        
        # 检查长度限制
        max_length = config.get("max_caption_length", 1024)
        if len(caption) > max_length:
            # 截断并添加省略号
            caption = caption[:max_length-3] + "..."
            self.log_warning(f"说明文字过长，已截断到 {max_length} 字符")
        
        return caption
    
    def _update_progress(self, task: UploadTask, current: int, total: int):
        """
        更新上传进度
        
        Args:
            task: 上传任务
            current: 当前上传字节数
            total: 总字节数
        """
        # 计算上传速度
        current_time = time.time()
        if hasattr(task, '_last_progress_time'):
            time_diff = current_time - task._last_progress_time
            bytes_diff = current - getattr(task, '_last_progress_bytes', 0)
            
            if time_diff > 0:
                speed = bytes_diff / time_diff
                task.progress.update_progress(current, total, speed)
        
        task._last_progress_time = current_time
        task._last_progress_bytes = current
        
        # 如果没有速度信息，只更新基础进度
        if not hasattr(task, '_last_progress_time'):
            task.progress.update_progress(current, total)
    
    async def retry_failed_task(self, client: Client, task: UploadTask,
                               progress_callback: Optional[Callable] = None) -> bool:
        """
        重试失败的任务
        
        Args:
            client: Pyrogram客户端
            task: 失败的上传任务
            progress_callback: 进度回调函数
            
        Returns:
            bool: 重试是否成功
        """
        if not task.can_retry():
            self.log_warning(f"任务 {task.task_id} 无法重试")
            return False
        
        task.increment_retry()
        self.log_info(f"重试上传任务: {task.file_name} (第 {task.retry_count} 次重试)")
        
        # 添加重试延迟
        retry_delay = min(2 ** task.retry_count, 30)  # 指数退避，最大30秒
        await asyncio.sleep(retry_delay)
        
        return await self.upload_task(client, task, progress_callback)
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """
        获取上传统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = self.upload_stats.copy()
        
        # 计算成功率
        if stats["total_uploads"] > 0:
            stats["success_rate"] = (stats["successful_uploads"] / stats["total_uploads"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        # 格式化总大小
        total_mb = stats["total_bytes"] / (1024 * 1024)
        stats["total_size_mb"] = round(total_mb, 2)
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.upload_stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_bytes": 0,
            "upload_speed_avg": 0.0
        }
        self.log_info("上传统计信息已重置")
    
    async def test_upload_permissions(self, client: Client, channel: str) -> bool:
        """
        测试上传权限
        
        Args:
            client: Pyrogram客户端
            channel: 目标频道
            
        Returns:
            bool: 是否有上传权限
        """
        try:
            # 尝试获取频道信息
            chat = await client.get_chat(channel)
            
            # 检查是否是频道管理员或有发送消息权限
            if chat.type in ["channel", "supergroup"]:
                member = await client.get_chat_member(channel, "me")
                if member.status in ["administrator", "creator"]:
                    return True
                elif hasattr(member, "privileges") and member.privileges:
                    return member.privileges.can_send_messages
            
            # 私聊或群组默认可以发送
            return True
            
        except Exception as e:
            self.log_error(f"检查上传权限失败: {e}")
            return False
