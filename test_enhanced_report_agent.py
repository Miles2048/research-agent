#!/usr/bin/env python3
"""
Enhanced Report Agent 测试脚本
测试完整的报告生成流程
"""

import sys
import os
import asyncio
from pathlib import Path

# 手动加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 添加src到路径（修正为绝对路径，确保可导入）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from enhanced_report_agent import (
    generate_enhanced_report_sync,
    generate_enhanced_report,
    load_config
)

def test_sync_generation():
    """测试同步报告生成"""
    print("🧪 开始测试同步报告生成...")
    
    try:
        # 测试topic_1
        result = generate_enhanced_report_sync("topic_1")
        
        if result["success"]:
            print(f"✅ 同步生成成功!")
            print(f"📁 输出文件: {result['output_path']}")
            print(f"📊 报告长度: {len(result['report_content'])} 字符")
            print(f"⏱️  生成时间: {result['generation_time']:.2f}秒")
            
            # 检查文件是否存在
            if os.path.exists(result['output_path']):
                print("✅ 输出文件已成功保存")
            else:
                print("❌ 输出文件未找到")
                
        else:
            print(f"❌ 同步生成失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 测试同步生成时出错: {str(e)}")

async def test_async_generation():
    """测试异步报告生成"""
    print("\n🧪 开始测试异步报告生成...")
    
    try:
        # 测试topic_1
        result = await generate_enhanced_report("topic_1")
        
        if result["success"]:
            print(f"✅ 异步生成成功!")
            print(f"📁 输出文件: {result['output_path']}")
            print(f"📊 报告长度: {len(result['report_content'])} 字符")
            print(f"⏱️  生成时间: {result['generation_time']:.2f}秒")
            
            # 检查文件是否存在
            if os.path.exists(result['output_path']):
                print("✅ 输出文件已成功保存")
                
                # 显示报告前200字符作为预览
                with open(result['output_path'], 'r', encoding='utf-8') as f:
                    preview = f.read(200)
                    print(f"📄 报告预览:\n{preview}...")
            else:
                print("❌ 输出文件未找到")
                
        else:
            print(f"❌ 异步生成失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 测试异步生成时出错: {str(e)}")

def test_config_loading():
    """测试配置加载"""
    print("\n🧪 开始测试配置加载...")
    
    try:
        config = load_config()
        print(f"✅ 配置加载成功!")
        print(f"📂 报告配置目录: {config.report_cfg_dir}")
        print(f"📁 结果输出目录: {config.results_dir}")
        print(f"🤖 Claude模型: {config.claude_model}")
        print(f"🔧 最大重试次数: {config.max_retries}")
        
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")

def test_topic_materials():
    """测试topic材料检测"""
    print("\n🧪 开始测试topic材料检测...")
    
    from enhanced_report_agent.content_loader import ContentLoader
    
    try:
        config = load_config()
        loader = ContentLoader(config)
        
        # 检查topic_1
        topic_id = "topic_1"
        topic_path = Path(config.report_cfg_dir) / topic_id
        
        if topic_path.exists():
            print(f"✅ 找到topic: {topic_id}")
            
            # 检查各个子目录
            subdirs = ["prompt", "source_data", "artifacts", "example"]
            for subdir in subdirs:
                subdir_path = topic_path / subdir
                if subdir_path.exists():
                    file_count = len(list(subdir_path.glob("*")))
                    print(f"  📁 {subdir}: {file_count} 个文件")
                else:
                    print(f"  📁 {subdir}: 不存在")
        else:
            print(f"❌ 未找到topic: {topic_id}")
            
    except Exception as e:
        print(f"❌ 测试材料检测时出错: {str(e)}")

def main():
    """主测试函数"""
    print("🚀 Enhanced Report Agent 完整测试开始")
    print("=" * 50)
    
    # 测试配置加载
    test_config_loading()
    
    # 测试材料检测
    test_topic_materials()
    
    # 测试同步生成
    test_sync_generation()
    
    # 测试异步生成
    print("\n⚡ 开始异步测试...")
    asyncio.run(test_async_generation())
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced Report Agent 测试完成!")

if __name__ == "__main__":
    main()