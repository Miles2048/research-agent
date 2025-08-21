#!/usr/bin/env python3
"""
配置优先级演示
"""

import os
from agent.configuration import Configuration
from langchain_core.runnables import RunnableConfig


def demonstrate_priority():
    """演示配置优先级"""
    
    print("🔧 配置优先级演示")
    print("=" * 60)
    
    # 清理环境变量
    env_vars_to_clean = ["QUERY_GENERATOR_MODEL", "MAX_RESEARCH_LOOPS"]
    for var in env_vars_to_clean:
        if var in os.environ:
            del os.environ[var]
    
    # 1. 只有默认值
    print("1️⃣ 只有默认值 (configuration.py):")
    config1 = Configuration.from_runnable_config(None)
    print(f"   query_generator_model: {config1.query_generator_model}")
    print(f"   max_research_loops: {config1.max_research_loops}")
    
    # 2. 环境变量覆盖默认值
    print("\n2️⃣ 环境变量覆盖默认值:")
    os.environ["QUERY_GENERATOR_MODEL"] = "gpt-3.5-turbo"
    os.environ["MAX_RESEARCH_LOOPS"] = "5"
    
    config2 = Configuration.from_runnable_config(None)
    print(f"   环境变量 QUERY_GENERATOR_MODEL: gpt-3.5-turbo")
    print(f"   环境变量 MAX_RESEARCH_LOOPS: 5")
    print(f"   实际使用 query_generator_model: {config2.query_generator_model}")
    print(f"   实际使用 max_research_loops: {config2.max_research_loops}")
    
    # 3. RunnableConfig覆盖环境变量
    print("\n3️⃣ RunnableConfig覆盖环境变量:")
    runtime_config = RunnableConfig(
        configurable={
            "query_generator_model": "gpt-4o",  # 覆盖环境变量
            "max_research_loops": 1             # 覆盖环境变量
        }
    )
    
    config3 = Configuration.from_runnable_config(runtime_config)
    print(f"   环境变量: gpt-3.5-turbo, 5")
    print(f"   RunnableConfig: gpt-4o, 1")
    print(f"   最终使用 query_generator_model: {config3.query_generator_model}")
    print(f"   最终使用 max_research_loops: {config3.max_research_loops}")
    
    # 4. 部分覆盖演示
    print("\n4️⃣ 部分覆盖演示:")
    partial_config = RunnableConfig(
        configurable={
            "query_generator_model": "gpt-4o"  # 只覆盖这一个
            # max_research_loops 不设置，会使用环境变量
        }
    )
    
    config4 = Configuration.from_runnable_config(partial_config)
    print(f"   RunnableConfig只设置: query_generator_model=gpt-4o")
    print(f"   环境变量设置: MAX_RESEARCH_LOOPS=5")
    print(f"   结果 query_generator_model: {config4.query_generator_model}")
    print(f"   结果 max_research_loops: {config4.max_research_loops}")
    
    # 清理环境变量
    for var in env_vars_to_clean:
        if var in os.environ:
            del os.environ[var]


def show_correct_ways_to_configure():
    """展示正确的配置方法"""
    
    print("\n✅ 正确的配置方法")
    print("=" * 60)
    
    print("方法1: 修改环境变量")
    print("```bash")
    print("export QUERY_GENERATOR_MODEL='gpt-4o'")
    print("export MAX_RESEARCH_LOOPS='1'")
    print("```")
    
    print("\n方法2: 在.env文件中设置")
    print("```")
    print("QUERY_GENERATOR_MODEL=gpt-4o")
    print("MAX_RESEARCH_LOOPS=1")
    print("```")
    
    print("\n方法3: 在代码中使用RunnableConfig")
    print("```python")
    print("config = RunnableConfig(")
    print("    configurable={")
    print("        'query_generator_model': 'gpt-4o',")
    print("        'max_research_loops': 1")
    print("    }")
    print(")")
    print("result = graph.invoke(state, config=config)")
    print("```")
    
    print("\n方法4: 修改configuration.py的默认值 (影响所有未配置的情况)")
    print("```python")
    print("query_generator_model: str = Field(")
    print("    default='gpt-4o',  # 修改这里")
    print("    metadata={...}")
    print(")")
    print("```")


def practical_example():
    """实际使用示例"""
    
    print("\n🚀 实际使用示例")
    print("=" * 60)
    
    # 创建不同场景的配置
    scenarios = {
        "调试模式": RunnableConfig(
            configurable={
                "query_generator_model": "gpt-4o-mini",
                "number_of_initial_queries": 1,
                "max_research_loops": 1
            }
        ),
        "标准模式": RunnableConfig(
            configurable={
                "query_generator_model": "gpt-4o",
                "number_of_initial_queries": 3,
                "max_research_loops": 2
            }
        ),
        "深度研究模式": RunnableConfig(
            configurable={
                "query_generator_model": "gpt-4o",
                "reflection_model": "gpt-4o",
                "answer_model": "gpt-4o",
                "number_of_initial_queries": 5,
                "max_research_loops": 3
            }
        )
    }
    
    for name, config in scenarios.items():
        print(f"\n📋 {name}:")
        settings = Configuration.from_runnable_config(config)
        print(f"   查询模型: {settings.query_generator_model}")
        print(f"   查询数量: {settings.number_of_initial_queries}")
        print(f"   最大循环: {settings.max_research_loops}")


if __name__ == "__main__":
    demonstrate_priority()
    show_correct_ways_to_configure()
    practical_example()