#!/usr/bin/env python3
"""
分析 web_searcher_instructions prompt 的构成和作用
"""

from agent.prompts import web_searcher_instructions, get_current_date


def analyze_prompt_structure():
    """分析prompt的结构"""
    print("🔍 Web Searcher Prompt 结构分析")
    print("=" * 60)
    
    # 1. 基础模板
    print("1️⃣ 基础模板 (web_searcher_instructions):")
    print("-" * 40)
    print(web_searcher_instructions)
    print("-" * 40)
    
    # 2. 模板变量
    print("\n2️⃣ 模板变量:")
    print("   📅 {current_date} - 当前日期")
    print("   🎯 {research_topic} - 研究主题")
    
    # 3. 动态添加的部分
    print("\n3️⃣ 动态添加的搜索结果部分:")
    print('   + "\\n\\nSearch Results:\\n{search_context}"')
    print('   + "\\n\\nBased on these search results, provide a comprehensive summary with citations."')


def demo_prompt_construction():
    """演示prompt的构建过程"""
    print("\n🏗️ Prompt 构建过程演示")
    print("=" * 60)
    
    # 模拟参数
    research_topic = "artificial intelligence trends"
    current_date = get_current_date()
    
    # 模拟搜索结果
    search_results = [
        {
            "title": "AI Trends 2024: Machine Learning Advances",
            "url": "https://techreview.com/ai-trends-2024",
            "snippet": "Machine learning continues to evolve with new transformer architectures and improved efficiency in 2024."
        },
        {
            "title": "The Future of Artificial Intelligence",
            "url": "https://aijournal.com/future-ai",
            "snippet": "AI applications are expanding into healthcare, finance, and autonomous systems with remarkable progress."
        }
    ]
    
    # 构建搜索上下文
    search_context = "\n\n".join([
        f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}"
        for result in search_results
    ])
    
    print("📋 构建参数:")
    print(f"   研究主题: {research_topic}")
    print(f"   当前日期: {current_date}")
    print(f"   搜索结果数量: {len(search_results)}")
    
    # 第一步：格式化基础模板
    print("\n🔸 步骤1: 格式化基础模板")
    base_prompt = web_searcher_instructions.format(
        current_date=current_date,
        research_topic=research_topic,
    )
    print("基础prompt长度:", len(base_prompt), "字符")
    
    # 第二步：添加搜索结果
    print("\n🔸 步骤2: 添加搜索结果和指令")
    final_prompt = base_prompt + f"\n\nSearch Results:\n{search_context}\n\nBased on these search results, provide a comprehensive summary with citations."
    
    print("最终prompt长度:", len(final_prompt), "字符")
    
    return final_prompt


def show_complete_prompt():
    """显示完整的prompt示例"""
    print("\n📄 完整Prompt示例")
    print("=" * 60)
    
    final_prompt = demo_prompt_construction()
    
    print("\n完整Prompt内容:")
    print("=" * 60)
    print(final_prompt)
    print("=" * 60)


def explain_prompt_purpose():
    """解释prompt的目的和作用"""
    print("\n🎯 Prompt的目的和作用")
    print("=" * 60)
    
    print("这个复合prompt的作用是:")
    print()
    
    print("1️⃣ 基础指令部分 (web_searcher_instructions):")
    print("   📝 告诉AI要做什么: 分析搜索结果")
    print("   📅 提供时间上下文: 当前日期")
    print("   🎯 明确研究主题: 要研究的内容")
    print("   ⚠️ 设置约束: 只使用搜索结果，不编造信息")
    
    print("\n2️⃣ 搜索结果部分:")
    print("   📊 提供真实数据: 网络搜索的结果")
    print("   🔗 包含来源信息: 标题、链接、摘要")
    print("   📚 多个信息源: 提供全面的信息基础")
    
    print("\n3️⃣ 最终指令部分:")
    print("   📋 明确输出要求: 综合摘要")
    print("   🔗 要求引用: 包含引用链接")
    print("   ✅ 确保质量: 基于证据的分析")
    
    print("\n🔄 整体工作流程:")
    print("   输入: 研究主题 + 搜索结果")
    print("   处理: AI分析和综合")
    print("   输出: 带引用的研究摘要")


def show_ai_perspective():
    """从AI的角度解释这个prompt"""
    print("\n🤖 从AI的角度看这个Prompt")
    print("=" * 60)
    
    print("AI收到这个prompt时会理解:")
    print()
    
    print("📋 任务定义:")
    print("   - 我需要分析提供的搜索结果")
    print("   - 我要生成一个综合性的研究摘要")
    print("   - 我必须包含适当的引用")
    
    print("\n📊 数据来源:")
    print("   - 我有具体的搜索结果数据")
    print("   - 每个结果都有标题、链接和摘要")
    print("   - 我不能编造额外的信息")
    
    print("\n🎯 输出要求:")
    print("   - 写一个全面的摘要")
    print("   - 基于提供的搜索结果")
    print("   - 包含引用链接")
    print("   - 保持信息的准确性")
    
    print("\n⚖️ 约束条件:")
    print("   - 只使用搜索结果中的信息")
    print("   - 不能添加我预训练知识中的额外信息")
    print("   - 必须保持客观和准确")


if __name__ == "__main__":
    analyze_prompt_structure()
    demo_prompt_construction()
    show_complete_prompt()
    explain_prompt_purpose()
    show_ai_perspective()