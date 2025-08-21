#!/usr/bin/env python3
"""
研究测试脚本 - 测试完整的研究流程包括文件保存
"""

import sys
import os
from datetime import datetime
from langchain_core.messages import HumanMessage

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.graph import graph


def main():
    """主函数"""
    print("🔬 研究代理完整测试")
    print("=" * 60)
    
    # 测试查询
    RESEARCH_QUERY = "What are the latest developments in machine learning?"
    
    print(f"📝 查询: {RESEARCH_QUERY}")
    print("⚙️ 配置: 快速测试模式")
    print("=" * 60)
    
    # 构建状态
    state = {
        "messages": [HumanMessage(content=RESEARCH_QUERY)],
        "initial_search_query_count": 2,  # 减少查询数量
        "max_research_loops": 1,          # 减少循环次数
        "reasoning_model": "gpt-4o-mini", # 使用快速模型
    }
    
    try:
        print("🤖 开始研究...")
        start_time = datetime.now()
        
        # 执行研究
        result = graph.invoke(state)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ 研究完成! 耗时: {duration:.2f}秒")
        print("=" * 60)
        
        # 显示结果
        messages = result.get("messages", [])
        if messages:
            print("📊 研究结果:")
            print("-" * 40)
            print(messages[-1].content[:500] + "..." if len(messages[-1].content) > 500 else messages[-1].content)
            print("-" * 40)
        
        # 显示文件保存信息
        report_path = result.get("saved_report_path")
        source_files = result.get("saved_source_files", [])
        
        print(f"\n💾 文件保存结果:")
        if report_path:
            print(f"   📄 报告: {report_path}")
        else:
            print(f"   ❌ 报告保存失败")
            
        if source_files:
            print(f"   📚 数据源: {len(source_files)} 个文件")
            for i, file_path in enumerate(source_files[:3], 1):
                print(f"      {i}. {os.path.basename(file_path)}")
            if len(source_files) > 3:
                print(f"      ... 还有 {len(source_files) - 3} 个文件")
        else:
            print(f"   ❌ 数据源保存失败")
        
        # 验证文件是否真的存在
        print(f"\n🔍 文件验证:")
        if report_path and os.path.exists(report_path):
            print(f"   ✅ 报告文件存在")
        elif report_path:
            print(f"   ❌ 报告文件不存在: {report_path}")
            
        existing_sources = 0
        for file_path in source_files:
            if os.path.exists(file_path):
                existing_sources += 1
        
        print(f"   📚 数据源文件: {existing_sources}/{len(source_files)} 个存在")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()