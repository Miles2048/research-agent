#!/usr/bin/env python3
"""
Debug Research Example
专门用于调试和开发的示例
适合与 langgraph dev 一起使用
"""

from langchain_core.messages import HumanMessage
from agent.graph import graph
import json


def create_debug_state(query: str):
    """创建用于调试的状态"""
    return {
        "messages": [HumanMessage(content=query)],
        "initial_search_query_count": 2,  # 减少查询数量以便调试
        "max_research_loops": 1,          # 减少循环次数
        "reasoning_model": "gpt-4o-mini", # 使用更快的模型进行调试
    }


def debug_single_query():
    """调试单个查询"""
    
    # 🔥 修改这里的查询进行调试
    DEBUG_QUERY = "What is the future of electric vehicles?"
    
    print(f"🐛 调试模式: {DEBUG_QUERY}")
    print("🔧 使用简化配置以便快速调试")
    
    state = create_debug_state(DEBUG_QUERY)
    
    print(f"📋 初始状态:")
    print(json.dumps({
        "query": DEBUG_QUERY,
        "config": {
            "initial_queries": state["initial_search_query_count"],
            "max_loops": state["max_research_loops"],
            "model": state["reasoning_model"]
        }
    }, indent=2))
    
    try:
        print("\n🚀 开始执行...")
        result = graph.invoke(state)
        
        print("\n✅ 执行完成!")
        print(f"📊 最终状态键: {list(result.keys())}")
        
        # 显示结果
        messages = result.get("messages", [])
        if messages:
            print(f"\n📝 最终答案 ({len(messages[-1].content)} 字符):")
            print("-" * 40)
            print(messages[-1].content[:500] + "..." if len(messages[-1].content) > 500 else messages[-1].content)
            print("-" * 40)
        
        # 显示调试信息
        print(f"\n🔍 搜索查询: {result.get('search_query', [])}")
        print(f"📚 信息源数量: {len(result.get('sources_gathered', []))}")
        print(f"🔄 研究循环次数: {result.get('research_loop_count', 0)}")
        
        return result
        
    except Exception as e:
        print(f"❌ 调试发现错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_queries():
    """测试多个简单查询"""
    
    test_queries = [
        "What is Python?",
        "Explain machine learning",
        "What is LangGraph?",
    ]
    
    print(f"🧪 测试 {len(test_queries)} 个简单查询")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*50}")
        print(f"测试 {i}: {query}")
        print('='*50)
        
        state = create_debug_state(query)
        
        try:
            result = graph.invoke(state)
            messages = result.get("messages", [])
            
            if messages:
                print(f"✅ 成功 - 结果长度: {len(messages[-1].content)} 字符")
            else:
                print("❌ 失败 - 没有结果")
                
        except Exception as e:
            print(f"❌ 错误: {e}")


def main():
    """主函数"""
    print("🐛 LangGraph 调试工具")
    print("=" * 50)
    
    # 选择调试模式
    print("选择调试模式:")
    print("1. 调试单个查询 (详细输出)")
    print("2. 测试多个简单查询")
    print("3. 直接运行单个查询")
    
    try:
        choice = input("\n请选择 (1-3, 默认1): ").strip() or "1"
        
        if choice == "1":
            debug_single_query()
        elif choice == "2":
            test_multiple_queries()
        elif choice == "3":
            # 快速测试
            result = graph.invoke(create_debug_state("What is artificial intelligence?"))
            messages = result.get("messages", [])
            if messages:
                print("\n🎯 快速结果:")
                print(messages[-1].content)
        else:
            print("❌ 无效选择")
            
    except KeyboardInterrupt:
        print("\n👋 调试已停止")
    except Exception as e:
        print(f"❌ 调试工具出错: {e}")


if __name__ == "__main__":
    main()