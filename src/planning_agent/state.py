from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, Dict, List, Any, Optional, Union
from enum import Enum

from langgraph.graph import add_messages
from typing_extensions import Annotated

import operator


class PlanningPhase(Enum):
    """Enumeration of planning workflow phases"""
    INITIALIZATION = "initialization"
    EVALUATION = "evaluation"
    CLARIFICATION = "clarification"
    GENERATION = "generation"
    VALIDATION = "validation"
    COMPLETION = "completion"
    ERROR = "error"


class PlanningAction(Enum):
    """Enumeration of possible next actions in planning workflow"""
    EVALUATE = "evaluate"
    CLARIFY = "clarify"
    GENERATE = "generate"
    VALIDATE = "validate"
    END = "end"
    RETRY = "retry"


class PlanningOverallState(TypedDict):
    """Main state for the planning agent workflow"""
    messages: Annotated[list, add_messages]  # 对话历史
    planning_result: str  # 最终生成的结果描述
    planning_file_path: str  # planning_list.md文件路径
    planning_data: Dict[str, Any]  # 规划数据（用于内部处理）
    evaluation_result: Dict[str, Any]  # 评估结果
    clarification_questions: List[str]  # 澄清问题列表
    planning_loop_count: int  # 当前循环次数
    max_planning_loops: int  # 最大循环次数
    is_sufficient: bool  # 是否足够明确
    reasoning_model: str  # 使用的模型名称
    current_phase: str  # 当前工作流阶段
    last_action: str  # 上一次执行的动作
    error_count: int  # 错误计数
    max_errors: int  # 最大错误次数
    start_time: Optional[float]  # 开始时间戳
    phase_history: List[str]  # 阶段历史记录
    state_metadata: Dict[str, Any]  # 状态元数据


class PlanningEvaluationState(TypedDict):
    """State for requirement evaluation phase"""
    is_sufficient: bool  # 评估是否通过
    knowledge_gap: str  # 知识缺口描述
    clarification_questions: List[str]  # 澄清问题
    confidence_score: float  # 评估置信度


class PlanningGenerationState(TypedDict):
    """State for JSON generation phase"""
    planning_json: str  # 生成的JSON字符串
    validation_result: bool  # JSON验证结果
    validation_error: Optional[str]  # 验证错误信息
    generation_attempts: int  # 生成尝试次数


class PlanningClarificationState(TypedDict):
    """State for clarification question generation"""
    questions: List[str]  # 生成的澄清问题
    question_count: int  # 问题数量
    target_areas: List[str]  # 需要澄清的目标领域


class PlanningRouterState(TypedDict):
    """State for routing decisions in the workflow"""
    next_action: str  # 下一步动作: evaluate/clarify/generate/end
    should_continue: bool  # 是否继续循环
    exit_reason: Optional[str]  # 退出原因
    routing_confidence: float  # 路由决策置信度
    alternative_actions: List[str]  # 备选动作列表


# Legacy compatibility - keeping original classes for backward compatibility
class OverallState(TypedDict):
    """Legacy state class - use PlanningOverallState instead"""
    messages: Annotated[list, add_messages]
    planning_list: Annotated[list, operator.add]
    planning_current: str
    max_research_loops: int
    planning_loop_count: int
    reasoning_model: str


class ReflectionState(TypedDict):
    """Legacy reflection state - use PlanningEvaluationState instead"""
    is_sufficient: bool
    knowledge_gap: str
    follow_up_queries: Annotated[list, operator.add]
    research_loop_count: int
    number_of_ran_queries: int


class Query(TypedDict):
    """Query structure for search operations"""
    query: str
    rationale: str


class QueryGenerationState(TypedDict):
    """State for query generation"""
    search_query: list[Query]


class WebSearchState(TypedDict):
    """State for web search operations"""
    search_query: str
    id: str


@dataclass(kw_only=True)
class PlanningStateOutput:
    """Output dataclass for planning agent results"""
    planning_json: str = field(default="")  # Final planning JSON
    evaluation_summary: str = field(default="")  # Evaluation summary
    total_iterations: int = field(default=0)  # Total iterations performed
    success: bool = field(default=False)  # Whether planning was successful


@dataclass(kw_only=True)
class SearchStateOutput:
    """Legacy output class - keeping for compatibility"""
    running_summary: str = field(default=None)  # Final report


# State transition utilities
def initialize_planning_state(
    messages: list = None,
    max_loops: int = 5,
    model: str = "claude-3-5-sonnet-20241022",
    max_errors: int = 3
) -> PlanningOverallState:
    """Initialize a new planning state with default values"""
    import time
    return PlanningOverallState(
        messages=messages or [],
        planning_result="",
        planning_file_path="",
        planning_data={},
        evaluation_result={},
        clarification_questions=[],
        planning_loop_count=0,
        max_planning_loops=max_loops,
        is_sufficient=False,
        reasoning_model=model,
        current_phase=PlanningPhase.INITIALIZATION.value,
        last_action="",
        error_count=0,
        max_errors=max_errors,
        start_time=time.time(),
        phase_history=[PlanningPhase.INITIALIZATION.value],
        state_metadata={}
    )


def update_evaluation_state(
    state: PlanningOverallState,
    is_sufficient: bool,
    knowledge_gap: str = "",
    questions: List[str] = None,
    confidence: float = 0.8
) -> PlanningOverallState:
    """Update state with evaluation results"""
    state["is_sufficient"] = is_sufficient
    state["evaluation_result"] = {
        "is_sufficient": is_sufficient,
        "knowledge_gap": knowledge_gap,
        "confidence_score": confidence
    }
    state["clarification_questions"] = questions or []
    return state


def increment_loop_count(state: PlanningOverallState) -> PlanningOverallState:
    """Increment the planning loop counter and update metadata"""
    state["planning_loop_count"] += 1
    state["state_metadata"]["last_loop_increment"] = state["planning_loop_count"]
    return state


def transition_phase(
    state: PlanningOverallState, 
    new_phase: Union[PlanningPhase, str],
    action: Union[PlanningAction, str] = None
) -> PlanningOverallState:
    """Transition to a new phase and record the change"""
    if isinstance(new_phase, PlanningPhase):
        new_phase = new_phase.value
    if isinstance(action, PlanningAction):
        action = action.value
    
    # Record previous phase
    previous_phase = state["current_phase"]
    state["current_phase"] = new_phase
    state["phase_history"].append(new_phase)
    
    if action:
        state["last_action"] = action
    
    # Update metadata
    state["state_metadata"]["previous_phase"] = previous_phase
    state["state_metadata"]["phase_transition_count"] = len(state["phase_history"])
    
    return state


def record_error(state: PlanningOverallState, error_type: str, error_message: str = "") -> PlanningOverallState:
    """Record an error and update error tracking"""
    state["error_count"] += 1
    
    # Initialize error tracking if not exists
    if "errors" not in state["state_metadata"]:
        state["state_metadata"]["errors"] = []
    
    state["state_metadata"]["errors"].append({
        "type": error_type,
        "message": error_message,
        "phase": state["current_phase"],
        "loop_count": state["planning_loop_count"],
        "timestamp": __import__('time').time()
    })
    
    # Transition to error phase if too many errors
    if state["error_count"] >= state["max_errors"]:
        state = transition_phase(state, PlanningPhase.ERROR)
    
    return state


def reset_error_count(state: PlanningOverallState) -> PlanningOverallState:
    """Reset error count after successful operation"""
    state["error_count"] = 0
    return state


def should_continue_planning(state: PlanningOverallState) -> bool:
    """Determine if planning should continue based on current state"""
    # Check basic continuation conditions
    basic_continue = (
        not state["is_sufficient"] and 
        state["planning_loop_count"] < state["max_planning_loops"]
    )
    
    # Check error conditions
    error_continue = state["error_count"] < state["max_errors"]
    
    # Check phase conditions
    phase_continue = state["current_phase"] not in [
        PlanningPhase.COMPLETION.value,
        PlanningPhase.ERROR.value
    ]
    
    return basic_continue and error_continue and phase_continue


def can_proceed_to_generation(state: PlanningOverallState) -> bool:
    """Check if state allows proceeding to JSON generation"""
    return (
        state["is_sufficient"] or 
        state["planning_loop_count"] >= state["max_planning_loops"] or
        state["current_phase"] == PlanningPhase.GENERATION.value
    )


def is_state_valid(state: PlanningOverallState) -> tuple[bool, str]:
    """Validate state consistency and return validation result"""
    errors = []
    
    # Check required fields
    if not isinstance(state.get("messages"), list):
        errors.append("messages must be a list")
    
    if state.get("planning_loop_count", -1) < 0:
        errors.append("planning_loop_count must be non-negative")
    
    if state.get("max_planning_loops", 0) <= 0:
        errors.append("max_planning_loops must be positive")
    
    if state.get("current_phase") not in [phase.value for phase in PlanningPhase]:
        errors.append(f"invalid current_phase: {state.get('current_phase')}")
    
    # Check loop count consistency
    if state.get("planning_loop_count", 0) > state.get("max_planning_loops", 0):
        errors.append("planning_loop_count exceeds max_planning_loops")
    
    return len(errors) == 0, "; ".join(errors)


def finalize_planning_state(
    state: PlanningOverallState,
    planning_json: str,
    success: bool = True
) -> PlanningOverallState:
    """Finalize the planning state with results"""
    state["planning_result"] = planning_json
    state["is_sufficient"] = success
    return state


def create_evaluation_state(
    is_sufficient: bool,
    knowledge_gap: str = "",
    questions: List[str] = None,
    confidence: float = 0.8
) -> PlanningEvaluationState:
    """Create a new evaluation state"""
    return PlanningEvaluationState(
        is_sufficient=is_sufficient,
        knowledge_gap=knowledge_gap,
        clarification_questions=questions or [],
        confidence_score=confidence
    )


def create_generation_state(
    planning_json: str = "",
    validation_result: bool = False,
    validation_error: str = None,
    attempts: int = 0
) -> PlanningGenerationState:
    """Create a new generation state"""
    return PlanningGenerationState(
        planning_json=planning_json,
        validation_result=validation_result,
        validation_error=validation_error,
        generation_attempts=attempts
    )


def create_clarification_state(
    questions: List[str] = None,
    target_areas: List[str] = None
) -> PlanningClarificationState:
    """Create a new clarification state"""
    questions = questions or []
    return PlanningClarificationState(
        questions=questions,
        question_count=len(questions),
        target_areas=target_areas or []
    )


def create_router_state(
    next_action: str = "evaluate",
    should_continue: bool = True,
    exit_reason: str = None
) -> PlanningRouterState:
    """Create a new router state"""
    return PlanningRouterState(
        next_action=next_action,
        should_continue=should_continue,
        exit_reason=exit_reason
    )


def merge_evaluation_to_overall(
    overall_state: PlanningOverallState,
    eval_state: PlanningEvaluationState
) -> PlanningOverallState:
    """Merge evaluation state results into overall state"""
    overall_state["is_sufficient"] = eval_state["is_sufficient"]
    overall_state["evaluation_result"] = {
        "is_sufficient": eval_state["is_sufficient"],
        "knowledge_gap": eval_state["knowledge_gap"],
        "confidence_score": eval_state["confidence_score"]
    }
    overall_state["clarification_questions"] = eval_state["clarification_questions"]
    return overall_state


def merge_generation_to_overall(
    overall_state: PlanningOverallState,
    gen_state: PlanningGenerationState
) -> PlanningOverallState:
    """Merge generation state results into overall state"""
    if gen_state["validation_result"]:
        overall_state["planning_result"] = gen_state["planning_json"]
        overall_state["is_sufficient"] = True
        overall_state = transition_phase(overall_state, PlanningPhase.COMPLETION)
    else:
        # Record generation failure
        overall_state = record_error(
            overall_state, 
            "generation_validation_failed", 
            gen_state.get("validation_error", "JSON validation failed")
        )
    return overall_state


def merge_clarification_to_overall(
    overall_state: PlanningOverallState,
    clarification_state: PlanningClarificationState
) -> PlanningOverallState:
    """Merge clarification state results into overall state"""
    overall_state["clarification_questions"] = clarification_state["questions"]
    
    # Update metadata with clarification info
    overall_state["state_metadata"]["last_clarification"] = {
        "question_count": clarification_state["question_count"],
        "target_areas": clarification_state["target_areas"],
        "timestamp": __import__('time').time()
    }
    
    return overall_state


def merge_router_to_overall(
    overall_state: PlanningOverallState,
    router_state: PlanningRouterState
) -> PlanningOverallState:
    """Merge router state decisions into overall state"""
    overall_state["last_action"] = router_state["next_action"]
    
    # Update metadata with routing info
    overall_state["state_metadata"]["last_routing"] = {
        "next_action": router_state["next_action"],
        "should_continue": router_state["should_continue"],
        "exit_reason": router_state["exit_reason"],
        "confidence": router_state.get("routing_confidence", 0.0),
        "alternatives": router_state.get("alternative_actions", []),
        "timestamp": __import__('time').time()
    }
    
    # Handle exit conditions
    if not router_state["should_continue"]:
        if router_state["exit_reason"]:
            overall_state = transition_phase(overall_state, PlanningPhase.COMPLETION)
        else:
            overall_state = transition_phase(overall_state, PlanningPhase.ERROR)
    
    return overall_state


def get_state_summary(state: PlanningOverallState) -> Dict[str, Any]:
    """Get a summary of the current state for logging/debugging"""
    return {
        "loop_count": state["planning_loop_count"],
        "max_loops": state["max_planning_loops"],
        "is_sufficient": state["is_sufficient"],
        "has_questions": len(state["clarification_questions"]) > 0,
        "has_result": bool(state["planning_result"]),
        "message_count": len(state["messages"]),
        "model": state["reasoning_model"],
        "current_phase": state["current_phase"],
        "error_count": state["error_count"],
        "phase_transitions": len(state["phase_history"]),
        "can_continue": should_continue_planning(state),
        "can_generate": can_proceed_to_generation(state)
    }


def get_state_flow_info(state: PlanningOverallState) -> Dict[str, Any]:
    """Get detailed information about state flow and transitions"""
    import time
    current_time = time.time()
    elapsed_time = current_time - state.get("start_time", current_time)
    
    return {
        "workflow_status": {
            "current_phase": state["current_phase"],
            "last_action": state["last_action"],
            "phase_history": state["phase_history"],
            "total_phases": len(state["phase_history"])
        },
        "loop_tracking": {
            "current_loop": state["planning_loop_count"],
            "max_loops": state["max_planning_loops"],
            "loops_remaining": state["max_planning_loops"] - state["planning_loop_count"],
            "loop_progress": state["planning_loop_count"] / state["max_planning_loops"] if state["max_planning_loops"] > 0 else 0
        },
        "evaluation_tracking": {
            "is_sufficient": state["is_sufficient"],
            "has_evaluation": bool(state["evaluation_result"]),
            "evaluation_confidence": state["evaluation_result"].get("confidence_score", 0.0),
            "knowledge_gap": state["evaluation_result"].get("knowledge_gap", ""),
            "clarification_count": len(state["clarification_questions"])
        },
        "error_tracking": {
            "error_count": state["error_count"],
            "max_errors": state["max_errors"],
            "errors_remaining": state["max_errors"] - state["error_count"],
            "recent_errors": state["state_metadata"].get("errors", [])[-3:] if "errors" in state["state_metadata"] else []
        },
        "timing": {
            "elapsed_seconds": elapsed_time,
            "start_time": state.get("start_time"),
            "current_time": current_time
        },
        "data_flow": {
            "message_count": len(state["messages"]),
            "has_planning_result": bool(state["planning_result"]),
            "result_length": len(state["planning_result"]) if state["planning_result"] else 0,
            "metadata_keys": list(state["state_metadata"].keys())
        }
    }


def validate_state_transitions(state: PlanningOverallState) -> tuple[bool, List[str]]:
    """Validate that state transitions are logical and allowed"""
    warnings = []
    
    # Check phase transition logic
    current_phase = state["current_phase"]
    phase_history = state["phase_history"]
    
    if len(phase_history) > 1:
        previous_phase = phase_history[-2]
        
        # Define allowed transitions
        allowed_transitions = {
            PlanningPhase.INITIALIZATION.value: [
                PlanningPhase.EVALUATION.value,
                PlanningPhase.ERROR.value
            ],
            PlanningPhase.EVALUATION.value: [
                PlanningPhase.CLARIFICATION.value,
                PlanningPhase.GENERATION.value,
                PlanningPhase.ERROR.value
            ],
            PlanningPhase.CLARIFICATION.value: [
                PlanningPhase.EVALUATION.value,
                PlanningPhase.GENERATION.value,
                PlanningPhase.ERROR.value
            ],
            PlanningPhase.GENERATION.value: [
                PlanningPhase.VALIDATION.value,
                PlanningPhase.COMPLETION.value,
                PlanningPhase.ERROR.value
            ],
            PlanningPhase.VALIDATION.value: [
                PlanningPhase.GENERATION.value,
                PlanningPhase.COMPLETION.value,
                PlanningPhase.ERROR.value
            ],
            PlanningPhase.COMPLETION.value: [],
            PlanningPhase.ERROR.value: [
                PlanningPhase.EVALUATION.value,
                PlanningPhase.GENERATION.value
            ]
        }
        
        if current_phase not in allowed_transitions.get(previous_phase, []):
            warnings.append(f"Potentially invalid transition from {previous_phase} to {current_phase}")
    
    # Check loop count consistency
    if state["planning_loop_count"] > state["max_planning_loops"]:
        warnings.append("Loop count exceeds maximum allowed loops")
    
    # Check error count consistency
    if state["error_count"] > state["max_errors"]:
        warnings.append("Error count exceeds maximum allowed errors")
    
    # Check phase-specific validations
    if current_phase == PlanningPhase.COMPLETION.value and not state["planning_result"]:
        warnings.append("Completion phase reached but no planning result available")
    
    if current_phase == PlanningPhase.CLARIFICATION.value and not state["clarification_questions"]:
        warnings.append("Clarification phase but no clarification questions available")
    
    return len(warnings) == 0, warnings


def optimize_state_for_next_iteration(state: PlanningOverallState) -> PlanningOverallState:
    """Optimize state data for the next iteration to prevent memory bloat"""
    # Limit message history to prevent excessive memory usage
    max_messages = 50
    if len(state["messages"]) > max_messages:
        # Keep first few messages (context) and recent messages
        context_messages = state["messages"][:5]
        recent_messages = state["messages"][-(max_messages-5):]
        state["messages"] = context_messages + recent_messages
        
        # Record the optimization in metadata
        state["state_metadata"]["message_optimization"] = {
            "original_count": len(state["messages"]) + (len(state["messages"]) - max_messages),
            "optimized_count": len(state["messages"]),
            "optimization_applied": True
        }
    
    # Limit error history to prevent bloat
    if "errors" in state["state_metadata"] and len(state["state_metadata"]["errors"]) > 10:
        state["state_metadata"]["errors"] = state["state_metadata"]["errors"][-10:]
    
    # Limit phase history to reasonable size
    if len(state["phase_history"]) > 20:
        state["phase_history"] = state["phase_history"][-20:]
    
    return state
