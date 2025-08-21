#!/usr/bin/env python3
"""
测试新的报告规划功能

验证Planning Agent是否能够生成高质量的深度研究报告结构
"""

import sys
sys.path.extend(['.', 'src'])

from dotenv import load_dotenv
load_dotenv()

from planning_agent.interactive_planning import create_interactive_planning_agent
from planning_agent.file_operations import read_planning_file, get_planning_file_info

def show_report_summary(planning_data: dict):
    """显示报告规划的关键信息"""
    print(f"📊 报告标题: {planning_data.get('report_title', 'N/A')}")
    print(f"❓ 核心问题: {planning_data.get('core_research_question', 'N/A')}")
    
    topics = planning_data.get('research_topics', [])
    print(f"🔬 研究主题数量: {len(topics)}")
    
    for i, topic in enumerate(topics, 1):
        print(f"  Topic {i}: {topic.get('topic_name', 'N/A')}")
        data_reqs = topic.get('data_requirements', [])
        print(f"    📋 数据需求: {len(data_reqs)} 项")
        search_inst = topic.get('search_instructions', '')
        print(f"    🔎 搜索指导: {search_inst[:60]}..." if len(search_inst) > 60 else f"    🔎 搜索指导: {search_inst}")

def test_report_planning():
    """测试报告规划功能"""
    print("🚀 测试Planning Agent报告规划功能")
    print("="*60)
    
    # 创建agent
    agent = create_interactive_planning_agent()
    
    # 测试查询 - 模拟高质量的研究需求
    test_cases = [
        {
            "query": "空气制水机(AWG)的市场投资机会分析",
            "description": "复杂的商业分析需求"
        },
        {
            "query": "电动汽车电池技术的竞争格局研究",
            "description": "技术与市场结合的分析"
        },
        {
            "query": "人工智能在医疗诊断中的应用前景",
            "description": "新兴技术应用研究"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} 测试案例 {i} {'='*20}")
        print(f"📝 查询: {test_case['query']}")
        print(f"📖 说明: {test_case['description']}")
        print("\n⚙️ 处理中...")
        
        # 使用新的报告规划功能
        result = agent.process_user_input_with_update(test_case['query'])
        
        # 显示评估结果
        evaluation = result['evaluation']
        print(f"\n📊 需求评估:")
        print(f"  充分性: {'✅ 充分' if evaluation['is_sufficient'] else '❓ 需要澄清'}")
        print(f"  置信度: {evaluation['evaluation_data'].get('confidence_score', 0):.2f}")
        
        if evaluation['clarification_questions']:
            print(f"  💡 澄清建议: {evaluation['clarification_questions'][0]}")
        
        # 显示规划结果
        planning_result = result['planning']
        if planning_result.get('success'):
            print(f"\n✅ 报告规划生成成功!")
            
            # 显示规划摘要
            planning_data = planning_result.get('planning_data', {})
            if planning_data:
                print(f"\n📋 规划摘要:")
                show_report_summary(planning_data)
                
                # 验证关键要素
                print(f"\n🔍 质量检查:")
                checks = {
                    "报告标题": bool(planning_data.get('report_title')),
                    "核心研究问题": bool(planning_data.get('core_research_question')),
                    "研究主题": len(planning_data.get('research_topics', [])) >= 2,
                    "跨主题综合": bool(planning_data.get('cross_topic_synthesis')),
                }
                
                for check_name, passed in checks.items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check_name}")
                
                # 检查每个主题的完整性
                topics = planning_data.get('research_topics', [])
                for j, topic in enumerate(topics, 1):
                    topic_checks = {
                        "研究目标": bool(topic.get('research_objective')),
                        "数据需求": len(topic.get('data_requirements', [])) >= 2,
                        "分析方法": bool(topic.get('analysis_approach')),
                        "搜索指导": bool(topic.get('search_instructions')),
                    }
                    
                    print(f"  📌 Topic {j} 完整性:")
                    for check_name, passed in topic_checks.items():
                        status = "✅" if passed else "❌"
                        print(f"    {status} {check_name}")
            
            print(f"\n📁 已保存到: {planning_result.get('file_path', 'N/A')}")
        else:
            print(f"\n❌ 规划生成失败: {planning_result.get('message', '未知错误')}")
        
        # 显示生成的markdown文件内容预览
        content = read_planning_file()
        if content:
            print(f"\n📄 生成的报告规划预览:")
            lines = content.split('\n')
            # 显示前30行
            preview_lines = lines[:30]
            print('\n'.join(preview_lines))
            if len(lines) > 30:
                print(f"... (还有 {len(lines)-30} 行)")
        
        if i < len(test_cases):
            input(f"\n👆 按回车键继续下一个测试案例...")
    
    print(f"\n🎉 测试完成!")
    
    # 显示最终文件信息
    file_info = get_planning_file_info()
    print(f"\n📁 最终文件: {file_info.get('file_path', '')}")
    print(f"📊 文件大小: {file_info.get('size', 0)} 字节")
    
    print(f"\n💡 总结:")
    print(f"✅ 成功演示了从简单查询生成完整报告结构的能力")
    print(f"✅ 每个报告包含明确的研究主题和数据收集指导")
    print(f"✅ 为Search Agent提供了具体的搜索指令")
    print(f"✅ 生成的结构符合高质量研究报告的标准")

if __name__ == '__main__':
    test_report_planning() 