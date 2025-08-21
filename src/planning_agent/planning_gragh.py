import os
import json
from loguru import logger
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_anthropic import ChatAnthropic
from langsmith import traceable
from langgraph.graph import StateGraph, START, END

from .state import (
    PlanningOverallState,
    PlanningEvaluationState,
    update_evaluation_state,
    increment_loop_count,
)
from .configuration import Configuration
from .prompts import (
    requirement_evaluation_prompt,
    clarification_generation_prompt,
    json_generation_prompt,
    format_conversation_history,
    inject_parameters,
)
from .tools_and_schemas import (
    RequirementEvaluation,
    PlanningOutput,
    create_default_planning_output,
    repair_json_format,
    validate_json_structure,
    format_planning_json,
)
from .file_operations import (
    append_planning_to_file,
    overwrite_planning_to_file,
    get_planning_file_path,
    get_planning_file_info,
    backup_planning_file
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

if os.getenv("OPENAI_API_KEY") is None:
    raise ValueError("OPENAI_API_KEY is not set")


@traceable(name="evaluate_requirement")
def evaluate_requirement(
    state: PlanningOverallState, 
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    LangGraph node that evaluates user requirement sufficiency using LLM.
    
    This node analyzes user input and conversation history to determine if the
    requirements are clear enough to generate a search strategy, or if clarification
    is needed.
    
    Args:
        state: Current planning state containing messages and evaluation context
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state updates including evaluation results
    """
    logger.info(f"Starting requirement evaluation - Loop {state['planning_loop_count']}")
    
    try:
        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        
        # Initialize LLM with retry mechanism
        llm = ChatAnthropic(
            model_name=configurable.evaluation_model,
            temperature=configurable.temperature,
            max_retries=3,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=configurable.llm_timeout,
        )
        
        # Structure LLM to output RequirementEvaluation
        structured_llm = llm.with_structured_output(RequirementEvaluation)
        
        # Get the latest user message
        user_messages = []
        for msg in state["messages"]:
            if hasattr(msg, 'type') and msg.type == "human":
                user_messages.append(msg)
            elif isinstance(msg, dict) and msg.get("role") == "user":
                user_messages.append(msg)
        
        if not user_messages:
            logger.warning("No user messages found in state")
            return {
                "is_sufficient": False,
                "evaluation_result": {
                    "is_sufficient": False,
                    "knowledge_gap": "No user input found",
                    "confidence_score": 0.1,
                },
                "clarification_questions": ["请提供您的查询需求"],
                "planning_loop_count": state["planning_loop_count"] + 1,
            }
        
        latest_user_msg = user_messages[-1]
        if hasattr(latest_user_msg, 'content'):
            latest_user_input = latest_user_msg.content
        else:
            latest_user_input = latest_user_msg.get("content", "")
            
        if not latest_user_input.strip():
            logger.warning("Empty user input detected")
            return {
                "is_sufficient": False,
                "evaluation_result": {
                    "is_sufficient": False,
                    "knowledge_gap": "Empty user input",
                    "confidence_score": 0.1,
                },
                "clarification_questions": ["请提供具体的查询需求"],
                "planning_loop_count": state["planning_loop_count"] + 1,
            }
        
        # Format conversation history
        conversation_history = format_conversation_history(state["messages"])
        
        # Prepare and inject parameters into prompt
        prompt_params = {
            "conversation_history": conversation_history,
            "user_input": latest_user_input,
        }
        
        formatted_prompt = inject_parameters(
            requirement_evaluation_prompt, 
            **prompt_params
        )
        
        logger.debug(f"Evaluating requirement with prompt length: {len(formatted_prompt)}")
        
        # Call LLM with structured output
        evaluation_result = structured_llm.invoke(formatted_prompt)
        
        logger.info(f"Evaluation completed - Sufficient: {evaluation_result.is_sufficient}")
        
        # Update state with evaluation results
        updated_state = update_evaluation_state(
            state,
            is_sufficient=evaluation_result.is_sufficient,
            knowledge_gap=evaluation_result.knowledge_gap,
            questions=evaluation_result.clarification_questions,
            confidence=evaluation_result.confidence_score
        )
        
        # Increment loop counter
        updated_state = increment_loop_count(updated_state)
        
        # Prepare return dictionary with state updates
        state_updates = {
            "is_sufficient": evaluation_result.is_sufficient,
            "evaluation_result": {
                "is_sufficient": evaluation_result.is_sufficient,
                "knowledge_gap": evaluation_result.knowledge_gap,
                "confidence_score": evaluation_result.confidence_score,
            },
            "clarification_questions": evaluation_result.clarification_questions,
            "planning_loop_count": updated_state["planning_loop_count"],
        }
        
        logger.info(f"Requirement evaluation completed successfully")
        return state_updates
        
    except Exception as e:
        logger.error(f"Error in requirement evaluation: {str(e)}")
        return {
            "is_sufficient": False,
            "evaluation_result": {
                "is_sufficient": False,
                "knowledge_gap": f"System error: {str(e)}",
                "confidence_score": 0.1,
            },
            "clarification_questions": ["系统处理您的需求时出现问题，请重新描述您的查询需求"],
            "planning_loop_count": state["planning_loop_count"] + 1,
        }


@traceable(name="generate_clarification")
def generate_clarification(
    state: PlanningOverallState, 
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    LangGraph node that generates targeted clarification questions based on evaluation results.
    
    This node creates specific, actionable questions to help users provide missing information
    needed for generating an effective search strategy.
    
    Args:
        state: Current planning state containing evaluation results and conversation history
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state updates including generated clarification questions
    """
    logger.info(f"Starting clarification generation - Loop {state['planning_loop_count']}")
    
    try:
        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        
        # Initialize LLM
        llm = ChatAnthropic(
            model_name=configurable.evaluation_model,
            temperature=configurable.temperature,
            max_retries=3,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=configurable.llm_timeout,
        )
        
        # Get evaluation results
        evaluation_result = state.get("evaluation_result", {})
        knowledge_gap = evaluation_result.get("knowledge_gap", "")
        
        if not knowledge_gap.strip():
            logger.warning("No knowledge gap found for clarification generation")
            return {
                "clarification_questions": ["请提供更多关于您查询需求的详细信息"]
            }
        
        # Format conversation history
        conversation_history = format_conversation_history(state["messages"])
        
        # Prepare prompt parameters
        prompt_params = {
            "conversation_history": conversation_history,
            "knowledge_gap": knowledge_gap,
            "max_questions": configurable.max_clarification_questions,
        }
        
        formatted_prompt = inject_parameters(
            clarification_generation_prompt,
            **prompt_params
        )
        
        logger.debug(f"Generating clarification with prompt length: {len(formatted_prompt)}")
        
        # Generate clarification questions
        response = llm.invoke(formatted_prompt)
        
        # Extract questions from response
        questions = _extract_questions_from_response(response.content)
        
        # Apply quality control and limits
        filtered_questions = _apply_question_quality_control(
            questions, 
            configurable.max_clarification_questions
        )
        
        logger.info(f"Generated {len(filtered_questions)} clarification questions")
        
        # Update state with generated questions
        state_updates = {
            "clarification_questions": filtered_questions,
        }
        
        logger.info("Clarification generation completed successfully")
        return state_updates
        
    except Exception as e:
        logger.error(f"Error in clarification generation: {str(e)}")
        return {
            "clarification_questions": ["请详细描述您想了解的具体内容", "您希望获得什么类型的信息？"]
        }


def _extract_questions_from_response(response_content: str) -> List[str]:
    """Extract questions from LLM response content."""
    try:
        questions = []
        lines = response_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove quotes if they wrap the entire line
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1].strip()
                
            # Remove common prefixes and numbering
            import re
            prefixes_to_remove = [
                r'^\d+\.\s*',  # "1. "
                r'^-\s*',      # "- "
                r'^\*\s*',     # "* "
                r'^•\s*',      # "• "
            ]
            
            for prefix in prefixes_to_remove:
                line = re.sub(prefix, '', line)
            
            line = line.strip()
            
            # Check if line looks like a question
            if line.endswith('？') or line.endswith('?') or '什么' in line or '如何' in line or '哪' in line:
                questions.append(line)
            elif len(line) > 10 and ('您' in line or '你' in line):
                # Likely a question even without question mark
                questions.append(line)
        
        logger.debug(f"Extracted {len(questions)} questions from response")
        return questions
        
    except Exception as e:
        logger.error(f"Error extracting questions: {str(e)}")
        return []


def _apply_question_quality_control(questions: List[str], max_questions: int) -> List[str]:
    """Apply quality control filters to clarification questions."""
    try:
        filtered_questions = []
        
        for question in questions:
            question = question.strip()
            
            # Skip empty or too short questions
            if len(question) < 8:
                continue
            
            # Skip overly generic questions
            generic_patterns = [
                '还需要什么',
                '其他信息',
                '更多详情',
                '还有什么',
                '其他问题'
            ]
            
            is_generic = any(pattern in question for pattern in generic_patterns)
            if is_generic:
                continue
            
            filtered_questions.append(question)
            
            # Stop if we have enough questions
            if len(filtered_questions) >= max_questions:
                break
        
        logger.debug(f"Quality control: {len(questions)} -> {len(filtered_questions)} questions")
        return filtered_questions
        
    except Exception as e:
        logger.error(f"Error in quality control: {str(e)}")
        return questions[:max_questions]  # Fallback to simple truncation


@traceable(name="generate_planning_json")
def generate_planning_json(
    state: PlanningOverallState, 
    config: RunnableConfig
) -> Dict[str, Any]:
    """
    LangGraph node that generates structured JSON planning output based on conversation history.
    
    This node analyzes the complete conversation history to create a comprehensive search
    strategy with categorized data sources, keywords, search angles, and other specifications.
    
    Args:
        state: Current planning state containing conversation history and evaluation results
        config: Configuration for the runnable, including LLM provider settings
        
    Returns:
        Dictionary with state updates including generated planning JSON
    """
    logger.info(f"Starting JSON generation - Loop {state['planning_loop_count']}")
    
    try:
        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        
        # Initialize LLM for generation (use more capable model)
        llm = ChatAnthropic(
            model_name=configurable.generation_model,
            temperature=configurable.temperature,
            max_retries=3,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=configurable.llm_timeout,
        )
        
        # Get conversation history
        if not state["messages"]:
            logger.warning("No conversation history available for JSON generation")
            return _handle_json_generation_error(state, "No conversation history")
        
        # Format conversation history
        conversation_history = format_conversation_history(state["messages"])
        
        # Prepare prompt parameters
        prompt_params = {
            "conversation_history": conversation_history,
        }
        
        formatted_prompt = inject_parameters(
            json_generation_prompt,
            **prompt_params
        )
        
        logger.debug(f"Generating JSON with prompt length: {len(formatted_prompt)}")
        
        # Generate JSON with retry mechanism
        planning_json = _generate_json_with_retry(
            llm, 
            formatted_prompt, 
            configurable.json_validation_retries
        )
        
        # Validate JSON structure
        is_valid, error_message = validate_json_structure(planning_json)
        
        if not is_valid:
            logger.warning(f"JSON validation failed: {error_message}")
            
            # Attempt to repair JSON
            repaired_json = repair_json_format(planning_json)
            is_valid_repaired, repair_error = validate_json_structure(repaired_json)
            
            if is_valid_repaired:
                logger.info("JSON successfully repaired")
                planning_json = repaired_json
            else:
                logger.error(f"JSON repair failed: {repair_error}")
                return _handle_json_generation_error(state, f"JSON validation and repair failed: {error_message}")
        
        # Extract search categories and keywords for verification
        try:
            parsed_json = json.loads(planning_json)
            planning_output = PlanningOutput(**parsed_json)
            
            # Log generation success metrics
            logger.info(f"JSON generation successful:")
            logger.info(f"  - Search categories: {len(planning_output.search_categories)}")
            logger.info(f"  - Keywords: {len(planning_output.keywords)}")
            logger.info(f"  - Search angles: {len(planning_output.search_angles)}")
            logger.info(f"  - Priority: {planning_output.priority}")
            
        except Exception as e:
            logger.error(f"Error parsing generated JSON: {str(e)}")
            return _handle_json_generation_error(state, f"JSON parsing error: {str(e)}")
        
        # 获取用户的原始查询
        user_query = ""
        for msg in state["messages"]:
            if hasattr(msg, 'type') and msg.type == "human":
                user_query = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                user_query = msg.get("content", "")
                break
        
        if not user_query:
            user_query = "未知查询"
        
        # 将JSON转换为字典格式以便写入Markdown
        try:
            planning_data = json.loads(planning_json)
            
            # 创建备份（可选）
            backup_path = backup_planning_file()
            if backup_path:
                logger.info(f"创建了planning文件备份: {backup_path}")
            
            # 覆盖planning_list.md文件，生成新计划
            overwrite_planning_to_file(planning_data, user_query)
            
            # 获取文件信息
            file_info = get_planning_file_info()
            file_path = file_info.get("file_path", "")
            
            logger.info(f"成功将计划写入文件: {file_path}")
            
            # Update state with successful generation
            state_updates = {
                "planning_result": f"计划已保存到文件: {file_path}",
                "planning_file_path": file_path,
                "planning_data": planning_data,  # 保留数据以备后用
                "is_sufficient": True,  # Mark as complete
            }
            
        except Exception as e:
            logger.error(f"写入planning文件失败: {str(e)}")
            # 如果文件写入失败，仍然返回JSON结果作为备用
            state_updates = {
                "planning_result": f"文件写入失败，JSON结果: {planning_json}",
                "planning_file_path": "",
                "is_sufficient": True,
            }
        
        logger.info("JSON generation completed successfully")
        return state_updates
        
    except Exception as e:
        logger.error(f"Error in JSON generation: {str(e)}")
        return _handle_json_generation_error(state, str(e))


def _generate_json_with_retry(
    llm: ChatAnthropic,
    formatted_prompt: str,
    max_retries: int = 2
) -> str:
    """Generate JSON with retry mechanism and progressive fallback."""
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"JSON generation attempt {attempt + 1}")
            
            # Generate response
            response = llm.invoke(formatted_prompt)
            raw_content = response.content
            
            # Extract JSON from response (handle markdown code blocks)
            json_content = _extract_json_from_response(raw_content)
            
            # Validate JSON
            is_valid, error_message = validate_json_structure(json_content)
            
            if is_valid:
                logger.debug(f"JSON generation successful on attempt {attempt + 1}")
                return json_content
            else:
                logger.warning(f"Attempt {attempt + 1} - Invalid JSON: {error_message}")
                
                # Try to repair JSON
                repaired_json = repair_json_format(json_content)
                is_repaired_valid, _ = validate_json_structure(repaired_json)
                
                if is_repaired_valid:
                    logger.info(f"JSON repaired successfully on attempt {attempt + 1}")
                    return repaired_json
                
                # If this is the last attempt, try fallback generation
                if attempt == max_retries:
                    logger.warning("All attempts failed, generating fallback JSON")
                    return _generate_fallback_json()
                    
        except Exception as e:
            logger.warning(f"JSON generation attempt {attempt + 1} failed: {str(e)}")
            
            if attempt == max_retries:
                logger.error("All JSON generation attempts failed, using default")
                return _generate_fallback_json()
    
    # This should never be reached, but just in case
    raise RuntimeError("All JSON generation attempts failed")


def _extract_json_from_response(response_content: str) -> str:
    """Extract JSON content from LLM response, handling markdown code blocks."""
    try:
        content = response_content.strip()
        
        # Remove markdown code blocks if present
        if "```json" in content:
            # Extract content between ```json and ```
            start_marker = "```json"
            end_marker = "```"
            
            start_idx = content.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = content.find(end_marker, start_idx)
                if end_idx != -1:
                    content = content[start_idx:end_idx].strip()
        
        elif content.startswith("```") and content.endswith("```"):
            # Remove generic code blocks
            content = content[3:-3].strip()
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        logger.debug(f"Extracted JSON content length: {len(content)}")
        return content
        
    except Exception as e:
        logger.error(f"Error extracting JSON from response: {str(e)}")
        return response_content


def _generate_fallback_json() -> str:
    """Generate a fallback JSON when normal generation fails."""
    try:
        # Create fallback planning output
        fallback_output = create_default_planning_output("general query")
        return format_planning_json(fallback_output)
        
    except Exception as e:
        logger.error(f"Fallback JSON generation failed: {str(e)}")
        # Ultimate fallback - minimal valid JSON
        return json.dumps({
            "search_categories": ["基础搜索"],
            "keywords": ["相关信息"],
            "search_angles": ["基本信息收集"],
            "data_sources": {
                "academic_sources": ["学术资料"],
                "industry_sources": ["行业信息"],
                "regulatory_sources": ["政策文件"],
                "market_sources": ["市场数据"]
            },
            "priority": "medium",
            "scope": "基础信息搜索和资料收集",
            "estimated_complexity": "simple"
        }, ensure_ascii=False, indent=2)


def _handle_json_generation_error(state: PlanningOverallState, error_message: str) -> Dict[str, Any]:
    """Handle JSON generation errors with fallback behavior."""
    logger.warning(f"Handling JSON generation error: {error_message}")
    
    try:
        # Try to create a fallback JSON based on conversation history
        user_query = ""
        if state["messages"]:
            # Extract user query from messages
            for msg in state["messages"]:
                if hasattr(msg, 'type') and msg.type == "human":
                    user_query = msg.content
                    break
                elif isinstance(msg, dict) and msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break
        
        if not user_query:
            user_query = "general research query"
        
        # Create fallback planning output
        fallback_output = create_default_planning_output(user_query)
        fallback_json = format_planning_json(fallback_output)
        
        logger.info("Generated fallback JSON for error recovery")
        
        return {
            "planning_result": fallback_json,
            "is_sufficient": True,  # Mark as complete with fallback
        }
        
    except Exception as fallback_error:
        logger.error(f"Fallback JSON generation also failed: {str(fallback_error)}")
        
        # Ultimate fallback - minimal JSON
        minimal_json = json.dumps({
            "search_categories": ["基础搜索"],
            "keywords": ["相关信息"],
            "search_angles": ["基本信息收集"],
            "data_sources": {
                "academic_sources": ["学术资料"],
                "industry_sources": ["行业信息"],
                "regulatory_sources": ["政策文件"],
                "market_sources": ["市场数据"]
            },
            "priority": "medium",
            "scope": "基础信息搜索，由于系统错误使用最小化配置",
            "estimated_complexity": "simple"
        }, ensure_ascii=False, indent=2)
        
        return {
            "planning_result": minimal_json,
            "is_sufficient": True,
        }


@traceable(name="evaluate_planning_flow")
def evaluate_planning_flow(
    state: PlanningOverallState, 
    config: RunnableConfig
) -> str:
    """
    LangGraph routing function that determines the next step in the planning workflow.
    
    This function implements the conditional logic to decide whether to continue with
    clarification, proceed to JSON generation, or end the workflow based on the
    current state and evaluation results.
    
    Args:
        state: Current planning state containing evaluation results and loop count
        config: Configuration for the runnable, including max loops settings
        
    Returns:
        String indicating the next node to visit: "clarify", "generate", or "end"
    """
    logger.info(f"Evaluating planning flow - Loop {state['planning_loop_count']}")
    
    try:
        # Get configuration
        configurable = Configuration.from_runnable_config(config)
        max_loops = state.get("max_planning_loops", configurable.max_planning_loops)
        
        # Check if we've reached maximum loops
        if state["planning_loop_count"] >= max_loops:
            logger.info(f"Maximum loops ({max_loops}) reached, proceeding to generation")
            return "generate"
        
        # Check if requirements are sufficient
        if state.get("is_sufficient", False):
            logger.info("Requirements are sufficient, proceeding to generation")
            return "generate"
        
        # Check if we have evaluation results
        evaluation_result = state.get("evaluation_result", {})
        if not evaluation_result:
            logger.warning("No evaluation result found, ending workflow")
            return "end"
        
        # Check if evaluation indicates sufficiency
        if evaluation_result.get("is_sufficient", False):
            logger.info("Evaluation indicates sufficiency, proceeding to generation")
            return "generate"
        
        # Check if we have clarification questions
        clarification_questions = state.get("clarification_questions", [])
        if not clarification_questions:
            logger.warning("No clarification questions available, proceeding to generation")
            return "generate"
        
        # Default: continue with clarification
        logger.info("Continuing with clarification process")
        return "clarify"
        
    except Exception as e:
        logger.error(f"Error in planning flow evaluation: {str(e)}")
        # On error, try to proceed to generation as fallback
        return "generate"


# Build the LangGraph workflow
def create_planning_graph():
    """
    Create and configure the LangGraph workflow for the planning agent.
    
    Returns:
        Compiled StateGraph instance
    """
    logger.info("Creating planning agent graph")
    
    # Create StateGraph with PlanningOverallState and Configuration
    builder = StateGraph(PlanningOverallState, config_schema=Configuration)
    
    # Add nodes to the graph
    builder.add_node("evaluate_requirement", evaluate_requirement)
    builder.add_node("generate_clarification", generate_clarification)  
    builder.add_node("generate_planning_json", generate_planning_json)
    
    # Set the entry point
    builder.add_edge(START, "evaluate_requirement")
    
    # Add conditional edges for routing logic
    builder.add_conditional_edges(
        "evaluate_requirement",
        evaluate_planning_flow,
        {
            "clarify": "generate_clarification",
            "generate": "generate_planning_json", 
            "end": END
        }
    )
    
    # After clarification, go back to evaluation
    builder.add_edge("generate_clarification", "evaluate_requirement")
    
    # After JSON generation, end the workflow
    builder.add_edge("generate_planning_json", END)
    
    # Compile the graph
    graph = builder.compile(name="planning-agent")
    
    logger.info("Planning agent graph created successfully")
    return graph


# Create the main graph instance
try:
    planning_graph = create_planning_graph()
    logger.info("Planning graph compiled successfully")
except Exception as e:
    logger.error(f"Failed to create planning graph: {str(e)}")
    planning_graph = None


# Export the graph and key functions
__all__ = [
    'planning_graph',
    'create_planning_graph',
    'evaluate_requirement',
    'generate_clarification',
    'generate_planning_json',
    'evaluate_planning_flow'
]