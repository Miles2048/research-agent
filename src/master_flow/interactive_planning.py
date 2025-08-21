#!/usr/bin/env python3
"""
交互式Planning Agent测试脚本

这个脚本演示新的交互式工作流程：
1. 用户输入查询或对话
2. 系统评估输入并立即更新planning_list.md
3. 显示澄清问题（如果需要）和更新结果
4. 用户可以继续对话进一步完善计划

核心特点：
- ✅ 每次输入后立即更新planning_list.md
- ✅ 保留澄清问题生成功能  
- ✅ 支持渐进式计划完善
- ✅ 基于现有planning内容和对话历史生成新计划

运行方法:
    cd backend
    python3 test_interactive_planning.py
"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage

# 导入交互式planning组件
from planning_agent.interactive_planning import create_interactive_planning_agent
from planning_agent.file_operations import read_planning_file, get_planning_file_path


def print_separator(title: str = "", width: int = 60):
    """打印分隔线"""
    if title:
        title_line = f" {title} "
        padding = (width - len(title_line)) // 2
        print(f"\n{'='*padding}{title_line}{'='*padding}")
    else:
        print("="*width)


def show_current_planning():
    """显示当前planning文件内容"""
    print_separator("当前Planning文件内容")
    
    file_path = get_planning_file_path()
    print(f"📁 文件路径: {file_path}")
    
    content = read_planning_file()
    if content:
        print("\n📄 文件内容:")
        print("-" * 50)
        # 显示最后1000字符
        if len(content) > 1000:
            print("...")
            print(content[-1000:])
        else:
            print(content)
        print("-" * 50)
    else:
        print("⚠️ planning_list.md 文件为空或不存在")


def test_interactive_planning():
    """测试交互式planning流程"""
    
    print("🚀 开始测试交互式Planning Agent")
    print_separator("初始化")
    
    # 检查环境
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 请设置 OPENAI_API_KEY 环境变量")
        return False
    
    print(f"✅ API Key exists...")
    
    # 创建交互式planning agent
    config = {
        "configurable": {
            "evaluation_model": "gpt-4o-mini",
            "generation_model": "gpt-4o",
            "temperature": 0.3
        }
    }
    
    agent = create_interactive_planning_agent(config)
    print("✅ 交互式Planning Agent 已创建")
    
    # 显示当前planning文件
    show_current_planning()
    
    # 开始交互循环
    conversation_history = []
    
    print_separator("交互式Planning流程")
    print("💡 使用说明:")
    print("1. 输入您的研究查询 -> 系统立即评估并生成报告规划")
    print("2. 系统显示规划结果，包含研究主题和澄清建议（如果需要）")
    print("3. 您可以通过自然语言修改研究主题:")
    print("   - '添加技术风险分析主题'")
    print("   - '删除第2个主题'")
    print("   - '修改市场分析为用户调研'")
    print("   - '重新设计整个报告结构'")
    print("4. 继续输入新的研究需求或回应澄清问题")
    print("")
    print("🔧 特殊命令:")
    print("  'done' - 确认规划完成，进入下一步研究")
    print("  'q' 或 'quit' - 结束当前规划，进入下一步研究")
    print("  'generate' - 基于对话历史重新生成计划")
    print("  'show' - 查看当前planning文件完整内容")
    print("")
    print("🎯 核心特点: 支持灵活的LLM生成+交互式修改topics")
    
    while True:
        try:
            print("\n" + "-"*50)
            # user_input = input("🔍 请输入您的查询或回应: ").strip()
            # 自动输入'q'来跳过planning agent
            user_input = 'q'
            print("🔍 请输入您的查询或回应: q")  # 显示自动输入的内容
            
            if user_input.lower() in ['quit', 'q', 'exit']:
                print("👋 步骤1结束，准备进入下一步!")
                print("📋 当前规划状态已保存，即将开始多Topic研究...")
                return True  # 直接返回True进入下一步
            
            if user_input.lower() in ['done', 'finish', 'complete']:
                print("✅ 规划已完成，准备进入下一步!")
                print("📋 当前规划已确认，即将开始多Topic研究...")
                return True  # 返回True表示规划成功完成
            
            if user_input.lower() == 'show':
                show_current_planning()
                continue
            
            if not user_input:
                print("⚠️ 请输入有效内容")
                continue
            
            # 添加到对话历史
            conversation_history.append(HumanMessage(content=user_input))
            
            # 检查是否为修改请求
            modification_keywords = ['修改', '改', '添加', '删除', '调整', '重新设计', '替换', '增加', '减少', '移除']
            is_modification = any(keyword in user_input for keyword in modification_keywords)
            
            if is_modification:
                print("🔧 检测到修改请求，正在调整研究主题...")
                
                # 使用新的修改功能
                mod_result = agent.modify_topics_based_on_feedback(user_input, conversation_history)
                
                if mod_result.get('success'):
                    print(f"✅ 主题修改成功!")
                    print(f"📊 修改后包含 {mod_result.get('topics_count', 0)} 个研究主题")
                    
                    # 显示修改后的主题概览
                    planning_data = mod_result.get('planning_data', {})
                    if planning_data:
                        print(f"📊 报告标题: {planning_data.get('report_title', 'N/A')}")
                        topics = planning_data.get('research_topics', [])
                        for i, topic in enumerate(topics, 1):
                            print(f"  Topic {i}: {topic.get('topic_name', 'N/A')}")
                    
                    print(f"📁 已保存到: {mod_result.get('file_path', 'N/A')}")
                else:
                    print(f"❌ 修改失败: {mod_result.get('message', '未知错误')}")
                
                continue  # 继续循环，等待下一个输入
            
            # 特殊命令：强制重新生成（基于对话历史）
            if user_input.lower() == 'generate':
                print("🔄 基于对话历史重新生成计划...")
                if conversation_history:
                    # 使用最后一个实际查询
                    last_query = ""
                    for msg in reversed(conversation_history):
                        if msg.content.lower() not in ['generate', 'show']:
                            last_query = msg.content
                            break
                    
                    if last_query:
                        result = agent.generate_planning_with_context(
                            last_query, 
                            conversation_history, 
                            force_generation=True
                        )
                        
                        if result["success"]:
                            print(f"✅ {result['message']}")
                            print(f"📁 文件路径: {result['file_path']}")
                            
                            # 显示新生成的内容
                            print("\n📋 重新生成的计划:")
                            show_current_planning()
                        else:
                            print(f"❌ 生成失败: {result['message']}")
                    else:
                        print("❌ 没有找到有效的查询内容")
                else:
                    print("❌ 没有对话历史，无法生成计划")
                continue
            
            # 核心改变：每次用户输入后立即处理和更新planning_list
            print("🤖 正在处理您的输入并更新计划...")
            
            # 使用新的统一处理方法：评估 + 立即更新
            result = agent.process_user_input_with_update(user_input, conversation_history)
            
            # 显示评估结果
            evaluation = result['evaluation']
            is_sufficient = evaluation['is_sufficient']
            clarification_questions = evaluation['clarification_questions']
            evaluation_data = evaluation['evaluation_data']
            
            print(f"📊 评估结果:")
            print(f"  需求充分性: {'✅ 充分' if is_sufficient else '❓ 需要澄清'}")
            print(f"  置信度: {evaluation_data.get('confidence_score', 0):.2f}")
            
            if evaluation_data.get('knowledge_gap'):
                print(f"  知识缺口: {evaluation_data['knowledge_gap']}")
            
            # 显示计划更新结果
            planning_result = result['planning']
            if planning_result.get('success'):
                print(f"\n✅ 报告规划已生成: {planning_result['message']}")
                
                # 显示关键统计信息
                planning_data = planning_result.get('planning_data', {})
                if planning_data:
                    print(f"📊 报告标题: {planning_data.get('report_title', 'N/A')}")
                    print(f"❓ 核心问题: {planning_data.get('core_research_question', 'N/A')}")
                    
                    topics = planning_data.get('research_topics', [])
                    print(f"🔬 研究主题数量: {len(topics)}")
                    
                    for i, topic in enumerate(topics, 1):
                        print(f"  Topic {i}: {topic.get('topic_name', 'N/A')}")
                
                # 显示澄清建议（如果需要）
                if not is_sufficient and clarification_questions:
                    print(f"\n💡 澄清建议 ({len(clarification_questions)}个):")
                    for i, question in enumerate(clarification_questions[:3], 1):  # 显示前3个
                        print(f"  {i}. {question}")
                
                # 询问用户是否要修改topics
                print(f"\n🔧 您可以:")
                print("  - 输入修改要求 (例如: '添加技术风险分析主题' 或 '删除第2个主题')")
                print("  - 输入 'show' 查看完整的planning文件")
                print("  - 输入新的研究需求")
                print("  - 输入 'done' 确认规划完成，进入下一步")
                print("  - 输入 'q' 或 'quit' 结束规划，进入下一步")
                
            else:
                print(f"\n❌ 计划更新失败: {planning_result.get('message', '未知错误')}")
                print("🔄 您可以尝试重新表述您的需求")
            
            # 可选：显示更新后的planning文件简要信息
            print(f"\n📁 planning_list.md 已更新 (路径: {planning_result.get('file_path', '未知')})")
            
            print(f"\n{'='*25} 继续对话 {'='*25}")
            print("💡 提示: 您可以通过自然语言修改研究主题")
            
        except KeyboardInterrupt:
            print("\n\n👋 测试被用户中断")
            break
        except Exception as e:
            print(f"❌ 意外错误: {str(e)}")
    
    # 显示最终状态
    print_separator("测试总结")
    print("📊 最终状态:")
    
    # 显示内存状态
    memory = agent.get_state_memory()
    if memory:
        print("🧠 状态内存:")
        for key, value in memory.items():
            print(f"  {key}: {str(value)[:100]}...")
    
    # 显示最终planning文件
    show_current_planning()
    
    print("\n💡 您可以:")
    print("1. 直接编辑 planning_list.md 文件")
    print("2. 重新运行此脚本继续对话")
    print("3. 查看生成的备份文件")
    
    return True


def main():
    """主函数"""
    print("")
    print("")
    try:
        success = test_interactive_planning()
        
        if success:
            print("\n🎉 交互式测试完成!")
        else:
            print("\n❌ 测试失败")
            
    except Exception as e:
        print(f"\n❌ 程序异常: {str(e)}")


if __name__ == '__main__':
    main() 