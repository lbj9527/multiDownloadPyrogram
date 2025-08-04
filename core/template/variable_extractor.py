"""
变量提取器
从消息内容中提取自定义变量
"""
import re
from typing import Dict, List, Optional, Any
from models.download_result import DownloadResult
from models.template_config import TemplateVariable, VariableType
from utils.logging_utils import LoggerMixin


class VariableExtractor(LoggerMixin):
    """变量提取器"""
    
    def __init__(self):
        """初始化变量提取器"""
        # 预定义的提取模式
        self.predefined_patterns = {
            "hashtag": r"#(\w+)",           # 提取话题标签
            "mention": r"@(\w+)",           # 提取用户提及
            "url": r"https?://[^\s]+",      # 提取URL
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # 提取邮箱
            "phone": r"\b\d{3}-\d{3}-\d{4}\b",  # 提取电话号码
            "number": r"\b\d+\b",           # 提取数字
            "price": r"\$\d+(?:\.\d{2})?",  # 提取价格
        }
    
    def extract_variables(self, download_result: DownloadResult,
                         custom_patterns: Dict[str, str] = None) -> Dict[str, str]:
        """
        从下载结果中提取变量
        
        Args:
            download_result: 下载结果
            custom_patterns: 自定义提取模式
            
        Returns:
            Dict[str, str]: 提取的变量字典
        """
        extracted_vars = {}
        
        # 获取文本内容
        text_content = self._get_text_content(download_result)
        
        if not text_content:
            return extracted_vars
        
        # 使用预定义模式提取
        for pattern_name, pattern in self.predefined_patterns.items():
            matches = self._extract_with_pattern(text_content, pattern)
            if matches:
                extracted_vars[pattern_name] = matches[0]  # 取第一个匹配
                extracted_vars[f"{pattern_name}_all"] = ", ".join(matches)  # 所有匹配
        
        # 使用自定义模式提取
        if custom_patterns:
            for var_name, pattern in custom_patterns.items():
                matches = self._extract_with_pattern(text_content, pattern)
                if matches:
                    extracted_vars[var_name] = matches[0]
                    extracted_vars[f"{var_name}_all"] = ", ".join(matches)
        
        # 提取基础信息
        extracted_vars.update(self._extract_basic_info(text_content))
        
        self.log_info(f"从消息中提取了 {len(extracted_vars)} 个变量")
        return extracted_vars
    
    def _get_text_content(self, download_result: DownloadResult) -> str:
        """
        获取文本内容
        
        Args:
            download_result: 下载结果
            
        Returns:
            str: 文本内容
        """
        content_parts = []
        
        if download_result.original_text:
            content_parts.append(download_result.original_text)
        
        if download_result.original_caption:
            content_parts.append(download_result.original_caption)
        
        return "\n".join(content_parts)
    
    def _extract_with_pattern(self, text: str, pattern: str) -> List[str]:
        """
        使用正则表达式提取内容
        
        Args:
            text: 文本内容
            pattern: 正则表达式模式
            
        Returns:
            List[str]: 匹配结果列表
        """
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            return [match if isinstance(match, str) else match[0] for match in matches]
        except Exception as e:
            self.log_error(f"正则表达式提取失败: {e}")
            return []
    
    def _extract_basic_info(self, text: str) -> Dict[str, str]:
        """
        提取基础信息
        
        Args:
            text: 文本内容
            
        Returns:
            Dict[str, str]: 基础信息字典
        """
        info = {}
        
        # 文本长度
        info["text_length"] = str(len(text))
        
        # 单词数量
        words = text.split()
        info["word_count"] = str(len(words))
        
        # 行数
        lines = text.split('\n')
        info["line_count"] = str(len(lines))
        
        # 第一行内容
        if lines:
            info["first_line"] = lines[0][:50]  # 限制长度
        
        # 最后一行内容
        if lines:
            info["last_line"] = lines[-1][:50]  # 限制长度
        
        return info
    
    def extract_with_template_variables(self, download_result: DownloadResult,
                                      template_variables: List[TemplateVariable]) -> Dict[str, str]:
        """
        使用模板变量定义提取内容
        
        Args:
            download_result: 下载结果
            template_variables: 模板变量列表
            
        Returns:
            Dict[str, str]: 提取的变量字典
        """
        extracted_vars = {}
        text_content = self._get_text_content(download_result)
        
        if not text_content:
            return extracted_vars
        
        for var in template_variables:
            if var.extractor_pattern:
                matches = self._extract_with_pattern(text_content, var.extractor_pattern)
                if matches:
                    extracted_vars[var.name] = matches[0]
                elif var.default_value:
                    extracted_vars[var.name] = var.default_value
        
        return extracted_vars
    
    def suggest_variables(self, text: str, max_suggestions: int = 10) -> List[Dict[str, Any]]:
        """
        建议可能的变量
        
        Args:
            text: 文本内容
            max_suggestions: 最大建议数量
            
        Returns:
            List[Dict[str, Any]]: 建议的变量列表
        """
        suggestions = []
        
        # 检查预定义模式
        for pattern_name, pattern in self.predefined_patterns.items():
            matches = self._extract_with_pattern(text, pattern)
            if matches:
                suggestions.append({
                    "name": pattern_name,
                    "type": "predefined",
                    "pattern": pattern,
                    "matches": matches[:3],  # 显示前3个匹配
                    "count": len(matches),
                    "description": self._get_pattern_description(pattern_name)
                })
        
        # 建议自定义模式
        custom_suggestions = self._suggest_custom_patterns(text)
        suggestions.extend(custom_suggestions)
        
        # 按匹配数量排序
        suggestions.sort(key=lambda x: x.get("count", 0), reverse=True)
        
        return suggestions[:max_suggestions]
    
    def _get_pattern_description(self, pattern_name: str) -> str:
        """
        获取模式描述
        
        Args:
            pattern_name: 模式名称
            
        Returns:
            str: 模式描述
        """
        descriptions = {
            "hashtag": "话题标签 (#标签)",
            "mention": "用户提及 (@用户名)",
            "url": "网址链接",
            "email": "电子邮箱地址",
            "phone": "电话号码",
            "number": "数字",
            "price": "价格 ($金额)"
        }
        return descriptions.get(pattern_name, f"{pattern_name} 模式")
    
    def _suggest_custom_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        建议自定义模式
        
        Args:
            text: 文本内容
            
        Returns:
            List[Dict[str, Any]]: 自定义模式建议
        """
        suggestions = []
        
        # 建议常见的重复模式
        # 这里可以添加更复杂的模式识别逻辑
        
        # 示例：检测重复的格式
        lines = text.split('\n')
        if len(lines) > 1:
            # 检查是否有相似的行格式
            for i, line in enumerate(lines[:5]):  # 只检查前5行
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key and value:
                            suggestions.append({
                                "name": f"field_{key.lower().replace(' ', '_')}",
                                "type": "custom",
                                "pattern": f"{re.escape(key)}:\\s*(.+)",
                                "matches": [value],
                                "count": 1,
                                "description": f"提取 '{key}' 字段的值"
                            })
        
        return suggestions
    
    def create_variable_from_suggestion(self, suggestion: Dict[str, Any]) -> TemplateVariable:
        """
        从建议创建模板变量
        
        Args:
            suggestion: 变量建议
            
        Returns:
            TemplateVariable: 模板变量
        """
        return TemplateVariable(
            name=suggestion["name"],
            type=VariableType.TEXT,  # 默认为文本类型
            description=suggestion.get("description", ""),
            extractor_pattern=suggestion.get("pattern", ""),
            default_value=""
        )
    
    def test_pattern(self, text: str, pattern: str) -> Dict[str, Any]:
        """
        测试正则表达式模式
        
        Args:
            text: 测试文本
            pattern: 正则表达式模式
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            matches = self._extract_with_pattern(text, pattern)
            return {
                "success": True,
                "matches": matches,
                "count": len(matches),
                "pattern": pattern
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }
