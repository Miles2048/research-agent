#!/usr/bin/env python3
"""
简单的多Topic研究函数
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加路径
sys.path.insert(0, 'src')

from src.tools.planning_parser import PlanningParser


async def multi_topic_research(planning_file_path: str = "src/planning_list.md", artifact_id: int = 1, company_id: int = 3, user_id: int = 3):
    """
    多Topic研究主函数
    1. 把planning_list拆分成多个topic
    2. 每个topic都调用search_agent进行搜索和报告撰写
    """
    
    print("🚀 多Topic研究开始")
    
    # 1. 智能查找planning_list文件
    current_dir = os.getcwd()
    potential_paths = [
        planning_file_path,  # 默认路径
        "src/planning_list.md",
        "../src/planning_list.md", 
        "../../src/planning_list.md",
        os.path.join(current_dir, "src/planning_list.md"),
        os.path.join(current_dir, "planning_list.md"),
    ]
    
    actual_planning_path = None
    for path in potential_paths:
        if os.path.exists(path):
            actual_planning_path = path
            print(f"📁 找到planning文件: {path}")
            break
    
    if not actual_planning_path:
        raise FileNotFoundError(f"无法找到planning_list.md文件，当前目录: {current_dir}")
    
    # 2. 解析planning_list
    parser = PlanningParser()
    topics = parser.parse_planning_file(actual_planning_path)
    
    print(f"📋 找到 {len(topics)} 个topics:")
    for topic in topics:
        print(f"  - {topic.topic_name}")
    
    # 2. 为每个topic调用search_agent
    for i, topic in enumerate(topics, 1):
        print(f"\n🔍 开始研究 Topic {i}: {topic.topic_name}")
        
        # 生成search查询
        search_query = parser.generate_search_query(topic)
        
        # 调用search_agent
        try:
            # 尝试导入search_agent
            from search_agent.search_graph import graph
            from langchain_core.messages import HumanMessage
            
            # 创建配置
            config = {
                "configurable": {
                    "output_dir": f"results/topic_{i}_{topic.topic_name.replace(' ', '_')}",
                    "source_data_dir": f"results/topic_{i}_{topic.topic_name.replace(' ', '_')}/source_data",
                    "report_filename": f"topic_{i}_report"
                }
            }
            
            # 调用search_agent，传递所有必要参数
            result = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=search_query)], 
                    "artifact_id": artifact_id,
                    "company_id": company_id,
                    "user_id": user_id
                },
                config=config
            )
            
            print(f"✅ Topic {i} 研究完成")
            print(f"   报告: {result.get('saved_report_path', 'N/A')}")
            
        except ImportError:
            print(f"⚠️ search_agent导入失败，跳过Topic {i}")
        except Exception as e:
            print(f"❌ Topic {i} 研究失败: {str(e)}")
    
    print("\n🎉 多Topic研究完成!")


if __name__ == "__main__":
    # 示例：使用测试参数
    test_artifact_id = 29
    test_company_id = 4
    test_user_id = 8
    asyncio.run(multi_topic_research(
        artifact_id=test_artifact_id,
        company_id=test_company_id,
        user_id=test_user_id
    )) 