#!/usr/bin/env python3
"""
Configuration Demo - 演示配置系统如何工作
"""

import os
from agent.configuration import Configuration
from langchain_core.runnables import RunnableConfig


def demo_configuration():
    """演示配置系统"""
    
    print("🔧 LangGraph 配置系统演示")
    print("=" * 50)
    
    # 1. 默认配置（无任何自定义）
    print("1️⃣ 默认配置:")
    default_config = Configuration.from_runnable_config(None)
    print(f"   查询生成模型: {default_config.query_generator_model}")
    print(f"   反思模型: {default_config.reflection_model}")
    print(f"   答案模型: {default_config.answer_model}")
    print(f"   初始查询数量: {default_config.number_of_initial_queries}")
    print(f"   最大循环次数: {default_config.max_research_loops}")
    
    # 2. 通过环境变量配置
    print("\n2️⃣ 环境变量配置:")
    os.environ["QUERY_GENERATOR_MODEL"] = "gpt-3.5-turbo"
    os.environ["NUMBER_OF_INITIAL_QUERIES"] = "5"
    
    env_config = Configuration.from_runnable_config(None)
    print(f"   查询生成模型: {env_config.query_generator_model}")
    print(f"   初始查询数量: {env_config.number_of_initial_queries}")
    
    # 清理环境变量
    del os.environ["QUERY_GENERATOR_MODEL"]
    del os.environ["NUMBER_OF_INITIAL_QUERIES"]
    
    # 3. 通过RunnableConfig配置
    print("\n3️⃣ RunnableConfig配置:")
    custom_config = RunnableConfig(
        configurable={
            "query_generator_model": "gpt-4o",
            "reflection_model": "gpt-4o-mini",
            "max_research_loops": 1
        }
    )
    
    runtime_config = Configuration.from_runnable_config(custom_config)
    print(f"   查询生成模型: {runtime_config.query_generator_model}")
    print(f"   反思模型: {runtime_config.reflection_model}")
    print(f"   最大循环次数: {runtime_config.max_research_loops}")
    
    # 4. 配置优先级演示
    print("\n4️⃣ 配置优先级 (RunnableConfig > 环境变量 > 默认值):")
    os.environ["REFLECTION_MODEL"] = "gpt-3.5-turbo"  # 环境变量
    
    priority_config = RunnableConfig(
        configurable={
            "reflection_model": "gpt-4o"  # RunnableConfig会覆盖环境变量
        }
    )
    
    final_config = Configuration.from_runnable_config(priority_config)
    print(f"   环境变量设置: gpt-3.5-turbo")
    print(f"   RunnableConfig设置: gpt-4o")
    print(f"   最终使用: {final_config.reflection_model}")
    
    # 清理
    del os.environ["REFLECTION_MODEL"]


def demo_practical_usage():
    """演示实际使用场景"""
    
    print("\n🚀 实际使用场景演示")
    print("=" * 50)
    
    # 场景1: 快速调试配置
    debug_config = RunnableConfig(
        configurable={
            "query_generator_model": "gpt-4o-mini",  # 更快更便宜
            "number_of_initial_queries": 1,          # 减少查询数量
            "max_research_loops": 1                  # 减少循环次数
        }
    )
    
    debug_settings = Configuration.from_runnable_config(debug_config)
    print("🐛 调试配置:")
    print(f"   模型: {debug_settings.query_generator_model}")
    print(f"   查询数: {debug_settings.number_of_initial_queries}")
    print(f"   循环数: {debug_settings.max_research_loops}")
    
    # 场景2: 高质量研究配置
    premium_config = RunnableConfig(
        configurable={
            "query_generator_model": "gpt-4o",
            "reflection_model": "gpt-4o",
            "answer_model": "gpt-4o",
            "number_of_initial_queries": 5,
            "max_research_loops": 3
        }
    )
    
    premium_settings = Configuration.from_runnable_config(premium_config)
    print("\n💎 高质量配置:")
    print(f"   所有模型: gpt-4o")
    print(f"   查询数: {premium_settings.number_of_initial_queries}")
    print(f"   循环数: {premium_settings.max_research_loops}")


def show_config_in_action():
    """展示配置在节点函数中的使用"""
    
    print("\n⚙️ 配置在节点函数中的使用")
    print("=" * 50)
    
    # 模拟节点函数中的配置使用
    def mock_node_function(state, config):
        """模拟的节点函数"""
        # 这就是在实际节点中使用的方式
        configurable = Configuration.from_runnable_config(config)
        
        print(f"📋 节点收到的配置:")
        print(f"   使用模型: {configurable.query_generator_model}")
        print(f"   查询数量: {configurable.number_of_initial_queries}")
        
        # 根据配置做不同的处理
        if configurable.query_generator_model == "gpt-4o-mini":
            print("   💡 使用快速模式")
        elif configurable.query_generator_model == "gpt-4o":
            print("   🎯 使用高质量模式")
        
        return {"processed": True}
    
    # 测试不同配置
    test_configs = [
        RunnableConfig(configurable={"query_generator_model": "gpt-4o-mini"}),
        RunnableConfig(configurable={"query_generator_model": "gpt-4o"}),
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n测试 {i}:")
        mock_node_function({}, config)


if __name__ == "__main__":
    demo_configuration()
    demo_practical_usage()
    show_config_in_action()