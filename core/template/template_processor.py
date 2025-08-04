"""
模板处理器
整合模板引擎和变量提取器，提供完整的模板处理功能
"""
from typing import Dict, List, Optional, Any
from models.template_config import TemplateConfig, TemplateMode
from models.download_result import DownloadResult
from .template_engine import TemplateEngine
from .variable_extractor import VariableExtractor
from utils.logging_utils import LoggerMixin


class TemplateProcessor(LoggerMixin):
    """模板处理器"""
    
    def __init__(self):
        """初始化模板处理器"""
        self.engine = TemplateEngine()
        self.extractor = VariableExtractor()
    
    def process(self, template_config: TemplateConfig,
                download_result: DownloadResult,
                auto_extract: bool = True,
                extra_variables: Dict[str, str] = None) -> Dict[str, Any]:
        """
        处理模板，生成最终内容
        
        Args:
            template_config: 模板配置
            download_result: 下载结果
            auto_extract: 是否自动提取变量
            extra_variables: 额外变量
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 记录处理开始
            self.log_info(f"开始处理模板: {template_config.name} (模式: {template_config.mode.value})")
            
            # 自动提取变量
            extracted_vars = {}
            if auto_extract and template_config.auto_extract_variables:
                extracted_vars = self.extractor.extract_variables(download_result)
                self.log_info(f"自动提取了 {len(extracted_vars)} 个变量")
            
            # 合并变量
            all_variables = {}
            if extra_variables:
                all_variables.update(extra_variables)
            all_variables.update(extracted_vars)
            
            # 渲染模板
            rendered_content = self.engine.render(
                template_config, 
                download_result, 
                all_variables
            )
            
            # 增加使用次数
            template_config.increment_usage()
            
            # 返回处理结果
            result = {
                "success": True,
                "content": rendered_content,
                "template_id": template_config.template_id,
                "template_name": template_config.name,
                "template_mode": template_config.mode.value,
                "extracted_variables": extracted_vars,
                "used_variables": all_variables,
                "original_content": download_result.get_content_text(),
                "processing_time": None  # 可以添加时间统计
            }
            
            self.log_info(f"模板处理完成: {template_config.name}")
            return result
            
        except Exception as e:
            self.log_error(f"模板处理失败: {e}")
            
            # 返回错误结果，包含原始内容作为回退
            return {
                "success": False,
                "error": str(e),
                "content": download_result.get_content_text(),  # 回退到原始内容
                "template_id": template_config.template_id,
                "template_name": template_config.name,
                "template_mode": template_config.mode.value,
                "extracted_variables": {},
                "used_variables": extra_variables or {},
                "original_content": download_result.get_content_text()
            }
    
    def batch_process(self, template_config: TemplateConfig,
                     download_results: List[DownloadResult],
                     auto_extract: bool = True,
                     extra_variables: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        批量处理模板
        
        Args:
            template_config: 模板配置
            download_results: 下载结果列表
            auto_extract: 是否自动提取变量
            extra_variables: 额外变量
            
        Returns:
            List[Dict[str, Any]]: 处理结果列表
        """
        results = []
        
        self.log_info(f"开始批量处理 {len(download_results)} 个下载结果")
        
        for i, download_result in enumerate(download_results):
            try:
                # 为每个结果添加序号变量
                batch_variables = extra_variables.copy() if extra_variables else {}
                batch_variables.update({
                    "batch_index": str(i + 1),
                    "batch_total": str(len(download_results))
                })
                
                result = self.process(
                    template_config,
                    download_result,
                    auto_extract,
                    batch_variables
                )
                
                result["batch_index"] = i + 1
                results.append(result)
                
            except Exception as e:
                self.log_error(f"批量处理第 {i+1} 项失败: {e}")
                
                # 添加错误结果
                results.append({
                    "success": False,
                    "error": str(e),
                    "batch_index": i + 1,
                    "content": download_result.get_content_text(),
                    "template_id": template_config.template_id
                })
        
        success_count = sum(1 for r in results if r.get("success", False))
        self.log_info(f"批量处理完成: {success_count}/{len(results)} 成功")
        
        return results
    
    def preview_template(self, template_config: TemplateConfig,
                        sample_data: Dict[str, str] = None) -> Dict[str, Any]:
        """
        预览模板效果
        
        Args:
            template_config: 模板配置
            sample_data: 示例数据
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        try:
            # 使用模板引擎预览
            preview_content = self.engine.preview_template(template_config, sample_data)
            
            # 获取模板中使用的变量
            used_variables = self.engine.extract_variables(template_config.content)
            
            return {
                "success": True,
                "preview_content": preview_content,
                "template_variables": list(used_variables),
                "available_variables": self.engine.get_available_variables(),
                "template_mode": template_config.mode.value
            }
            
        except Exception as e:
            self.log_error(f"模板预览失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "preview_content": "",
                "template_variables": [],
                "available_variables": []
            }
    
    def validate_template(self, template_config: TemplateConfig) -> Dict[str, Any]:
        """
        验证模板配置
        
        Args:
            template_config: 模板配置
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = self.engine.validate_template(template_config)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "template_id": template_config.template_id,
            "template_name": template_config.name
        }
    
    def suggest_variables(self, download_result: DownloadResult,
                         max_suggestions: int = 10) -> List[Dict[str, Any]]:
        """
        为下载结果建议变量
        
        Args:
            download_result: 下载结果
            max_suggestions: 最大建议数量
            
        Returns:
            List[Dict[str, Any]]: 变量建议列表
        """
        text_content = download_result.get_content_text()
        if not text_content:
            return []
        
        return self.extractor.suggest_variables(text_content, max_suggestions)
    
    def create_template_from_content(self, template_id: str, name: str,
                                   content: str, description: str = "",
                                   auto_detect_variables: bool = True) -> TemplateConfig:
        """
        从内容创建模板
        
        Args:
            template_id: 模板ID
            name: 模板名称
            content: 模板内容
            description: 模板描述
            auto_detect_variables: 是否自动检测变量
            
        Returns:
            TemplateConfig: 模板配置
        """
        template_config = self.engine.create_template_from_content(
            template_id, name, content, description
        )
        
        if auto_detect_variables:
            # 可以添加自动检测变量的逻辑
            pass
        
        return template_config
    
    def get_template_statistics(self, template_config: TemplateConfig) -> Dict[str, Any]:
        """
        获取模板统计信息
        
        Args:
            template_config: 模板配置
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 提取模板中的变量
        template_vars = self.engine.extract_variables(template_config.content)
        
        return {
            "template_id": template_config.template_id,
            "template_name": template_config.name,
            "template_mode": template_config.mode.value,
            "content_length": len(template_config.content),
            "variable_count": len(template_vars),
            "variables": list(template_vars),
            "usage_count": template_config.usage_count,
            "created_time": template_config.created_time,
            "updated_time": template_config.updated_time,
            "has_required_variables": len(template_config.get_required_variables()) > 0,
            "required_variables": [var.name for var in template_config.get_required_variables()]
        }
