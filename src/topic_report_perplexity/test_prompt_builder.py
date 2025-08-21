#!/usr/bin/env python3
"""
测试 Prompt Builder 功能
演示如何使用和自定义 prompt
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from topic_report_perplexity.prompt_builder import PromptBuilder
from topic_report_perplexity.perplexity_prompts import PerplexityPrompts


def test_basic_prompt():
    """测试基础 prompt 构建"""
    print("=" * 60)
    print("测试基础 Prompt 构建")
    print("=" * 60)
    
    builder = PromptBuilder()
    
    # 构建标准 prompt
    prompt = builder.build_prompt(
        planning_info="研究空气制水机的市场潜力",
        task_guidance="重点分析技术可行性和市场规模",
        source_data=[
            {"filename": "market_data.md", "content": "市场数据内容..."},
            {"filename": "tech_spec.md", "content": "技术规格内容..."}
        ]
    )
    
    print(prompt[:500])  # 打印前500字符
    print("\n...")
    print(prompt[-300:])  # 打印后300字符


def test_topic_specific_prompt():
    """测试特定主题的 prompt"""
    print("\n" + "=" * 60)
    print("测试特定主题 Prompt")
    print("=" * 60)
    
    builder = PromptBuilder()
    
    materials = {
        "planning_info": "分析国际市场机会",
        "prompt": "关注北美和欧洲市场",
        "source_data": [
            {"filename": "us_market.json", "content": "美国市场数据..."},
            {"filename": "eu_market.json", "content": "欧洲市场数据..."}
        ]
    }
    
    # 市场分析类型
    prompt = builder.build_topic_specific_prompt(
        topic_id="topic_1_市场格局分析",
        materials=materials
    )
    
    print("市场分析 Prompt 包含的特定指导：")
    if "市场规模与增长" in prompt:
        print("✓ 包含市场分析专用指导")
    
    # 技术分析类型
    prompt_tech = builder.build_topic_specific_prompt(
        topic_id="topic_2_技术评估",
        materials=materials
    )
    
    if "技术原理" in prompt_tech:
        print("✓ 包含技术分析专用指导")


def test_simple_vs_detailed():
    """测试不同报告类型"""
    print("\n" + "=" * 60)
    print("测试不同报告类型")
    print("=" * 60)
    
    materials = {
        "planning_info": "测试内容",
        "source_data": []
    }
    
    # 简单报告
    builder_simple = PromptBuilder()
    prompt_simple = builder_simple.build_prompt(
        planning_info="简单分析",
        report_type="simple"
    )
    
    # 详细报告
    builder_detailed = PromptBuilder()
    prompt_detailed = builder_detailed.build_prompt(
        planning_info="详细分析",
        report_type="detailed"
    )
    
    print(f"简单报告 Prompt 长度: {len(prompt_simple)} 字符")
    print(f"详细报告 Prompt 长度: {len(prompt_detailed)} 字符")
    
    if "1500-2000字" in prompt_simple:
        print("✓ 简单报告使用简化要求")
    
    if "5000字" in prompt_detailed:
        print("✓ 详细报告使用扩展要求")


def test_custom_prompt():
    """测试自定义 prompt 模板"""
    print("\n" + "=" * 60)
    print("测试自定义 Prompt 模板")
    print("=" * 60)
    
    # 创建自定义 prompt 模板
    class MyCustomPrompts(PerplexityPrompts):
        BASE_INSTRUCTION = "生成一份简洁的技术分析报告，重点关注创新性和实用性。"
        REPORT_REQUIREMENTS = "报告应包含：1. 技术创新点 2. 实际应用 3. 投资建议"
    
    # 使用自定义模板
    custom_builder = PromptBuilder(MyCustomPrompts())
    
    prompt = custom_builder.build_prompt(
        planning_info="分析新技术"
    )
    
    print("自定义 Prompt 内容：")
    print(prompt[:300])
    
    if "创新性和实用性" in prompt:
        print("\n✓ 成功使用自定义模板")


def test_configuration():
    """测试配置参数"""
    print("\n" + "=" * 60)
    print("测试配置参数")
    print("=" * 60)
    
    builder = PromptBuilder()
    
    # 配置参数
    builder.configure(
        max_source_files=5,  # 只包含5个文件
        max_source_content_length=500  # 每个文件最多500字符
    )
    
    # 创建多个数据源
    source_data = [
        {"filename": f"file_{i}.md", "content": "x" * 1000}
        for i in range(20)
    ]
    
    prompt = builder.build_prompt(source_data=source_data)
    
    # 检查是否只包含5个数据源
    data_source_count = prompt.count("### 数据源")
    print(f"数据源数量: {data_source_count}")
    
    if data_source_count == 5:
        print("✓ 成功限制数据源数量")
    
    if "共有 20 个数据源" in prompt:
        print("✓ 包含数据源总数提示")


def main():
    """运行所有测试"""
    print("\n🚀 开始测试 Prompt Builder\n")
    
    test_basic_prompt()
    test_topic_specific_prompt()
    test_simple_vs_detailed()
    test_custom_prompt()
    test_configuration()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    print("\n现在你可以在 prompts.py 中轻松修改任何 prompt 文本，")
    print("而不需要修改主逻辑代码。")


if __name__ == "__main__":
    main()