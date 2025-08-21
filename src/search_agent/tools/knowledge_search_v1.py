# 此版本已过时
# 此版本已过时
# 此版本已过时
# 此版本已过时
# 此版本已过时

"""
简化版的知识库搜索工具
用于测试，不依赖 FAISS 和 langchain_community
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.tools import tool
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 模拟的知识库数据
MOCK_KNOWLEDGE_BASE = [
    {
        "id": "kb_001",
        "title": "人工智能基础概念",
        "content": "人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。人工智能的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。",
        "category": "AI基础",
        "tags": ["人工智能", "AI", "基础概念"]
    },
    {
        "id": "kb_002", 
        "title": "机器学习入门指南",
        "content": "机器学习是人工智能的一个子集，它使计算机系统能够从数据中学习和改进，而无需明确编程。机器学习算法建立数学模型，基于训练数据进行预测或决策。主要分为监督学习、无监督学习和强化学习三大类。",
        "category": "机器学习",
        "tags": ["机器学习", "ML", "算法"]
    },
    {
        "id": "kb_003",
        "title": "深度学习技术详解", 
        "content": "深度学习是机器学习的一个分支，它基于人工神经网络进行学习。深度学习网络能够学习数据的多层表示，在计算机视觉、语音识别、自然语言处理等领域取得了突破性进展。常见的深度学习框架包括TensorFlow、PyTorch等。",
        "category": "深度学习",
        "tags": ["深度学习", "神经网络", "DL"]
    },
    {
        "id": "kb_004",
        "title": "自然语言处理技术",
        "content": "自然语言处理（NLP）是人工智能和语言学领域的分支学科，它研究如何处理和运用自然语言。NLP技术包括文本分类、命名实体识别、情感分析、机器翻译等。近年来，基于Transformer的模型如BERT、GPT等在NLP领域取得重大突破。",
        "category": "NLP",
        "tags": ["NLP", "自然语言处理", "文本分析"]
    },
    {
        "id": "kb_005",
        "title": "计算机视觉应用",
        "content": "计算机视觉是一门研究如何使机器'看'的科学，它用摄影机和计算机代替人眼对目标进行识别、跟踪和测量等。计算机视觉的典型应用包括人脸识别、物体检测、图像分割、自动驾驶等。卷积神经网络（CNN）是计算机视觉领域的核心技术。",
        "category": "计算机视觉", 
        "tags": ["计算机视觉", "CV", "图像识别"]
    }
]


def calculate_similarity(query: str, text: str) -> float:
    """简单的相似度计算（基于关键词匹配）"""
    query_lower = query.lower()
    text_lower = text.lower()
    
    # 简单的关键词匹配评分
    score = 0.0
    query_words = query_lower.split()
    
    for word in query_words:
        if word in text_lower:
            # 标题匹配权重更高
            if word in text_lower[:100]:  # 假设前100字符是标题部分
                score += 0.3
            else:
                score += 0.1
    
    # 限制最大分数为1.0
    return min(score, 1.0)


@tool
def knowledge_search_simple(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.1
) -> List[Dict[str, Any]]:
    """搜索模拟的知识库（简化版，用于测试）
    
    这是一个简化的知识库搜索工具，使用模拟数据进行测试。
    
    Args:
        query: 搜索查询字符串
        top_k: 返回的最大结果数（默认：5）
        score_threshold: 最小相似度分数阈值（默认：0.1）
        
    Returns:
        知识库搜索结果列表
    """
    try:
        logger.info(f"简化知识库搜索: query='{query}', top_k={top_k}")
        
        # 验证输入
        if not query or not isinstance(query, str):
            logger.warning("无效的查询")
            return []
        
        # 计算每个文档的相似度分数
        results = []
        for doc in MOCK_KNOWLEDGE_BASE:
            # 合并所有文本内容用于搜索
            full_text = f"{doc['title']} {doc['content']} {' '.join(doc['tags'])}"
            score = calculate_similarity(query, full_text)
            
            if score >= score_threshold:
                results.append({
                    "score": score,
                    "document": doc
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # 取前top_k个结果
        results = results[:top_k]
        
        # 格式化输出
        formatted_results = []
        for idx, result in enumerate(results):
            doc = result["document"]
            formatted_results.append({
                "title": doc["title"],
                "url": f"kb://document/{doc['id']}",
                "snippet": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                "full_text": doc["content"],
                "source_type": "knowledge_base",
                "metadata": {
                    "doc_id": doc["id"],
                    "category": doc["category"],
                    "tags": doc["tags"],
                    "relevance_score": result["score"]
                },
                "confidence_score": 0.95,  # 知识库内容可信度高
                "timestamp": datetime.now().isoformat(),
                "verified": True
            })
        
        logger.info(f"简化知识库搜索完成: 找到 {len(formatted_results)} 个结果")
        return formatted_results
        
    except Exception as e:
        logger.error(f"简化知识库搜索失败: {str(e)}")
        return []


# 用于测试
if __name__ == "__main__":
    # 测试搜索功能
    test_queries = ["人工智能", "深度学习", "NLP", "图像识别"]
    
    for query in test_queries:
        print(f"\n搜索: {query}")
        results = knowledge_search_simple(query)
        
        if results:
            for i, result in enumerate(results):
                print(f"\n结果 {i+1}:")
                print(f"  标题: {result['title']}")
                print(f"  相关度: {result['metadata']['relevance_score']:.2f}")
                print(f"  摘要: {result['snippet'][:100]}...")
        else:
            print("  没有找到结果")