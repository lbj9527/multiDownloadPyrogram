"""
目标分发器
负责将媒体组分发到多个目标频道
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import asyncio
import time

from pyrogram.client import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from utils.logging_utils import LoggerMixin
from .media_group_manager import MediaGroupBatch


@dataclass
class ChannelDistributionResult:
    """单个频道的分发结果"""
    channel: str
    success: bool
    message_ids: List[int] = field(default_factory=list)
    error: Optional[str] = None
    upload_time: Optional[float] = None
    
    def __post_init__(self):
        if self.upload_time is None and self.success:
            self.upload_time = time.time()


@dataclass
class DistributionResult:
    """分发结果"""
    batch: MediaGroupBatch
    channel_results: List[ChannelDistributionResult] = field(default_factory=list)
    total_channels: int = 0
    successful_channels: int = 0
    failed_channels: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    def __post_init__(self):
        self.total_channels = len(self.channel_results)
        self.successful_channels = sum(1 for r in self.channel_results if r.success)
        self.failed_channels = self.total_channels - self.successful_channels
        
        if self.end_time is None:
            self.end_time = time.time()
    
    def is_successful(self) -> bool:
        """检查是否所有频道都分发成功"""
        return self.failed_channels == 0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_channels == 0:
            return 0.0
        return self.successful_channels / self.total_channels
    
    def get_duration(self) -> float:
        """获取分发耗时（秒）"""
        return (self.end_time or time.time()) - self.start_time


class TargetDistributor(LoggerMixin):
    """目标分发器"""
    
    def __init__(self, max_concurrent: int = 3, retry_delay: float = 5.0, max_retries: int = 3):
        self.max_concurrent = max_concurrent
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        
        # 统计信息
        self.stats = {
            "total_distributions": 0,
            "successful_distributions": 0,
            "failed_distributions": 0,
            "total_channels": 0,
            "successful_channels": 0,
            "failed_channels": 0
        }
    
    async def distribute_media_group(self, 
                                   client: Client,
                                   batch: MediaGroupBatch,
                                   input_media_group: List[Any],
                                   target_channels: List[str]) -> DistributionResult:
        """
        将媒体组分发到多个目标频道
        
        Args:
            client: Pyrogram客户端
            batch: 媒体组批次
            input_media_group: InputMedia对象列表
            target_channels: 目标频道列表
            
        Returns:
            DistributionResult: 分发结果
        """
        try:
            self.stats["total_distributions"] += 1
            self.stats["total_channels"] += len(target_channels)
            
            self.log_info(f"开始分发媒体组到 {len(target_channels)} 个频道")
            self.log_info(f"媒体组包含 {len(input_media_group)} 个媒体项")
            
            # 创建分发任务
            distribution_tasks = []
            for channel in target_channels:
                task = self._distribute_to_single_channel(
                    client, channel, input_media_group, batch
                )
                distribution_tasks.append(task)
            
            # 并发执行分发任务
            channel_results = await asyncio.gather(*distribution_tasks, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            for i, result in enumerate(channel_results):
                if isinstance(result, Exception):
                    self.log_error(f"频道 {target_channels[i]} 分发异常: {result}")
                    processed_results.append(ChannelDistributionResult(
                        channel=target_channels[i],
                        success=False,
                        error=str(result)
                    ))
                else:
                    processed_results.append(result)
            
            # 创建分发结果
            distribution_result = DistributionResult(
                batch=batch,
                channel_results=processed_results
            )
            
            # 更新统计信息
            if distribution_result.is_successful():
                self.stats["successful_distributions"] += 1
            else:
                self.stats["failed_distributions"] += 1
            
            self.stats["successful_channels"] += distribution_result.successful_channels
            self.stats["failed_channels"] += distribution_result.failed_channels
            
            self.log_info(f"媒体组分发完成: {distribution_result.successful_channels}/{distribution_result.total_channels} 个频道成功")
            
            return distribution_result
            
        except Exception as e:
            self.log_error(f"分发媒体组失败: {e}")
            self.stats["failed_distributions"] += 1
            self.stats["failed_channels"] += len(target_channels)
            
            # 返回失败结果
            failed_results = [
                ChannelDistributionResult(
                    channel=channel,
                    success=False,
                    error=str(e)
                ) for channel in target_channels
            ]
            
            return DistributionResult(
                batch=batch,
                channel_results=failed_results
            )
    
    async def _distribute_to_single_channel(self, 
                                          client: Client,
                                          channel: str,
                                          input_media_group: List[Any],
                                          batch: MediaGroupBatch) -> ChannelDistributionResult:
        """
        分发到单个频道
        
        Args:
            client: Pyrogram客户端
            channel: 目标频道
            input_media_group: InputMedia对象列表
            batch: 媒体组批次
            
        Returns:
            ChannelDistributionResult: 单个频道的分发结果
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                self.log_info(f"开始上传媒体组到频道 {channel} (尝试 {retry_count + 1}/{self.max_retries + 1})")
                
                # 发送媒体组
                messages = await client.send_media_group(
                    chat_id=channel,
                    media=input_media_group
                )
                
                # 提取消息ID
                message_ids = [msg.id for msg in messages] if messages else []
                
                self.log_info(f"成功上传媒体组到频道 {channel}: {len(message_ids)} 条消息")
                
                return ChannelDistributionResult(
                    channel=channel,
                    success=True,
                    message_ids=message_ids
                )
                
            except FloodWait as e:
                self.log_warning(f"频道 {channel} 遇到频率限制，等待 {e.value} 秒...")
                await asyncio.sleep(e.value)
                retry_count += 1
                last_error = str(e)
                
            except Exception as e:
                self.log_error(f"上传媒体组到频道 {channel} 失败 (尝试 {retry_count + 1}): {e}")
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    await asyncio.sleep(self.retry_delay)
        
        # 所有重试都失败了
        self.log_error(f"频道 {channel} 分发最终失败，已重试 {self.max_retries} 次")
        
        return ChannelDistributionResult(
            channel=channel,
            success=False,
            error=last_error or "未知错误"
        )
    
    async def distribute_single_media(self,
                                    client: Client,
                                    media_item: Any,
                                    target_channels: List[str],
                                    caption: str = "") -> DistributionResult:
        """
        分发单个媒体到多个频道（用于非媒体组的情况）
        
        Args:
            client: Pyrogram客户端
            media_item: 媒体项（消息ID或文件路径）
            target_channels: 目标频道列表
            caption: 说明文字
            
        Returns:
            DistributionResult: 分发结果
        """
        try:
            self.log_info(f"开始分发单个媒体到 {len(target_channels)} 个频道")
            
            # 创建分发任务
            distribution_tasks = []
            for channel in target_channels:
                task = self._distribute_single_to_channel(client, channel, media_item, caption)
                distribution_tasks.append(task)
            
            # 并发执行
            channel_results = await asyncio.gather(*distribution_tasks, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            for i, result in enumerate(channel_results):
                if isinstance(result, Exception):
                    processed_results.append(ChannelDistributionResult(
                        channel=target_channels[i],
                        success=False,
                        error=str(result)
                    ))
                else:
                    processed_results.append(result)
            
            return DistributionResult(
                batch=None,  # 单个媒体没有批次
                channel_results=processed_results
            )
            
        except Exception as e:
            self.log_error(f"分发单个媒体失败: {e}")
            failed_results = [
                ChannelDistributionResult(
                    channel=channel,
                    success=False,
                    error=str(e)
                ) for channel in target_channels
            ]
            
            return DistributionResult(
                batch=None,
                channel_results=failed_results
            )
    
    async def _distribute_single_to_channel(self,
                                          client: Client,
                                          channel: str,
                                          media_item: Any,
                                          caption: str) -> ChannelDistributionResult:
        """分发单个媒体到单个频道"""
        try:
            # 这里可以根据媒体类型选择合适的发送方法
            # 简化实现，假设使用copy_message
            message = await client.copy_message(
                chat_id=channel,
                from_chat_id="me",
                message_id=media_item,
                caption=caption
            )
            
            return ChannelDistributionResult(
                channel=channel,
                success=True,
                message_ids=[message.id] if message else []
            )
            
        except Exception as e:
            return ChannelDistributionResult(
                channel=channel,
                success=False,
                error=str(e)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
