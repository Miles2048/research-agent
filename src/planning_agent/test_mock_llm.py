"""
Mock LLM Testing Tools for Planning Agent

提供模拟LLM响应的测试工具，支持不同场景的测试而无需实际API调用
"""

import json
import random
from typing import Dict, Any, List, Optional, Union, Callable
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum

from .tools_and_schemas import RequirementEvaluation, PlanningOutput, DataSourceCategory


class MockResponseType(Enum):
    """模拟响应类型枚举"""
    SUFFICIENT_REQUIREMENT = "sufficient_requirement"
    INSUFFICIENT_REQUIREMENT = "insufficient_requirement"
    CLARIFICATION_QUESTIONS = "clarification_questions"
    VALID_JSON_OUTPUT = "valid_json_output"
    INVALID_JSON_OUTPUT = "invalid_json_output"
    ERROR_RESPONSE = "error_response"
    TIMEOUT_RESPONSE = "timeout_response"


@dataclass
class MockLLMResponse:
    """模拟LLM响应结构"""
    content: str
    response_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.response_metadata is None:
            self.response_metadata = {
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model_name": "mock-gpt-4o-mini",
                "finish_reason": "stop"
            }


class MockLLMProvider:
    """
    模拟LLM提供者，用于测试不同响应场景
    """
    
    def __init__(self, response_type: MockResponseType = MockResponseType.SUFFICIENT_REQUIREMENT):
        self.response_type = response_type
        self.call_count = 0
        self.call_history = []
        self.custom_responses = {}
        self.error_probability = 0.0
        self.delay_simulation = False
        
    def set_response_type(self, response_type: MockResponseType):
        """设置响应类型"""
        self.response_type = response_type
        
    def set_custom_response(self, response_type: MockResponseType, content: str):
        """设置自定义响应内容"""
        self.custom_responses[response_type] = content
        
    def set_error_probability(self, probability: float):
        """设置错误概率 (0.0 到 1.0)"""
        self.error_probability = max(0.0, min(1.0, probability))
        
    def enable_delay_simulation(self, enabled: bool = True):
        """启用/禁用延迟模拟"""
        self.delay_simulation = enabled
        
    def invoke(self, prompt: str) -> MockLLMResponse:
        """
        模拟LLM调用
        
        Args:
            prompt: 输入提示词
            
        Returns:
            MockLLMResponse: 模拟响应
        """
        self.call_count += 1
        self.call_history.append({
            "call_number": self.call_count,
            "prompt": prompt,
            "response_type": self.response_type
        })
        
        # 模拟延迟
        if self.delay_simulation:
            import time
            time.sleep(0.1)
            
        # 模拟随机错误
        if random.random() < self.error_probability:
            raise Exception("Simulated LLM API error")
            
        # 生成响应内容
        if self.response_type in self.custom_responses:
            content = self.custom_responses[self.response_type]
        else:
            content = self._generate_mock_content(self.response_type, prompt)
            
        return MockLLMResponse(content=content)
    
    def with_structured_output(self, schema_class):
        """
        模拟结构化输出功能
        
        Args:
            schema_class: Pydantic模型类
            
        Returns:
            返回结构化响应的模拟对象
        """
        mock_structured = Mock()
        mock_structured.invoke = lambda prompt: self._generate_structured_response(schema_class, prompt)
        return mock_structured
    
    def _generate_mock_content(self, response_type: MockResponseType, prompt: str) -> str:
        """根据响应类型生成模拟内容"""
        
        if response_type == MockResponseType.SUFFICIENT_REQUIREMENT:
            return "用户输入已经足够明确，可以直接进行搜索规划生成。"
            
        elif response_type == MockResponseType.INSUFFICIENT_REQUIREMENT:
            return "用户输入需要进一步澄清，缺少关键信息。"
            
        elif response_type == MockResponseType.CLARIFICATION_QUESTIONS:
            return self._generate_clarification_questions()
            
        elif response_type == MockResponseType.VALID_JSON_OUTPUT:
            return self._generate_valid_json_output()
            
        elif response_type == MockResponseType.INVALID_JSON_OUTPUT:
            return self._generate_invalid_json_output()
            
        elif response_type == MockResponseType.ERROR_RESPONSE:
            raise Exception("Simulated LLM processing error")
            
        elif response_type == MockResponseType.TIMEOUT_RESPONSE:
            import time
            time.sleep(2)
            return "Delayed response"
            
        else:
            return "Mock response for testing"
    
    def _generate_structured_response(self, schema_class, prompt: str):
        """生成结构化响应"""
        
        if schema_class == RequirementEvaluation:
            if self.response_type == MockResponseType.SUFFICIENT_REQUIREMENT:
                return RequirementEvaluation(
                    is_sufficient=True,
                    knowledge_gap="",
                    clarification_questions=[],
                    confidence_score=0.9
                )
            else:
                return RequirementEvaluation(
                    is_sufficient=False,
                    knowledge_gap="需要更多关于具体应用场景和技术要求的信息",
                    clarification_questions=[
                        "您主要关注哪个具体的应用领域？",
                        "您需要了解技术原理还是市场应用？",
                        "您希望获得什么深度的信息？"
                    ],
                    confidence_score=0.7
                )
                
        elif schema_class == PlanningOutput:
            return self._generate_planning_output_object()
            
        else:
            return Mock()
    
    def _generate_clarification_questions(self) -> str:
        """生成澄清问题"""
        questions = [
            "请问您主要关注哪个具体的技术领域或应用场景？",
            "您希望了解基础概念还是深入的技术细节？",
            "您需要的信息主要用于什么目的？",
            "您对时间范围有特定要求吗？"
        ]
        
        selected_questions = random.sample(questions, random.randint(2, 3))
        return "\n".join([f"{i+1}. {q}" for i, q in enumerate(selected_questions)])
    
    def _generate_valid_json_output(self) -> str:
        """生成有效的JSON输出"""
        planning_data = {
            "search_categories": [
                "技术原理分析",
                "市场应用研究", 
                "发展趋势预测"
            ],
            "keywords": [
                "人工智能",
                "机器学习",
                "AI applications",
                "技术发展"
            ],
            "search_angles": [
                "AI技术的核心原理和算法机制",
                "当前主流AI技术的应用领域",
                "AI技术发展的历史脉络和未来趋势"
            ],
            "data_sources": {
                "academic_sources": [
                    "IEEE人工智能相关期刊和会议论文",
                    "Nature、Science等顶级期刊的AI研究"
                ],
                "industry_sources": [
                    "Google、OpenAI等公司技术博客",
                    "科技公司的AI产品官方文档"
                ],
                "regulatory_sources": [
                    "各国AI治理政策和法规文件",
                    "AI伦理和安全相关的监管指导"
                ],
                "market_sources": [
                    "Gartner、IDC等机构的AI市场报告",
                    "投资机构的AI行业分析"
                ]
            },
            "priority": "high",
            "scope": "全面分析人工智能技术的发展现状、应用前景和市场机遇",
            "estimated_complexity": "complex"
        }
        
        return f"```json\n{json.dumps(planning_data, ensure_ascii=False, indent=2)}\n```"
    
    def _generate_invalid_json_output(self) -> str:
        """生成无效的JSON输出用于错误测试"""
        return """
        ```json
        {
            "search_categories": [
                "基础搜索",
                "相关分析"
            ],
            "keywords": ["测试", "关键词"],
            "search_angles": [
                "基本信息收集"
            ],
            "data_sources": {
                "academic_sources": ["学术资料"]
                // Missing comma and closing braces
        ```
        """
    
    def _generate_planning_output_object(self) -> PlanningOutput:
        """生成PlanningOutput对象"""
        return PlanningOutput(
            search_categories=["技术分析", "市场研究"],
            keywords=["AI", "机器学习", "技术发展"],
            search_angles=["技术原理", "应用场景", "发展趋势"],
            data_sources=DataSourceCategory(
                academic_sources=["学术论文", "研究报告"],
                industry_sources=["公司博客", "技术文档"],
                regulatory_sources=["政策文件", "法规标准"],
                market_sources=["市场报告", "行业分析"]
            ),
            priority="medium",
            scope="基于用户需求进行技术和市场分析",
            estimated_complexity="moderate"
        )
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """获取调用历史"""
        return self.call_history
    
    def reset(self):
        """重置模拟器状态"""
        self.call_count = 0
        self.call_history = []
        self.custom_responses = {}
        self.error_probability = 0.0
        self.delay_simulation = False


def create_mock_llm_patch(mock_provider: MockLLMProvider):
    """
    创建LLM模拟补丁，用于在测试中替换真实的LLM调用
    
    Args:
        mock_provider: 模拟LLM提供者实例
        
    Returns:
        可用于with语句的patch对象
    """
    return patch('planning_agent.planning_gragh.ChatOpenAI', return_value=mock_provider)


def create_test_state(
    messages: List[Dict[str, str]] = None,
    planning_loop_count: int = 0,
    is_sufficient: bool = False,
    max_planning_loops: int = 5
) -> Dict[str, Any]:
    """
    创建测试用的状态对象
    
    Args:
        messages: 对话消息列表
        planning_loop_count: 当前循环计数
        is_sufficient: 是否足够明确
        max_planning_loops: 最大循环次数
        
    Returns:
        测试状态字典
    """
    if messages is None:
        messages = [{"role": "user", "content": "我想了解人工智能技术"}]
    
    return {
        "messages": messages,
        "planning_result": "",
        "evaluation_result": {},
        "clarification_questions": [],
        "planning_loop_count": planning_loop_count,
        "max_planning_loops": max_planning_loops,
        "is_sufficient": is_sufficient,
        "reasoning_model": "gpt-4o-mini",
        "current_phase": "evaluation",
        "last_action": "",
        "error_count": 0,
        "max_errors": 3,
        "start_time": None,
        "phase_history": ["initialization"],
        "state_metadata": {}
    }


def create_test_config() -> Dict[str, Any]:
    """
    创建测试用的配置对象
    
    Returns:
        测试配置字典
    """
    return {
        "configurable": {
            "evaluation_model": "gpt-4o-mini",
            "generation_model": "gpt-4o",
            "temperature": 0.3,
            "max_planning_loops": 5,
            "max_clarification_questions": 3,
            "json_validation_retries": 2,
            "llm_timeout": 30
        }
    }


# 预定义的测试场景
class TestScenarios:
    """预定义的测试场景"""
    
    @staticmethod
    def sufficient_requirement_scenario():
        """需求充分的测试场景"""
        mock_provider = MockLLMProvider(MockResponseType.SUFFICIENT_REQUIREMENT)
        state = create_test_state(
            messages=[{"role": "user", "content": "我需要了解人工智能在医疗领域的应用现状、技术挑战和发展前景，重点关注深度学习在医学影像诊断中的应用"}]
        )
        config = create_test_config()
        return mock_provider, state, config
    
    @staticmethod
    def insufficient_requirement_scenario():
        """需求不充分的测试场景"""
        mock_provider = MockLLMProvider(MockResponseType.INSUFFICIENT_REQUIREMENT)
        state = create_test_state(
            messages=[{"role": "user", "content": "AI"}]
        )
        config = create_test_config()
        return mock_provider, state, config
    
    @staticmethod
    def json_generation_scenario():
        """JSON生成测试场景"""
        mock_provider = MockLLMProvider(MockResponseType.VALID_JSON_OUTPUT)
        state = create_test_state(
            messages=[
                {"role": "user", "content": "我想了解人工智能技术"},
                {"role": "assistant", "content": "请问您主要关注哪个应用领域？"},
                {"role": "user", "content": "主要关注医疗领域的应用"}
            ],
            is_sufficient=True
        )
        config = create_test_config()
        return mock_provider, state, config
    
    @staticmethod
    def error_handling_scenario():
        """错误处理测试场景"""
        mock_provider = MockLLMProvider(MockResponseType.ERROR_RESPONSE)
        mock_provider.set_error_probability(1.0)  # 100%错误率
        state = create_test_state()
        config = create_test_config()
        return mock_provider, state, config
    
    @staticmethod
    def max_loops_scenario():
        """最大循环次数测试场景"""
        mock_provider = MockLLMProvider(MockResponseType.INSUFFICIENT_REQUIREMENT)
        state = create_test_state(
            planning_loop_count=4,  # 接近最大循环次数
            max_planning_loops=5
        )
        config = create_test_config()
        return mock_provider, state, config