"""
数据库参考文献评估模块
使用 LLM 评估参考文献的可信度和相关性
"""

import json
import asyncio
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# 添加父目录到路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.search_agent.tools.database import DatabaseManager

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseEvaluator:
    """数据库参考文献评估器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化评估器
        
        Args:
            config_path: 配置文件路径，默认为 database_cfg/evaluation_criteria.json
        """
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "database_cfg" / "evaluation_criteria.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 初始化 LLM
        llm_config = self.config['llm_config']
        self.llm = ChatOpenAI(
            model=llm_config['model'],
            temperature=llm_config['temperature'],
            max_tokens=llm_config['max_tokens']
        )
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 批处理配置
        self.batch_config = self.config['batch_processing']
        
        logger.info(f"评估器初始化完成，使用模型: {llm_config['model']}")
    
    async def evaluate_credibility(self, reference: Dict[str, any]) -> Tuple[int, str]:
        """
        评估参考文献的可信度
        
        Args:
            reference: 参考文献数据
            
        Returns:
            (credibility, credibility_assessment) 元组
        """
        try:
            # 构建提示词
            prompt_template = self.config['credibility_evaluation']['prompt_template']
            prompt = prompt_template.format(
                title=reference.get('reference_title', ''),
                url=reference.get('reference_url', ''),
                publisher=reference.get('publisher', '未知'),
                snippet=reference.get('reference_content', '')[:500]  # 限制长度
            )
            
            # 调用 LLM
            messages = [
                SystemMessage(content=self.config['llm_config']['system_prompt']),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # 解析响应
            try:
                result = json.loads(response.content)
                credibility = result.get('credibility', 2)
                credibility_assessment = result.get('credibility_assessment', '')
                
                # 验证可信度值
                if credibility not in [1, 2, 3]:
                    credibility = 2
                    
                return credibility, credibility_assessment
                
            except json.JSONDecodeError:
                logger.error(f"JSON 解析失败: {response.content}")
                return 2, "评估过程出现错误，默认为中等可信度"
                
        except Exception as e:
            logger.error(f"可信度评估失败: {str(e)}")
            return 2, f"评估失败: {str(e)}"
    
    async def evaluate_relevance(self, reference: Dict[str, any], research_topic: str) -> Tuple[float, str]:
        """
        评估参考文献的相关性
        
        Args:
            reference: 参考文献数据
            research_topic: 研究主题
            
        Returns:
            (related_assessment, related_assessment_text) 元组
        """
        try:
            # 构建提示词
            prompt_template = self.config['relevance_evaluation']['prompt_template']
            prompt = prompt_template.format(
                research_topic=research_topic,
                title=reference.get('reference_title', ''),
                snippet=reference.get('reference_content', '')[:500]  # 限制长度
            )
            
            # 调用 LLM
            messages = [
                SystemMessage(content=self.config['llm_config']['system_prompt']),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # 解析响应
            try:
                result = json.loads(response.content)
                related_assessment = result.get('related_assessment', 0.5)
                related_assessment_text = result.get('related_assessment_text', '')
                
                # 验证相关性值
                if not (0 <= related_assessment <= 1):
                    related_assessment = 0.5
                    
                return round(related_assessment, 2), related_assessment_text
                
            except json.JSONDecodeError:
                logger.error(f"JSON 解析失败: {response.content}")
                return 0.5, "评估过程出现错误，默认为中等相关性"
                
        except Exception as e:
            logger.error(f"相关性评估失败: {str(e)}")
            return 0.5, f"评估失败: {str(e)}"
    
    async def evaluate_reference(self, reference: Dict[str, any], research_topic: str) -> Dict[str, any]:
        """
        完整评估一条参考文献
        
        Args:
            reference: 参考文献数据
            research_topic: 研究主题
            
        Returns:
            包含所有评估结果的字典
        """
        logger.info(f"开始评估: {reference.get('reference_title', '')[:50]}")
        
        # 并行执行两个评估
        credibility_task = self.evaluate_credibility(reference)
        relevance_task = self.evaluate_relevance(reference, research_topic)
        
        (credibility, credibility_assessment), (related_assessment, related_assessment_text) = \
            await asyncio.gather(credibility_task, relevance_task)
        
        # 构建更新数据
        update_data = {
            'credibility': credibility,
            'credibility_assessment': credibility_assessment,
            'related_assessment': related_assessment,
            'related_assessment_text': related_assessment_text,
            'status': 1  # 标记为已评估
        }
        
        logger.info(f"评估完成 - 可信度: {credibility}, 相关性: {related_assessment}")
        
        return update_data
    
    async def evaluate_batch(self, research_topic: str, limit: int = None) -> int:
        """
        批量评估未处理的参考文献
        
        Args:
            research_topic: 研究主题
            limit: 限制处理数量，None 表示处理所有
            
        Returns:
            成功处理的数量
        """
        # 查询未评估的记录
        query_sql = """
        SELECT * FROM "references" 
        WHERE status = 0 
        ORDER BY reference_create_time DESC
        """
        
        if limit:
            query_sql += f" LIMIT {limit}"
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(query_sql)
                references = [dict(row) for row in cursor.fetchall()]
            
            if not references:
                logger.info("没有需要评估的参考文献")
                return 0
            
            logger.info(f"找到 {len(references)} 条待评估记录")
            
            # 分批处理
            batch_size = self.batch_config['batch_size']
            success_count = 0
            
            for i in range(0, len(references), batch_size):
                batch = references[i:i + batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}, 包含 {len(batch)} 条记录")
                
                # 并行处理批次中的所有记录
                tasks = [self.evaluate_reference(ref, research_topic) for ref in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 更新数据库
                for ref, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"评估失败 {ref['reference_url']}: {str(result)}")
                        continue
                    
                    # 更新记录
                    success = self.db_manager.update_reference(ref['reference_url'], result)
                    if success:
                        success_count += 1
                    else:
                        logger.error(f"更新失败: {ref['reference_url']}")
                
                # 批次间延迟，避免 API 限流
                if i + batch_size < len(references):
                    await asyncio.sleep(self.batch_config['retry_delay'])
            
            logger.info(f"批量评估完成，成功处理 {success_count}/{len(references)} 条记录")
            return success_count
            
        except Exception as e:
            logger.error(f"批量评估失败: {str(e)}")
            return 0
    
    def get_evaluation_stats(self) -> Dict[str, any]:
        """
        获取评估统计信息
        
        Returns:
            统计信息字典
        """
        stats_sql = """
        SELECT 
            COUNT(*) as total_count,
            SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as evaluated_count,
            AVG(CASE WHEN status = 1 THEN credibility ELSE NULL END) as avg_credibility,
            AVG(CASE WHEN status = 1 THEN related_assessment ELSE NULL END) as avg_relevance,
            SUM(CASE WHEN credibility = 1 THEN 1 ELSE 0 END) as low_credibility_count,
            SUM(CASE WHEN credibility = 2 THEN 1 ELSE 0 END) as medium_credibility_count,
            SUM(CASE WHEN credibility = 3 THEN 1 ELSE 0 END) as high_credibility_count
        FROM "references"
        """
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(stats_sql)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'total_references': row['total_count'],
                        'pending_evaluation': row['pending_count'],
                        'evaluated': row['evaluated_count'],
                        'average_credibility': round(row['avg_credibility'] or 0, 2),
                        'average_relevance': round(row['avg_relevance'] or 0, 2),
                        'credibility_distribution': {
                            'low': row['low_credibility_count'],
                            'medium': row['medium_credibility_count'],
                            'high': row['high_credibility_count']
                        }
                    }
                return {}
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}


# 便捷函数
async def evaluate_database_references(research_topic: str, limit: int = None) -> int:
    """
    便捷函数：评估数据库中的参考文献
    
    Args:
        research_topic: 研究主题
        limit: 限制处理数量
        
    Returns:
        成功处理的数量
    """
    evaluator = DatabaseEvaluator()
    return await evaluator.evaluate_batch(research_topic, limit)


if __name__ == "__main__":
    # 测试评估功能
    async def test_evaluator():
        evaluator = DatabaseEvaluator()
        
        # 获取统计信息
        stats = evaluator.get_evaluation_stats()
        print("📊 评估前统计信息:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # 执行评估
        research_topic = "空气制水机"
        success_count = await evaluator.evaluate_batch(research_topic, limit=5)
        
        print(f"\n✅ 评估完成，成功处理 {success_count} 条记录")
        
        # 再次获取统计信息
        stats = evaluator.get_evaluation_stats()
        print("\n📊 评估后统计信息:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 运行测试
    asyncio.run(test_evaluator())