#!/usr/bin/env python3
"""
测试优化后的输出界面
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from langchain_core.messages import HumanMessage
from agent.graph import graph
from loguru import logger

# 配置loguru输出格式
logger.remove()  # 移除默认处理器
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)


def main():
    """测试优化后的输出"""
    
    logger.info("开始研究代理测试")
    
    # 测试查询
    query = "What are the latest developments in machine learning?"
    
    # 构建状态
    state = {
        "messages": [HumanMessage(content=query)],
        "initial_search_query_count": 2,
        "max_research_loops": 1,
        "reasoning_model": "gpt-4o-mini",
    }
    
    try:
        logger.info(f"查询: {query[:50]}...")
        
        start_time = datetime.now()
        result = graph.invoke(state)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # 获取结果统计
        messages = result.get("messages", [])
        sources = result.get("sources_gathered", [])
        report_path = result.get("saved_report_path")
        source_files = result.get("saved_source_files", [])
        
        # 输出总结
        if messages:
            logger.success(f"研究完成 - 耗时: {duration:.1f}秒")
            logger.info(f"数据源: {len(sources)} 个")
            
            if report_path:
                logger.info(f"报告已保存: {os.path.basename(report_path)}")
            
            if source_files:
                logger.info(f"数据源文件: {len(source_files)} 个")
        else:
            logger.error("研究失败 - 未获得结果")
            
    except Exception as e:
        logger.error(f"研究过程出错: {str(e)[:50]}...")


if __name__ == "__main__":
    main()