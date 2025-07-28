"""
消息组相关数据模型
用于媒体组感知的任务分配
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入常量
from config.constants import MB, SUPPORTED_MEDIA_TYPES


@dataclass
class MessageGroup:
    """消息组模型"""
    group_id: str
    messages: List[Any] = field(default_factory=list)
    group_type: str = "media_group"  # media_group, single_message
    total_files: int = 0
    estimated_size: int = 0  # 估算大小（字节）
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: Any):
        """添加消息到组"""
        self.messages.append(message)
        self.total_files = len(self.messages)
        self._update_estimated_size(message)
    
    def _get_real_file_size(self, message: Any) -> Optional[int]:
        """获取真实文件大小

        Args:
            message: Pyrogram 消息对象

        Returns:
            文件大小（字节），如果无法获取则返回 None
        """
        # 检查所有媒体类型的 file_size 属性
        for media_type in SUPPORTED_MEDIA_TYPES:
            if hasattr(message, media_type):
                media = getattr(message, media_type)
                if media and hasattr(media, 'file_size') and media.file_size:
                    return media.file_size

        return None

    def _update_estimated_size(self, message: Any):
        """更新估算大小（改进版）

        优先使用真实文件大小，如果不可用则使用基于实际数据的改进估算值
        """
        # 优先尝试获取真实文件大小
        real_size = self._get_real_file_size(message)
        if real_size:
            self.estimated_size += real_size
            return

        # 回退到基于实际测试数据的改进估算值
        if hasattr(message, 'media') and message.media:
            if hasattr(message, 'photo') and message.photo:
                self.estimated_size += 3 * MB  # 3MB (基于实际平均值 2.7MB)
            elif hasattr(message, 'video') and message.video:
                self.estimated_size += 37 * MB  # 37MB (基于实际平均值 36.4MB)
            elif hasattr(message, 'audio') and message.audio:
                self.estimated_size += 5 * MB   # 5MB
            elif hasattr(message, 'document') and message.document:
                self.estimated_size += 10 * MB  # 10MB
            elif hasattr(message, 'animation') and message.animation:
                self.estimated_size += 3 * MB   # 3MB
            elif hasattr(message, 'voice') and message.voice:
                self.estimated_size += 1 * MB   # 1MB
            elif hasattr(message, 'video_note') and message.video_note:
                self.estimated_size += 2 * MB   # 2MB
            else:
                self.estimated_size += 5 * MB   # 5MB default for unknown media
        else:
            self.estimated_size += 1024  # 1KB for text messages
    
    @property
    def is_media_group(self) -> bool:
        """是否为媒体组"""
        return self.group_type == "media_group"
    
    @property
    def message_ids(self) -> List[int]:
        """获取所有消息ID"""
        return [msg.id for msg in self.messages if msg]
    
    def __len__(self) -> int:
        """返回消息数量"""
        return len(self.messages)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"MessageGroup(id={self.group_id}, type={self.group_type}, files={self.total_files})"


@dataclass
class MessageGroupCollection:
    """消息组集合"""
    media_groups: Dict[str, MessageGroup] = field(default_factory=dict)
    single_messages: List[Any] = field(default_factory=list)
    total_messages: int = 0
    total_media_groups: int = 0
    
    def add_media_group(self, group: MessageGroup):
        """添加媒体组"""
        self.media_groups[group.group_id] = group
        self.total_media_groups = len(self.media_groups)
        self._update_total_messages()
    
    def add_single_message(self, message: Any):
        """添加单条消息"""
        self.single_messages.append(message)
        self._update_total_messages()
    
    def _update_total_messages(self):
        """更新总消息数"""
        media_group_messages = sum(len(group) for group in self.media_groups.values())
        self.total_messages = media_group_messages + len(self.single_messages)
    
    def get_all_groups(self) -> List[MessageGroup]:
        """获取所有组（包括单消息组）"""
        all_groups = list(self.media_groups.values())
        
        # 将单消息转换为MessageGroup
        for i, message in enumerate(self.single_messages):
            single_group = MessageGroup(
                group_id=f"single_{message.id if message else i}",
                group_type="single_message"
            )
            if message:
                single_group.add_message(message)
            all_groups.append(single_group)
        
        return all_groups
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_files = sum(group.total_files for group in self.media_groups.values())
        total_files += len(self.single_messages)
        
        total_estimated_size = sum(group.estimated_size for group in self.media_groups.values())
        # 单消息估算1KB
        total_estimated_size += len(self.single_messages) * 1024
        
        return {
            "total_messages": self.total_messages,
            "total_files": total_files,
            "media_groups_count": self.total_media_groups,
            "single_messages_count": len(self.single_messages),
            "estimated_total_size": total_estimated_size,
            "average_group_size": total_files / max(self.total_media_groups, 1)
        }


@dataclass
class ClientTaskAssignment:
    """客户端任务分配"""
    client_name: str
    message_groups: List[MessageGroup] = field(default_factory=list)
    total_messages: int = 0
    total_files: int = 0
    estimated_size: int = 0
    
    def add_group(self, group: MessageGroup):
        """添加消息组"""
        self.message_groups.append(group)
        self.total_messages += len(group)
        self.total_files += group.total_files
        self.estimated_size += group.estimated_size
    
    def get_all_messages(self) -> List[Any]:
        """获取所有消息"""
        all_messages = []
        for group in self.message_groups:
            all_messages.extend(group.messages)
        return all_messages
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "client_name": self.client_name,
            "total_messages": self.total_messages,
            "total_files": self.total_files,
            "estimated_size": self.estimated_size,
            "groups_count": len(self.message_groups),
            "media_groups_count": len([g for g in self.message_groups if g.is_media_group]),
            "single_messages_count": len([g for g in self.message_groups if not g.is_media_group])
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ClientTask({self.client_name}: {self.total_files} files, {len(self.message_groups)} groups)"


@dataclass
class TaskDistributionResult:
    """任务分配结果"""
    client_assignments: List[ClientTaskAssignment] = field(default_factory=list)
    distribution_strategy: str = ""
    total_messages: int = 0
    total_files: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_assignment(self, assignment: ClientTaskAssignment):
        """添加客户端分配"""
        self.client_assignments.append(assignment)
        self.total_messages += assignment.total_messages
        self.total_files += assignment.total_files
    
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
            "average_files_per_client": sum(file_counts) / len(file_counts),
            "average_size_per_client": sum(size_estimates) / len(size_estimates)
        }
    
    def get_summary(self) -> str:
        """获取分配摘要"""
        stats = self.get_load_balance_stats()
        summary_lines = [
            f"任务分配摘要 (策略: {self.distribution_strategy})",
            f"总计: {self.total_files} 个文件, {len(self.client_assignments)} 个客户端",
            f"负载均衡比例: {stats.get('file_balance_ratio', 0):.2f}"
        ]
        
        for assignment in self.client_assignments:
            summary_lines.append(f"  {assignment}")
        
        return "\n".join(summary_lines)
