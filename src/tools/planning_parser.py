#!/usr/bin/env python3
"""
Planning解析器 - 解析planning_list.md文件，提取topic信息
"""

import re
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class TopicInfo:
    """Topic信息结构"""
    topic_id: str
    topic_name: str
    topic_subtitle: str
    research_objective: str
    data_requirements: List[str]
    analysis_approach: str
    expected_insights: str
    deliverables: List[str]
    search_instructions: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "topic_subtitle": self.topic_subtitle,
            "research_objective": self.research_objective,
            "data_requirements": self.data_requirements,
            "analysis_approach": self.analysis_approach,
            "expected_insights": self.expected_insights,
            "deliverables": self.deliverables,
            "search_instructions": self.search_instructions
        }


class PlanningParser:
    """Planning文件解析器"""
    
    def __init__(self):
        self.topics: List[TopicInfo] = []
        self.report_metadata: Dict[str, str] = {}
    
    def parse_planning_file(self, file_path: str) -> List[TopicInfo]:
        """解析planning_list.md文件"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Planning文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析报告元数据
        self._parse_metadata(content)
        
        # 解析topics
        self.topics = self._parse_topics(content)
        
        logger.info(f"解析完成: 找到 {len(self.topics)} 个topics")
        return self.topics
    
    def _parse_metadata(self, content: str) -> None:
        """解析报告元数据"""
        
        # 提取报告标题
        title_match = re.search(r'### 🎯 报告标题\s*\*\*(.*?)\*\*', content, re.DOTALL)
        if title_match:
            self.report_metadata['title'] = title_match.group(1).strip()
        
        # 提取核心研究问题
        question_match = re.search(r'### ❓ 核心研究问题\s*(.*?)(?=###|$)', content, re.DOTALL)
        if question_match:
            self.report_metadata['core_question'] = question_match.group(1).strip()
        
        # 提取目标受众
        audience_match = re.search(r'### 👥 目标受众\s*(.*?)(?=###|$)', content, re.DOTALL)
        if audience_match:
            self.report_metadata['target_audience'] = audience_match.group(1).strip()
        
        logger.debug(f"解析元数据: {self.report_metadata}")
    
    def _parse_topics(self, content: str) -> List[TopicInfo]:
        """解析所有topics"""
        
        topics = []
        
        # 查找所有topic部分
        topic_pattern = r'### Topic (\d+): (.*?)\n\*\*(.*?)\*\*\s*(.*?)(?=### Topic |\Z)'
        topic_matches = re.finditer(topic_pattern, content, re.DOTALL)
        
        for match in topic_matches:
            topic_id = match.group(1)
            topic_name = match.group(2).strip()
            topic_subtitle = match.group(3).strip()
            topic_content = match.group(4)
            
            try:
                topic_info = self._parse_single_topic(
                    topic_id, topic_name, topic_subtitle, topic_content
                )
                topics.append(topic_info)
                logger.debug(f"解析Topic {topic_id}: {topic_name}")
                
            except Exception as e:
                logger.warning(f"解析Topic {topic_id}失败: {str(e)}")
                continue
        
        return topics
    
    def _parse_single_topic(self, topic_id: str, topic_name: str, 
                           topic_subtitle: str, content: str) -> TopicInfo:
        """解析单个topic的详细信息"""
        
        # 解析研究目标
        objective_match = re.search(r'\*\*🎯 研究目标:\*\*\s*(.*?)(?=\*\*📋|\*\*🔍|\*\*💡|\*\*📦|\*\*🔎|$)', content, re.DOTALL)
        research_objective = objective_match.group(1).strip() if objective_match else ""
        
        # 解析数据需求
        data_match = re.search(r'\*\*📋 数据需求:\*\*\s*(.*?)(?=\*\*🔍|\*\*💡|\*\*📦|\*\*🔎|$)', content, re.DOTALL)
        data_requirements = []
        if data_match:
            data_text = data_match.group(1).strip()
            # 提取列表项
            data_requirements = [
                line.strip().lstrip('- ').strip()
                for line in data_text.split('\n')
                if line.strip() and line.strip().startswith('-')
            ]
        
        # 解析分析方法
        analysis_match = re.search(r'\*\*🔍 分析方法:\*\*\s*(.*?)(?=\*\*💡|\*\*📦|\*\*🔎|$)', content, re.DOTALL)
        analysis_approach = analysis_match.group(1).strip() if analysis_match else ""
        
        # 解析预期洞察
        insights_match = re.search(r'\*\*💡 预期洞察:\*\*\s*(.*?)(?=\*\*📦|\*\*🔎|$)', content, re.DOTALL)
        expected_insights = insights_match.group(1).strip() if insights_match else ""
        
        # 解析交付物
        deliverables_match = re.search(r'\*\*📦 交付物:\*\*\s*(.*?)(?=\*\*🔎|$)', content, re.DOTALL)
        deliverables = []
        if deliverables_match:
            deliverables_text = deliverables_match.group(1).strip()
            deliverables = [
                line.strip().lstrip('- ').strip()
                for line in deliverables_text.split('\n')
                if line.strip() and line.strip().startswith('-')
            ]
        
        # 解析Search Agent指导
        search_match = re.search(r'\*\*🔎 Search Agent指导:\*\*\s*(.*?)(?=---|$)', content, re.DOTALL)
        search_instructions = search_match.group(1).strip() if search_match else ""
        
        return TopicInfo(
            topic_id=topic_id,
            topic_name=topic_name,
            topic_subtitle=topic_subtitle,
            research_objective=research_objective,
            data_requirements=data_requirements,
            analysis_approach=analysis_approach,
            expected_insights=expected_insights,
            deliverables=deliverables,
            search_instructions=search_instructions
        )
    
    def generate_search_query(self, topic: TopicInfo) -> str:
        """为topic生成search_agent查询"""
        
        # 构建综合查询
        query_parts = [
            f"# {topic.topic_name}: {topic.topic_subtitle}",
            "",
            "## 研究目标",
            topic.research_objective,
            "",
            "## 重点收集的数据类型"
        ]
        
        # 添加数据需求（限制前5个最重要的）
        for i, req in enumerate(topic.data_requirements[:5], 1):
            query_parts.append(f"{i}. {req}")
        
        query_parts.extend([
            "",
            "## 分析方法",
            topic.analysis_approach,
            "",
            "## 期望获得的关键洞察",
            topic.expected_insights,
            "",
            "## 具体搜索指导",
            topic.search_instructions
        ])
        
        return "\n".join(query_parts)
    
    def get_report_metadata(self) -> Dict[str, str]:
        """获取报告元数据"""
        return self.report_metadata
    
    def get_topics_summary(self) -> Dict[str, Any]:
        """获取topics概览"""
        return {
            "total_topics": len(self.topics),
            "topics": [
                {
                    "id": topic.topic_id,
                    "name": topic.topic_name,
                    "subtitle": topic.topic_subtitle,
                    "data_requirements_count": len(topic.data_requirements),
                    "deliverables_count": len(topic.deliverables)
                }
                for topic in self.topics
            ]
        }


def demo_planning_parser():
    """演示planning解析功能"""
    
    # 查找planning_list.md文件
    possible_paths = [
        "src/planning_list.md",
        "../planning_list.md",
        "planning_list.md"
    ]
    
    planning_file = None
    for path in possible_paths:
        if os.path.exists(path):
            planning_file = path
            break
    
    if not planning_file:
        print("❌ 找不到planning_list.md文件")
        return
    
    print(f"📁 读取planning文件: {planning_file}")
    
    # 创建解析器
    parser = PlanningParser()
    
    try:
        # 解析文件
        topics = parser.parse_planning_file(planning_file)
        
        # 显示元数据
        metadata = parser.get_report_metadata()
        print("\n📊 报告元数据:")
        for key, value in metadata.items():
            print(f"  {key}: {value[:100]}...")
        
        # 显示topics概览
        summary = parser.get_topics_summary()
        print(f"\n🔬 找到 {summary['total_topics']} 个研究主题:")
        
        for topic in summary['topics']:
            print(f"  📋 Topic {topic['id']}: {topic['name']}")
            print(f"    - 副标题: {topic['subtitle']}")
            print(f"    - 数据需求: {topic['data_requirements_count']} 项")
            print(f"    - 交付物: {topic['deliverables_count']} 项")
        
        # 显示第一个topic的完整查询
        if topics:
            print(f"\n🔍 Topic 1查询示例:")
            print("=" * 60)
            query = parser.generate_search_query(topics[0])
            print(query[:500] + "..." if len(query) > 500 else query)
        
        return topics
        
    except Exception as e:
        print(f"❌ 解析失败: {str(e)}")
        return None


if __name__ == "__main__":
    demo_planning_parser() 