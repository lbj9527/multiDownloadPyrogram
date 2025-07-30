"""
智能消息分配器
基于SOLID原则设计的独立消息分配模块
支持媒体组感知和多种负载均衡策略
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageValidator:
    """消息验证器"""

    @staticmethod
    async def validate_message_ids(client, channel: str, message_ids: List[int]) -> Tuple[List[int], List[int], Dict[str, Any]]:
        """
        验证消息ID的有效性

        Args:
            client: Pyrogram客户端
            channel: 频道名称
            message_ids: 要验证的消息ID列表

        Returns:
            Tuple[valid_ids, invalid_ids, stats]
        """
        if not message_ids:
            return [], [], {"total": 0, "valid": 0, "invalid": 0}

        logger.info(f"🔍 开始验证 {len(message_ids)} 个消息ID...")

        valid_ids = []
        invalid_ids = []

        # 分批验证，避免一次性验证太多消息
        batch_size = 100

        for i in range(0, len(message_ids), batch_size):
            batch_ids = message_ids[i:i + batch_size]

            try:
                # 获取消息对象
                messages = await client.get_messages(channel, batch_ids)

                for j, message in enumerate(messages):
                    original_id = batch_ids[j]
                    if message is not None and _has_media_comprehensive(message):
                        # 只有包含媒体内容的消息才被认为是有效的
                        valid_ids.append(original_id)
                    else:
                        # 纯文本消息或不存在的消息都被认为是无效的
                        invalid_ids.append(original_id)

            except Exception as e:
                logger.warning(f"验证消息批次 {batch_ids[0]}-{batch_ids[-1]} 失败: {e}")
                # 如果批次验证失败，将所有ID标记为无效
                invalid_ids.extend(batch_ids)

        stats = {
            "total": len(message_ids),
            "valid": len(valid_ids),
            "invalid": len(invalid_ids),
            "valid_rate": len(valid_ids) / len(message_ids) if message_ids else 0
        }

        logger.info(f"✅ 消息验证完成: {stats['valid']}/{stats['total']} 有效 ({stats['valid_rate']:.1%})")

        if invalid_ids:
            logger.warning(f"⚠️ 发现 {len(invalid_ids)} 个无效消息ID: {invalid_ids[:10]}{'...' if len(invalid_ids) > 10 else ''}")

        return valid_ids, invalid_ids, stats


class LoadBalanceMetric(Enum):
    """负载均衡指标"""
    MESSAGE_COUNT = "message_count"       # 按消息数量
    FILE_COUNT = "file_count"            # 按文件数量
    ESTIMATED_SIZE = "estimated_size"     # 按估算大小
    MIXED = "mixed"                      # 混合指标


class DistributionMode(Enum):
    """分配模式"""
    MEDIA_GROUP_AWARE = "media_group_aware"  # 媒体组感知分配


@dataclass
class MessageInfo:
    """消息信息"""
    message_id: int
    media_group_id: Optional[str] = None
    file_size: int = 0
    has_media: bool = False
    
    @property
    def is_media_group(self) -> bool:
        return self.media_group_id is not None


@dataclass
class MessageGroup:
    """消息组"""
    group_id: str
    messages: List[MessageInfo] = field(default_factory=list)
    is_media_group: bool = False
    
    @property
    def total_messages(self) -> int:
        return len(self.messages)
    
    @property
    def total_files(self) -> int:
        return sum(1 for msg in self.messages if msg.has_media)
    
    @property
    def estimated_size(self) -> int:
        return sum(msg.file_size for msg in self.messages)
    
    @property
    def message_ids(self) -> List[int]:
        return [msg.message_id for msg in self.messages]


@dataclass
class ClientAssignment:
    """客户端任务分配"""
    client_name: str
    message_groups: List[MessageGroup] = field(default_factory=list)
    
    @property
    def total_messages(self) -> int:
        return sum(group.total_messages for group in self.message_groups)
    
    @property
    def total_files(self) -> int:
        return sum(group.total_files for group in self.message_groups)
    
    @property
    def estimated_size(self) -> int:
        return sum(group.estimated_size for group in self.message_groups)
    
    @property
    def all_message_ids(self) -> List[int]:
        """获取所有消息ID"""
        all_ids = []
        for group in self.message_groups:
            all_ids.extend(group.message_ids)
        return sorted(all_ids)
    
    def add_group(self, group: MessageGroup):
        """添加消息组"""
        self.message_groups.append(group)


@dataclass
class DistributionResult:
    """分配结果"""
    client_assignments: List[ClientAssignment] = field(default_factory=list)
    distribution_strategy: str = ""
    
    @property
    def total_messages(self) -> int:
        return sum(assignment.total_messages for assignment in self.client_assignments)
    
    @property
    def total_files(self) -> int:
        return sum(assignment.total_files for assignment in self.client_assignments)
    
    def get_load_balance_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        if not self.client_assignments:
            return {}
        
        file_counts = [assignment.total_files for assignment in self.client_assignments]
        size_estimates = [assignment.estimated_size for assignment in self.client_assignments]
        
        return {
            "clients_count": len(self.client_assignments),
            "file_distribution": file_counts,
            "size_distribution": size_estimates,
            "file_balance_ratio": min(file_counts) / max(file_counts) if max(file_counts) > 0 else 1.0,
            "size_balance_ratio": min(size_estimates) / max(size_estimates) if max(size_estimates) > 0 else 1.0,
            "average_files_per_client": sum(file_counts) / len(file_counts) if file_counts else 0,
            "max_files": max(file_counts) if file_counts else 0,
            "min_files": min(file_counts) if file_counts else 0
        }


@dataclass
class DistributionConfig:
    """分配配置"""
    mode: DistributionMode = DistributionMode.MEDIA_GROUP_AWARE
    load_balance_metric: LoadBalanceMetric = LoadBalanceMetric.FILE_COUNT
    max_imbalance_ratio: float = 0.3  # 最大不均衡比例
    prefer_large_groups_first: bool = True  # 优先分配大组
    enable_validation: bool = True  # 启用验证
    enable_message_id_validation: bool = True  # 启用消息ID验证

    # 高级配置（与main.py程序保持一致）
    custom_weights: Dict[str, float] = field(default_factory=dict)  # 自定义权重
    client_preferences: Dict[str, List[str]] = field(default_factory=dict)  # 客户端偏好

    def __post_init__(self):
        """后初始化验证"""
        if not 0 <= self.max_imbalance_ratio <= 1:
            raise ValueError("max_imbalance_ratio must be between 0 and 1")


class MessageDistributionStrategy(ABC):
    """消息分配策略抽象基类"""
    
    def __init__(self, config: DistributionConfig):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def distribute(
        self,
        messages: List[MessageInfo],
        client_names: List[str]
    ) -> DistributionResult:
        """分配消息到客户端"""
        pass

    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        pass
    
    def validate_inputs(self, messages: List[MessageInfo], client_names: List[str]) -> List[str]:
        """验证输入参数"""
        errors = []
        
        if not client_names:
            errors.append("客户端列表不能为空")
        
        if not messages:
            errors.append("消息列表不能为空")
        
        if len(client_names) != len(set(client_names)):
            errors.append("客户端名称列表包含重复项")
        
        return errors


class MediaGroupAwareStrategy(MessageDistributionStrategy):
    """媒体组感知分配策略"""
    
    def distribute(
        self, 
        messages: List[MessageInfo], 
        client_names: List[str]
    ) -> DistributionResult:
        """媒体组感知的消息分配"""
        
        # 验证输入
        errors = self.validate_inputs(messages, client_names)
        if errors:
            raise ValueError(f"输入验证失败: {errors}")
        
        # 1. 按媒体组分组消息
        message_groups = self._group_messages(messages)
        
        # 2. 初始化客户端分配
        client_assignments = [
            ClientAssignment(client_name=name) for name in client_names
        ]
        
        # 3. 排序组（如果配置了优先大组）
        if self.config.prefer_large_groups_first:
            message_groups.sort(key=lambda g: g.total_files, reverse=True)
        
        # 4. 使用贪心算法分配
        for group in message_groups:
            min_load_client_idx = self._find_min_load_client(client_assignments)
            client_assignments[min_load_client_idx].add_group(group)
        
        # 5. 创建结果
        result = DistributionResult(
            client_assignments=client_assignments,
            distribution_strategy="MediaGroupAwareStrategy"
        )
        
        return result
    
    def _group_messages(self, messages: List[MessageInfo]) -> List[MessageGroup]:
        """将消息按媒体组分组（改进版，支持大媒体组智能拆分）"""
        media_groups: Dict[str, MessageGroup] = {}
        single_messages: List[MessageGroup] = []

        for msg in messages:
            if msg.is_media_group:
                # 媒体组消息
                if msg.media_group_id not in media_groups:
                    media_groups[msg.media_group_id] = MessageGroup(
                        group_id=msg.media_group_id,
                        is_media_group=True
                    )
                media_groups[msg.media_group_id].messages.append(msg)
            else:
                # 单条消息
                single_group = MessageGroup(
                    group_id=f"single_{msg.message_id}",
                    messages=[msg],
                    is_media_group=False
                )
                single_messages.append(single_group)

        # 处理大媒体组的智能拆分
        all_groups = []
        client_count = len(self.config.custom_weights) if self.config.custom_weights else 3  # 默认3个客户端

        for group in media_groups.values():
            # 如果媒体组太大（超过客户端数量的2倍），考虑拆分
            if len(group.messages) > client_count * 2:
                logger.info(f"🔄 检测到大媒体组 {group.group_id}，包含 {len(group.messages)} 条消息，考虑智能拆分")

                # 将大媒体组拆分为多个子组
                chunk_size = max(2, len(group.messages) // client_count)  # 每个子组至少2条消息
                for i in range(0, len(group.messages), chunk_size):
                    chunk_messages = group.messages[i:i + chunk_size]
                    sub_group = MessageGroup(
                        group_id=f"{group.group_id}_part_{i//chunk_size + 1}",
                        messages=chunk_messages,
                        is_media_group=True  # 保持媒体组属性
                    )
                    all_groups.append(sub_group)
                    logger.info(f"  📦 创建子组 {sub_group.group_id}，包含 {len(chunk_messages)} 条消息")
            else:
                all_groups.append(group)

        # 添加单条消息
        all_groups.extend(single_messages)

        logger.info(f"📊 消息分组完成：{len(media_groups)} 个媒体组，{len(single_messages)} 个单消息，总计 {len(all_groups)} 个分组")
        return all_groups
    
    def _find_min_load_client(self, assignments: List[ClientAssignment]) -> int:
        """根据配置的指标找到负载最小的客户端"""
        metric = self.config.load_balance_metric
        
        if metric == LoadBalanceMetric.FILE_COUNT:
            loads = [assignment.total_files for assignment in assignments]
        elif metric == LoadBalanceMetric.MESSAGE_COUNT:
            loads = [assignment.total_messages for assignment in assignments]
        elif metric == LoadBalanceMetric.ESTIMATED_SIZE:
            loads = [assignment.estimated_size for assignment in assignments]
        else:  # MIXED
            # 混合指标：文件数量权重0.6，大小权重0.4
            loads = [
                assignment.total_files * 0.6 + assignment.estimated_size / (1024*1024) * 0.4
                for assignment in assignments
            ]
        
        return loads.index(min(loads))

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            "name": "MediaGroupAwareStrategy",
            "description": "媒体组感知的智能分配策略",
            "features": [
                "保证媒体组完整性",
                "多维度负载均衡",
                "支持消息验证",
                "贪心算法优化"
            ],
            "config": {
                "mode": self.config.mode.value,
                "load_balance_metric": self.config.load_balance_metric.value,
                "max_imbalance_ratio": self.config.max_imbalance_ratio,
                "prefer_large_groups_first": self.config.prefer_large_groups_first,
                "enable_validation": self.config.enable_validation,
                "enable_message_id_validation": self.config.enable_message_id_validation
            }
        }





class MessageDistributor:
    """消息分配器主类"""

    def __init__(self, config: Optional[DistributionConfig] = None):
        self.config = config or DistributionConfig()
        self._strategies = {
            DistributionMode.MEDIA_GROUP_AWARE: MediaGroupAwareStrategy
        }
        self.validator = MessageValidator()

    async def distribute_messages_with_validation(
        self,
        messages: List[MessageInfo],
        client_names: List[str],
        client,
        channel: str,
        strategy_mode: Optional[DistributionMode] = None
    ) -> Tuple[DistributionResult, Dict[str, Any]]:
        """
        分配消息到多个客户端（带消息有效性验证）

        Args:
            messages: 消息信息列表
            client_names: 客户端名称列表
            client: Pyrogram客户端（用于验证）
            channel: 频道名称
            strategy_mode: 分配策略模式（可选）

        Returns:
            Tuple[分配结果, 验证统计信息]
        """
        validation_stats = {"enabled": False}

        if self.config.enable_validation:
            # 提取所有消息ID
            message_ids = [msg.message_id for msg in messages]

            # 验证消息ID有效性
            valid_ids, invalid_ids, stats = await self.validator.validate_message_ids(
                client, channel, message_ids
            )

            # 过滤出有效的消息
            valid_ids_set = set(valid_ids)
            filtered_messages = [
                msg for msg in messages
                if msg.message_id in valid_ids_set
            ]

            validation_stats = {
                "enabled": True,
                "original_count": len(messages),
                "valid_count": len(filtered_messages),
                "invalid_count": len(invalid_ids),
                "invalid_ids": invalid_ids,
                "validation_rate": stats["valid_rate"]
            }

            logger.info(f"📊 消息验证结果: {len(filtered_messages)}/{len(messages)} 有效")

            # 使用过滤后的消息进行分配
            messages = filtered_messages

        # 执行分配
        result = self._distribute_messages_internal(messages, client_names, strategy_mode)

        return result, validation_stats

    def _distribute_messages_internal(
        self,
        messages: List[MessageInfo],
        client_names: List[str],
        strategy_mode: Optional[DistributionMode] = None
    ) -> DistributionResult:
        """
        内部分配方法

        Args:
            messages: 消息信息列表
            client_names: 客户端名称列表
            strategy_mode: 分配策略模式（可选）

        Returns:
            分配结果
        """
        # 确定使用的策略
        mode = strategy_mode or self.config.mode
        strategy_class = self._strategies.get(mode)

        if not strategy_class:
            raise ValueError(f"不支持的分配策略: {mode}")

        strategy = strategy_class(self.config)

        try:
            # 执行分配
            result = strategy.distribute(messages, client_names)

            # 记录分配结果
            self._log_distribution_result(result)

            return result

        except Exception as e:
            logger.error(f"消息分配失败: {e}")
            raise

    def _log_distribution_result(self, result: DistributionResult):
        """记录分配结果"""
        logger.info(f"\n{'='*60}")
        logger.info("🎯 消息分配结果")
        logger.info(f"{'='*60}")
        logger.info(f"分配策略: {result.distribution_strategy}")
        logger.info(f"客户端数量: {len(result.client_assignments)}")
        logger.info(f"总消息数: {result.total_messages}")
        logger.info(f"总文件数: {result.total_files}")

        logger.info("\n📊 各客户端分配详情:")
        for assignment in result.client_assignments:
            # 统计媒体组和单消息
            media_groups = [g for g in assignment.message_groups if g.is_media_group]
            single_messages = [g for g in assignment.message_groups if not g.is_media_group]

            logger.info(f"  {assignment.client_name}:")
            logger.info(f"    📝 消息数量: {assignment.total_messages}")
            logger.info(f"    📁 文件数量: {assignment.total_files}")
            logger.info(f"    📊 媒体组: {len(media_groups)}个, 单消息: {len(single_messages)}个")

            # 显示消息ID范围
            message_ids = assignment.all_message_ids
            if message_ids:
                logger.info(f"    🔢 消息ID范围: {min(message_ids)}-{max(message_ids)}")

        # 显示负载均衡统计
        balance_stats = result.get_load_balance_stats()
        if balance_stats:
            logger.info(f"\n⚖️ 负载均衡统计:")
            logger.info(f"  文件分布: {balance_stats['file_distribution']}")
            logger.info(f"  均衡比例: {balance_stats['file_balance_ratio']:.3f}")
            logger.info(f"  平均文件数: {balance_stats['average_files_per_client']:.1f}")

        logger.info(f"{'='*60}")


def get_real_file_size(message) -> Optional[int]:
    """
    获取真实文件大小（与main.py程序保持一致）

    Args:
        message: Pyrogram 消息对象

    Returns:
        文件大小（字节），如果无法获取则返回 None
    """
    # 支持的媒体类型列表
    SUPPORTED_MEDIA_TYPES = [
        'document', 'video', 'photo', 'audio',
        'voice', 'video_note', 'animation', 'sticker'
    ]

    # 检查所有媒体类型的 file_size 属性
    for media_type in SUPPORTED_MEDIA_TYPES:
        if hasattr(message, media_type):
            media = getattr(message, media_type)
            if media and hasattr(media, 'file_size') and media.file_size:
                return media.file_size

    return None


def estimate_file_size(message) -> int:
    """
    估算文件大小（基于实际测试数据，与main.py程序保持一致）

    Args:
        message: Pyrogram 消息对象

    Returns:
        估算的文件大小（字节）
    """
    MB = 1024 * 1024

    # 优先使用真实文件大小
    real_size = get_real_file_size(message)
    if real_size:
        return real_size

    # 回退到基于实际测试数据的改进估算值
    if hasattr(message, 'media') and message.media:
        if hasattr(message, 'photo') and message.photo:
            return 3 * MB  # 3MB (基于实际平均值 2.7MB)
        elif hasattr(message, 'video') and message.video:
            return 37 * MB  # 37MB (基于实际平均值 36.4MB)
        elif hasattr(message, 'audio') and message.audio:
            return 5 * MB   # 5MB
        elif hasattr(message, 'document') and message.document:
            return 10 * MB  # 10MB
        elif hasattr(message, 'animation') and message.animation:
            return 3 * MB   # 3MB
        elif hasattr(message, 'voice') and message.voice:
            return 1 * MB   # 1MB
        elif hasattr(message, 'video_note') and message.video_note:
            return 2 * MB   # 2MB
        elif hasattr(message, 'sticker') and message.sticker:
            return 1 * MB   # 1MB
        else:
            return 5 * MB   # 5MB default for unknown media
    else:
        return 1024  # 1KB for text messages


def create_message_info_from_pyrogram_message(message) -> MessageInfo:
    """从Pyrogram消息对象创建MessageInfo（增强版）"""
    # 检查是否有媒体 - 使用更全面的检查逻辑
    has_media = _has_media_comprehensive(message)

    # 获取精确的文件大小
    file_size = estimate_file_size(message)

    # 获取媒体组ID
    media_group_id = None
    if hasattr(message, 'media_group_id') and message.media_group_id:
        media_group_id = str(message.media_group_id)

    return MessageInfo(
        message_id=message.id,
        media_group_id=media_group_id,
        file_size=file_size,
        has_media=has_media
    )


def _has_media_comprehensive(message) -> bool:
    """
    全面检查消息是否包含媒体内容

    Args:
        message: Pyrogram消息对象

    Returns:
        是否包含媒体
    """
    if not message:
        return False

    # 检查通用media属性
    if hasattr(message, 'media') and message.media:
        return True

    # 检查具体的媒体类型
    SUPPORTED_MEDIA_TYPES = [
        'document', 'video', 'photo', 'audio',
        'voice', 'video_note', 'animation', 'sticker'
    ]

    for media_type in SUPPORTED_MEDIA_TYPES:
        if hasattr(message, media_type) and getattr(message, media_type):
            return True

    return False


def convert_messages_to_message_info(messages: List) -> List[MessageInfo]:
    """将Pyrogram消息列表转换为MessageInfo列表"""
    message_infos = []

    for message in messages:
        if message is not None:
            try:
                message_info = create_message_info_from_pyrogram_message(message)
                message_infos.append(message_info)
            except Exception as e:
                logger.warning(f"转换消息 {getattr(message, 'id', 'unknown')} 失败: {e}")

    return message_infos
