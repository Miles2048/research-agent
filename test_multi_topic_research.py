#!/usr/bin/env python3
"""
完整的多Topic研究测试
利用planning_list.md生成多topic并发调用search_agent
""" 

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, 'src')

def test_planning_parser():
    """测试planning解析器"""
    print("🧪 测试Planning解析器...")
    
    try:
        from src.tools.planning_parser import PlanningParser
        
        parser = PlanningParser()
        planning_file = "src/planning_list.md"
        
        if not os.path.exists(planning_file):
            print(f"❌ 找不到planning文件: {planning_file}")
            return False
        
        topics = parser.parse_planning_file(planning_file)
        metadata = parser.get_report_metadata()
        
        print(f"✅ 解析成功: {len(topics)} 个topics")
        print(f"📊 报告标题: {metadata.get('title', 'N/A')[:80]}...")
        
        for topic in topics:
            print(f"  📋 {topic.topic_name}: {len(topic.data_requirements)} 个数据需求")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析器测试失败: {str(e)}")
        return False

def test_search_agent_import():
    """测试search_agent导入"""
    print("🧪 测试Search Agent导入...")
    
    try:
        # 尝试不同的导入方式
        try:
            from search_agent.search_graph import graph
            print("✅ search_agent.search_graph 导入成功")
            return True
        except ImportError:
            from src.search_agent.search_graph import graph
            print("✅ src.search_agent.search_graph 导入成功")
            return True
            
    except Exception as e:
        print(f"❌ Search Agent导入失败: {str(e)}")
        return False

async def test_single_topic_research():
    """测试单个topic研究"""
    print("🧪 测试单个Topic研究...")
    
    try:
        from src.tools.topic_research_orchestrator import TopicResearchOrchestrator
        from src.tools.planning_parser import PlanningParser
        
        # 创建协调器
        orchestrator = TopicResearchOrchestrator("test_research_results")
        
        # 加载planning文件
        if not orchestrator.load_planning_file("src/planning_list.md"):
            print("❌ 无法加载planning文件")
            return False
        
        # 测试第一个topic
        if orchestrator.topics:
            first_topic = orchestrator.topics[0]
            print(f"🔍 测试Topic: {first_topic.topic_name}")
            
            result = await orchestrator.research_single_topic(first_topic)
            
            if result.get("success"):
                print(f"✅ 单topic研究成功")
                print(f"📄 报告: {result.get('report_path', 'None')}")
                print(f"📊 数据源: {result.get('sources_count', 0)} 个")
                return True
            else:
                print(f"❌ 单topic研究失败: {result.get('error', 'Unknown')}")
                return False
        else:
            print("❌ 没有找到topics")
            return False
            
    except Exception as e:
        print(f"❌ 单topic研究测试失败: {str(e)}")
        return False

async def test_full_research_pipeline():
    """测试完整的研究流水线"""
    print("🚀 测试完整的研究流水线...")
    
    try:
        from src.tools.topic_research_orchestrator import run_full_research_pipeline
        
        # 运行完整流水线
        result = await run_full_research_pipeline("src/planning_list.md")
        
        statistics = result["statistics"]
        
        print("✅ 完整流水线测试成功!")
        print(f"📊 成功率: {statistics['successful_topics']}/{statistics['total_topics']}")
        print(f"📚 总数据源: {statistics['total_data_sources']} 个")
        print(f"📁 输出目录: {statistics['output_directory']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整流水线测试失败: {str(e)}")
        return False

async def run_comprehensive_test():
    """运行综合测试"""
    
    print("🧪 多Topic研究系统综合测试")
    print("=" * 80)
    
    test_results = {}
    
    # 1. 测试planning解析器
    print("\n1️⃣ 测试Planning解析器")
    test_results["parser"] = test_planning_parser()
    
    # 2. 测试search_agent导入
    print("\n2️⃣ 测试Search Agent导入")
    test_results["search_agent"] = test_search_agent_import()
    
    # 3. 测试单个topic研究（如果前面的测试通过）
    if test_results["parser"] and test_results["search_agent"]:
        print("\n3️⃣ 测试单个Topic研究")
        test_results["single_topic"] = await test_single_topic_research()
        
        # 4. 测试完整流水线（如果单topic测试通过）
        if test_results["single_topic"]:
            print("\n4️⃣ 测试完整研究流水线")
            test_results["full_pipeline"] = await test_full_research_pipeline()
        else:
            print("\n⚠️  跳过完整流水线测试（单topic测试失败）")
            test_results["full_pipeline"] = False
    else:
        print("\n⚠️  跳过后续测试（前置测试失败）")
        test_results["single_topic"] = False
        test_results["full_pipeline"] = False
    
    # 输出测试总结
    print("\n" + "=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)
    
    test_names = {
        "parser": "Planning解析器",
        "search_agent": "Search Agent导入",
        "single_topic": "单Topic研究",
        "full_pipeline": "完整研究流水线"
    }
    
    for key, name in test_names.items():
        status = "✅ 通过" if test_results.get(key) else "❌ 失败"
        print(f"{name}: {status}")
    
    success_count = sum(1 for result in test_results.values() if result)
    total_count = len(test_results)
    
    print(f"\n🎯 总体成功率: {success_count}/{total_count} ({success_count/total_count:.1%})")
    
    if success_count == total_count:
        print("🎉 所有测试通过! 多Topic研究系统运行正常!")
    elif success_count >= 2:
        print("⚠️  部分功能正常，请检查失败的测试项")
    else:
        print("❌ 系统存在重要问题，需要修复")
    
    return test_results

async def run_production_research():
    """运行生产级别的多topic研究"""
    
    print("🚀 启动生产级别的多Topic研究")
    print("=" * 80)
    
    try:
        from src.tools.topic_research_orchestrator import run_full_research_pipeline
        
        start_time = datetime.now()
        
        # 运行完整的研究流水线
        result = await run_full_research_pipeline("src/planning_list.md")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        statistics = result["statistics"]
        
        print(f"\n⏱️  执行时间: {duration:.1f} 秒")
        print(f"📊 会话ID: {statistics['session_id']}")
        print(f"✅ 成功Topics: {statistics['successful_topics']}/{statistics['total_topics']}")
        print(f"📚 总数据源: {statistics['total_data_sources']} 个")
        print(f"📈 平均每topic数据源: {statistics['average_sources_per_topic']:.1f} 个")
        print(f"📁 输出目录: {statistics['output_directory']}")
        print(f"📄 综合摘要: {result['summary_path']}")
        
        # 显示各topic的详细结果
        print("\n📋 各Topic详细结果:")
        for res in result["results"]:
            if res.get("success"):
                topic_info = res.get("topic_info", {})
                topic_name = topic_info.get("topic_name", "Unknown")
                sources = res.get("sources_count", 0)
                print(f"  ✅ {topic_name}: {sources} 个数据源")
            else:
                topic_info = res.get("topic_info", {})
                topic_name = topic_info.get("topic_name", "Unknown")
                error = res.get("error", "Unknown error")
                print(f"  ❌ {topic_name}: {error}")
        
        return result
        
    except Exception as e:
        print(f"❌ 生产研究失败: {str(e)}")
        return None

def main():
    """主函数"""
    
    print("🎯 多Topic研究系统")
    print("基于planning_list.md的智能研究协调器")
    print("=" * 80)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = "test"  # 默认运行测试
    
    if mode == "test":
        print("🧪 运行测试模式...")
        try:
            test_results = asyncio.run(run_comprehensive_test())
        except KeyboardInterrupt:
            print("\n⚠️  测试被用户中断")
        except Exception as e:
            print(f"\n❌ 测试执行失败: {str(e)}")
            
    elif mode == "run" or mode == "production":
        print("🚀 运行生产模式...")
        try:
            result = asyncio.run(run_production_research())
            if result:
                print("\n🎉 生产研究完成!")
            else:
                print("\n❌ 生产研究失败!")
        except KeyboardInterrupt:
            print("\n⚠️  研究被用户中断")
        except Exception as e:
            print(f"\n❌ 研究执行失败: {str(e)}")
            
    else:
        print(f"❌ 未知模式: {mode}")
        print("用法:")
        print("  python test_multi_topic_research.py test        # 运行测试")
        print("  python test_multi_topic_research.py run         # 运行生产研究")
        print("  python test_multi_topic_research.py production  # 运行生产研究")

if __name__ == "__main__":
    main() 