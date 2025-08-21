#!/usr/bin/env python3
"""
Simple Research Example
直接在代码中设置查询，无需命令行参数
"""

import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from langchain_core.messages import HumanMessage
from agent.graph import graph


def main():
    """运行简单的研究示例"""
    
    # 🔥 在这里直接修改您的查询！
    RESEARCH_QUERY = "What are the latest developments in artificial intelligence?"
    
    # 可选配置
    INITIAL_QUERIES = 2  # 初始搜索查询数量
    MAX_LOOPS = 2        # 最大研究循环次数
    REASONING_MODEL = "gpt-4o"  # 推理模型
    
    print(f"🔍 开始研究: {RESEARCH_QUERY}")
    print("=" * 60)
    
    # 构建状态
    state = {
        "messages": [HumanMessage(content=RESEARCH_QUERY)],
        "initial_search_query_count": INITIAL_QUERIES,
        "max_research_loops": MAX_LOOPS,
        "reasoning_model": REASONING_MODEL,
    }
    
    # 执行研究
    print("🤖 AI代理正在工作...")
    result = graph.invoke(state)
    
    # 获取结果
    messages = result.get("messages", [])
    if messages:
        print("\n📊 研究结果:")
        print("=" * 60)
        print(messages[-1].content)
        print("=" * 60)
        
        # 显示额外信息
        sources = result.get("sources_gathered", [])
        if sources:
            print(f"\n📚 找到 {len(sources)} 个信息源")
            
        queries = result.get("search_query", [])
        if queries:
            print(f"🔍 执行了 {len(queries)} 个搜索查询")
            
    else:
        print("❌ 没有获得研究结果")
            



if __name__ == "__main__":
    main()