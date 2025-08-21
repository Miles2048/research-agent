from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import json
from enum import Enum

from loguru import logger
from .error_handling import (
    JSONValidationError,
    log_error,
    safe_execute,
    performance_monitor,
    retry_with_backoff
)


class PriorityLevel(str, Enum):
    """Priority levels for planning output"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RequirementEvaluation(BaseModel):
    """Model for evaluating user requirement sufficiency for report planning"""
    is_sufficient: bool = Field(
        description="用户输入是否足够规划一个完整的研究报告结构"
    )
    knowledge_gap: str = Field(
        description="缺失信息的详细描述，主要关注报告规划所需的关键要素"
    )
    clarification_questions: List[str] = Field(
        description="针对报告规划生成的澄清问题，重点关注研究目标、分析深度、目标受众等",
        max_items=5
    )
    confidence_score: float = Field(
        description="对能否规划出完整报告结构的置信度 (0.0-1.0)",
        ge=0.0,
        le=1.0,
        default=0.8
    )
    suggested_report_scope: str = Field(
        description="基于当前信息建议的报告范围和重点",
        default=""
    )

    @validator('clarification_questions')
    def validate_questions(cls, v):
        """Validate clarification questions focus on report planning aspects"""
        if not v:
            return v
        
        # Filter out empty or too short questions
        valid_questions = [q.strip() for q in v if q.strip() and len(q.strip()) > 10]
        return valid_questions[:5]  # Limit to 5 questions max


class ResearchTopic(BaseModel):
    """Model for individual research topic within a report"""
    topic_name: str = Field(
        description="主题名称，简洁明确",
        min_length=5,
        max_length=100
    )
    topic_subtitle: str = Field(
        description="主题副标题，说明具体分析角度",
        default=""
    )
    research_objective: str = Field(
        description="该主题要解决的核心问题或研究目标",
        min_length=20
    )
    data_requirements: List[str] = Field(
        description="需要收集的具体数据类型和信息源",
        min_items=2,
        max_items=8
    )
    analysis_approach: str = Field(
        description="分析方法和思路，如对比分析、趋势分析、案例研究等",
        min_length=20
    )
    expected_insights: str = Field(
        description="期望获得的关键洞察和发现",
        min_length=20
    )
    deliverables: List[str] = Field(
        description="具体产出物，如数据表、对比分析、图表等",
        min_items=1,
        max_items=5
    )
    search_instructions: str = Field(
        description="给Search Agent的具体搜索指导",
        min_length=30
    )

    @validator('data_requirements')
    def validate_data_requirements(cls, v):
        """Ensure data requirements are specific and actionable"""
        if not v:
            raise ValueError("每个主题必须有明确的数据需求")
        return [req.strip() for req in v if req.strip()]


class ReportPlan(BaseModel):
    """Model for complete research report planning"""
    report_title: str = Field(
        description="研究报告标题，体现核心价值和分析角度",
        min_length=10,
        max_length=150
    )
    core_research_question: str = Field(
        description="报告要回答的核心研究问题",
        min_length=20
    )
    executive_summary_focus: str = Field(
        description="核心摘要应该重点阐述的关键发现和建议",
        min_length=30
    )
    research_topics: List[ResearchTopic] = Field(
        description="研究主题列表，通常3-4个主要主题",
        min_items=2,
        max_items=6
    )
    target_audience: str = Field(
        description="目标读者和报告用途",
        default="决策者和相关利益方"
    )
    analysis_depth: str = Field(
        description="分析深度要求：浅层概览、中等分析、深度研究",
        default="深度研究"
    )
    cross_topic_synthesis: str = Field(
        description="如何整合各主题发现形成完整的商业洞察",
        min_length=30
    )
    final_deliverable_type: str = Field(
        description="最终报告类型：战略建议、市场分析、竞争研究等",
        default="数据驱动的战略分析报告"
    )

    @validator('research_topics')
    def validate_topics_coverage(cls, v):
        """Ensure topics provide comprehensive coverage"""
        if len(v) < 2:
            raise ValueError("报告至少需要2个主要研究主题")
        return v


class DataSourceCategory(BaseModel):
    """Categorized data sources for different types of information"""
    academic_sources: List[str] = Field(
        description="学术数据源列表，包括论文、专利、科研报告等",
        default_factory=list
    )
    industry_sources: List[str] = Field(
        description="行业数据源列表，包括公司官网、产品页面、行业报告等",
        default_factory=list
    )
    regulatory_sources: List[str] = Field(
        description="政策法规数据源列表，包括政府文件、标准规范等",
        default_factory=list
    )
    market_sources: List[str] = Field(
        description="市场数据源列表，包括市场研究、统计数据、消费者调研等",
        default_factory=list
    )

    @validator('*', pre=True)
    def ensure_list(cls, v):
        """Ensure all fields are lists"""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


# Legacy PlanningOutput for backward compatibility
class PlanningOutput(BaseModel):
    """Legacy output structure - use ReportPlan for new implementations"""
    search_categories: List[str] = Field(
        description="搜索分类列表，定义主要的研究方向和主题",
        min_items=1,
        max_items=10
    )
    keywords: List[str] = Field(
        description="关键词列表，包括中英文关键词和相关术语",
        min_items=1,
        max_items=20
    )
    search_angles: List[str] = Field(
        description="搜索角度列表，定义具体的研究问题和分析维度",
        min_items=1,
        max_items=15
    )
    data_sources: DataSourceCategory = Field(
        description="按类型分类的数据源规范"
    )
    priority: PriorityLevel = Field(
        description="搜索任务的优先级",
        default=PriorityLevel.MEDIUM
    )

    @classmethod
    def from_report_plan(cls, report_plan: ReportPlan) -> "PlanningOutput":
        """Convert ReportPlan to legacy PlanningOutput format"""
        # Extract search categories from topics
        search_categories = [topic.topic_name for topic in report_plan.research_topics]
        
        # Extract keywords from data requirements
        keywords = []
        for topic in report_plan.research_topics:
            keywords.extend([req for req in topic.data_requirements if len(req.split()) <= 3])
        
        # Extract search angles from research objectives
        search_angles = [topic.research_objective for topic in report_plan.research_topics]
        
        return cls(
            search_categories=search_categories,
            keywords=list(set(keywords))[:20],  # Remove duplicates and limit
            search_angles=search_angles,
            data_sources=DataSourceCategory(),
            priority=PriorityLevel.HIGH  # Report planning typically high priority
        )
    scope: str = Field(
        description="搜索范围的详细描述，说明研究的深度和广度"
    )
    estimated_complexity: str = Field(
        description="预估的任务复杂度：simple/moderate/complex",
        default="moderate"
    )
    
    @validator('search_categories', 'keywords', 'search_angles')
    def validate_non_empty_strings(cls, v):
        """Validate that list items are non-empty strings"""
        if not v:
            raise ValueError("List cannot be empty")
        
        # Filter out empty or whitespace-only strings
        valid_items = [item.strip() for item in v if item.strip()]
        if not valid_items:
            raise ValueError("List must contain at least one non-empty item")
        
        return valid_items

    @validator('scope')
    def validate_scope(cls, v):
        """Validate scope description is meaningful"""
        if not v or len(v.strip()) < 20:
            raise ValueError("Scope description must be at least 20 characters long")
        return v.strip()


# JSON validation and formatting utilities

def validate_json_structure(json_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate JSON string structure and format
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse JSON
        data = json.loads(json_str)
        
        # Validate it's a dictionary
        if not isinstance(data, dict):
            return False, "JSON must be an object/dictionary"
        
        # Try to create PlanningOutput from the data
        planning_output = PlanningOutput(**data)
        
        logger.info("JSON validation successful")
        return True, None
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON format: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"JSON validation failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def format_planning_json(planning_output: PlanningOutput) -> str:
    """
    Format PlanningOutput as pretty JSON string
    
    Args:
        planning_output: PlanningOutput instance
        
    Returns:
        Formatted JSON string
    """
    try:
        # Convert to dict and then to formatted JSON
        data = planning_output.dict()
        formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
        
        logger.info("JSON formatting successful")
        return formatted_json
        
    except Exception as e:
        logger.error(f"JSON formatting failed: {str(e)}")
        raise


def create_default_planning_output(user_query: str) -> PlanningOutput:
    """
    Create a default PlanningOutput when evaluation fails
    
    Args:
        user_query: Original user query
        
    Returns:
        Default PlanningOutput instance
    """
    try:
        # Extract basic keywords from user query
        basic_keywords = [word.strip() for word in user_query.split() if len(word.strip()) > 2][:5]
        
        if not basic_keywords:
            basic_keywords = ["general", "research"]
        
        default_output = PlanningOutput(
            search_categories=["基础信息搜索", "相关资料收集"],
            keywords=basic_keywords + ["相关信息", "基础资料"],
            search_angles=[
                "基本概念和定义",
                "相关背景信息",
                "主要特点和特征"
            ],
            data_sources=DataSourceCategory(
                academic_sources=["学术论文", "研究报告"],
                industry_sources=["行业资讯", "公司信息"],
                regulatory_sources=["相关政策", "行业标准"],
                market_sources=["市场信息", "统计数据"]
            ),
            priority=PriorityLevel.MEDIUM,
            scope="基于用户查询进行基础信息搜索和资料收集，涵盖相关领域的基本概念、背景信息和主要特征，为后续深入研究提供基础支撑",
            estimated_complexity="simple"
        )
        
        logger.info("Created default planning output")
        return default_output
        
    except Exception as e:
        logger.error(f"Failed to create default planning output: {str(e)}")
        raise


def repair_json_format(malformed_json: str) -> str:
    """
    Attempt to repair common JSON formatting issues
    
    Args:
        malformed_json: Potentially malformed JSON string
        
    Returns:
        Repaired JSON string
    """
    try:
        # Common repairs
        repaired = malformed_json.strip()
        
        # Remove markdown code blocks if present
        if repaired.startswith("```json"):
            repaired = repaired[7:]
        if repaired.startswith("```"):
            repaired = repaired[3:]
        if repaired.endswith("```"):
            repaired = repaired[:-3]
        
        # Remove leading/trailing whitespace
        repaired = repaired.strip()
        
        # Try to parse - if successful, return formatted version
        data = json.loads(repaired)
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.warning(f"JSON repair failed: {str(e)}")
        return malformed_json


# Export main classes and functions
__all__ = [
    'RequirementEvaluation',
    'PlanningOutput', 
    'DataSourceCategory',
    'PriorityLevel',
    'validate_json_structure',
    'format_planning_json',
    'create_default_planning_output',
    'repair_json_format'
]