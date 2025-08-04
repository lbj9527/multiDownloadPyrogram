"""
模板配置数据模型
支持原格式和自定义模板两种模式
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time

class TemplateMode(Enum):
    """模板模式枚举"""
    ORIGINAL = "original"    # 保持原格式
    CUSTOM = "custom"       # 使用自定义模板

class VariableType(Enum):
    """变量类型枚举"""
    TEXT = "text"           # 文本变量
    MEDIA = "media"         # 媒体变量
    METADATA = "metadata"   # 元数据变量
    COMPUTED = "computed"   # 计算变量

@dataclass
class TemplateVariable:
    """模板变量定义"""
    name: str                           # 变量名
    type: VariableType                  # 变量类型
    description: str = ""               # 变量描述
    default_value: str = ""             # 默认值
    required: bool = False              # 是否必需
    extractor_pattern: Optional[str] = None  # 提取模式(正则表达式)

@dataclass
class TemplateConfig:
    """模板配置"""
    
    # 基础配置
    template_id: str                    # 模板ID
    name: str                          # 模板名称
    mode: TemplateMode                 # 模板模式
    
    # 模板内容
    content: str = ""                  # 模板内容
    description: str = ""              # 模板描述
    
    # 变量配置
    variables: List[TemplateVariable] = field(default_factory=list)
    variable_values: Dict[str, str] = field(default_factory=dict)
    
    # 格式配置
    format_type: str = "markdown"      # 格式类型: markdown, html, plain
    enable_preview: bool = True        # 启用预览
    
    # 处理选项
    preserve_media_group: bool = True   # 保持媒体组
    auto_extract_variables: bool = True # 自动提取变量
    
    # 元数据
    created_time: Optional[float] = None
    updated_time: Optional[float] = None
    usage_count: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.mode, str):
            self.mode = TemplateMode(self.mode)
        
        # 设置时间戳
        current_time = time.time()
        if self.created_time is None:
            self.created_time = current_time
        self.updated_time = current_time
        
        # 验证模板内容
        if self.mode == TemplateMode.CUSTOM and not self.content:
            raise ValueError("Custom template mode requires content")
    
    def get_variable_by_name(self, name: str) -> Optional[TemplateVariable]:
        """根据名称获取变量"""
        for var in self.variables:
            if var.name == name:
                return var
        return None
    
    def add_variable(self, variable: TemplateVariable) -> None:
        """添加变量"""
        # 检查是否已存在
        existing = self.get_variable_by_name(variable.name)
        if existing:
            # 更新现有变量
            idx = self.variables.index(existing)
            self.variables[idx] = variable
        else:
            self.variables.append(variable)
        
        self.updated_time = time.time()
    
    def remove_variable(self, name: str) -> bool:
        """移除变量"""
        variable = self.get_variable_by_name(name)
        if variable:
            self.variables.remove(variable)
            self.variable_values.pop(name, None)
            self.updated_time = time.time()
            return True
        return False
    
    def set_variable_value(self, name: str, value: str) -> None:
        """设置变量值"""
        self.variable_values[name] = value
        self.updated_time = time.time()
    
    def get_variable_value(self, name: str) -> str:
        """获取变量值"""
        if name in self.variable_values:
            return self.variable_values[name]
        
        # 返回默认值
        variable = self.get_variable_by_name(name)
        if variable:
            return variable.default_value
        
        return ""
    
    def get_required_variables(self) -> List[TemplateVariable]:
        """获取必需变量列表"""
        return [var for var in self.variables if var.required]
    
    def validate_variables(self) -> List[str]:
        """验证变量，返回错误列表"""
        errors = []
        
        for var in self.get_required_variables():
            value = self.get_variable_value(var.name)
            if not value:
                errors.append(f"Required variable '{var.name}' is missing")
        
        return errors
    
    def increment_usage(self) -> None:
        """增加使用次数"""
        self.usage_count += 1
        self.updated_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "mode": self.mode.value,
            "content": self.content,
            "description": self.description,
            "variables": [
                {
                    "name": var.name,
                    "type": var.type.value,
                    "description": var.description,
                    "default_value": var.default_value,
                    "required": var.required,
                    "extractor_pattern": var.extractor_pattern
                }
                for var in self.variables
            ],
            "variable_values": self.variable_values,
            "format_type": self.format_type,
            "enable_preview": self.enable_preview,
            "preserve_media_group": self.preserve_media_group,
            "auto_extract_variables": self.auto_extract_variables,
            "created_time": self.created_time,
            "updated_time": self.updated_time,
            "usage_count": self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateConfig':
        """从字典创建实例"""
        # 处理变量列表
        variables_data = data.pop("variables", [])
        variables = []
        for var_data in variables_data:
            var_data["type"] = VariableType(var_data["type"])
            variables.append(TemplateVariable(**var_data))
        
        # 创建实例
        config = cls(**data)
        config.variables = variables
        return config

# 预定义模板变量
BUILTIN_VARIABLES = [
    TemplateVariable(
        name="original_text",
        type=VariableType.TEXT,
        description="原始消息文本",
        default_value=""
    ),
    TemplateVariable(
        name="original_caption",
        type=VariableType.TEXT,
        description="原始媒体说明",
        default_value=""
    ),
    TemplateVariable(
        name="file_name",
        type=VariableType.METADATA,
        description="文件名",
        default_value=""
    ),
    TemplateVariable(
        name="file_size",
        type=VariableType.METADATA,
        description="文件大小",
        default_value=""
    ),
    TemplateVariable(
        name="file_size_formatted",
        type=VariableType.METADATA,
        description="格式化的文件大小",
        default_value=""
    ),
    TemplateVariable(
        name="source_channel",
        type=VariableType.METADATA,
        description="来源频道",
        default_value=""
    ),
    TemplateVariable(
        name="message_id",
        type=VariableType.METADATA,
        description="消息ID",
        default_value=""
    ),
    TemplateVariable(
        name="timestamp",
        type=VariableType.COMPUTED,
        description="当前时间戳",
        default_value=""
    ),
    TemplateVariable(
        name="date",
        type=VariableType.COMPUTED,
        description="当前日期",
        default_value=""
    ),
    TemplateVariable(
        name="time",
        type=VariableType.COMPUTED,
        description="当前时间",
        default_value=""
    )
]

# 默认模板配置
DEFAULT_TEMPLATE = TemplateConfig(
    template_id="default",
    name="默认模板",
    mode=TemplateMode.ORIGINAL,
    content="{original_text}{original_caption}",
    description="保持原始格式的默认模板"
)

# 示例自定义模板
EXAMPLE_CUSTOM_TEMPLATE = TemplateConfig(
    template_id="custom_example",
    name="示例自定义模板",
    mode=TemplateMode.CUSTOM,
    content="📸 来自 {source_channel} 的内容\n\n{original_text}\n\n📁 文件: {file_name} ({file_size_formatted})\n🕒 转发时间: {date} {time}",
    description="包含来源信息和时间戳的自定义模板"
)
