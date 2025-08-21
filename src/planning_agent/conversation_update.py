"""
Conversation Update Module for Planning Agent

这个模块实现通过对话修改计划的功能
用户可以通过自然语言描述来更新planning_list.md文件
"""

import os
import json
from typing import Dict, Any, List
from loguru import logger

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from .state import PlanningOverallState
from .configuration import Configuration
from .file_operations import (
    read_planning_file,
    write_planning_file,
    process_conversation_update,
    get_planning_file_info
)
from .prompts import format_conversation_history


# 对话更新的系统提示
CONVERSATION_UPDATE_PROMPT = """你是一个专业的计划管理助手，负责根据用户的对话请求来更新研究计划。

当前planning_list.md文件内容:
{current_content}

用户的更新请求:
{user_request}

请分析用户的请求，并生成更新后的planning_list.md文件内容。

更新原则:
1. 保持文件的基本结构和格式
2. 根据用户意图进行精确更新
3. 更新时间戳
4. 保留重要的历史信息
5. 确保Markdown格式正确

如果用户要求:
- "添加新计划": 在文件末尾添加新的计划条目
- "修改某个计划": 找到对应计划并修改
- "删除计划": 移除指定的计划条目
- "重新组织": 重新安排计划的顺序或结构

请输出完整的更新后的文件内容。"""


@traceable(name="handle_conversation_update")
def handle_conversation_update(
    state: PlanningOverallState,
    config: RunnableConfig,
    user_message: str
) -> Dict[str, Any]:
    """
    处理用户通过对话修改计划的请求
    
    Args:
        state: 当前planning状态
        config: 运行配置
        user_message: 用户的修改请求
        
    Returns:
        更新后的状态字典
    """
    logger.info(f"处理对话更新请求: {user_message[:100]}...")
    
    try:
        # 获取配置
        configurable = Configuration.from_runnable_config(config)
        
        # 读取当前planning文件内容
        current_content = read_planning_file()
        if not current_content:
            logger.warning("无法读取planning文件，创建新的文件")
            current_content = "# 研究计划列表\n\n> 更新时间: 刚刚创建\n\n---\n"
        
        # 初始化LLM
        llm = ChatAnthropic(
            model_name=configurable.generation_model,
            temperature=0.3,
            max_retries=3,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=configurable.llm_timeout,
        )
        
        # 构建更新提示
        formatted_prompt = CONVERSATION_UPDATE_PROMPT.format(
            current_content=current_content,
            user_request=user_message
        )
        
        logger.debug(f"发送更新请求到LLM，提示长度: {len(formatted_prompt)}")
        
        # 调用LLM生成更新后的内容
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        updated_content = response.content
        
        # 验证更新后的内容
        if not updated_content or len(updated_content.strip()) < 50:
            logger.warning("LLM返回的更新内容太短，使用简单更新逻辑")
            updated_content = process_conversation_update(user_message, current_content)
        
        # 写入更新后的内容
        write_planning_file(updated_content)
        
        # 获取文件信息
        file_info = get_planning_file_info()
        
        logger.info("成功通过对话更新了planning文件")
        
        # 更新状态
        state_updates = {
            "planning_result": f"通过对话更新了计划文件: {user_message[:50]}...",
            "planning_file_path": file_info.get("file_path", ""),
            "state_metadata": {
                **state.get("state_metadata", {}),
                "last_conversation_update": {
                    "request": user_message,
                    "timestamp": file_info.get("modified_time", ""),
                    "success": True
                }
            }
        }
        
        return state_updates
        
    except Exception as e:
        logger.error(f"对话更新失败: {str(e)}")
        
        # 返回错误状态
        return {
            "planning_result": f"对话更新失败: {str(e)}",
            "state_metadata": {
                **state.get("state_metadata", {}),
                "last_conversation_update": {
                    "request": user_message,
                    "error": str(e),
                    "success": False
                }
            }
        }


def validate_update_request(user_message: str) -> tuple[bool, str]:
    """
    验证用户的更新请求是否合理
    
    Args:
        user_message: 用户的更新请求
        
    Returns:
        (是否有效, 错误信息或建议)
    """
    if not user_message or len(user_message.strip()) < 5:
        return False, "更新请求太短，请提供更详细的说明"
    
    # 检查是否包含有效的更新动词
    update_keywords = [
        "添加", "增加", "新增", "创建",
        "修改", "更改", "调整", "编辑",
        "删除", "移除", "去掉",
        "重新组织", "重排", "调换顺序"
    ]
    
    has_update_intent = any(keyword in user_message for keyword in update_keywords)
    
    if not has_update_intent:
        return False, "请明确说明要进行什么操作，例如：'添加新计划'、'修改某个计划'等"
    
    return True, "请求有效"


def extract_update_intent(user_message: str) -> Dict[str, Any]:
    """
    从用户消息中提取更新意图
    
    Args:
        user_message: 用户的更新请求
        
    Returns:
        包含更新意图的字典
    """
    intent = {
        "action": "unknown",
        "target": "",
        "content": user_message
    }
    
    message_lower = user_message.lower()
    
    # 识别操作类型
    if any(word in message_lower for word in ["添加", "增加", "新增", "创建"]):
        intent["action"] = "add"
    elif any(word in message_lower for word in ["修改", "更改", "调整", "编辑"]):
        intent["action"] = "modify"
    elif any(word in message_lower for word in ["删除", "移除", "去掉"]):
        intent["action"] = "delete"
    elif any(word in message_lower for word in ["重新组织", "重排", "调换"]):
        intent["action"] = "reorganize"
    
    # 尝试提取目标对象
    if "计划" in message_lower:
        intent["target"] = "plan"
    elif "关键词" in message_lower:
        intent["target"] = "keywords"
    elif "搜索" in message_lower:
        intent["target"] = "search"
    
    return intent


def generate_update_summary(old_content: str, new_content: str) -> str:
    """
    生成更新摘要
    
    Args:
        old_content: 更新前的内容
        new_content: 更新后的内容
        
    Returns:
        更新摘要字符串
    """
    try:
        # 简单的更新摘要生成逻辑
        old_lines = len(old_content.split('\n'))
        new_lines = len(new_content.split('\n'))
        
        line_diff = new_lines - old_lines
        
        if line_diff > 0:
            return f"添加了 {line_diff} 行内容"
        elif line_diff < 0:
            return f"删除了 {abs(line_diff)} 行内容"
        else:
            return "修改了文件内容"
    
    except Exception:
        return "更新了计划文件" 