#!/usr/bin/env python3
"""
Topic协调器 - 使用修改后的search_agent支持自定义路径
"""

import asyncio
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from typing import List, Dict, Any
from datetime import datetime
from langchain_core.messages import HumanMessage
from loguru import logger

# 延迟导入，避免循环依赖
def get_search_graph():
    try:
        from search_agent.search_graph import graph
        return graph
    except ImportError as e:
        print(f"导入search_agent失败: {str(e)}")
        return None


class TopicOrchestrator:
    """Topic协调器，管理多个search_agent实例的并发执行"""
    
    def __init__(self, base_output_dir: str = "research_results"):
        self.base_output_dir = base_output_dir
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _sanitize_topic_name(self, topic_name: str) -> str:
        """将topic名称转换为安全的文件名"""
        import re
        safe_name = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', topic_name)
        safe_name = re.sub(r'\s+', '_', safe_name).strip('_')
        return safe_name[:50] if safe_name else "unnamed_topic"
    
    def _create_topic_config(self, topic_name: str) -> Dict[str, Any]:
        """为每个topic创建独立的search_agent配置"""
        
        safe_name = self._sanitize_topic_name(topic_name)
        session_dir = f"{self.base_output_dir}/session_{self.session_timestamp}"
        topic_dir = f"{session_dir}/{safe_name}"
        
        return {
            "configurable": {
                "output_dir": topic_dir,
                "source_data_dir": f"{topic_dir}/source_data",
                "report_filename": f"{safe_name}_report",
                "max_research_loops": 2  # 控制研究深度
            }
        }
    
    async def _research_single_topic(self, topic_name: str, query: str) -> Dict[str, Any]:
        """为单个topic执行研究"""
        
        logger.info(f"开始研究topic: {topic_name}")
        
        # 创建topic专用配置
        config = self._create_topic_config(topic_name)
        
        try:
            # 获取search_agent graph
            graph = get_search_graph()
            if graph is None:
                raise ImportError("无法导入search_agent")
            
            # 调用search_agent
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )
            
            logger.success(f"Topic研究完成: {topic_name}")
            
            return {
                "topic_name": topic_name,
                "query": query,
                "success": True,
                "report_path": result.get("saved_report_path"),
                "source_files": result.get("saved_source_files", []),
                "summary_path": result.get("saved_summary_path"),
                "sources_count": result.get("db_saved_count", 0),
                "config": config
            }
            
        except Exception as e:
            logger.error(f"Topic研究失败 {topic_name}: {str(e)}")
            return {
                "topic_name": topic_name,
                "query": query,
                "success": False,
                "error": str(e),
                "config": config
            }
    
    async def research_multiple_topics(self, topics_queries: Dict[str, str]) -> List[Dict[str, Any]]:
        """并发执行多个topic的研究"""
        
        logger.info(f"开始并发研究 {len(topics_queries)} 个topics")
        
        # 创建并发任务
        tasks = [
            self._research_single_topic(topic_name, query)
            for topic_name, query in topics_queries.items()
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result)})
            elif result.get("success"):
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        logger.info(f"研究完成: {len(successful_results)} 成功, {len(failed_results)} 失败")
        
        return successful_results + failed_results
    
    def create_session_summary(self, results: List[Dict[str, Any]]) -> str:
        """创建研究会话摘要"""
        
        session_dir = f"{self.base_output_dir}/session_{self.session_timestamp}"
        os.makedirs(session_dir, exist_ok=True)
        
        summary_path = f"{session_dir}/SESSION_SUMMARY.md"
        
        successful_topics = [r for r in results if r.get("success")]
        failed_topics = [r for r in results if not r.get("success")]
        
        content = f"""# 多Topic研究会话摘要

## 📊 会话信息
- **会话ID**: session_{self.session_timestamp}
- **完成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **成功Topics**: {len(successful_topics)} 个
- **失败Topics**: {len(failed_topics)} 个

## ✅ 成功完成的Topics

"""
        
        for result in successful_topics:
            topic_name = result["topic_name"]
            safe_name = self._sanitize_topic_name(topic_name)
            sources_count = result.get("sources_count", 0)
            
            content += f"""### {topic_name}
- **查询**: {result["query"]}
- **报告**: `./{safe_name}/{safe_name}_report.md`
- **数据源**: {sources_count} 个文件
- **目录**: `./{safe_name}/`

"""
        
        if failed_topics:
            content += f"""## ❌ 失败的Topics

"""
            for result in failed_topics:
                content += f"""### {result.get("topic_name", "Unknown Topic")}
- **错误**: {result.get("error", "Unknown error")}

"""
        
        content += f"""## 📁 目录结构
```
session_{self.session_timestamp}/
├── SESSION_SUMMARY.md          # 本文件
"""
        
        for result in successful_topics:
            safe_name = self._sanitize_topic_name(result["topic_name"])
            content += f"""├── {safe_name}/
│   ├── {safe_name}_report.md
│   ├── research_summary.md
│   └── source_data/
│       └── (数据源文件)
"""
        
        content += """```

---
*多Topic研究系统自动生成*
"""
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.success(f"会话摘要已创建: {summary_path}")
        except Exception as e:
            logger.error(f"创建会话摘要失败: {str(e)}")
        
        return summary_path


async def demo_multi_topic_research():
    """演示多topic并发研究"""
    
    # 模拟4个topics的查询
    topics_queries = {
        "市场格局分析": """
请深度研究空气制水机(AWG)的市场格局，包括：
- 全球市场规模和增长预测
- 主要地理市场分布
- 细分市场机会分析
- 政策驱动因素影响
""",
        
        "消费者洞察": """
请分析空气制水机的消费者需求和行为，包括：
- 用户痛点和关注点
- 不同用户群体的需求差异
- 价格敏感度分析
- 与传统净水器的对比认知
""",
        
        "竞争环境分析": """
请分析空气制水机行业的竞争格局，包括：
- 主要竞争对手对比(Watergen、A1RWATER等)
- 技术路线差异分析
- 关键性能指标对比
- 市场份额和定价策略
""",
        
        "技术可行性评估": """
请评估空气制水机的技术成熟度和商业化前景，包括：
- 核心技术分析和能效评估
- 成本结构和规模化潜力
- 技术壁垒和创新机会
- 商业模式可持续性分析
"""
    }
    
    # 创建协调器
    orchestrator = TopicOrchestrator("research_results")
    
    print("🚀 开始多Topic并发研究...")
    print(f"📊 将研究 {len(topics_queries)} 个topics")
    
    # 执行并发研究
    results = await orchestrator.research_multiple_topics(topics_queries)
    
    # 创建会话摘要
    summary_path = orchestrator.create_session_summary(results)
    
    # 打印结果
    print("\n📈 研究结果总结:")
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"✅ 成功: {len(successful)} 个topics")
    print(f"❌ 失败: {len(failed)} 个topics")
    
    for result in successful:
        print(f"  📋 {result['topic_name']}: {result['sources_count']} 个数据源")
    
    print(f"\n📁 会话摘要: {summary_path}")
    print(f"📂 所有结果保存在: research_results/session_{orchestrator.session_timestamp}/")


if __name__ == "__main__":
    asyncio.run(demo_multi_topic_research()) 