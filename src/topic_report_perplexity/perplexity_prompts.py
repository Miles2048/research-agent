"""
Perplexity Report Generator 的 Prompt 模板管理
可以方便地修改和调整不同的 prompt 策略
"""

class PerplexityPrompts:
    """Perplexity 报告生成的 Prompt 模板"""
    
    # ==================== 基础模板 ====================
    
    BASE_INSTRUCTION = """你是一位专业的研究分析师，基于以下提供的材料生成一份深度研究报告。报告需要：
- 使用中文撰写
- 保持专业、客观、数据驱动的风格
- 引用具体的数据和来源
- 字数约7000字"""
    
    # ==================== 固定的任务指导 ====================
    
    TASK_GUIDANCE = """## 任务指导

输出一个报告。报告研究方式按照a1.md，报告数据源根据sourcedata，报告格式按照高分模版。我给你传的文件，是来自这三部分。

- a1.md只是你的研究思路，你研究方式仿照它。
- 引用数据源应该按照我传给你的数据源。
- 你输出的报告格式应该按照我给你的高分模版"""
    
    # ==================== 章节标题 ====================
    
    RESEARCH_BACKGROUND_TITLE = "## 研究背景和目标"
    
    METHODOLOGY_TITLE = "## a1.md 你需要严格按照以下这个a1.md的研究思路来展开"
    
    DATA_SOURCE_TITLE = "## 研究数据源：你需要使用这个数据源"
    
    TEMPLATE_TITLE = "## 高分报告模版。你的报告格式应该仿照这个"
    
    EXAMPLE_TITLE = "## 参考样例（请模仿其风格和结构）"
    
    # ==================== 报告要求 ====================
    
    REPORT_REQUIREMENTS = """## 报告要求

1. **结构要求**：
   - 执行摘要（500-800字）
   - 详细分析（分多个章节，每章节800-1200字）
   - 结论与建议（500-800字）
   - 参考文献

2. **内容要求**：
   - 基于提供的数据源进行分析
   - 使用具体的数据和案例支撑观点
   - 保持客观中立的分析视角
   - 提供可行的战略建议
   - 充分利用Perplexity的实时搜索能力补充最新信息

3. **格式要求**：
   - 使用Markdown格式
   - 适当使用标题层级（# ## ### ####）
   - 数据引用使用[数字]格式
   - 包含必要的列表和表格

请基于以上材料和要求，生成一份专业的深度研究报告。"""
    
    # ==================== 最终强调指令 ====================
    
    FINAL_INSTRUCTION = "重要：请基于以上材料和要求，生成一份专业的深度研究报告。必须给出具体的数据,必须有具体的mermaid图表，直接生成约7000字的完整报告。"
    
    # ==================== 特定场景的 Prompt ====================
    
    @staticmethod
    def get_market_analysis_prompt():
        """市场分析专用 prompt"""
        return """### 市场分析重点

请在报告中深入分析以下方面：
- **市场规模与增长**：当前市场容量、年增长率、未来5年预测
- **竞争格局**：主要玩家市场份额、竞争优势对比、新进入者威胁
- **客户分析**：目标客户群体、购买决策因素、需求痛点
- **市场趋势**：技术发展趋势、政策影响、消费者偏好变化
- **机会与风险**：市场机会窗口、潜在风险因素、应对策略"""
    
    @staticmethod
    def get_technical_analysis_prompt():
        """技术分析专用 prompt"""
        return """### 技术分析重点

请在报告中深入分析以下技术维度：
- **技术原理**：核心技术原理、创新点、技术优势
- **技术对比**：与竞品技术参数对比、性能评估、成本分析
- **技术成熟度**：TRL等级评估、量产可行性、技术瓶颈
- **知识产权**：专利布局、技术壁垒、许可要求
- **发展路线图**：技术演进路径、下一代技术方向、研发投入需求"""
    
    @staticmethod
    def get_competitive_analysis_prompt():
        """竞争分析专用 prompt"""
        return """### 竞争分析重点

请在报告中重点评估：
- **竞争者识别**：直接竞争者、间接竞争者、潜在竞争者
- **竞争优势分析**：各竞争者的核心优势、劣势、差异化策略
- **市场定位**：价格定位、品牌定位、渠道策略对比
- **竞争动态**：近期竞争者动作、市场份额变化、并购整合
- **竞争策略建议**：差异化路径、竞争应对、合作机会"""
    
    @staticmethod
    def get_international_expansion_prompt():
        """国际化扩展专用 prompt"""
        return """### 国际化分析重点

请在报告中详细评估：
- **目标市场选择**：优先级市场排序、进入时机、市场容量评估
- **进入策略**：直接出口、合资、收购、绿地投资等模式对比
- **本地化要求**：产品本地化、营销本地化、合规要求
- **风险评估**：政治风险、汇率风险、文化差异、法律合规
- **资源需求**：资金投入、人才需求、时间规划、ROI预测"""
    
    # ==================== 简化版 Prompt ====================
    
    SIMPLE_INSTRUCTION = """基于提供的材料，生成一份简洁的分析报告：
- 字数1500-2000字
- 重点突出关键发现
- 提供可执行建议
- 使用中文撰写"""
    
    SIMPLE_REQUIREMENTS = """## 简化报告要求

1. **核心发现**（500字）：3-5个关键洞察
2. **数据支撑**（500字）：引用关键数据和事实
3. **策略建议**（500字）：3-5条可执行建议
4. **风险提示**（200字）：主要风险和注意事项

请确保报告简洁、实用、可执行。"""
    
    # ==================== 自定义组合方法 ====================
    
    @classmethod
    def get_custom_prompt_for_topic(cls, topic_name: str) -> str:
        """
        根据 topic 名称返回定制化的额外 prompt
        
        Args:
            topic_name: 主题名称
            
        Returns:
            定制化的 prompt 补充内容
        """
        topic_lower = topic_name.lower()
        
        # 根据关键词匹配返回相应的 prompt
        if '市场' in topic_name or 'market' in topic_lower:
            return cls.get_market_analysis_prompt()
        elif '技术' in topic_name or 'technical' in topic_lower or 'technology' in topic_lower:
            return cls.get_technical_analysis_prompt()
        elif '竞争' in topic_name or 'competitive' in topic_lower or 'competition' in topic_lower:
            return cls.get_competitive_analysis_prompt()
        elif '国际' in topic_name or 'international' in topic_lower or 'global' in topic_lower:
            return cls.get_international_expansion_prompt()
        else:
            return ""
    
    @classmethod
    def get_prompt_by_type(cls, report_type: str = "standard") -> dict:
        """
        根据报告类型返回相应的 prompt 配置
        
        Args:
            report_type: 报告类型 (standard, simple, detailed)
            
        Returns:
            包含指令和要求的字典
        """
        if report_type == "simple":
            return {
                "instruction": cls.SIMPLE_INSTRUCTION,
                "requirements": cls.SIMPLE_REQUIREMENTS
            }
        elif report_type == "detailed":
            return {
                "instruction": cls.BASE_INSTRUCTION + "\n- 提供详尽的数据分析和图表说明\n- 字数约5000-7000字",
                "requirements": cls.REPORT_REQUIREMENTS
            }
        else:  # standard
            return {
                "instruction": cls.BASE_INSTRUCTION,
                "requirements": cls.REPORT_REQUIREMENTS
            }