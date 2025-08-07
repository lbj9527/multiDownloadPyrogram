"""
工作流配置数据模型
定义本地下载和转发工作流的配置结构
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import time
from .template_config import TemplateConfig

class WorkflowType(Enum):
    """工作流类型枚举"""
    LOCAL_DOWNLOAD = "local_download"   # 本地下载
    FORWARD = "forward"                 # 转发上传

class PriorityLevel(Enum):
    """优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class WorkflowConfig:
    """工作流配置"""
    
    # 基础配置
    workflow_id: str = ""
    workflow_type: WorkflowType = WorkflowType.LOCAL_DOWNLOAD
    name: str = ""
    description: str = ""
    
    # 源配置
    source_channel: str = ""
    message_range: Tuple[int, int] = (1, 100)
    
    # 本地下载配置
    # 注意：下载目录由 config/settings.py 中的 DownloadConfig.download_dir 配置
    create_subfolder: bool = True       # 是否创建子文件夹
    subfolder_pattern: str = "{channel}_{date}"  # 子文件夹命名模式

    # 转发配置
    target_channels: List[str] = field(default_factory=list)
    template_config: Optional[TemplateConfig] = None

    # 分阶段上传配置（现在是默认行为）
    staged_batch_size: int = 10           # 媒体组大小
    cleanup_after_success: bool = True    # 成功后清理临时文件
    cleanup_after_failure: bool = False   # 失败后清理临时文件

    # 执行配置
    # 注意：并发数由 config/settings.py 中的 TelegramConfig.session_names 数量决定
    batch_size: int = 10               # 批处理大小
    delay_between_batches: float = 1.0  # 批次间延迟（秒）
    
    # 过滤配置
    file_types: List[str] = field(default_factory=list)  # 文件类型过滤
    min_file_size: int = 0             # 最小文件大小（字节）
    max_file_size: int = 0             # 最大文件大小（字节，0表示无限制）
    skip_duplicates: bool = True       # 跳过重复文件
    
    # 重试配置
    max_retries: int = 3               # 最大重试次数
    retry_delay: float = 5.0           # 重试延迟（秒）
    
    # 监控配置
    enable_monitoring: bool = True     # 启用监控
    enable_progress_callback: bool = True  # 启用进度回调
    log_level: str = "INFO"           # 日志级别
    
    # 优先级和调度
    priority: PriorityLevel = PriorityLevel.NORMAL
    scheduled_time: Optional[float] = None  # 计划执行时间
    
    # 额外配置
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间信息
    created_time: Optional[float] = None
    updated_time: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.workflow_type, str):
            self.workflow_type = WorkflowType(self.workflow_type)
        
        if isinstance(self.priority, str):
            self.priority = PriorityLevel(self.priority)
        
        # 设置时间戳
        current_time = time.time()
        if self.created_time is None:
            self.created_time = current_time
        self.updated_time = current_time
        
        # 生成工作流ID
        if not self.workflow_id:
            self.workflow_id = f"{self.workflow_type.value}_{int(current_time)}"
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置"""
        if not self.source_channel:
            raise ValueError("源频道不能为空")
        
        if self.workflow_type == WorkflowType.FORWARD:
            if not self.target_channels:
                raise ValueError("转发模式必须指定目标频道")
        
        if self.message_range[0] > self.message_range[1]:
            raise ValueError("消息范围起始值不能大于结束值")
        
        # 注意：并发数由 config/settings.py 中的 TelegramConfig.session_names 数量决定
    
    def is_local_download(self) -> bool:
        """是否为本地下载工作流"""
        return self.workflow_type == WorkflowType.LOCAL_DOWNLOAD
    
    def is_forward(self) -> bool:
        """是否为转发工作流"""
        return self.workflow_type == WorkflowType.FORWARD
    
    def get_message_count(self) -> int:
        """获取消息数量"""
        return self.message_range[1] - self.message_range[0] + 1
    
    def should_filter_file_type(self, file_name: str) -> bool:
        """
        是否应该过滤文件类型
        
        Args:
            file_name: 文件名
            
        Returns:
            bool: 是否过滤（True表示跳过）
        """
        if not self.file_types:
            return False  # 没有设置过滤器，不过滤
        
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        return file_ext not in [ft.lower().lstrip('.') for ft in self.file_types]
    
    def should_filter_file_size(self, file_size: int) -> bool:
        """
        是否应该过滤文件大小
        
        Args:
            file_size: 文件大小（字节）
            
        Returns:
            bool: 是否过滤（True表示跳过）
        """
        if self.min_file_size > 0 and file_size < self.min_file_size:
            return True
        
        if self.max_file_size > 0 and file_size > self.max_file_size:
            return True
        
        return False
    
    def get_subfolder_name(self) -> str:
        """
        获取子文件夹名称
        
        Returns:
            str: 子文件夹名称
        """
        if not self.create_subfolder:
            return ""
        
        from datetime import datetime
        
        # 替换模式变量
        pattern = self.subfolder_pattern
        replacements = {
            "{channel}": self.source_channel.lstrip('@'),
            "{date}": datetime.now().strftime("%Y-%m-%d"),
            "{time}": datetime.now().strftime("%H-%M-%S"),
            "{datetime}": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "{workflow_id}": self.workflow_id,
            "{start_msg}": str(self.message_range[0]),
            "{end_msg}": str(self.message_range[1])
        }
        
        for placeholder, value in replacements.items():
            pattern = pattern.replace(placeholder, value)
        
        return pattern
    
    def is_scheduled(self) -> bool:
        """是否为计划任务"""
        return self.scheduled_time is not None
    
    def is_ready_to_execute(self) -> bool:
        """是否准备好执行"""
        if not self.is_scheduled():
            return True
        
        return time.time() >= self.scheduled_time
    
    def get_estimated_duration(self) -> float:
        """
        估算执行时间
        
        Returns:
            float: 预计执行时间（秒）
        """
        message_count = self.get_message_count()
        
        # 基础时间估算（每条消息平均处理时间）
        if self.is_local_download():
            base_time_per_message = 2.0  # 本地下载较快
        else:
            base_time_per_message = 5.0  # 转发需要更多时间
        
        base_time = message_count * base_time_per_message
        
        # 考虑并发因素（使用默认3个客户端）
        max_concurrent = 3  # 由 config/settings.py 中的 session_names 数量决定
        concurrent_factor = min(max_concurrent, message_count) / message_count
        estimated_time = base_time * concurrent_factor
        
        # 考虑批次延迟
        batch_count = (message_count + self.batch_size - 1) // self.batch_size
        batch_delay_time = (batch_count - 1) * self.delay_between_batches
        
        return estimated_time + batch_delay_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "name": self.name,
            "description": self.description,
            "source_channel": self.source_channel,
            "message_range": list(self.message_range),
            "create_subfolder": self.create_subfolder,
            "subfolder_pattern": self.subfolder_pattern,
            "target_channels": self.target_channels,
            "batch_size": self.batch_size,
            "delay_between_batches": self.delay_between_batches,
            "file_types": self.file_types,
            "min_file_size": self.min_file_size,
            "max_file_size": self.max_file_size,
            "skip_duplicates": self.skip_duplicates,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "enable_monitoring": self.enable_monitoring,
            "enable_progress_callback": self.enable_progress_callback,
            "log_level": self.log_level,
            "priority": self.priority.value,
            "scheduled_time": self.scheduled_time,
            "metadata": self.metadata,
            "created_time": self.created_time,
            "updated_time": self.updated_time,
            "message_count": self.get_message_count(),
            "estimated_duration": self.get_estimated_duration(),
            "is_scheduled": self.is_scheduled(),
            "is_ready": self.is_ready_to_execute()
        }
        
        # 添加模板配置
        if self.template_config:
            result["template_config"] = self.template_config.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowConfig':
        """从字典创建实例"""
        # 处理模板配置
        template_data = data.pop("template_config", None)
        template_config = None
        if template_data:
            from .template_config import TemplateConfig
            template_config = TemplateConfig.from_dict(template_data)
        
        # 移除计算字段
        computed_fields = [
            "message_count", "estimated_duration", "is_scheduled", "is_ready"
        ]
        for field in computed_fields:
            data.pop(field, None)
        
        # 转换消息范围
        if "message_range" in data and isinstance(data["message_range"], list):
            data["message_range"] = tuple(data["message_range"])
        
        # 创建实例
        config = cls(**data)
        config.template_config = template_config
        return config
    
    def clone(self, **overrides) -> 'WorkflowConfig':
        """
        克隆配置
        
        Args:
            **overrides: 要覆盖的字段
            
        Returns:
            WorkflowConfig: 新的配置实例
        """
        data = self.to_dict()
        data.update(overrides)
        
        # 生成新的ID
        data["workflow_id"] = f"{self.workflow_type.value}_{int(time.time())}"
        
        return self.from_dict(data)
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"WorkflowConfig(ID={self.workflow_id}, "
                f"类型={self.workflow_type.value}, "
                f"源={self.source_channel}, "
                f"消息={self.message_range[0]}-{self.message_range[1]})")
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"WorkflowConfig(workflow_id='{self.workflow_id}', "
                f"workflow_type='{self.workflow_type.value}', "
                f"source_channel='{self.source_channel}', "
                f"message_range={self.message_range})")
