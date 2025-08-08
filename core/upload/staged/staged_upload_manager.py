"""
分阶段上传管理器
协调整个分阶段上传流程
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import asyncio
import time

from pyrogram.client import Client

from utils.logging_utils import LoggerMixin
from .data_source import DataSource, MediaData
from .temporary_storage import TemporaryStorage, TemporaryMediaItem
from .media_group_manager import MediaGroupManager, MediaGroupBatch
from .target_distributor import TargetDistributor, DistributionResult
from .preservation_config import MediaGroupPreservationConfig
from models.message_group import ClientTaskAssignment, MessageGroup


@dataclass
class StagedUploadConfig:
    """分阶段上传配置"""
    batch_size: int = 10                    # 媒体组大小（仅在非媒体组保持模式下使用）
    max_concurrent_distributions: int = 3   # 最大并发分发数
    cleanup_after_success: bool = True      # 成功后清理临时文件
    cleanup_after_failure: bool = False     # 失败后清理临时文件
    retry_delay: float = 5.0                # 重试延迟
    max_retries: int = 3                    # 最大重试次数
    progress_callback_interval: int = 5     # 进度回调间隔

    # 新增媒体组完整性配置
    media_group_preservation: Optional[MediaGroupPreservationConfig] = None

    def __post_init__(self):
        if self.media_group_preservation is None:
            self.media_group_preservation = MediaGroupPreservationConfig()


@dataclass
class StagedUploadResult:
    """分阶段上传结果"""
    total_items: int = 0
    staged_items: int = 0
    distributed_items: int = 0
    failed_items: int = 0
    
    total_batches: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    
    total_channels: int = 0
    successful_channels: int = 0
    failed_channels: int = 0
    
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    distribution_results: List[DistributionResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.end_time is None:
            self.end_time = time.time()
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_items == 0:
            return 0.0
        return self.distributed_items / self.total_items
    
    def get_duration(self) -> float:
        """获取总耗时（秒）"""
        return (self.end_time or time.time()) - self.start_time
    
    def is_successful(self) -> bool:
        """检查是否完全成功"""
        return self.failed_items == 0 and self.failed_batches == 0


class StagedUploadManager(LoggerMixin):
    """分阶段上传管理器"""
    
    def __init__(self,
                 data_source: DataSource,
                 temporary_storage: TemporaryStorage,
                 config: Optional[StagedUploadConfig] = None):
        self.data_source = data_source
        self.temporary_storage = temporary_storage
        self.config = config or StagedUploadConfig()
        
        # 初始化组件
        self.media_group_manager = MediaGroupManager(
            batch_size=self.config.batch_size,
            auto_send_threshold=self.config.batch_size
        )
        self.target_distributor = TargetDistributor(
            max_concurrent=self.config.max_concurrent_distributions,
            retry_delay=self.config.retry_delay,
            max_retries=self.config.max_retries
        )
        
        # 状态跟踪
        self.staged_items: List[TemporaryMediaItem] = []
        self.pending_cleanup: List[TemporaryMediaItem] = []
    
    async def upload_with_structure_awareness(self,
                                            assignment: ClientTaskAssignment,
                                            target_channels: List[str],
                                            client: Client,
                                            preserve_structure: bool = False,
                                            template_processor: Optional[Any] = None,
                                            progress_callback: Optional[Callable] = None) -> StagedUploadResult:
        """
        结构感知的分阶段上传

        Args:
            assignment: 包含媒体组信息的任务分配
            target_channels: 目标频道列表
            client: Pyrogram客户端
            preserve_structure: 是否保持原始媒体组结构
            template_processor: 模板处理器
            progress_callback: 进度回调函数
        """
        if preserve_structure and assignment.has_media_groups():
            return await self._upload_with_structure_preservation(
                assignment, target_channels, client, template_processor, progress_callback
            )
        else:
            # 回退到传统模式
            messages = assignment.get_all_messages()
            return await self.upload_with_staging(messages, target_channels, client, progress_callback)

    async def upload_with_staging(self,
                                source_items: List[Any],
                                target_channels: List[str],
                                client: Client,
                                progress_callback: Optional[Callable] = None) -> StagedUploadResult:
        """
        执行分阶段上传
        
        Args:
            source_items: 源数据项列表（如Telegram消息）
            target_channels: 目标频道列表
            client: Pyrogram客户端
            progress_callback: 进度回调函数
            
        Returns:
            StagedUploadResult: 上传结果
        """
        result = StagedUploadResult(
            total_items=len(source_items),
            total_channels=len(target_channels)
        )
        
        try:
            self.log_info(f"开始分阶段上传: {len(source_items)} 个项目 -> {len(target_channels)} 个频道")
            
            # 阶段1: 数据获取和临时存储
            await self._stage_1_data_acquisition_and_staging(
                source_items, client, result, progress_callback
            )
            
            # 阶段2: 媒体组管理和分发
            await self._stage_2_grouping_and_distribution(
                target_channels, client, result, progress_callback
            )
            
            # 阶段3: 清理
            await self._stage_3_cleanup(result)
            
            result.end_time = time.time()
            
            self.log_info(f"分阶段上传完成: 成功率 {result.get_success_rate():.1%}, 耗时 {result.get_duration():.1f}秒")
            
            return result
            
        except Exception as e:
            self.log_error(f"分阶段上传失败: {e}")
            result.errors.append(str(e))
            result.end_time = time.time()
            
            # 尝试清理已存储的项目
            await self._emergency_cleanup()
            
            return result

    async def _upload_with_structure_preservation(self,
                                                assignment: ClientTaskAssignment,
                                                target_channels: List[str],
                                                client: Client,
                                                template_processor: Optional[Any] = None,
                                                progress_callback: Optional[Callable] = None) -> StagedUploadResult:
        """
        保持结构的上传处理
        """
        self.log_info(f"开始结构保持上传: {assignment.get_group_count()} 个原始媒体组")

        result = StagedUploadResult(
            total_items=assignment.total_messages,
            total_channels=len(target_channels)
        )

        total_success = 0
        total_failed = 0
        start_time = time.time()

        try:
            # 按原始媒体组逐个处理
            for group_index, original_group in enumerate(assignment.get_original_groups(), 1):
                self.log_info(f"处理原始媒体组 {group_index}/{assignment.get_group_count()}: {len(original_group.messages)} 个文件")

                if progress_callback:
                    progress_callback(f"正在处理媒体组 {group_index}/{assignment.get_group_count()}")

                try:
                    # 阶段1: 下载并暂存当前媒体组
                    temp_items = await self._stage_media_group(original_group, client, template_processor)

                    if not temp_items:
                        self.log_warning(f"媒体组 {group_index} 暂存失败，跳过")
                        total_failed += len(original_group.messages)
                        continue

                    # 阶段2: 保持原始结构分发到目标频道
                    success = await self._distribute_original_group(temp_items, target_channels, client)

                    if success:
                        total_success += len(temp_items)
                        self.log_info(f"✅ 媒体组 {group_index} 分发成功")
                    else:
                        total_failed += len(temp_items)
                        self.log_error(f"❌ 媒体组 {group_index} 分发失败")

                    # 阶段3: 清理当前媒体组的临时文件
                    await self._cleanup_temp_items(temp_items, client)

                except Exception as e:
                    self.log_error(f"处理媒体组 {group_index} 时发生错误: {e}")
                    total_failed += len(original_group.messages)
                    result.errors.append(f"媒体组 {group_index}: {str(e)}")

            # 生成结果
            result.staged_items = total_success + total_failed
            result.distributed_items = total_success
            result.failed_items = total_failed
            result.end_time = time.time()

            duration = result.get_duration()
            success_rate = result.get_success_rate() * 100

            self.log_info(f"分阶段上传完成: 成功率 {success_rate:.1f}%, 耗时 {duration:.1f}秒")

            return result

        except Exception as e:
            self.log_error(f"结构保持上传失败: {e}")
            result.errors.append(str(e))
            result.end_time = time.time()
            return result

    async def _stage_1_data_acquisition_and_staging(self,
                                                  source_items: List[Any],
                                                  client: Client,
                                                  result: StagedUploadResult,
                                                  progress_callback: Optional[Callable]):
        """阶段1: 数据获取和临时存储"""
        self.log_info("阶段1: 开始数据获取和临时存储")
        
        for i, source_item in enumerate(source_items):
            try:
                # 进度回调
                if progress_callback and i % self.config.progress_callback_interval == 0:
                    progress_callback(f"正在处理项目 {i + 1}/{len(source_items)}")
                
                # 从数据源获取媒体数据
                media_data = await self.data_source.get_media_data(source_item)
                if not media_data:
                    self.log_warning(f"跳过无效的源项目 {i + 1}")
                    result.failed_items += 1
                    continue
                
                # 存储到临时位置
                temp_item = await self.temporary_storage.store_media(media_data)
                if not temp_item:
                    self.log_error(f"临时存储失败: {media_data.file_name}")
                    result.failed_items += 1
                    continue
                
                self.staged_items.append(temp_item)
                result.staged_items += 1
                
                self.log_debug(f"已暂存: {media_data.file_name}")
                
            except Exception as e:
                self.log_error(f"处理源项目 {i + 1} 失败: {e}")
                result.failed_items += 1
                result.errors.append(f"项目 {i + 1}: {str(e)}")
        
        self.log_info(f"阶段1完成: 成功暂存 {result.staged_items}/{result.total_items} 个项目")
    
    async def _stage_2_grouping_and_distribution(self,
                                               target_channels: List[str],
                                               client: Client,
                                               result: StagedUploadResult,
                                               progress_callback: Optional[Callable]):
        """阶段2: 媒体组管理和分发"""
        self.log_info("阶段2: 开始媒体组管理和分发")
        
        # 将所有暂存项目添加到媒体组管理器
        ready_batches = []
        for temp_item in self.staged_items:
            ready_batch = await self.media_group_manager.add_media_item(temp_item)
            if ready_batch:
                ready_batches.append(ready_batch)
        
        # 获取剩余的批次
        remaining_batches = await self.media_group_manager.flush_all_batches()
        ready_batches.extend(remaining_batches)
        
        result.total_batches = len(ready_batches)
        self.log_info(f"创建了 {len(ready_batches)} 个媒体组批次")
        
        # 分发每个批次
        for i, batch in enumerate(ready_batches):
            try:
                if progress_callback:
                    progress_callback(f"正在分发批次 {i + 1}/{len(ready_batches)}")
                
                # 创建InputMedia组
                input_media_group = await self.media_group_manager.create_input_media_group(batch)
                if not input_media_group:
                    self.log_error(f"批次 {i + 1} 创建InputMedia组失败")
                    result.failed_batches += 1
                    continue
                
                # 分发到目标频道
                distribution_result = await self.target_distributor.distribute_media_group(
                    client, batch, input_media_group, target_channels
                )
                
                result.distribution_results.append(distribution_result)
                
                if distribution_result.is_successful():
                    result.successful_batches += 1
                    result.distributed_items += len(batch.items)
                    
                    # 标记成功的项目用于清理
                    if self.config.cleanup_after_success:
                        self.pending_cleanup.extend(batch.items)
                else:
                    result.failed_batches += 1
                    
                    # 标记失败的项目用于清理（如果配置允许）
                    if self.config.cleanup_after_failure:
                        self.pending_cleanup.extend(batch.items)
                
                # 更新频道统计
                result.successful_channels += distribution_result.successful_channels
                result.failed_channels += distribution_result.failed_channels
                
            except Exception as e:
                self.log_error(f"分发批次 {i + 1} 失败: {e}")
                result.failed_batches += 1
                result.errors.append(f"批次 {i + 1}: {str(e)}")
        
        self.log_info(f"阶段2完成: 成功分发 {result.successful_batches}/{result.total_batches} 个批次")
    
    async def _stage_3_cleanup(self, result: StagedUploadResult):
        """阶段3: 清理临时文件"""
        if not self.pending_cleanup:
            self.log_info("阶段3: 无需清理")
            return
        
        self.log_info(f"阶段3: 开始清理 {len(self.pending_cleanup)} 个临时文件")
        
        try:
            cleaned_count = await self.temporary_storage.cleanup_batch(self.pending_cleanup)
            self.log_info(f"阶段3完成: 成功清理 {cleaned_count}/{len(self.pending_cleanup)} 个临时文件")
            
        except Exception as e:
            self.log_error(f"清理临时文件失败: {e}")
            result.errors.append(f"清理失败: {str(e)}")
        
        finally:
            self.pending_cleanup.clear()
    
    async def _emergency_cleanup(self):
        """紧急清理所有暂存的项目"""
        if not self.staged_items:
            return
        
        self.log_warning(f"执行紧急清理: {len(self.staged_items)} 个项目")
        
        try:
            await self.temporary_storage.cleanup_batch(self.staged_items)
        except Exception as e:
            self.log_error(f"紧急清理失败: {e}")
        finally:
            self.staged_items.clear()
            self.pending_cleanup.clear()

    async def _stage_media_group(self,
                                group: MessageGroup,
                                client: Client,
                                template_processor: Optional[Any] = None) -> List[TemporaryMediaItem]:
        """暂存单个媒体组"""
        temp_items = []

        for message in group.messages:
            try:
                # 下载到内存
                media_data = await self.data_source.get_media_data(message)
                if not media_data:
                    continue

                # 模板处理（如果需要）
                if template_processor:
                    # 这里可以添加模板处理逻辑
                    pass

                # 暂存到me聊天
                temp_item = await self.temporary_storage.store_media(media_data)
                if temp_item:
                    temp_items.append(temp_item)

            except Exception as e:
                self.log_error(f"暂存消息 {message.id} 失败: {e}")

        return temp_items

    async def _distribute_original_group(self,
                                       temp_items: List[TemporaryMediaItem],
                                       target_channels: List[str],
                                       client: Client) -> bool:
        """分发单个原始媒体组到目标频道"""
        try:
            if not temp_items:
                self.log_warning("没有临时项目可分发")
                return False

            # 从临时项目构建输入媒体组
            input_media_group = []
            for temp_item in temp_items:
                try:
                    # 获取临时消息
                    temp_message = await client.get_messages("me", temp_item.message_id)
                    if temp_message and temp_message.media:
                        # 将Message对象转换为InputMedia对象
                        input_media = await self._convert_message_to_input_media(temp_message, temp_item)
                        if input_media:
                            input_media_group.append(input_media)
                except Exception as e:
                    self.log_error(f"获取临时消息 {temp_item.message_id} 失败: {e}")

            if not input_media_group:
                self.log_error("无法构建输入媒体组")
                return False

            # 创建单个媒体组批次（保持原始结构）
            from .media_group_manager import MediaGroupType
            media_group_batch = MediaGroupBatch(
                group_type=MediaGroupType.PHOTO_VIDEO,  # 默认使用照片视频类型
                items=temp_items
            )

            self.log_info(f"准备分发媒体组: {len(input_media_group)} 个InputMedia对象到 {len(target_channels)} 个频道")

            # 分发到所有目标频道
            distribution_result = await self.target_distributor.distribute_media_group(
                client, media_group_batch, input_media_group, target_channels
            )

            return distribution_result.is_successful()

        except Exception as e:
            self.log_error(f"分发原始媒体组失败: {e}")
            return False

    async def _cleanup_temp_items(self, temp_items: List[TemporaryMediaItem], client: Client):
        """清理临时项目"""
        try:
            if temp_items:
                cleaned_count = await self.temporary_storage.cleanup_batch(temp_items)
                self.log_debug(f"清理了 {cleaned_count}/{len(temp_items)} 个临时文件")
        except Exception as e:
            self.log_error(f"清理临时文件失败: {e}")

    async def _convert_message_to_input_media(self, message, temp_item: TemporaryMediaItem):
        """将Message对象转换为InputMedia对象"""
        try:
            from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAnimation

            # 获取原始文件名和标题
            original_caption = getattr(message, 'caption', None) or ""
            file_name = temp_item.media_data.file_name if temp_item.media_data else "unknown"

            # 根据媒体类型创建对应的InputMedia对象
            if message.photo:
                return InputMediaPhoto(
                    media=message.photo.file_id,
                    caption=original_caption
                )
            elif message.video:
                return InputMediaVideo(
                    media=message.video.file_id,
                    caption=original_caption,
                    duration=getattr(message.video, 'duration', None),
                    width=getattr(message.video, 'width', None),
                    height=getattr(message.video, 'height', None)
                )
            elif message.animation:
                return InputMediaAnimation(
                    media=message.animation.file_id,
                    caption=original_caption,
                    duration=getattr(message.animation, 'duration', None),
                    width=getattr(message.animation, 'width', None),
                    height=getattr(message.animation, 'height', None)
                )
            elif message.document:
                return InputMediaDocument(
                    media=message.document.file_id,
                    caption=original_caption
                )
            else:
                self.log_warning(f"不支持的媒体类型: {type(message.media)}")
                return None

        except Exception as e:
            self.log_error(f"转换消息为InputMedia失败: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "staged_items": len(self.staged_items),
            "pending_cleanup": len(self.pending_cleanup),
            "media_group_manager": self.media_group_manager.get_stats(),
            "target_distributor": self.target_distributor.get_stats()
        }
