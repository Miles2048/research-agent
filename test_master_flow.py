#!/usr/bin/env python3
"""
Master Flow 测试脚本
验证完整流程的各个组件是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, 'src')

def test_master_flow_components():
    """测试Master Flow各个组件"""
    
    print("🧪 Master Flow 组件测试")
    print("=" * 50)
    
    # 测试1: 导入检查
    print("\n📦 1. 模块导入测试")
    try:
        from master_flow import run_complete_research_flow
        print("✅ Master Flow主模块导入成功")
        
        from planning_agent.interactive_planning import create_interactive_planning_agent
        print("✅ Planning Agent导入成功")
        
        from citation_agent import run_citation
        print("✅ Citation Agent导入成功")
        
        # 检查search_agent
        from search_agent.search_graph import graph
        print("✅ Search Agent导入成功")
        
        print("🎉 所有核心模块导入测试通过")
        
    except Exception as e:
        print(f"❌ 模块导入失败: {str(e)}")
        return False
    
    # 测试2: 文件结构检查
    print("\n📁 2. 文件结构检查")
    
    required_files = [
        "src/master_flow/master_flow.py",
        "src/master_flow/__init__.py", 
        "src/citation_agent/citation_agent.py",
        "src/planning_agent/interactive_planning.py",
        "src/search_agent/search_graph.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} 缺失")
            return False
    
    print("🎉 文件结构检查通过")
    
    # 测试3: 功能组件测试
    print("\n⚙️ 3. 功能组件测试")
    
    try:
        # 测试Citation Agent检查功能
        from citation_agent import EasyCitationAgent
        agent = EasyCitationAgent()
        status = agent.check_inputs()
        print(f"✅ Citation Agent状态检查: {status['topics_found']} topics, 规划文件: {status['planning_file_exists']}")
        
        # 测试Planning Parser
        from tools.planning_parser import PlanningParser
        parser = PlanningParser()
        print("✅ Planning Parser创建成功")
        
        print("🎉 功能组件测试通过")
        
    except Exception as e:
        print(f"❌ 功能组件测试失败: {str(e)}")
        return False
    
    print("\n✅ Master Flow所有组件测试通过！")
    print("🚀 可以运行完整的研究流程")
    
    return True


def show_usage_guide():
    """显示使用指南"""
    
    print("\n" + "=" * 60)
    print("🎯 Master Flow 使用指南")
    print("=" * 60)
    
    print("\n📋 快速开始:")
    print("1. 交互式运行:")
    print("   python3 run_master_flow.py")
    print()
    print("2. 命令行快速模式:")
    print("   python3 run_master_flow.py '人工智能技术趋势分析'")
    print()
    print("3. Python代码调用:")
    print("   from master_flow import run_complete_research_flow")
    print("   result = run_complete_research_flow('研究主题')")
    
    print("\n🔄 完整流程:")
    print("   📝 步骤1: 交互式规划 → src/planning_list.md")
    print("   🔍 步骤2: 多Topic研究 → results/topic_*/")
    print("   📄 步骤3: Citation整合 → deepResearchReport.md")
    
    print("\n⚠️ 注意事项:")
    print("- 确保OPENAI_API_KEY已配置")
    print("- 在backend目录下运行")
    print("- 整个流程需要10-30分钟")
    print("- 建议网络稳定环境下运行")


if __name__ == "__main__":
    # 运行组件测试
    success = test_master_flow_components()
    
    if success:
        show_usage_guide()
        
        # 询问是否运行实际流程
        print("\n" + "=" * 60)
        user_choice = input("是否现在运行完整的研究流程? (y/n): ").strip().lower()
        
        if user_choice in ['y', 'yes', 'Y']:
            print("\n🚀 启动Master Flow...")
            os.system("python3 run_master_flow.py")
        else:
            print("👋 测试完成，您可以稍后运行 run_master_flow.py")
    else:
        print("\n❌ 组件测试失败，请检查配置") 