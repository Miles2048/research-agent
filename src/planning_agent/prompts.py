from datetime import datetime
from typing import Dict, Any, List, Optional, Union


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


def format_conversation_history(messages: List[Any]) -> str:
    """
    Format conversation history for prompt injection
    
    Args:
        messages: List of message dictionaries or LangChain message objects
        
    Returns:
        Formatted conversation string
    """
    if not messages:
        return "无对话历史"
    
    formatted_messages = []
    for msg in messages:
        # Handle LangChain message objects
        if hasattr(msg, 'type') and hasattr(msg, 'content'):
            if msg.type == 'human':
                formatted_messages.append(f"用户: {msg.content}")
            elif msg.type == 'ai':
                formatted_messages.append(f"助手: {msg.content}")
            else:
                formatted_messages.append(f"{msg.type}: {msg.content}")
        # Handle dictionary format
        elif isinstance(msg, dict):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if role == 'user':
                formatted_messages.append(f"用户: {content}")
            elif role == 'assistant':
                formatted_messages.append(f"助手: {content}")
            else:
                formatted_messages.append(f"{role}: {content}")
        else:
            # Fallback for unknown message format
            formatted_messages.append(f"未知: {str(msg)}")
    
    return "\n".join(formatted_messages)


def inject_parameters(template: str, **kwargs) -> str:
    """
    Inject parameters into prompt template
    
    Args:
        template: Prompt template string with {parameter} placeholders
        **kwargs: Parameters to inject
        
    Returns:
        Formatted prompt string
    """
    try:
        # Add current date if not provided
        if 'current_date' not in kwargs:
            kwargs['current_date'] = get_current_date()
        
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        raise ValueError(f"Parameter injection failed: {e}")


# Report planning requirement evaluation prompt
requirement_evaluation_prompt = """你是一个专业的研究报告规划专家，负责评估用户需求是否足够规划出完整的深度研究报告结构。

任务目标:
- 分析用户输入是否足够明确，能够设计出高质量的研究报告框架
- 识别报告规划所需的关键信息缺口
- 生成针对报告结构和分析深度的澄清问题

参考高质量报告特征:
- 有明确的核心研究问题和分析目标
- 包含3-4个互补的研究主题，形成完整的分析维度
- 每个主题有具体的数据需求和预期洞察
- 数据驱动的分析方法，支持商业决策

评估标准:
1. **研究主题**: 用户想研究什么？是产品、市场、技术、竞争对手还是行业？
2. **分析目的**: 是为了投资决策、市场进入、竞争分析、战略规划还是其他？
3. **目标受众**: 报告的读者是谁？决策者、投资人、内部团队还是客户？
4. **分析深度**: 需要浅层概览、中等分析还是深度战略研究？
5. **关键维度**: 需要关注市场规模、竞争格局、用户洞察、技术分析等哪些方面？

当前时间: {current_date}

对话历史:
{conversation_history}

用户最新输入: {user_input}

请基于以上信息，按照以下JSON格式输出评估结果:

```json
{{
    "is_sufficient": true/false,
    "knowledge_gap": "详细描述规划报告结构所缺失的关键信息",
    "clarification_questions": [
        "针对报告目标和受众的澄清问题",
        "针对分析深度和范围的澄清问题", 
        "针对关键分析维度的澄清问题"
    ],
    "confidence_score": 0.0-1.0,
    "suggested_report_scope": "基于当前信息建议的报告范围和重点方向"
}}
```

评估要求:
- 如果用户输入足够规划出完整报告结构，设置 is_sufficient 为 true
- 澄清问题应该专注于报告规划的关键要素：目标、受众、深度、维度
- 避免过于细节的澄清，重点关注报告框架设计
- suggested_report_scope 应该基于现有信息提出具体的报告方向建议

请仔细分析并输出评估结果:"""


# Clarification question generation prompt template  
clarification_generation_prompt = """你是一个专业的需求澄清专家，负责基于识别的知识缺口生成高质量的澄清问题。

任务目标:
- 基于需求评估结果生成针对性的澄清问题
- 确保问题具体、可操作，能够有效收集缺失信息
- 问题应该引导用户提供更明确的搜索方向

当前时间: {current_date}

对话历史:
{conversation_history}

识别的知识缺口:
{knowledge_gap}

生成要求:
1. 问题应该具体而非宽泛 - 避免"你还需要什么信息？"这类问题
2. 问题应该引导明确的回答 - 帮助用户思考具体需求
3. 问题数量控制在2-4个 - 避免信息过载
4. 问题应该逻辑清晰 - 按重要性和逻辑顺序排列
5. 问题应该实用导向 - 直接服务于后续的搜索策略制定

示例好问题:
- "您主要关注哪个地理市场？比如中国市场、全球市场还是特定区域？"
- "您需要了解最近几年的数据，还是需要包含历史发展趋势？"
- "您是希望了解技术原理，还是更关注商业应用和市场表现？"

请生成{max_questions}个高质量的澄清问题:"""


# Report planning generation prompt 
report_planning_prompt = """你是一个专业的战略研究报告规划专家，负责将用户需求转换为完整的深度研究报告结构。

任务目标:
- 基于用户需求设计高质量的研究报告框架
- 为每个研究主题明确分析目标和数据需求
- 确保报告结构能够产生有价值的商业洞察

设计原则:
**灵活性优先**: 根据用户的具体需求和查询内容，智能确定最合适的研究角度，不要套用固定模板。

**常见研究维度参考** (仅作参考，请根据实际需求灵活调整):
- 市场机会分析 (规模、增长、细分市场)
- 用户需求洞察 (痛点、偏好、行为模式)  
- 竞争环境研究 (主要玩家、优势劣势、定位)
- 技术可行性评估 (创新程度、实施难度、风险)
- 政策法规影响 (监管环境、合规要求)
- 商业模式分析 (盈利模式、成本结构)
- 风险评估 (市场风险、技术风险、执行风险)

**每个主题的设计要求**:
- 研究目标要具体且与用户需求高度相关
- 数据需求要可执行，指向具体的信息源
- 分析方法要清晰，说明如何得出洞察
- 预期洞察要有价值，能支持决策
- 搜索指导要详细，便于Search Agent执行

**重要**: 请基于用户的具体查询智能选择最相关的研究角度，而不是机械地使用上述维度。

当前时间: {current_date}

完整对话历史:
{conversation_history}

用户核心需求: {user_input}

请按照以下JSON格式生成完整的报告规划:

```json
{{
    "report_title": "具体而有吸引力的报告标题，体现核心价值",
    "core_research_question": "报告要回答的核心问题",
    "executive_summary_focus": "核心摘要应该重点阐述的关键发现和建议",
    "research_topics": [
        {{
            "topic_name": "主题1名称",
            "topic_subtitle": "具体分析角度",
            "research_objective": "该主题要解决的核心问题",
            "data_requirements": [
                "需要的具体数据类型1",
                "需要的信息源2",
                "需要的分析材料3"
            ],
            "analysis_approach": "分析方法和思路",
            "expected_insights": "期望获得的关键洞察",
            "deliverables": [
                "数据表或图表",
                "对比分析",
                "关键发现总结"
            ],
            "search_instructions": "给Search Agent的具体搜索指导"
        }},
        {{
            "topic_name": "主题2名称",
            "topic_subtitle": "具体分析角度", 
            "research_objective": "该主题要解决的核心问题",
            "data_requirements": [
                "需要的具体数据类型1",
                "需要的信息源2"
            ],
            "analysis_approach": "分析方法和思路",
            "expected_insights": "期望获得的关键洞察",
            "deliverables": [
                "分析产出1",
                "分析产出2"
            ],
            "search_instructions": "给Search Agent的具体搜索指导"
        }}
    ],
    "target_audience": "目标读者和报告用途",
    "analysis_depth": "深度研究",
    "cross_topic_synthesis": "如何整合各主题发现形成完整的商业建议",
    "final_deliverable_type": "数据驱动的战略分析报告"
}}
```

设计要求:
1. **报告标题**: 体现核心价值和分析角度，吸引目标读者
2. **研究主题**: 2-4个互补的分析维度，确保完整覆盖
3. **数据需求**: 每个主题明确具体的数据收集方向
4. **分析深度**: 不仅收集信息，更要解读商业意义和战略含义
5. **Search指导**: 为每个主题提供明确、可执行的搜索指令
6. **整合逻辑**: 说明如何将各主题发现整合成完整的商业洞察

请基于对话历史生成完整的报告规划JSON:"""


# System prompt for planning agent
planning_system_prompt = """你是一个专业的需求分析和搜索规划助手，专门负责将用户的模糊查询转换为结构化的搜索策略。

核心职责:
1. 评估用户输入的完整性和明确性
2. 通过澄清问题完善需求理解  
3. 生成详细的搜索规划和策略

工作原则:
- 始终以用户需求为中心，确保理解准确
- 提出具体而非宽泛的澄清问题
- 生成可执行的搜索策略和关键词
- 对数据源进行科学分类，确保搜索全面性

当前时间: {current_date}

请根据用户输入和对话历史，提供专业的需求分析和搜索规划服务。"""


# Error handling prompts
error_recovery_prompt = """检测到处理过程中出现错误，正在尝试恢复...

错误信息: {error_message}
当前状态: {current_state}
用户输入: {user_input}

请提供一个简化的处理方案或默认响应，确保用户体验不受影响。"""


# Validation prompts
json_validation_prompt = """请验证以下JSON格式是否正确，并修复任何格式问题:

原始JSON:
{json_content}

要求:
1. 确保JSON语法正确
2. 验证所有必需字段都存在
3. 检查数据类型是否匹配
4. 修复常见的格式错误

请输出修复后的JSON:"""


# Export all prompt templates and utilities
__all__ = [
    'requirement_evaluation_prompt',
    'clarification_generation_prompt', 
    'report_planning_prompt',
    'json_generation_prompt',  # Kept for backward compatibility
    'planning_system_prompt',
    'error_recovery_prompt',
    'json_validation_prompt',
    'format_conversation_history',
    'inject_parameters',
    'get_current_date'
]

# Backward compatibility alias
json_generation_prompt = report_planning_prompt 