"""
消息组相关数据模型
用于媒体组感知的任务分配
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# 移除未使用的常量定义


@dataclass
class MessageGroup:
    """消息组模型"""
    group_id: str
    messages: List[Any] = field(default_factory=list)
    group_type: str = "media_group"  # media_group, single_message
    total_files: int = 0
    estimated_size: int = 0  # 真实文件大小（字节）
    
    def add_message(self, message: Any):
        """添加消息到组"""
        self.messages.append(message)
        self.total_files = len(self.messages)
        # 累加真实文件大小
        self.estimated_size += self._get_message_file_size(message)
    @property
    def is_media_group(self) -> bool:
        """是否为媒体组"""
        return self.group_type == "media_group"
    

    def __len__(self) -> int:
        """返回消息数量"""
        return len(self.messages)
    
    def _get_message_file_size(self, message: Any) -> int:
        """获取消息的真实文件大小（字节）"""
        if not message:
            return 0

        # 检查所有可能的媒体类型
        media_types = ['document', 'video', 'photo', 'audio', 'voice',
                      'video_note', 'animation', 'sticker']

        for media_type in media_types:
            media = getattr(message, media_type, None)
            if media and hasattr(media, 'file_size') and media.file_size:
                return media.file_size

        return 0




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

        # 计算总的真实文件大小
        total_size = sum(group.estimated_size for group in self.media_groups.values())

        return {
            "total_messages": self.total_messages,
            "total_files": total_files,
            "media_groups_count": self.total_media_groups,
            "single_messages_count": len(self.single_messages),
            "estimated_total_size": total_size,
            "average_group_size": total_files / max(self.total_media_groups, 1)
        }


@dataclass
class ClientTaskAssignment:
    """客户端任务分配"""
    client_name: str
    message_groups: List[MessageGroup] = field(default_factory=list)
    total_messages: int = 0
    total_files: int = 0
    estimated_size: int = 0  # 真实文件大小总和（字节）
    
    def add_group(self, group: MessageGroup):
        """添加消息组"""
        self.message_groups.append(group)
        self.total_messages += len(group)
        self.total_files += group.total_files
        # 累加真实文件大小
        self.estimated_size += group.estimated_size
    
    def get_all_messages(self) -> List[Any]:
        """获取所有消息"""
        all_messages = []
        for group in self.message_groups:
            all_messages.extend(group.messages)
        return all_messages
    




@dataclass
class TaskDistributionResult:
    """任务分配结果"""
    client_assignments: List[ClientTaskAssignment] = field(default_factory=list)
    distribution_strategy: str = ""
    total_messages: int = 0
    total_files: int = 0
    
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
        real_sizes = [assignment.estimated_size for assignment in self.client_assignments]
        
        return {
            "clients_count": len(self.client_assignments),
            "file_distribution": file_counts,
            "size_distribution": real_sizes,
            "file_balance_ratio": min(file_counts) / max(file_counts) if max(file_counts) > 0 else 1.0,
            "size_balance_ratio": min(real_sizes) / max(real_sizes) if max(real_sizes) > 0 else 1.0,
            "average_files_per_client": sum(file_counts) / len(file_counts),
            "average_size_per_client": sum(real_sizes) / len(real_sizes)
        }
    

