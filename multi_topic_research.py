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


async def multi_topic_research(planning_file_path: str = "src/planning_list.md"):
    """
    多Topic研究主函数
    1. 把planning_list拆分成多个topic
    2. 每个topic都调用search_agent进行搜索和报告撰写
    """
    
    print("🚀 多Topic研究开始")
    
    # 1. 解析planning_list
    parser = PlanningParser()
    topics = parser.parse_planning_file(planning_file_path)
    
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
            
            # 调用search_agent
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=search_query)]},
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
    asyncio.run(multi_topic_research()) 