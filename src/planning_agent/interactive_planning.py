"""
Interactive Planning Module

交互式Planning Agent模块，支持：
1. 评估后停止，等待用户输入
2. 基于用户对话和现有planning_list.md生成新计划
3. 支持直接编辑planning_list.md影响后续生成
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from .state import PlanningOverallState, initialize_planning_state
from .configuration import Configuration
from .file_operations import (
    read_planning_file,
    write_planning_file,
    append_planning_to_file,
    overwrite_planning_to_file,
    get_planning_file_info,
    backup_planning_file
)
from .prompts import (
    requirement_evaluation_prompt,
    clarification_generation_prompt,
    report_planning_prompt,
    format_conversation_history,
    inject_parameters
)
from .tools_and_schemas import RequirementEvaluation, PlanningOutput, ReportPlan


# 交互式报告规划的系统提示
INTERACTIVE_REPORT_PLANNING_PROMPT = """你是一个专业的战略研究报告规划专家，负责基于用户对话和现有规划文件生成完整的深度研究报告结构。

当前planning_list.md文件内容:
{current_planning_content}

用户的查询历史:
{conversation_history}

用户的最新输入:
{user_input}

内存中的评估信息:
{evaluation_info}

任务目标：
基于用户需求和现有规划，设计或改进深度研究报告的完整结构，确保：
1. 报告具有明确的核心研究问题和分析目标
2. 包含3-4个互补的研究主题，形成完整的分析维度
3. 每个主题有具体的数据需求和预期洞察
4. 生成的报告结构能够支持商业决策

参考高质量报告的典型结构：
- **市场格局分析**: 量化市场机会、规模、增长趋势
- **用户/消费者洞察**: 验证需求、分析痛点、识别机会
- **竞争环境分析**: 对标分析、差异化定位、竞争策略
- **技术/产品分析**: 可行性评估、风险识别、实施路径

设计要求：
- 如果存在现有规划，在其基础上进行改进和完善
- 结合用户最新输入，调整或重新设计报告结构
- 确保每个研究主题都有明确的分析目标和数据收集指导
- 为Search Agent提供具体、可执行的搜索指令
- 保持报告结构的逻辑性和商业价值

请直接输出符合ReportPlan格式的JSON结构。"""


class InteractivePlanningAgent:
    """交互式Planning Agent"""
    
    def __init__(self, config: Optional[RunnableConfig] = None):
        """初始化交互式Planning Agent"""
        self.config = config or {}
        self.configurable = Configuration.from_runnable_config(config)
        self.state_memory = {}  # 用于存储评估和对话信息
        
        # 初始化LLM
        self.evaluation_llm = ChatOpenAI(
            model=self.configurable.evaluation_model,
            temperature=self.configurable.temperature,
            max_retries=3,
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=self.configurable.llm_timeout,
        )
        
        self.generation_llm = ChatOpenAI(
            model=self.configurable.generation_model,
            temperature=self.configurable.temperature,
            max_retries=3,
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=self.configurable.llm_timeout,
        )
    
    def evaluate_user_input(self, user_input: str, conversation_history: List = None) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        评估用户输入的充分性
        
        Returns:
            (is_sufficient, evaluation_result, clarification_questions)
        """
        logger.info(f"评估用户输入: {user_input[:50]}...")
        
        try:
            # 准备消息
            messages = conversation_history or []
            messages.append(HumanMessage(content=user_input))
            
            # 使用结构化输出
            structured_llm = self.evaluation_llm.with_structured_output(RequirementEvaluation)
            
            # 格式化提示
            conversation_text = format_conversation_history(messages)
            formatted_prompt = inject_parameters(
                requirement_evaluation_prompt,
                conversation_history=conversation_text,
                user_input=user_input
            )
            
            # 执行评估
            evaluation_result = structured_llm.invoke(formatted_prompt)
            
            # 保存评估结果到内存
            self.state_memory["last_evaluation"] = {
                "user_input": user_input,
                "is_sufficient": evaluation_result.is_sufficient,
                "knowledge_gap": evaluation_result.knowledge_gap,
                "clarification_questions": evaluation_result.clarification_questions,
                "confidence_score": evaluation_result.confidence_score
            }
            
            logger.info(f"评估完成 - 充分性: {evaluation_result.is_sufficient}")
            
            return (
                evaluation_result.is_sufficient,
                {
                    "is_sufficient": evaluation_result.is_sufficient,
                    "knowledge_gap": evaluation_result.knowledge_gap,
                    "confidence_score": evaluation_result.confidence_score
                },
                evaluation_result.clarification_questions
            )
            
        except Exception as e:
            logger.error(f"评估失败: {str(e)}")
            return False, {"error": str(e)}, ["请提供更详细的信息"]
    
    def generate_clarification_questions(self, user_input: str, evaluation_result: Dict[str, Any]) -> List[str]:
        """
        仅用于生成澄清问题，不影响主流程
        """
        logger.info("生成澄清问题")
        
        try:
            # 如果评估结果中已有澄清问题，直接返回
            if "knowledge_gap" in evaluation_result:
                knowledge_gap = evaluation_result["knowledge_gap"]
                
                # 构建澄清提示
                clarification_prompt = f"""
基于用户输入: {user_input}
知识缺口: {knowledge_gap}

请生成3-5个具体的澄清问题，帮助用户提供更详细的信息。
每个问题应该针对不同方面，例如：
- 研究范围和深度
- 时间范围和地理范围  
- 具体关注的子领域
- 期望的输出类型
- 数据源偏好

请直接输出问题列表，每行一个问题。
"""
                
                response = self.evaluation_llm.invoke([SystemMessage(content=clarification_prompt)])
                
                # 解析问题
                questions = []
                for line in response.content.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or '?' in line or '？' in line):
                        # 清理格式
                        question = line.lstrip('-•').strip()
                        if question:
                            questions.append(question)
                
                logger.info(f"生成了 {len(questions)} 个澄清问题")
                return questions[:5]  # 最多5个问题
                
        except Exception as e:
            logger.error(f"生成澄清问题失败: {str(e)}")
        
        return ["请提供更多具体信息来帮助我们生成更准确的研究计划"]
    
    def generate_planning_with_context(
        self, 
        user_input: str, 
        conversation_history: List = None,
        force_generation: bool = False
    ) -> Dict[str, Any]:
        """
        基于用户输入、对话历史和现有planning文件生成新的计划
        
        Args:
            user_input: 用户最新输入
            conversation_history: 对话历史
            force_generation: 是否强制生成（即使评估不充分）
            
        Returns:
            包含计划信息和文件路径的字典
        """
        logger.info("开始生成基于上下文的计划")
        
        try:
            # 读取现有planning文件
            current_planning = read_planning_file()
            if not current_planning:
                current_planning = "# 研究计划列表\n\n暂无现有计划\n"
            
            # 获取评估信息
            evaluation_info = self.state_memory.get("last_evaluation", {})
            
            # 如果不是强制生成且评估不充分，返回澄清建议
            if not force_generation and not evaluation_info.get("is_sufficient", False):
                return {
                    "success": False,
                    "message": "需求信息不够充分，建议先进行澄清",
                    "clarification_questions": evaluation_info.get("clarification_questions", [])
                }
            
            # 格式化对话历史
            conversation_text = format_conversation_history(conversation_history or [])
            
            # 构建报告规划生成提示
            formatted_prompt = INTERACTIVE_REPORT_PLANNING_PROMPT.format(
                current_planning_content=current_planning,
                conversation_history=conversation_text,
                user_input=user_input,
                evaluation_info=json.dumps(evaluation_info, ensure_ascii=False, indent=2)
            )
            
            logger.debug(f"发送报告规划生成请求，提示长度: {len(formatted_prompt)}")
            
            # 使用结构化输出生成报告规划
            structured_llm = self.generation_llm.with_structured_output(ReportPlan)
            
            try:
                report_plan = structured_llm.invoke(formatted_prompt)
                logger.info(f"成功生成报告规划: {report_plan.report_title}")
            except Exception as e:
                logger.warning(f"结构化输出失败，尝试常规生成: {str(e)}")
                # 如果结构化输出失败，尝试使用默认结构
                report_plan = self._create_default_report_plan(user_input)
            
            # 转换为字典格式以便文件操作
            planning_data = {
                "report_title": report_plan.report_title,
                "core_research_question": report_plan.core_research_question,
                "executive_summary_focus": report_plan.executive_summary_focus,
                "research_topics": [
                    {
                        "topic_name": topic.topic_name,
                        "topic_subtitle": topic.topic_subtitle,
                        "research_objective": topic.research_objective,
                        "data_requirements": topic.data_requirements,
                        "analysis_approach": topic.analysis_approach,
                        "expected_insights": topic.expected_insights,
                        "deliverables": topic.deliverables,
                        "search_instructions": topic.search_instructions
                    }
                    for topic in report_plan.research_topics
                ],
                "target_audience": report_plan.target_audience,
                "analysis_depth": report_plan.analysis_depth,
                "cross_topic_synthesis": report_plan.cross_topic_synthesis,
                "final_deliverable_type": report_plan.final_deliverable_type
            }
            
            # 创建备份
            backup_path = backup_planning_file()
            if backup_path:
                logger.info(f"创建了备份: {backup_path}")
            
            # 覆盖planning文件，生成新计划
            overwrite_planning_to_file(planning_data, user_input)
            
            # 获取文件信息
            file_info = get_planning_file_info()
            
            logger.info("计划生成完成")
            
            return {
                "success": True,
                "planning_data": planning_data,
                "file_path": file_info.get("file_path", ""),
                "message": f"新计划已生成并保存到文件: {user_input[:50]}...",
                "backup_path": backup_path
            }
            
        except Exception as e:
            logger.error(f"生成计划失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"计划生成失败: {str(e)}"
            }
    
    def _create_default_report_plan(self, user_input: str) -> ReportPlan:
        """创建简化的默认报告规划 - 用于错误恢复"""
        from .tools_and_schemas import ResearchTopic
        
        # 创建最基本的研究主题
        default_topic = ResearchTopic(
            topic_name=f"{user_input} - 基础研究",
            topic_subtitle="核心信息收集与分析",
            research_objective=f"收集和分析关于{user_input}的基础信息和关键数据",
            data_requirements=[
                f"{user_input}的基本信息和定义",
                "相关的统计数据和趋势",
                "主要参与者和利益相关方信息"
            ],
            analysis_approach="数据收集与基础分析，识别关键模式和趋势",
            expected_insights=f"获得关于{user_input}的基本认知和初步判断",
            deliverables=[
                "基础信息汇总",
                "关键数据整理",
                "初步分析结论"
            ],
            search_instructions=f"搜索{user_input}的基础信息、定义、统计数据和相关报告"
        )
        
        return ReportPlan(
            report_title=f"{user_input} 研究报告",
            core_research_question=f"关于{user_input}的基本情况和关键信息是什么？",
            executive_summary_focus=f"提供关于{user_input}的基础认知和关键发现",
            research_topics=[default_topic],
            target_audience="一般读者",
            analysis_depth="基础研究",
            cross_topic_synthesis="整合收集到的基础信息，形成对主题的全面认知",
            final_deliverable_type="基础研究报告"
        )
    
    def get_current_planning_content(self) -> str:
        """获取当前planning文件内容"""
        return read_planning_file()
    
    def get_state_memory(self) -> Dict[str, Any]:
        """获取状态内存"""
        return self.state_memory.copy()
    
    def clear_state_memory(self):
        """清空状态内存"""
        self.state_memory.clear()
        logger.info("状态内存已清空")
    
    def process_user_input_with_update(self, user_input: str, conversation_history: List = None) -> Dict[str, Any]:
        """
        处理用户输入并立即更新planning_list.md
        
        这个方法会：
        1. 评估用户输入
        2. 立即更新planning_list（无论是否充分）
        3. 返回综合结果
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            
        Returns:
            包含评估结果、澄清问题和计划更新状态的字典
        """
        logger.info(f"处理用户输入并更新计划: {user_input[:50]}...")
        
        # 第1步：评估用户输入
        is_sufficient, evaluation, questions = self.evaluate_user_input(user_input, conversation_history)
        
        # 第2步：无论评估结果如何，都尝试更新计划
        # 即使信息不够充分，也基于现有信息生成/更新计划
        planning_result = self.generate_planning_with_context(
            user_input, 
            conversation_history, 
            force_generation=True  # 总是生成，不管是否充分
        )
        
        # 综合返回结果
        return {
            "evaluation": {
                "is_sufficient": is_sufficient,
                "evaluation_data": evaluation,
                "clarification_questions": questions
            },
            "planning": planning_result,
            "user_input": user_input,
            "should_ask_clarification": not is_sufficient and len(questions) > 0,
            "overall_success": planning_result.get("success", False)
        }

    def modify_topics_based_on_feedback(self, modification_request: str, conversation_history: List = None) -> Dict[str, Any]:
        """
        基于用户反馈修改研究主题
        
        Args:
            modification_request: 用户的修改要求
            conversation_history: 对话历史
            
        Returns:
            修改结果字典
        """
        logger.info(f"处理主题修改请求: {modification_request[:50]}...")
        
        try:
            # 读取当前规划内容
            current_planning = read_planning_file()
            if not current_planning:
                return {
                    "success": False,
                    "message": "没有找到当前的规划文件，请先生成初始规划"
                }
            
            # 格式化对话历史
            conversation_text = format_conversation_history(conversation_history or [])
            
            # 构建修改提示
            modification_prompt = f"""你是一个专业的研究报告规划专家，需要根据用户的反馈修改现有的研究主题规划。

当前的规划内容:
{current_planning}

用户的修改要求:
{modification_request}

对话历史:
{conversation_text}

请基于用户的反馈，对研究主题进行智能调整：
1. 如果用户要求添加新主题，请增加相应的研究主题
2. 如果用户要求修改某个主题，请调整该主题的内容
3. 如果用户要求删除主题，请移除相应主题
4. 如果用户要求重新设计，请重新规划整个报告结构
5. 保持修改后的规划逻辑性和完整性

请输出完整的修改后的报告规划，格式与之前相同。"""

            # 使用LLM生成修改后的规划
            structured_llm = self.generation_llm.with_structured_output(ReportPlan)
            
            try:
                modified_plan = structured_llm.invoke(modification_prompt)
                logger.info(f"成功生成修改后的报告规划: {modified_plan.report_title}")
            except Exception as e:
                logger.warning(f"结构化输出失败: {str(e)}")
                # 降级处理
                return {
                    "success": False,
                    "message": f"修改失败: {str(e)}"
                }
            
            # 转换为字典格式
            planning_data = {
                "report_title": modified_plan.report_title,
                "core_research_question": modified_plan.core_research_question,
                "executive_summary_focus": modified_plan.executive_summary_focus,
                "research_topics": [
                    {
                        "topic_name": topic.topic_name,
                        "topic_subtitle": topic.topic_subtitle,
                        "research_objective": topic.research_objective,
                        "data_requirements": topic.data_requirements,
                        "analysis_approach": topic.analysis_approach,
                        "expected_insights": topic.expected_insights,
                        "deliverables": topic.deliverables,
                        "search_instructions": topic.search_instructions
                    }
                    for topic in modified_plan.research_topics
                ],
                "target_audience": modified_plan.target_audience,
                "analysis_depth": modified_plan.analysis_depth,
                "cross_topic_synthesis": modified_plan.cross_topic_synthesis,
                "final_deliverable_type": modified_plan.final_deliverable_type
            }
            
            # 创建备份并保存修改后的规划
            backup_path = backup_planning_file()
            if backup_path:
                logger.info(f"创建了备份: {backup_path}")
            
            # 覆盖规划文件
            overwrite_planning_to_file(planning_data, modification_request)
            
            # 获取文件信息
            file_info = get_planning_file_info()
            
            logger.info("主题修改完成")
            return {
                "success": True,
                "planning_data": planning_data,
                "file_path": file_info.get("file_path", ""),
                "message": f"成功根据反馈修改了研究主题规划",
                "backup_path": backup_path,
                "topics_count": len(modified_plan.research_topics)
            }
            
        except Exception as e:
            logger.error(f"修改主题失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"主题修改失败: {str(e)}"
            }


# 便捷函数
def create_interactive_planning_agent(config: Optional[RunnableConfig] = None) -> InteractivePlanningAgent:
    """创建交互式Planning Agent实例"""
    return InteractivePlanningAgent(config) 