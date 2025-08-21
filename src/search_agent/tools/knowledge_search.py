#!/usr/bin/env python3
"""
知识库搜索工具模块
提供基于FAISS向量数据库的本地知识检索功能
"""

import os
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from langchain_community.vectorstores import FAISS
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger
import json
from datetime import datetime

# 配置常量
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.3
EMBEDDING_MODEL_NAME = "BAAI/bge-base-zh-v1.5"  # 中文嵌入模型
FAISS_INDEX_PATH = "faiss_index"  # 默认索引路径

# 全局变量存储向量数据库实例
_db_instance: Optional[FAISS] = None
_embedding_model: Optional[HuggingFaceEmbeddings] = None


def initialize_knowledge_base(index_path: str = None) -> FAISS:
    """初始化或获取知识库实例
    
    Args:
        index_path: FAISS索引路径，默认使用FAISS_INDEX_PATH
        
    Returns:
        FAISS向量数据库实例
    """
    global _db_instance, _embedding_model
    
    if _db_instance is not None:
        return _db_instance
    
    try:
        # 初始化嵌入模型
        logger.info(f"初始化嵌入模型: {EMBEDDING_MODEL_NAME}")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},  # 可以改为 "cuda" 使用GPU
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # 加载FAISS索引
        index_path = index_path or FAISS_INDEX_PATH
        if not os.path.exists(index_path):
            logger.warning(f"知识库索引不存在: {index_path}")
            return None
            
        logger.info(f"加载知识库索引: {index_path}")
        _db_instance = FAISS.load_local(
            index_path, 
            _embedding_model, 
            allow_dangerous_deserialization=True
        )
        
        logger.success("知识库初始化成功")
        return _db_instance
        
    except Exception as e:
        logger.error(f"知识库初始化失败: {str(e)}")
        return None


@tool
def knowledge_search(
    query: str, 
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD
) -> List[Dict[str, Any]]:
    """Search internal knowledge base for verified and curated information.
    
    This tool searches through pre-indexed documents in the local knowledge base.
    Best for: technical documentation, verified facts, company policies, historical data.
    
    Args:
        query: Search query string
        top_k: Maximum number of results to return (default: 5)
        score_threshold: Minimum similarity score threshold (default: 0.3)
        
    Returns:
        List of knowledge base results with content, metadata, and relevance scores
    """
    try:
        # 初始化知识库
        db = initialize_knowledge_base()
        if db is None:
            logger.warning("知识库未初始化，返回空结果")
            return []
        
        # 创建检索器
        retriever = db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                'score_threshold': score_threshold,
                'k': top_k
            }
        )
        
        # 执行搜索
        logger.info(f"知识库搜索: {query}")
        docs = retriever.get_relevant_documents(query)
        
        # 格式化结果
        results = []
        for i, doc in enumerate(docs):
            # 提取元数据
            metadata = doc.metadata or {}
            
            # 构建结果
            result = {
                "title": metadata.get("title", f"知识库文档 {i+1}"),
                "url": metadata.get("source", f"kb://document/{i+1}"),
                "snippet": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "full_text": doc.page_content,
                "source_type": "knowledge_base",
                "metadata": {
                    "original_metadata": metadata,
                    "doc_id": metadata.get("doc_id", f"kb_doc_{i+1}"),
                    "created_at": metadata.get("created_at", ""),
                    "last_updated": metadata.get("last_updated", ""),
                    "category": metadata.get("category", "general"),
                    "tags": metadata.get("tags", [])
                },
                "confidence_score": 0.95,  # 知识库内容可信度高
                "timestamp": datetime.now().isoformat(),
                "verified": True  # 知识库内容默认已验证
            }
            results.append(result)
        
        logger.info(f"知识库搜索完成: 找到 {len(results)} 个相关文档")
        return results
        
    except Exception as e:
        logger.error(f"知识库搜索失败: {str(e)}")
        return []


def add_to_knowledge_base(
    content: str,
    metadata: Dict[str, Any],
    index_path: str = None
) -> bool:
    """向知识库添加新文档
    
    Args:
        content: 文档内容
        metadata: 文档元数据
        index_path: 索引保存路径
        
    Returns:
        是否添加成功
    """
    try:
        db = initialize_knowledge_base(index_path)
        if db is None:
            logger.error("无法添加文档：知识库未初始化")
            return False
        
        # 添加时间戳
        metadata["added_at"] = datetime.now().isoformat()
        
        # 创建文档并添加
        from langchain.schema import Document
        doc = Document(page_content=content, metadata=metadata)
        
        # 添加到数据库
        db.add_documents([doc])
        
        # 保存更新后的索引
        save_path = index_path or FAISS_INDEX_PATH
        db.save_local(save_path)
        
        logger.success(f"文档已添加到知识库: {metadata.get('title', 'Untitled')}")
        return True
        
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        return False


def get_knowledge_base_stats() -> Dict[str, Any]:
    """获取知识库统计信息
    
    Returns:
        包含文档数量、索引大小等统计信息的字典
    """
    try:
        db = initialize_knowledge_base()
        if db is None:
            return {"status": "not_initialized", "document_count": 0}
        
        # 获取文档数量
        doc_count = db.index.ntotal if hasattr(db, 'index') else 0
        
        # 获取索引文件大小
        index_size = 0
        if os.path.exists(FAISS_INDEX_PATH):
            for file in os.listdir(FAISS_INDEX_PATH):
                file_path = os.path.join(FAISS_INDEX_PATH, file)
                if os.path.isfile(file_path):
                    index_size += os.path.getsize(file_path)
        
        return {
            "status": "active",
            "document_count": doc_count,
            "index_size_mb": round(index_size / (1024 * 1024), 2),
            "embedding_model": EMBEDDING_MODEL_NAME,
            "index_path": FAISS_INDEX_PATH
        }
        
    except Exception as e:
        logger.error(f"获取知识库统计信息失败: {str(e)}")
        return {"status": "error", "error": str(e)}


# 用于测试的函数
if __name__ == "__main__":
    # 测试知识库搜索
    test_query = "人工智能的应用"
    results = knowledge_search.invoke({"query": test_query})
    
    if results:
        print(f"找到 {len(results)} 个结果:")
        for i, result in enumerate(results):
            print(f"\n{i+1}. {result['title']}")
            print(f"   来源: {result['url']}")
            print(f"   摘要: {result['snippet'][:100]}...")
    else:
        print("未找到相关结果")
    
    # 显示统计信息
    stats = get_knowledge_base_stats()
    print(f"\n知识库统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")