"""
Prompt 构建器 - 负责组装完整的 prompt
支持灵活的配置和定制化
"""

from typing import Dict, List, Union, Optional

try:
    # 作为模块导入时使用相对导入
    from .perplexity_prompts import PerplexityPrompts
except ImportError:
    # 直接运行时使用绝对导入
    from perplexity_prompts import PerplexityPrompts


class PromptBuilder:
    """构建 Perplexity 报告生成的 Prompt"""
    
    def __init__(self, prompt_template: Optional[PerplexityPrompts] = None):
        """
        初始化 Prompt 构建器
        
        Args:
            prompt_template: 自定义的 prompt 模板，如果不提供则使用默认模板
        """
        self.prompts = prompt_template or PerplexityPrompts()
        self.max_source_files = 10  # 默认最大数据源文件数
        self.max_source_content_length = 1000  # 每个数据源的最大长度
        self.max_guidance_length = 2000  # 任务指导的最大长度
        self.max_example_length = 3000  # 示例的最大长度
    
    def build_prompt(
        self,
        planning_info: str = "",
        task_guidance: str = "",
        example: str = "",
        source_data: List[Dict] = None,
        custom_requirements: str = "",
        report_type: str = "standard",
        include_example: bool = True,
        topic_name: str = ""
    ) -> str:
        """
        构建完整的 prompt
        
        Args:
            planning_info: 研究背景和目标信息
            task_guidance: 任务指导内容
            example: 参考样例
            source_data: 数据源列表
            custom_requirements: 自定义要求（替代默认要求）
            report_type: 报告类型 (standard, simple, detailed)
            include_example: 是否包含参考样例
            topic_name: 主题名称，用于自动匹配特定的 prompt
            
        Returns:
            完整的 prompt 字符串
        """
        sections = []
        
        # 获取报告类型对应的配置
        prompt_config = self.prompts.get_prompt_by_type(report_type)
        
        # 1. 基础指令
        sections.append(prompt_config["instruction"])
        
        # 2. 研究背景和目标
        if planning_info:
            sections.append(f"{self.prompts.RESEARCH_BACKGROUND_TITLE}\n\n{planning_info}")
        
        # 3. 任务指导（包含自动匹配的特定 prompt）
        guidance_parts = []
        if task_guidance:
            guidance_parts.append(task_guidance[:self.max_guidance_length])
        
        # 自动添加特定类型的 prompt
        if topic_name:
            custom_prompt = self.prompts.get_custom_prompt_for_topic(topic_name)
            if custom_prompt:
                guidance_parts.append(custom_prompt)
        
        if guidance_parts:
            combined_guidance = "\n\n".join(guidance_parts)
            sections.append(f"{self.prompts.TASK_GUIDANCE_TITLE}\n\n{combined_guidance}")
        
        # 4. 参考样例（根据配置决定是否包含）
        if example and include_example and report_type != "simple":
            sections.append(f"{self.prompts.EXAMPLE_TITLE}\n\n{example[:self.max_example_length]}")
        
        # 5. 数据源
        if source_data:
            sections.append(self._build_data_source_section(source_data))
        
        # 6. 报告要求
        requirements = custom_requirements or prompt_config["requirements"]
        sections.append(requirements)
        
        return "\n\n".join(sections)
    
    def _build_data_source_section(self, source_data: List[Dict]) -> str:
        """
        构建数据源部分
        
        Args:
            source_data: 数据源列表
            
        Returns:
            格式化的数据源部分
        """
        if not source_data:
            return ""
        
        source_section = f"{self.prompts.DATA_SOURCE_TITLE}\n\n"
        
        # 限制数据源数量
        limited_sources = source_data[:self.max_source_files]
        
        for i, source in enumerate(limited_sources, 1):
            filename = source.get('filename', f'Source_{i}')
            content = source.get('content', '')
            
            # 截断过长的内容
            if len(content) > self.max_source_content_length:
                content = content[:self.max_source_content_length] + "..."
            
            source_section += f"### 数据源 {i}: {filename}\n"
            source_section += f"{content}\n\n"
        
        # 如果有更多数据源，添加提示
        if len(source_data) > self.max_source_files:
            source_section += f"\n*注：共有 {len(source_data)} 个数据源，此处仅展示前 {self.max_source_files} 个*\n"
        
        return source_section
    
    def build_topic_specific_prompt(
        self,
        topic_id: str,
        materials: Dict[str, Union[str, List]],
        report_type: str = "standard"
    ) -> str:
        """
        根据 topic 构建特定的 prompt
        
        Args:
            topic_id: topic 标识（如 'topic_1_市场格局分析'）
            materials: 包含所有材料的字典
            report_type: 报告类型
            
        Returns:
            针对特定 topic 的 prompt
        """
        # 从 topic_id 提取 topic 名称
        topic_name = ""
        if '_' in topic_id:
            parts = topic_id.split('_', 2)
            if len(parts) > 2:
                topic_name = parts[2]
            elif len(parts) > 1:
                topic_name = parts[1]
        
        # 构建 prompt
        return self.build_prompt(
            planning_info=materials.get('planning_info', ''),
            task_guidance=materials.get('prompt', ''),
            example=materials.get('example', ''),
            source_data=materials.get('source_data', []),
            report_type=report_type,
            topic_name=topic_name
        )
    
    def build_research_prompt(
        self,
        methodology: str = "",
        template: str = "",
        source_data: List[Dict] = None,
        planning_info: str = ""
    ) -> str:
        """
        构建研究报告的完整 prompt
        按照新的三部分结构组装
        
        Args:
            methodology: 研究方法论 (A1.md内容)
            template: 报告模板 (example内容)
            source_data: 数据源列表
            planning_info: 规划信息（可选）
            
        Returns:
            完整的 prompt 字符串
        """
        sections = []
        
        # 1. 基础指令
        sections.append(self.prompts.BASE_INSTRUCTION)
        
        # 2. 任务指导（固定的三句话）
        sections.append(self.prompts.TASK_GUIDANCE)
        
        # 3. 研究方法论 (a1.md)
        if methodology:
            sections.append(f"{self.prompts.METHODOLOGY_TITLE}\n\n{methodology}")
        
        # 4. 数据源
        if source_data:
            source_section = f"{self.prompts.DATA_SOURCE_TITLE}\n\n"
            for i, source in enumerate(source_data[:10], 1):  # 限制10个
                source_section += f"### 数据源 {i}: {source.get('filename', 'Unknown')}\n"
                content = source.get('content', '')[:2000]  # 每个源限制2000字符
                source_section += f"{content}\n\n"
            
            if len(source_data) > 10:
                source_section += f"*注：共有 {len(source_data)} 个数据源，此处仅展示前 10 个*\n\n"
            
            sections.append(source_section)
        
        # 5. 报告模板
        if template:
            sections.append(f"{self.prompts.TEMPLATE_TITLE}\n\n{template}")
        
        # 6. 最终强调指令
        sections.append(f"\n{self.prompts.FINAL_INSTRUCTION}")
        
        return "\n\n".join(sections)
    
    def build_simple_prompt(self, query: str, context: str = "") -> str:
        """
        构建简单的查询 prompt
        
        Args:
            query: 查询问题
            context: 上下文信息
            
        Returns:
            简单的 prompt
        """
        prompt = f"请回答以下问题：\n\n{query}"
        
        if context:
            prompt = f"基于以下背景信息：\n{context}\n\n{prompt}"
        
        return prompt
    
    def configure(
        self,
        max_source_files: int = None,
        max_source_content_length: int = None,
        max_guidance_length: int = None,
        max_example_length: int = None
    ) -> 'PromptBuilder':
        """
        配置 prompt 构建器的参数
        
        Args:
            max_source_files: 最大数据源文件数
            max_source_content_length: 每个数据源的最大长度
            max_guidance_length: 任务指导的最大长度
            max_example_length: 示例的最大长度
            
        Returns:
            self，支持链式调用
        """
        if max_source_files is not None:
            self.max_source_files = max_source_files
        if max_source_content_length is not None:
            self.max_source_content_length = max_source_content_length
        if max_guidance_length is not None:
            self.max_guidance_length = max_guidance_length
        if max_example_length is not None:
            self.max_example_length = max_example_length
        
        return self
    
    @staticmethod
    def create_custom_builder(
        base_instruction: str,
        report_requirements: str
    ) -> 'PromptBuilder':
        """
        创建一个使用自定义模板的构建器
        
        Args:
            base_instruction: 自定义的基础指令
            report_requirements: 自定义的报告要求
            
        Returns:
            配置了自定义模板的 PromptBuilder
        """
        # 创建自定义的 prompt 类
        class CustomPrompts(PerplexityPrompts):
            BASE_INSTRUCTION = base_instruction
            REPORT_REQUIREMENTS = report_requirements
        
        return PromptBuilder(CustomPrompts())