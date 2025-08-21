#!/usr/bin/env python3
"""
Interactive Research Example
交互式研究示例，支持多个预设查询
"""

from langchain_core.messages import HumanMessage
from agent.graph import graph
import json
import os
from datetime import datetime


def save_result_to_file(query: str, result: str, sources: list):
    """保存结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_result_{timestamp}.md"
    
    content = f"""# Research Result

**Query**: {query}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Result

{result}

## Sources

"""
    
    for i, source in enumerate(sources, 1):
        content += f"{i}. [{source.get('title', 'Unknown')}]({source.get('url', '#')})\n"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"💾 结果已保存到: {filename}")


def run_research(query: str, config: dict = None):
    """执行研究"""
    if config is None:
        config = {
            "initial_search_query_count": 3,
            "max_research_loops": 2,
            "reasoning_model": "gpt-4o"
        }
    
    print(f"\n🔍 研究主题: {query}")
    print(f"📋 配置: {config}")
    print("🤖 AI代理工作中...")
    print("-" * 50)
    
    state = {
        "messages": [HumanMessage(content=query)],
        **config
    }
    
    try:
        result = graph.invoke(state)
        messages = result.get("messages", [])
        
        if messages:
            result_text = messages[-1].content
            sources = result.get("sources_gathered", [])
            
            print("✅ 研究完成!")
            print("=" * 60)
            print(result_text)
            print("=" * 60)
            
            # 保存结果
            save_result_to_file(query, result_text, sources)
            
            return {
                "success": True,
                "result": result_text,
                "sources": sources,
                "queries_used": result.get("search_query", [])
            }
        else:
            print("❌ 没有获得结果")
            return {"success": False, "error": "No results"}
            
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        return {"success": False, "error": str(e)}


def main():
    """主函数 - 预设多个研究查询"""
    
    # 🔥 在这里添加您想研究的主题！
    research_topics = [
        {
            "query": "What are the latest trends in machine learning?",
            "config": {"initial_search_query_count": 3, "max_research_loops": 1}
        },
        {
            "query": "How is blockchain technology evolving in 2025?",
            "config": {"initial_search_query_count": 2, "max_research_loops": 1}
        },
        {
            "query": "What are the current developments in quantum computing?",
            "config": {"initial_search_query_count": 3, "max_research_loops": 2}
        }
    ]
    
    print("🚀 交互式研究代理启动!")
    print(f"📝 准备研究 {len(research_topics)} 个主题")
    
    results = []
    
    for i, topic in enumerate(research_topics, 1):
        print(f"\n{'='*60}")
        print(f"📊 研究 {i}/{len(research_topics)}")
        print(f"{'='*60}")
        
        result = run_research(topic["query"], topic.get("config"))
        results.append({
            "topic": topic["query"],
            "result": result
        })
        
        # 询问是否继续
        if i < len(research_topics):
            print(f"\n⏳ 即将开始下一个研究...")
            print("💡 如果想停止，请按 Ctrl+C")
            try:
                input("按 Enter 继续...")
            except KeyboardInterrupt:
                print("\n👋 研究已停止")
                break
    
    # 总结
    print(f"\n🎉 研究完成! 总共完成了 {len([r for r in results if r['result']['success']])} 个成功的研究")
    
    # 保存总结
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_topics": len(research_topics),
        "completed": len([r for r in results if r['result']['success']]),
        "results": results
    }
    
    with open("research_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("📄 总结已保存到: research_summary.json")


if __name__ == "__main__":
    main()