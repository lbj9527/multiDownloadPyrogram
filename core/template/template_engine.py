"""
模板引擎核心
负责模板解析、变量替换和内容生成
"""
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from models.template_config import TemplateConfig, TemplateMode, BUILTIN_VARIABLES
from models.download_result import DownloadResult
from utils.logging_utils import LoggerMixin


class TemplateEngine(LoggerMixin):
    """模板引擎核心类"""
    
    # 变量匹配正则表达式
    VARIABLE_PATTERN = re.compile(r'\{([^}]+)\}')
    
    def __init__(self):
        """初始化模板引擎"""
        self.builtin_variables = {var.name: var for var in BUILTIN_VARIABLES}
    
    def render(self, template_config: TemplateConfig, 
               download_result: DownloadResult,
               extra_variables: Dict[str, str] = None) -> str:
        """
        渲染模板
        
        Args:
            template_config: 模板配置
            download_result: 下载结果
            extra_variables: 额外变量
            
        Returns:
            str: 渲染后的内容
        """
        try:
            # 检查模板模式
            if template_config.mode == TemplateMode.ORIGINAL:
                return self._render_original(download_result)
            elif template_config.mode == TemplateMode.CUSTOM:
                return self._render_custom(template_config, download_result, extra_variables)
            else:
                raise ValueError(f"Unsupported template mode: {template_config.mode}")
                
        except Exception as e:
            self.log_error(f"模板渲染失败: {e}")
            # 返回原始内容作为回退
            return self._render_original(download_result)
    
    def _render_original(self, download_result: DownloadResult) -> str:
        """
        渲染原格式模板
        
        Args:
            download_result: 下载结果
            
        Returns:
            str: 原始内容
        """
        content_parts = []
        
        # 添加原始文本
        if download_result.original_text:
            content_parts.append(download_result.original_text)
        
        # 添加原始说明
        if download_result.original_caption:
            content_parts.append(download_result.original_caption)
        
        return "\n".join(content_parts) if content_parts else ""
    
    def _render_custom(self, template_config: TemplateConfig,
                      download_result: DownloadResult,
                      extra_variables: Dict[str, str] = None) -> str:
        """
        渲染自定义模板
        
        Args:
            template_config: 模板配置
            download_result: 下载结果
            extra_variables: 额外变量
            
        Returns:
            str: 渲染后的内容
        """
        # 构建变量字典
        variables = self._build_variables(template_config, download_result, extra_variables)
        
        # 替换模板中的变量
        content = template_config.content

        # 处理转义字符（将 \n 转换为真正的换行符）
        content = self._process_escape_sequences(content)

        # 使用正则表达式替换变量
        def replace_variable(match):
            var_name = match.group(1).strip()
            return variables.get(var_name, f"{{{var_name}}}")  # 未找到变量时保持原样

        rendered_content = self.VARIABLE_PATTERN.sub(replace_variable, content)

        self.log_info(f"模板渲染完成，替换了 {len(self.extract_variables(content))} 个变量")
        return rendered_content
    
    def _build_variables(self, template_config: TemplateConfig,
                        download_result: DownloadResult,
                        extra_variables: Dict[str, str] = None) -> Dict[str, str]:
        """
        构建变量字典
        
        Args:
            template_config: 模板配置
            download_result: 下载结果
            extra_variables: 额外变量
            
        Returns:
            Dict[str, str]: 变量字典
        """
        variables = {}
        
        # 1. 从下载结果提取基础变量
        variables.update({
            "original_text": download_result.original_text or "",
            "original_caption": download_result.original_caption or "",
            "file_name": download_result.file_name or "",
            "file_size": str(download_result.file_size),
            "file_size_formatted": download_result.get_size_formatted(),
            "message_id": str(download_result.message_id),
            "client_name": download_result.client_name or ""
        })
        
        # 2. 添加计算变量
        now = datetime.now()
        variables.update({
            "timestamp": str(int(time.time())),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. 添加模板配置中的变量值
        variables.update(template_config.variable_values)
        
        # 4. 添加额外变量
        if extra_variables:
            variables.update(extra_variables)
        
        return variables

    def _process_escape_sequences(self, content: str) -> str:
        """
        处理模板中的转义字符

        Args:
            content: 原始模板内容

        Returns:
            str: 处理转义字符后的内容
        """
        # 处理常见的转义字符
        escape_sequences = {
            '\\n': '\n',    # 换行符
            '\\t': '\t',    # 制表符
            '\\r': '\r',    # 回车符
            '\\\\': '\\',   # 反斜杠
        }

        processed_content = content
        for escape_seq, actual_char in escape_sequences.items():
            processed_content = processed_content.replace(escape_seq, actual_char)

        return processed_content

    def extract_variables(self, template_content: str) -> Set[str]:
        """
        从模板内容中提取变量名
        
        Args:
            template_content: 模板内容
            
        Returns:
            Set[str]: 变量名集合
        """
        matches = self.VARIABLE_PATTERN.findall(template_content)
        return {match.strip() for match in matches}
    
    def validate_template(self, template_config: TemplateConfig) -> List[str]:
        """
        验证模板配置
        
        Args:
            template_config: 模板配置
            
        Returns:
            List[str]: 错误列表
        """
        errors = []
        
        # 验证基础配置
        if not template_config.template_id:
            errors.append("Template ID is required")
        
        if not template_config.name:
            errors.append("Template name is required")
        
        # 验证自定义模板内容
        if template_config.mode == TemplateMode.CUSTOM:
            if not template_config.content:
                errors.append("Custom template content is required")
            else:
                # 检查模板中的变量
                template_vars = self.extract_variables(template_config.content)
                unknown_vars = template_vars - set(self.builtin_variables.keys())
                
                # 检查是否有未定义的变量
                for var_name in unknown_vars:
                    if not template_config.get_variable_by_name(var_name):
                        errors.append(f"Unknown variable '{var_name}' in template")
        
        # 验证必需变量
        variable_errors = template_config.validate_variables()
        errors.extend(variable_errors)
        
        return errors
    
    def preview_template(self, template_config: TemplateConfig,
                        sample_data: Dict[str, str] = None) -> str:
        """
        预览模板效果

        Args:
            template_config: 模板配置
            sample_data: 示例数据

        Returns:
            str: 预览内容
        """
        # 处理空的示例数据
        if sample_data is None:
            sample_data = {}

        # 创建示例下载结果
        sample_download_result = DownloadResult.create_memory_result(
            message_id=12345,
            file_data=b"sample data",
            file_name="sample_file.jpg",
            client_name="preview_client",
            original_text=sample_data.get("original_text", "这是示例消息文本"),
            original_caption=sample_data.get("original_caption", "这是示例图片说明"),
            mime_type="image/jpeg"
        )
        
        # 渲染模板
        return self.render(template_config, sample_download_result, sample_data)
    
    def get_available_variables(self) -> List[Dict[str, str]]:
        """
        获取可用变量列表
        
        Returns:
            List[Dict[str, str]]: 变量信息列表
        """
        variables = []
        
        for var in BUILTIN_VARIABLES:
            variables.append({
                "name": var.name,
                "type": var.type.value,
                "description": var.description,
                "example": self._get_variable_example(var.name)
            })
        
        return variables
    
    def _get_variable_example(self, var_name: str) -> str:
        """
        获取变量示例值
        
        Args:
            var_name: 变量名
            
        Returns:
            str: 示例值
        """
        examples = {
            "original_text": "这是原始消息文本",
            "original_caption": "这是图片说明",
            "file_name": "example_file.jpg",
            "file_size": "1048576",
            "file_size_formatted": "1.0 MB",
            "source_channel": "@example_channel",
            "message_id": "12345",
            "timestamp": str(int(time.time())),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "client_name": "client_1"
        }
        
        return examples.get(var_name, f"示例_{var_name}")
    
    def create_template_from_content(self, template_id: str, name: str, 
                                   content: str, description: str = "") -> TemplateConfig:
        """
        从内容创建模板配置
        
        Args:
            template_id: 模板ID
            name: 模板名称
            content: 模板内容
            description: 模板描述
            
        Returns:
            TemplateConfig: 模板配置
        """
        # 提取模板中的变量
        template_vars = self.extract_variables(content)
        
        # 创建模板配置
        template_config = TemplateConfig(
            template_id=template_id,
            name=name,
            mode=TemplateMode.CUSTOM,
            content=content,
            description=description
        )
        
        # 添加模板中使用的变量
        for var_name in template_vars:
            if var_name in self.builtin_variables:
                template_config.add_variable(self.builtin_variables[var_name])
        
        return template_config
