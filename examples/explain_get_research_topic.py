#!/usr/bin/env python3
"""
演示 get_research_topic 函数的工作原理
"""

from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Union


def get_research_topic_explained(messages: List[Union[HumanMessage, AIMessage]]) -> str:
    """
    从消息历史中提取研究主题
    
    Args:
        messages: 消息列表，包含用户和AI的对话历史
        
    Returns:
        str: 格式化的研究主题字符串
    """
    print(f"📥 收到 {len(messages)} 条消息")
    
    # 情况1: 只有一条消息（通常是用户的初始问题）
    if len(messages) == 1:
        print("📝 单条消息模式")
        research_topic = messages[-1].content  # 取最后一条消息的内容
        print(f"   直接使用: {research_topic}")
        return research_topic
    
    # 情况2: 多条消息（对话历史）
    else:
        print("💬 多轮对话模式")
        research_topic = ""
        
        for i, message in enumerate(messages):
            if isinstance(message, HumanMessage):
                research_topic += f"User: {message.content}\n"
                print(f"   {i+1}. 用户消息: {message.content[:50]}...")
            elif isinstance(message, AIMessage):
                research_topic += f"Assistant: {message.content}\n"
                print(f"   {i+1}. AI消息: {message.content[:50]}...")
        
        print(f"📋 合并后的研究主题长度: {len(research_topic)} 字符")
        return research_topic


def demo_single_message():
    """演示单条消息的情况"""
    print("🔸 场景1: 单条消息")
    print("=" * 40)
    
    messages = [
        HumanMessage(content="What are the latest trends in AI?")
    ]
    
    result = get_research_topic_explained(messages)
    print(f"📤 输出: {result}")
    print()


def demo_multi_message():
    """演示多条消息的情况"""
    print("🔸 场景2: 多轮对话")
    print("=" * 40)
    
    messages = [
        HumanMessage(content="Tell me about renewable energy"),
        AIMessage(content="Renewable energy includes solar, wind, and hydro power..."),
        HumanMessage(content="What about the latest developments in solar technology?"),
        AIMessage(content="Recent solar developments include perovskite cells..."),
        HumanMessage(content="How does this compare to wind energy advances?")
    ]
    
    result = get_research_topic_explained(messages)
    print(f"📤 输出预览:")
    print(result[:200] + "..." if len(result) > 200 else result)
    print()


def demo_why_this_matters():
    """解释为什么需要这个函数"""
    print("🤔 为什么需要这个函数？")
    print("=" * 40)
    
    print("1. 📝 单轮对话: 直接使用用户问题")
    print("   - 简单直接")
    print("   - 适合独立的研究查询")
    
    print("\n2. 💬 多轮对话: 保持上下文")
    print("   - 保留对话历史")
    print("   - AI可以理解前面的讨论")
    print("   - 生成更准确的搜索查询")
    
    print("\n3. 🎯 实际应用:")
    print("   - 传递给AI模型作为上下文")
    print("   - 帮助生成相关的搜索查询")
    print("   - 保持研究的连贯性")


if __name__ == "__main__":
    demo_single_message()
    demo_multi_message()
    demo_why_this_matters()