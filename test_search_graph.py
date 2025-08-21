!/usr/bin/env python3
"""
简单研究测试脚本
整合了 simple_research.py 的功能，使用正确的导入路径
"""

import sys
import os

# 添加正确的路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(backend_dir, 'src'))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

from langchain_core.messages import HumanMessage
from agent.graph import graph


def simple_research():
    """运行简单的研究示例（移植自 simple_research.py）"""
    
    # 🔥 在这里直接修改您的查询！
    RESEARCH_QUERY = """atmospheric water generator" OR "air-to-water generator" OR "AWG" OR "air water generator" OR "ice maker" OR "ice machine") AND ("market report" OR "industry analysis" OR "market research" OR "industry report") AND ("North America" OR "United States" OR "USA" OR "Canada" OR "US market") AND ("2024" OR "2025" OR "market size" OR "forecast" OR "trends")

**北美空气制水机和制冰机行业研究报告**

**目标**：深入研究北美空气制水机和制冰机市场的行业现状、发展趋势、竞争格局及市场机会。

**关键搜索维度**：
1. 市场规模数据：北美空气制水机/制冰机市场规模、增长率、预测、细分市场分析（家用、商用、工业用）
2. 竞争格局分析：主要竞争对手、市场份额、定价策略、技术优势
3. 消费者行为研究：北美消费者对空气制水机/制冰机的接受度、购买决策因素、品牌偏好
4. 技术发展趋势：空气制水/制冰技术发展、能效标准、环保要求、智能化
5. 法规政策环境：产品认证（UL、FCC等）、环保法规、进口关税、贸易政策
6. 渠道供应链：分销渠道、供应链成本、物流效率、售后服务

**搜索重点**：
- 必须是北美市场（美国、加拿大）
- 必须是空气制水机或制冰机相关
- 优先选择行业报告、市场研究、公司年报
- 包含具体数据、预测、趋势分析"""
    
    # 可选配置
    INITIAL_QUERIES = 2  # 初始搜索查询数量
    MAX_LOOPS = 3        # 最大研究循环次数
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
    try:
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
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


def test_simple_research():
    """使用 GPT-4o 测试简单的研究查询"""
    
    # 测试查询
    query = "What is the latest news about OpenAI?"
    
    print(f"🧪 测试查询: {query}")
    print("-" * 50)
    
    # 配置状态
    state = {
        "messages": [HumanMessage(content=query)],
        "initial_search_query_count": 2,    # 生成2个初始查询
        "max_research_loops": 3,            # 最多1轮研究循环
        "reasoning_model": "gpt-4o",        # 使用 GPT-4o
    }
    
    try:
        # 调用图
        print("⏳ 正在执行研究...")
        result = graph.invoke(state)
        
        # 输出结果
        if result.get("messages"):
            print("\n✅ 研究完成!")
            print("\n📝 最终答案:")
            print(result["messages"][-1].content)
            
            # 显示使用的查询
            if result.get("search_query"):
                print(f"\n🔍 使用的搜索查询 ({len(result['search_query'])}):")
                for i, q in enumerate(result['search_query'], 1):
                    print(f"  {i}. {q}")
            
            # 显示找到的源
            if result.get("sources_gathered"):
                print(f"\n📚 找到的信息源 ({len(result['sources_gathered'])}):")
                for i, source in enumerate(result['sources_gathered'], 1):
                    print(f"  {i}. {source.get('label', 'Unknown')}")
                    
        else:
            print("❌ 没有返回结果")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_custom_config():
    """测试自定义配置"""
    
    query = "Tell me about Python 3.12 new features"
    
    print(f"\n🧪 自定义配置测试: {query}")
    print("-" * 50)
    
    state = {
        "messages": [HumanMessage(content=query)],
        "initial_search_query_count": 3,    # 更多初始查询
        "max_research_loops": 2,            # 更多研究循环
        "reasoning_model": "gpt-4o",
    }
    
    try:
        result = graph.invoke(state)
        
        if result.get("messages"):
            print("✅ 测试成功!")
            print(f"生成了 {len(result.get('search_query', []))} 个查询")
            print(f"找到了 {len(result.get('sources_gathered', []))} 个信息源")
        else:
            print("❌ 没有结果")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主函数 - 提供选项菜单"""
    print("=" * 60)
    print("🚀 研究测试脚本")
    print("=" * 60)
    print("\n请选择要运行的功能：")
    print("1. 运行简单研究（类似 simple_research.py）")
    print("2. 运行测试套件")
    print("3. 运行所有功能")
    
    # choice = input("\n请输入选项 (1/2/3，默认为1): ").strip() or "1"
    choice = "1"
    
    if choice == "1":
        simple_research()
    elif choice == "2":
        test_simple_research()
        print("\n" + "="*60 + "\n")
        test_with_custom_config()
    elif choice == "3":
        simple_research()
        print("\n" + "="*60 + "\n")
        test_simple_research()
        print("\n" + "="*60 + "\n")
        test_with_custom_config()
    else:
        print("❌ 无效选项，运行默认功能...")
        simple_research()


if __name__ == "__main__":
    # 如果有命令行参数，根据参数运行
    if len(sys.argv) > 1:
        if sys.argv[1] == "simple":
            simple_research()
        elif sys.argv[1] == "test":
            test_simple_research()
            print("\n" + "="*60 + "\n")
            test_with_custom_config()
        else:
            print(f"❌ 未知参数: {sys.argv[1]}")
            print("用法: python test_graph_simple.py [simple|test]")
    else:
        # 没有参数时显示菜单
        main()