#!/usr/bin/env python3
"""
规划代理演示脚本

这个脚本演示了如何使用规划代理来分析用户查询并生成搜索策略。
包含了基本用法、错误处理和状态管理的示例。

运行方法:
    python examples/planning_agent_demo.py
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))

# 导入规划代理组件
from planning_agent.configuration import Configuration
from planning_agent.state import initialize_planning_state, get_state_summary
from planning_agent.planning_gragh import planning_graph
from planning_agent.tools_and_schemas import validate_json_structure


def print_banner():
    """打印程序横幅"""
    print("=" * 70)
    print("规划代理演示程序")
    print("=" * 70)
    print("这个程序演示了如何使用规划代理来分析用户查询并生成搜索策略。")
    print()


def check_environment():
    """检查环境配置"""
    print("检查环境配置...")
    
    # 检查 API 密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到 OPENAI_API_KEY 环境变量")
        print("请在 .env 文件中设置您的 OpenAI API 密钥:")
        print("OPENAI_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ 找到 OPENAI_API_KEY: {api_key[:10]}...")
    
    # 检查规划图
    if planning_graph is None:
        print("❌ 错误: 规划图未正确初始化")
        return False
    
    print("✅ 规划图已就绪")
    print()
    return True


def create_demo_queries():
    """创建演示查询列表"""
    return [
        {
            "title": "简单技术查询",
            "query": "我想了解人工智能的发展历史",
            "description": "一个相对简单的查询，应该能够直接生成搜索策略"
        },
        {
            "title": "复杂商业查询", 
            "query": "分析中国新能源汽车市场的竞争格局和发展趋势",
            "description": "一个复杂的商业分析查询，可能需要澄清"
        },
        {
            "title": "模糊查询",
            "query": "最新技术",
            "description": "一个非常模糊的查询，应该会触发澄清问题"
        },
        {
            "title": "学术研究查询",
            "query": "量子计算在密码学中的应用和安全影响",
            "description": "一个学术性的查询，需要多种数据源"
        }
    ]


def format_planning_result(planning_json: str) -> str:
    """格式化规划结果用于显示"""
    try:
        data = json.loads(planning_json)
        
        result = []
        result.append("📋 搜索策略:")
        result.append("-" * 50)
        
        # 搜索分类
        result.append(f"🎯 搜索分类 ({len(data['search_categories'])}个):")
        for i, category in enumerate(data['search_categories'], 1):
            result.append(f"  {i}. {category}")
        result.append("")
        
        # 关键词
        result.append(f"🔑 关键词 ({len(data['keywords'])}个):")
        keywords_str = ", ".join(data['keywords'])
        result.append(f"  {keywords_str}")
        result.append("")
        
        # 搜索角度
        result.append(f"🔍 搜索角度 ({len(data['search_angles'])}个):")
        for i, angle in enumerate(data['search_angles'], 1):
            result.append(f"  {i}. {angle}")
        result.append("")
        
        # 数据源
        result.append("📚 数据源分类:")
        data_sources = data['data_sources']
        for source_type, sources in data_sources.items():
            if sources:
                type_name = {
                    'academic_sources': '学术数据源',
                    'industry_sources': '行业数据源', 
                    'regulatory_sources': '政策法规数据源',
                    'market_sources': '市场数据源'
                }.get(source_type, source_type)
                result.append(f"  {type_name}: {', '.join(sources)}")
        result.append("")
        
        # 其他信息
        result.append(f"⚡ 优先级: {data['priority']}")
        result.append(f"🎚️ 复杂度: {data['estimated_complexity']}")
        result.append(f"📖 范围: {data['scope']}")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"❌ 解析规划结果时出错: {str(e)}"


def run_planning_demo(query: str, max_loops: int = 3) -> Dict[str, Any]:
    """运行规划演示"""
    print(f"🚀 开始处理查询: {query}")
    print()
    
    try:
        # 初始化状态
        initial_state = initialize_planning_state(
            messages=[{"role": "user", "content": query}],
            max_loops=max_loops
        )
        
        # 配置
        config = {
            "configurable": {
                "max_planning_loops": max_loops,
                "temperature": 0.3
            }
        }
        
        print("📊 初始状态:")
        summary = get_state_summary(initial_state)
        print(f"  循环计数: {summary['loop_count']}/{summary['max_loops']}")
        print(f"  当前阶段: {initial_state['current_phase']}")
        print()
        
        # 执行规划
        print("⚙️ 执行规划工作流...")
        result = planning_graph.invoke(initial_state, config)
        
        # 分析结果
        final_summary = get_state_summary(result)
        print("📈 最终状态:")
        print(f"  循环计数: {final_summary['loop_count']}/{final_summary['max_loops']}")
        print(f"  需求是否充分: {final_summary['is_sufficient']}")
        print(f"  是否有结果: {final_summary['has_result']}")
        print(f"  消息数量: {final_summary['message_count']}")
        print()
        
        # 显示澄清问题（如果有）
        if result.get("clarification_questions"):
            print("❓ 澄清问题:")
            for i, question in enumerate(result["clarification_questions"], 1):
                print(f"  {i}. {question}")
            print()
        
        # 显示规划结果
        if result.get("planning_result"):
            print("✅ 生成的搜索策略:")
            print(format_planning_result(result["planning_result"]))
        else:
            print("⚠️ 未生成规划结果")
        
        return {
            "success": True,
            "result": result,
            "summary": final_summary
        }
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def interactive_demo():
    """交互式演示"""
    print("🎮 交互式模式")
    print("输入您的查询，或输入 'quit' 退出")
    print("-" * 50)
    
    while True:
        try:
            query = input("\n请输入您的查询: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if not query:
                print("⚠️ 请输入有效的查询")
                continue
            
            print()
            result = run_planning_demo(query)
            
            if not result["success"]:
                print("是否要重试？(y/n): ", end="")
                retry = input().strip().lower()
                if retry != 'y':
                    continue
            
            print("\n" + "=" * 70)
            
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 意外错误: {str(e)}")


def batch_demo():
    """批量演示"""
    print("📦 批量演示模式")
    print("运行预定义的查询示例")
    print("-" * 50)
    
    demo_queries = create_demo_queries()
    results = []
    
    for i, demo in enumerate(demo_queries, 1):
        print(f"\n🔄 示例 {i}/{len(demo_queries)}: {demo['title']}")
        print(f"📝 描述: {demo['description']}")
        print(f"❓ 查询: {demo['query']}")
        print()
        
        result = run_planning_demo(demo['query'])
        results.append({
            "demo": demo,
            "result": result
        })
        
        print("\n" + "=" * 70)
        
        # 询问是否继续
        if i < len(demo_queries):
            print("按 Enter 继续下一个示例，或输入 'q' 退出: ", end="")
            user_input = input().strip()
            if user_input.lower() == 'q':
                break
    
    # 显示总结
    print("\n📊 批量演示总结:")
    print("-" * 30)
    successful = sum(1 for r in results if r["result"]["success"])
    print(f"成功处理: {successful}/{len(results)}")
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["result"]["success"] else "❌"
        print(f"{status} 示例 {i}: {r['demo']['title']}")


def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 选择运行模式
    print("请选择运行模式:")
    print("1. 批量演示 (运行预定义示例)")
    print("2. 交互式演示 (输入自定义查询)")
    print("3. 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (1-3): ").strip()
            
            if choice == '1':
                batch_demo()
                break
            elif choice == '2':
                interactive_demo()
                break
            elif choice == '3':
                print("👋 再见！")
                break
            else:
                print("⚠️ 请输入有效选择 (1-3)")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 意外错误: {str(e)}")
            break


if __name__ == '__main__':
    main()