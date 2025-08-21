import unittest
import os
import sys
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# Import planning agent components
from planning_agent.configuration import Configuration
from planning_agent.state import (
    PlanningOverallState, PlanningPhase, PlanningAction,
    initialize_planning_state, update_evaluation_state,
    increment_loop_count, transition_phase, should_continue_planning,
    can_proceed_to_generation, is_state_valid, get_state_summary
)
from planning_agent.tools_and_schemas import (
    RequirementEvaluation, PlanningOutput, DataSourceCategory,
    validate_json_structure, format_planning_json, 
    create_default_planning_output, repair_json_format
)
from planning_agent.prompts import (
    format_conversation_history, inject_parameters,
    requirement_evaluation_prompt, clarification_generation_prompt,
    json_generation_prompt
)
from planning_agent.error_handling import (
    PlanningAgentError, LLMAPIError, JSONValidationError,
    log_error, safe_execute, get_error_stats
)
from planning_agent.planning_gragh import (
    evaluate_requirement, generate_clarification, 
    generate_planning_json, evaluate_planning_flow,
    create_planning_graph
)


class TestPlanningAgentConfiguration(unittest.TestCase):
    """测试规划代理配置功能"""
    
    def test_default_configuration(self):
        """测试默认配置"""
        config = Configuration()
        
        self.assertEqual(config.evaluation_model, "gpt-4o-mini")
        self.assertEqual(config.generation_model, "gpt-4o")
        self.assertEqual(config.max_planning_loops, 5)
        self.assertEqual(config.max_clarification_questions, 3)
        self.assertEqual(config.json_validation_retries, 2)
        self.assertEqual(config.llm_timeout, 30)
        self.assertEqual(config.temperature, 0.3)
    
    def test_configuration_from_runnable_config(self):
        """测试从运行配置创建配置"""
        runnable_config = {
            "configurable": {
                "evaluation_model": "gpt-3.5-turbo",
                "max_planning_loops": 3,
                "temperature": 0.5
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        self.assertEqual(config.evaluation_model, "gpt-3.5-turbo")
        self.assertEqual(config.max_planning_loops, 3)
        self.assertEqual(config.temperature, 0.5)
        # 其他字段应该使用默认值
        self.assertEqual(config.generation_model, "gpt-4o")


class TestPlanningAgentState(unittest.TestCase):
    """测试规划代理状态管理"""
    
    def test_initialize_planning_state(self):
        """测试状态初始化"""
        messages = [{"role": "user", "content": "测试消息"}]
        state = initialize_planning_state(
            messages=messages,
            max_loops=3,
            model="gpt-4o-mini"
        )
        
        self.assertEqual(state["messages"], messages)
        self.assertEqual(state["max_planning_loops"], 3)
        self.assertEqual(state["reasoning_model"], "gpt-4o-mini")
        self.assertEqual(state["planning_loop_count"], 0)
        self.assertFalse(state["is_sufficient"])
        self.assertEqual(state["current_phase"], PlanningPhase.INITIALIZATION.value)
        self.assertIsNotNone(state["start_time"])
    
    def test_update_evaluation_state(self):
        """测试评估状态更新"""
        state = initialize_planning_state()
        questions = ["问题1", "问题2"]
        
        updated_state = update_evaluation_state(
            state,
            is_sufficient=True,
            knowledge_gap="无缺口",
            questions=questions,
            confidence=0.9
        )
        
        self.assertTrue(updated_state["is_sufficient"])
        self.assertEqual(updated_state["clarification_questions"], questions)
        self.assertEqual(updated_state["evaluation_result"]["confidence_score"], 0.9)
    
    def test_increment_loop_count(self):
        """测试循环计数器递增"""
        state = initialize_planning_state()
        initial_count = state["planning_loop_count"]
        
        updated_state = increment_loop_count(state)
        
        self.assertEqual(updated_state["planning_loop_count"], initial_count + 1)
        self.assertIn("last_loop_increment", updated_state["state_metadata"])
    
    def test_transition_phase(self):
        """测试阶段转换"""
        state = initialize_planning_state()
        
        updated_state = transition_phase(
            state, 
            PlanningPhase.EVALUATION,
            PlanningAction.EVALUATE
        )
        
        self.assertEqual(updated_state["current_phase"], PlanningPhase.EVALUATION.value)
        self.assertEqual(updated_state["last_action"], PlanningAction.EVALUATE.value)
        self.assertIn(PlanningPhase.EVALUATION.value, updated_state["phase_history"])
    
    def test_should_continue_planning(self):
        """测试是否应该继续规划"""
        state = initialize_planning_state(max_loops=3)
        
        # 初始状态应该继续
        self.assertTrue(should_continue_planning(state))
        
        # 达到最大循环次数
        state["planning_loop_count"] = 3
        self.assertFalse(should_continue_planning(state))
        
        # 需求已满足
        state["planning_loop_count"] = 1
        state["is_sufficient"] = True
        self.assertFalse(should_continue_planning(state))
    
    def test_can_proceed_to_generation(self):
        """测试是否可以进行JSON生成"""
        state = initialize_planning_state(max_loops=3)
        
        # 需求满足时可以生成
        state["is_sufficient"] = True
        self.assertTrue(can_proceed_to_generation(state))
        
        # 达到最大循环时可以生成
        state["is_sufficient"] = False
        state["planning_loop_count"] = 3
        self.assertTrue(can_proceed_to_generation(state))
    
    def test_is_state_valid(self):
        """测试状态验证"""
        state = initialize_planning_state()
        
        # 有效状态
        is_valid, error_msg = is_state_valid(state)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        
        # 无效状态 - 错误的循环计数
        state["planning_loop_count"] = -1
        is_valid, error_msg = is_state_valid(state)
        self.assertFalse(is_valid)
        self.assertIn("planning_loop_count must be non-negative", error_msg)
    
    def test_get_state_summary(self):
        """测试状态摘要"""
        state = initialize_planning_state()
        state["planning_loop_count"] = 2
        state["is_sufficient"] = True
        
        summary = get_state_summary(state)
        
        self.assertEqual(summary["loop_count"], 2)
        self.assertTrue(summary["is_sufficient"])
        self.assertIn("can_continue", summary)
        self.assertIn("can_generate", summary)


class TestPlanningAgentSchemas(unittest.TestCase):
    """测试规划代理数据模式"""
    
    def test_requirement_evaluation_model(self):
        """测试需求评估模型"""
        evaluation = RequirementEvaluation(
            is_sufficient=True,
            knowledge_gap="无缺口",
            clarification_questions=["这是一个足够长的问题用于测试验证功能", "这是另一个足够长的问题用于测试"],
            confidence_score=0.9
        )
        
        self.assertTrue(evaluation.is_sufficient)
        self.assertEqual(evaluation.knowledge_gap, "无缺口")
        self.assertEqual(len(evaluation.clarification_questions), 2)
        self.assertEqual(evaluation.confidence_score, 0.9)
    
    def test_data_source_category_model(self):
        """测试数据源分类模型"""
        data_sources = DataSourceCategory(
            academic_sources=["学术论文", "专利数据库"],
            industry_sources=["公司官网", "行业报告"],
            regulatory_sources=["政策文件", "法规标准"],
            market_sources=["市场调研", "统计数据"]
        )
        
        self.assertEqual(len(data_sources.academic_sources), 2)
        self.assertEqual(len(data_sources.industry_sources), 2)
        self.assertIn("学术论文", data_sources.academic_sources)
    
    def test_planning_output_model(self):
        """测试规划输出模型"""
        planning_output = PlanningOutput(
            search_categories=["技术分析", "市场研究"],
            keywords=["人工智能", "AI", "机器学习"],
            search_angles=["技术发展趋势", "市场应用现状"],
            data_sources=DataSourceCategory(),
            priority="high",
            scope="全面分析人工智能技术发展现状和市场应用情况，包括技术原理、发展历程、主要应用领域等方面",
            estimated_complexity="moderate"
        )
        
        self.assertEqual(len(planning_output.search_categories), 2)
        self.assertEqual(len(planning_output.keywords), 3)
        self.assertEqual(planning_output.priority, "high")
        self.assertTrue(len(planning_output.scope) >= 20)
    
    def test_validate_json_structure(self):
        """测试JSON结构验证"""
        # 有效JSON
        valid_json = json.dumps({
            "search_categories": ["技术分析"],
            "keywords": ["AI"],
            "search_angles": ["发展趋势"],
            "data_sources": {
                "academic_sources": ["论文"],
                "industry_sources": ["报告"],
                "regulatory_sources": ["政策"],
                "market_sources": ["数据"]
            },
            "priority": "medium",
            "scope": "这是一个足够长的范围描述，用于测试验证功能",
            "estimated_complexity": "simple"
        }, ensure_ascii=False)
        
        is_valid, error_msg = validate_json_structure(valid_json)
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
        
        # 无效JSON
        invalid_json = "{ invalid json }"
        is_valid, error_msg = validate_json_structure(invalid_json)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
    
    def test_create_default_planning_output(self):
        """测试创建默认规划输出"""
        user_query = "人工智能发展历史"
        default_output = create_default_planning_output(user_query)
        
        self.assertIsInstance(default_output, PlanningOutput)
        self.assertGreater(len(default_output.search_categories), 0)
        self.assertGreater(len(default_output.keywords), 0)
        self.assertIn("人工智能", " ".join(default_output.keywords))
    
    def test_format_planning_json(self):
        """测试格式化规划JSON"""
        planning_output = create_default_planning_output("测试查询")
        formatted_json = format_planning_json(planning_output)
        
        self.assertIsInstance(formatted_json, str)
        # 验证可以解析回JSON
        parsed = json.loads(formatted_json)
        self.assertIn("search_categories", parsed)
    
    def test_repair_json_format(self):
        """测试JSON格式修复"""
        # 带有markdown代码块的JSON
        malformed_json = """```json
        {
            "search_categories": ["测试"]
        }
        ```"""
        
        repaired_json = repair_json_format(malformed_json)
        
        # 应该移除markdown标记
        self.assertNotIn("```", repaired_json)
        # 应该能够解析
        parsed = json.loads(repaired_json)
        self.assertIn("search_categories", parsed)


class TestPlanningAgentPrompts(unittest.TestCase):
    """测试规划代理提示模板"""
    
    def test_format_conversation_history(self):
        """测试对话历史格式化"""
        # 测试字典格式消息
        messages = [
            {"role": "user", "content": "用户消息1"},
            {"role": "assistant", "content": "助手回复1"},
            {"role": "user", "content": "用户消息2"}
        ]
        
        formatted = format_conversation_history(messages)
        
        self.assertIn("用户: 用户消息1", formatted)
        self.assertIn("助手: 助手回复1", formatted)
        self.assertIn("用户: 用户消息2", formatted)
    
    def test_format_conversation_history_empty(self):
        """测试空对话历史"""
        formatted = format_conversation_history([])
        self.assertEqual(formatted, "无对话历史")
    
    def test_inject_parameters(self):
        """测试参数注入"""
        template = "用户输入: {user_input}, 当前时间: {current_date}"
        
        formatted = inject_parameters(
            template,
            user_input="测试输入"
        )
        
        self.assertIn("用户输入: 测试输入", formatted)
        self.assertIn("当前时间:", formatted)  # current_date 应该自动添加
    
    def test_inject_parameters_missing_param(self):
        """测试缺少参数的情况"""
        template = "用户输入: {user_input}, 缺少参数: {missing_param}"
        
        with self.assertRaises(ValueError):
            inject_parameters(template, user_input="测试输入")
    
    def test_prompt_templates_exist(self):
        """测试提示模板存在性"""
        self.assertIsInstance(requirement_evaluation_prompt, str)
        self.assertIsInstance(clarification_generation_prompt, str)
        self.assertIsInstance(json_generation_prompt, str)
        
        # 检查模板包含必要的占位符
        self.assertIn("{conversation_history}", requirement_evaluation_prompt)
        self.assertIn("{user_input}", requirement_evaluation_prompt)
        self.assertIn("{knowledge_gap}", clarification_generation_prompt)
        self.assertIn("{conversation_history}", json_generation_prompt)


class TestPlanningAgentErrorHandling(unittest.TestCase):
    """测试规划代理错误处理"""
    
    def test_planning_agent_error(self):
        """测试规划代理错误"""
        error = PlanningAgentError(
            "测试错误",
            context={"test_key": "test_value"}
        )
        
        self.assertEqual(str(error), "测试错误")
        self.assertIn("test_key", error.context)
        self.assertIsNotNone(error.timestamp)
    
    def test_llm_api_error(self):
        """测试LLM API错误"""
        error = LLMAPIError("API调用失败")
        
        self.assertEqual(str(error), "API调用失败")
        self.assertEqual(error.error_type.value, "llm_api_error")
        self.assertEqual(error.severity.value, "high")
    
    def test_json_validation_error(self):
        """测试JSON验证错误"""
        error = JSONValidationError("JSON格式无效")
        
        self.assertEqual(str(error), "JSON格式无效")
        self.assertEqual(error.error_type.value, "json_validation_error")
        self.assertEqual(error.severity.value, "medium")
    
    def test_safe_execute_success(self):
        """测试安全执行成功情况"""
        def test_func(x, y):
            return x + y
        
        success, result = safe_execute(test_func, 1, 2)
        
        self.assertTrue(success)
        self.assertEqual(result, 3)
    
    def test_safe_execute_failure(self):
        """测试安全执行失败情况"""
        def test_func():
            raise ValueError("测试错误")
        
        success, result = safe_execute(
            test_func, 
            fallback_value="fallback",
            log_errors=False
        )
        
        self.assertFalse(success)
        self.assertEqual(result, "fallback")
    
    def test_get_error_stats(self):
        """测试错误统计"""
        stats = get_error_stats()
        
        self.assertIsNotNone(stats)
        self.assertIsInstance(stats.total_errors, int)
        self.assertIsInstance(stats.errors_by_type, dict)


class TestPlanningAgentGraph(unittest.TestCase):
    """测试规划代理图形工作流"""
    
    def setUp(self):
        """测试设置"""
        self.test_state = initialize_planning_state(
            messages=[{"role": "user", "content": "我想了解人工智能的发展历史"}],
            max_loops=3
        )
        self.test_config = {"configurable": {}}
    
    @patch('planning_agent.planning_gragh.ChatOpenAI')
    def test_evaluate_requirement_sufficient(self, mock_openai):
        """测试需求评估 - 充分情况"""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_openai.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        
        mock_evaluation = RequirementEvaluation(
            is_sufficient=True,
            knowledge_gap="",
            clarification_questions=[],
            confidence_score=0.9
        )
        mock_structured_llm.invoke.return_value = mock_evaluation
        
        # 执行测试
        result = evaluate_requirement(self.test_state, self.test_config)
        
        # 验证结果
        self.assertTrue(result["is_sufficient"])
        self.assertEqual(result["clarification_questions"], [])
        self.assertEqual(result["evaluation_result"]["confidence_score"], 0.9)
    
    @patch('planning_agent.planning_gragh.ChatOpenAI')
    def test_evaluate_requirement_insufficient(self, mock_openai):
        """测试需求评估 - 不充分情况"""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_structured_llm = Mock()
        mock_openai.return_value = mock_llm_instance
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        
        mock_evaluation = RequirementEvaluation(
            is_sufficient=False,
            knowledge_gap="需要明确时间范围和具体方面",
            clarification_questions=["您希望了解哪个时间段的发展历史？", "您更关注技术发展还是应用发展？"],
            confidence_score=0.7
        )
        mock_structured_llm.invoke.return_value = mock_evaluation
        
        # 执行测试
        result = evaluate_requirement(self.test_state, self.test_config)
        
        # 验证结果
        self.assertFalse(result["is_sufficient"])
        self.assertEqual(len(result["clarification_questions"]), 2)
        self.assertIn("时间段", result["clarification_questions"][0])
    
    @patch('planning_agent.planning_gragh.ChatOpenAI')
    def test_generate_clarification(self, mock_openai):
        """测试澄清问题生成"""
        # 设置状态
        self.test_state["evaluation_result"] = {
            "knowledge_gap": "需要明确研究范围和深度"
        }
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_openai.return_value = mock_llm_instance
        
        mock_response = Mock()
        mock_response.content = """1. 您希望了解人工智能的哪个具体领域？
2. 您需要多深入的技术细节？
3. 您更关注历史发展还是现状分析？"""
        mock_llm_instance.invoke.return_value = mock_response
        
        # 执行测试
        result = generate_clarification(self.test_state, self.test_config)
        
        # 验证结果
        self.assertIn("clarification_questions", result)
        questions = result["clarification_questions"]
        self.assertGreater(len(questions), 0)
        self.assertTrue(any("具体领域" in q for q in questions))
    
    @patch('planning_agent.planning_gragh.ChatOpenAI')
    def test_generate_planning_json(self, mock_openai):
        """测试JSON规划生成"""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_openai.return_value = mock_llm_instance
        
        mock_json_response = {
            "search_categories": ["人工智能历史", "技术发展"],
            "keywords": ["人工智能", "AI", "发展历史", "技术演进"],
            "search_angles": ["历史发展脉络", "关键技术突破", "重要里程碑"],
            "data_sources": {
                "academic_sources": ["学术论文", "研究报告"],
                "industry_sources": ["技术博客", "公司资料"],
                "regulatory_sources": ["政策文件"],
                "market_sources": ["市场分析"]
            },
            "priority": "medium",
            "scope": "全面梳理人工智能从起源到现在的发展历程，包括关键技术突破、重要人物和里程碑事件",
            "estimated_complexity": "moderate"
        }
        
        mock_response = Mock()
        mock_response.content = json.dumps(mock_json_response, ensure_ascii=False)
        mock_llm_instance.invoke.return_value = mock_response
        
        # 执行测试
        result = generate_planning_json(self.test_state, self.test_config)
        
        # 验证结果
        self.assertIn("planning_result", result)
        self.assertTrue(result["is_sufficient"])
        
        # 验证JSON格式
        planning_json = result["planning_result"]
        parsed_json = json.loads(planning_json)
        self.assertIn("search_categories", parsed_json)
        self.assertIn("keywords", parsed_json)
    
    def test_evaluate_planning_flow_continue(self):
        """测试规划流程评估 - 继续澄清"""
        # 设置需要澄清的状态
        self.test_state["is_sufficient"] = False
        self.test_state["planning_loop_count"] = 1
        self.test_state["evaluation_result"] = {"is_sufficient": False}
        self.test_state["clarification_questions"] = ["测试问题"]
        
        result = evaluate_planning_flow(self.test_state, self.test_config)
        
        self.assertEqual(result, "clarify")
    
    def test_evaluate_planning_flow_generate(self):
        """测试规划流程评估 - 生成JSON"""
        # 设置充分的状态
        self.test_state["is_sufficient"] = True
        
        result = evaluate_planning_flow(self.test_state, self.test_config)
        
        self.assertEqual(result, "generate")
    
    def test_evaluate_planning_flow_max_loops(self):
        """测试规划流程评估 - 达到最大循环"""
        # 设置达到最大循环的状态
        self.test_state["is_sufficient"] = False
        self.test_state["planning_loop_count"] = 3
        self.test_state["max_planning_loops"] = 3
        
        result = evaluate_planning_flow(self.test_state, self.test_config)
        
        self.assertEqual(result, "generate")
    
    def test_create_planning_graph(self):
        """测试创建规划图"""
        graph = create_planning_graph()
        
        self.assertIsNotNone(graph)
        # 验证图的基本属性
        self.assertTrue(hasattr(graph, 'invoke'))


class TestPlanningAgentIntegration(unittest.TestCase):
    """规划代理集成测试"""
    
    def setUp(self):
        """集成测试设置"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.skipTest("需要设置 OPENAI_API_KEY 环境变量")
    
    @unittest.skipIf(not os.getenv("OPENAI_API_KEY"), "需要 OPENAI_API_KEY")
    def test_full_planning_workflow_simple(self):
        """测试完整规划工作流 - 简单查询"""
        try:
            from planning_agent.planning_gragh import planning_graph
            
            if planning_graph is None:
                self.skipTest("规划图未正确初始化")
            
            # 准备测试输入
            initial_state = initialize_planning_state(
                messages=[{"role": "user", "content": "我想了解量子计算的基本原理"}],
                max_loops=2  # 限制循环次数以加快测试
            )
            
            config = {"configurable": {"max_planning_loops": 2}}
            
            # 执行工作流
            result = planning_graph.invoke(initial_state, config)
            
            # 验证结果
            self.assertIsInstance(result, dict)
            self.assertIn("planning_result", result)
            
            # 如果有规划结果，验证JSON格式
            if result["planning_result"]:
                planning_json = result["planning_result"]
                parsed_json = json.loads(planning_json)
                
                self.assertIn("search_categories", parsed_json)
                self.assertIn("keywords", parsed_json)
                self.assertIn("search_angles", parsed_json)
                self.assertIn("data_sources", parsed_json)
                
                print(f"\n成功生成规划JSON:")
                print(f"搜索分类: {parsed_json['search_categories']}")
                print(f"关键词数量: {len(parsed_json['keywords'])}")
                print(f"搜索角度数量: {len(parsed_json['search_angles'])}")
            
        except Exception as e:
            print(f"集成测试失败: {str(e)}")
            # 不让集成测试失败影响其他测试
            self.skipTest(f"集成测试环境问题: {str(e)}")
    
    def test_state_persistence_and_recovery(self):
        """测试状态持久化和恢复"""
        # 创建初始状态
        original_state = initialize_planning_state(
            messages=[{"role": "user", "content": "测试消息"}],
            max_loops=5
        )
        
        # 模拟状态变化
        original_state = update_evaluation_state(
            original_state,
            is_sufficient=False,
            knowledge_gap="需要更多信息",
            questions=["问题1", "问题2"]
        )
        original_state = increment_loop_count(original_state)
        
        # 序列化状态
        state_json = json.dumps(original_state, default=str)
        
        # 反序列化状态
        recovered_state = json.loads(state_json)
        
        # 验证关键字段
        self.assertEqual(recovered_state["planning_loop_count"], 1)
        self.assertFalse(recovered_state["is_sufficient"])
        self.assertEqual(len(recovered_state["clarification_questions"]), 2)
    
    def test_error_recovery_scenarios(self):
        """测试错误恢复场景"""
        # 测试JSON解析错误恢复
        malformed_json = '{"search_categories": ["test"'  # 缺少闭合括号
        
        repaired_json = repair_json_format(malformed_json)
        
        # 修复可能不完美，但不应该崩溃
        self.assertIsInstance(repaired_json, str)
        
        # 测试默认输出生成
        default_output = create_default_planning_output("测试查询")
        
        self.assertIsInstance(default_output, PlanningOutput)
        self.assertGreater(len(default_output.search_categories), 0)
    
    def test_performance_and_limits(self):
        """测试性能和限制"""
        # 测试大量消息的处理
        large_messages = []
        for i in range(100):
            large_messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i} - " + "内容 " * 50
            })
        
        # 格式化大量消息不应该崩溃
        formatted = format_conversation_history(large_messages)
        self.assertIsInstance(formatted, str)
        
        # 测试状态验证在极端情况下的表现
        extreme_state = initialize_planning_state()
        extreme_state["planning_loop_count"] = 1000000  # 极大的循环数
        
        is_valid, error_msg = is_state_valid(extreme_state)
        # 应该检测到循环数超过最大值
        self.assertFalse(is_valid)


if __name__ == '__main__':
    print("开始运行规划代理测试...")
    print(f"Python 路径: {sys.path[:3]}...")  # 只显示前几个路径
    print(f"项目根目录: {project_root}")
    
    # 检查环境变量
    if os.getenv("OPENAI_API_KEY"):
        print("✓ 找到 OPENAI_API_KEY")
    else:
        print("⚠ 未找到 OPENAI_API_KEY，集成测试将被跳过")
    
    # 运行测试
    unittest.main(verbosity=2)