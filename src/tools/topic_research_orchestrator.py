#!/usr/bin/env python3
"""
Topic研究协调器 - 主要的多topic研究协调逻辑
从planning_list.md解析topics，并发调用search_agent生成研究结果
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

# 确保能找到本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '..')
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

from .planning_parser import PlanningParser, TopicInfo


class TopicResearchOrchestrator:
    """Topic研究协调器"""
    
    def __init__(self, base_output_dir: str = "research_results"):
        self.base_output_dir = base_output_dir
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.parser = PlanningParser()
        self.topics: List[TopicInfo] = []
        self.report_metadata: Dict[str, str] = {}
        
    def _sanitize_topic_name(self, topic_name: str) -> str:
        """将topic名称转换为安全的文件名"""
        import re
        safe_name = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', topic_name)
        safe_name = re.sub(r'\s+', '_', safe_name).strip('_')
        return safe_name[:50] if safe_name else "unnamed_topic"
    
    def _create_topic_config(self, topic: TopicInfo) -> Dict[str, Any]:
        """为每个topic创建独立的search_agent配置"""
        
        safe_name = self._sanitize_topic_name(topic.topic_name)
        session_dir = f"{self.base_output_dir}/session_{self.session_timestamp}"
        topic_dir = f"{session_dir}/{safe_name}"
        
        return {
            "configurable": {
                "output_dir": topic_dir,
                "source_data_dir": f"{topic_dir}/source_data",
                "report_filename": f"{safe_name}_report",
                "max_research_loops": 1,  # 控制研究深度
                "number_of_initial_queries": 1  # 控制初始查询数量
            }
        }
    
    def load_planning_file(self, planning_file_path: str) -> bool:
        """加载和解析planning文件"""
        
        logger.info(f"加载planning文件: {planning_file_path}")
        
        try:
            self.topics = self.parser.parse_planning_file(planning_file_path)
            self.report_metadata = self.parser.get_report_metadata()
            
            logger.success(f"成功解析 {len(self.topics)} 个topics")
            return True
            
        except Exception as e:
            logger.error(f"解析planning文件失败: {str(e)}")
            return False
    
    def get_search_agent_graph(self):
        """获取search_agent图，处理导入问题"""
        try:
            # 尝试不同的导入方式
            try:
                from search_agent.search_graph import graph
                return graph
            except ImportError:
                from src.search_agent.search_graph import graph
                return graph
        except Exception as e:
            logger.error(f"导入search_agent失败: {str(e)}")
            return None
    
    async def research_single_topic(self, topic: TopicInfo) -> Dict[str, Any]:
        """为单个topic执行研究"""
        
        logger.info(f"🔍 开始研究topic: {topic.topic_name}")
        
        try:
            # 获取search_agent graph
            graph = self.get_search_agent_graph()
            if graph is None:
                raise ImportError("无法导入search_agent")
            
            # 动态导入，避免循环依赖
            from langchain_core.messages import HumanMessage
            
            # 生成search查询
            search_query = self.parser.generate_search_query(topic)
            logger.debug(f"生成查询长度: {len(search_query)} 字符")
            
            # 创建topic专用配置
            config = self._create_topic_config(topic)
            logger.info(f"📁 输出目录: {config['configurable']['output_dir']}")
            
            # 调用search_agent
            # 从配置中获取artifact_id，默认为1
            artifact_id = config.get('configurable', {}).get('artifact_id', 1)
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=search_query)], "artifact_id": artifact_id},
                config=config
            )
            
            logger.success(f"✅ Topic研究完成: {topic.topic_name}")
            logger.info(f"📄 报告: {result.get('saved_report_path', 'None')}")
            logger.info(f"📊 数据源: {len(result.get('saved_source_files', []))} 个")
            
            return {
                "topic_info": topic.to_dict(),
                "success": True,
                "report_path": result.get("saved_report_path"),
                "source_files": result.get("saved_source_files", []),
                "summary_path": result.get("saved_summary_path"),
                "sources_count": result.get("db_saved_count", 0),
                "search_query": search_query,
                "config": config,
                "execution_time": None  # 可以添加时间统计
            }
            
        except Exception as e:
            logger.error(f"❌ Topic研究失败 {topic.topic_name}: {str(e)}")
            return {
                "topic_info": topic.to_dict(),
                "success": False,
                "error": str(e),
                "search_query": self.parser.generate_search_query(topic) if hasattr(self, 'parser') else "",
                "config": self._create_topic_config(topic) if hasattr(self, '_create_topic_config') else {}
            }
    
    async def research_all_topics(self) -> List[Dict[str, Any]]:
        """并发执行所有topics的研究"""
        
        if not self.topics:
            raise ValueError("没有加载topics，请先调用load_planning_file()")
        
        logger.info(f"🚀 开始并发研究 {len(self.topics)} 个topics")
        start_time = datetime.now()
        
        # 创建并发任务
        tasks = [
            self.research_single_topic(topic)
            for topic in self.topics
        ]
        
        # 并发执行
        logger.info("⏱️  开始并发执行...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 处理结果
        processed_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "topic_info": {"topic_name": "Unknown"}
                })
                logger.error(f"异常结果: {str(result)}")
            elif result.get("success"):
                successful_count += 1
                processed_results.append(result)
            else:
                failed_count += 1
                processed_results.append(result)
        
        logger.info(f"📈 研究完成: {successful_count} 成功, {failed_count} 失败, 耗时 {duration:.1f}秒")
        
        return processed_results
    
    def create_comprehensive_summary(self, results: List[Dict[str, Any]]) -> str:
        """创建综合研究摘要"""
        
        session_dir = f"{self.base_output_dir}/session_{self.session_timestamp}"
        os.makedirs(session_dir, exist_ok=True)
        
        summary_path = f"{session_dir}/COMPREHENSIVE_RESEARCH_SUMMARY.md"
        
        successful_topics = [r for r in results if r.get("success")]
        failed_topics = [r for r in results if not r.get("success")]
        
        # 构建摘要内容
        content_parts = [
            f"# 综合研究摘要 - {self.report_metadata.get('title', '未知项目')}",
            "",
            "## 📊 研究会话信息",
            f"- **会话ID**: session_{self.session_timestamp}",
            f"- **完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **成功Topics**: {len(successful_topics)} 个",
            f"- **失败Topics**: {len(failed_topics)} 个",
            f"- **总数据源**: {sum(r.get('sources_count', 0) for r in successful_topics)} 个",
            "",
            "## 🎯 原始研究目标",
            f"**核心研究问题**: {self.report_metadata.get('core_question', 'N/A')}",
            f"**目标受众**: {self.report_metadata.get('target_audience', 'N/A')}",
            "",
            "## ✅ 成功完成的研究主题",
            ""
        ]
        
        # 添加成功的topics
        for result in successful_topics:
            topic_info = result.get("topic_info", {})
            topic_name = topic_info.get("topic_name", "Unknown")
            safe_name = self._sanitize_topic_name(topic_name)
            sources_count = result.get("sources_count", 0)
            
            content_parts.extend([
                f"### 📋 {topic_name}",
                f"**副标题**: {topic_info.get('topic_subtitle', 'N/A')}",
                f"**研究目标**: {topic_info.get('research_objective', 'N/A')[:200]}...",
                f"**数据源数量**: {sources_count} 个",
                f"**报告路径**: `./{safe_name}/{safe_name}_report.md`",
                f"**数据源目录**: `./{safe_name}/source_data/`",
                ""
            ])
        
        # 添加失败的topics（如果有）
        if failed_topics:
            content_parts.extend([
                "## ❌ 失败的研究主题",
                ""
            ])
            
            for result in failed_topics:
                topic_info = result.get("topic_info", {})
                topic_name = topic_info.get("topic_name", "Unknown")
                error = result.get("error", "Unknown error")
                
                content_parts.extend([
                    f"### {topic_name}",
                    f"**错误**: {error}",
                    ""
                ])
        
        # 添加目录结构
        content_parts.extend([
            "## 📁 完整目录结构",
            "```",
            f"session_{self.session_timestamp}/",
            "├── COMPREHENSIVE_RESEARCH_SUMMARY.md    # 本文件"
        ])
        
        for result in successful_topics:
            topic_info = result.get("topic_info", {})
            topic_name = topic_info.get("topic_name", "Unknown")
            safe_name = self._sanitize_topic_name(topic_name)
            sources_count = result.get("sources_count", 0)
            
            content_parts.extend([
                f"├── {safe_name}/",
                f"│   ├── {safe_name}_report.md",
                f"│   ├── research_summary.md",
                f"│   └── source_data/",
                f"│       └── ({sources_count} 个数据源文件)"
            ])
        
        content_parts.extend([
            "```",
            "",
            "## 🎯 下一步建议",
            "",
            "1. **深度分析**: 阅读各topic的详细研究报告",
            "2. **交叉验证**: 对比不同topic间的相关发现",
            "3. **综合洞察**: 基于所有研究结果形成整体战略建议",
            "4. **行动计划**: 根据研究发现制定具体的实施方案",
            "",
            "---",
            "*由多Topic研究系统自动生成*"
        ])
        
        content = "\n".join(content_parts)
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.success(f"综合摘要已创建: {summary_path}")
        except Exception as e:
            logger.error(f"创建综合摘要失败: {str(e)}")
        
        return summary_path
    
    def get_research_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取研究统计信息"""
        
        successful_results = [r for r in results if r.get("success")]
        failed_results = [r for r in results if not r.get("success")]
        
        total_sources = sum(r.get("sources_count", 0) for r in successful_results)
        
        return {
            "session_id": f"session_{self.session_timestamp}",
            "total_topics": len(self.topics),
            "successful_topics": len(successful_results),
            "failed_topics": len(failed_results),
            "success_rate": len(successful_results) / len(results) if results else 0,
            "total_data_sources": total_sources,
            "average_sources_per_topic": total_sources / len(successful_results) if successful_results else 0,
            "output_directory": f"{self.base_output_dir}/session_{self.session_timestamp}",
            "report_metadata": self.report_metadata
        }


async def run_full_research_pipeline(planning_file_path: str = "src/planning_list.md") -> Dict[str, Any]:
    """运行完整的研究流水线"""
    
    logger.info("🚀 启动完整的多Topic研究流水线")
    
    # 创建协调器
    orchestrator = TopicResearchOrchestrator()
    
    # 1. 加载planning文件
    if not orchestrator.load_planning_file(planning_file_path):
        raise ValueError(f"无法加载planning文件: {planning_file_path}")
    
    # 2. 执行研究
    results = await orchestrator.research_all_topics()
    
    # 3. 创建综合摘要
    summary_path = orchestrator.create_comprehensive_summary(results)
    
    # 4. 获取统计信息
    statistics = orchestrator.get_research_statistics(results)
    
    # 5. 打印结果概览
    print("\n" + "=" * 80)
    print("🎉 多Topic研究完成!")
    print("=" * 80)
    print(f"📊 会话ID: {statistics['session_id']}")
    print(f"✅ 成功率: {statistics['successful_topics']}/{statistics['total_topics']} ({statistics['success_rate']:.1%})")
    print(f"📚 总数据源: {statistics['total_data_sources']} 个")
    print(f"📁 输出目录: {statistics['output_directory']}")
    print(f"📄 综合摘要: {summary_path}")
    
    return {
        "results": results,
        "statistics": statistics,
        "summary_path": summary_path,
        "orchestrator": orchestrator
    }


if __name__ == "__main__":
    # 运行完整的研究流水线
    try:
        pipeline_result = asyncio.run(run_full_research_pipeline())
        print("\n🎯 流水线执行成功!")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
    except Exception as e:
        print(f"\n❌ 流水线执行失败: {str(e)}")
        logger.error(f"流水线失败: {str(e)}", exc_info=True) 