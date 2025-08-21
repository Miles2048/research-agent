"""
数据库查询示例
展示如何查询和使用新增的字段
"""

from database import DatabaseManager
import json


def query_references_with_new_fields(db_manager: DatabaseManager):
    """
    查询包含新字段的参考文献记录
    
    Args:
        db_manager: 数据库管理器实例
    """
    # 自定义查询SQL，包含所有新字段
    query_sql = """
    SELECT 
        id,
        reference_title as name,
        reference_url as url,
        reference_type,
        publisher,
        collection_time,
        credibility,
        related_assessment,
        word_count,
        reading_time,
        file_path,
        file_size,
        status,
        reference_create_time as created_at
    FROM "references"
    WHERE status = 0  -- 只查询状态为0的记录
    ORDER BY reference_create_time DESC
    LIMIT 10
    """
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.execute(query_sql)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(row)
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"查询失败: {str(e)}")
        return []


def update_reference_with_llm_data(db_manager: DatabaseManager, url: str, llm_data: dict):
    """
    使用LLM生成的数据更新参考文献记录
    
    Args:
        db_manager: 数据库管理器实例
        url: 参考文献URL
        llm_data: LLM生成的数据，包含：
            - publisher: 发布机构
            - credibility: 可信度（1/2/3）
            - related_assessment: 相关性评分（0.00-1.00）
            - credibility_assessment: 可信度评估文本
            - related_assessment_text: 相关性评估文本
    
    Returns:
        bool: 更新成功返回True
    """
    update_data = {
        'publisher': llm_data.get('publisher'),
        'credibility': llm_data.get('credibility', 2),
        'related_assessment': llm_data.get('related_assessment', 0.80),
        'credibility_assessment': llm_data.get('credibility_assessment'),
        'related_assessment_text': llm_data.get('related_assessment_text'),
        'status': 1  # 更新后将状态改为1，表示已处理
    }
    
    # 过滤掉None值
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    return db_manager.update_reference(url, update_data)


def get_references_by_credibility(db_manager: DatabaseManager, credibility: int):
    """
    根据可信度查询参考文献
    
    Args:
        db_manager: 数据库管理器实例
        credibility: 可信度等级（1/2/3）
    
    Returns:
        List[Dict]: 符合条件的记录列表
    """
    query_sql = """
    SELECT * FROM "references"
    WHERE credibility = ?
    ORDER BY related_assessment DESC
    """
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.execute(query_sql, (credibility,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        print(f"查询失败: {str(e)}")
        return []


def get_reading_statistics(db_manager: DatabaseManager):
    """
    获取阅读统计信息
    
    Args:
        db_manager: 数据库管理器实例
    
    Returns:
        Dict: 统计信息
    """
    stats_sql = """
    SELECT 
        COUNT(*) as total_count,
        SUM(word_count) as total_words,
        SUM(reading_time) as total_reading_time,
        AVG(word_count) as avg_word_count,
        AVG(reading_time) as avg_reading_time,
        AVG(related_assessment) as avg_related_assessment
    FROM "references"
    WHERE status != 0  -- 排除未处理的记录
    """
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.execute(stats_sql)
            row = cursor.fetchone()
            
            if row:
                return {
                    'total_references': row['total_count'],
                    'total_words': row['total_words'] or 0,
                    'total_reading_time_minutes': row['total_reading_time'] or 0,
                    'avg_word_count': round(row['avg_word_count'] or 0, 2),
                    'avg_reading_time_minutes': round(row['avg_reading_time'] or 0, 2),
                    'avg_related_assessment': round(row['avg_related_assessment'] or 0, 2)
                }
            return {}
            
    except Exception as e:
        print(f"统计查询失败: {str(e)}")
        return {}


if __name__ == "__main__":
    # 使用示例
    db = DatabaseManager()
    
    # 1. 查询包含新字段的记录
    print("📋 查询最新的10条记录：")
    records = query_references_with_new_fields(db)
    for record in records[:3]:  # 只显示前3条
        print(f"\n标题: {record['name']}")
        print(f"URL: {record['url']}")
        print(f"发布机构: {record['publisher'] or '未知'}")
        print(f"可信度: {record['credibility']}")
        print(f"相关性: {record['related_assessment']}")
        print(f"字数: {record['word_count']}")
        print(f"阅读时间: {record['reading_time']}")
        print(f"状态: {record['status']}")
    
    # 2. 模拟LLM更新数据
    if records:
        print("\n\n🤖 模拟LLM更新数据...")
        llm_data = {
            'publisher': 'Example Publisher',
            'credibility': 3,
            'related_assessment': 0.95,
            'credibility_assessment': '该文献来自知名出版机构，内容经过严格的同行评审，数据来源可靠，引用充分，可信度较高。',
            'related_assessment_text': '该文献与研究主题高度相关，涵盖了核心概念，提供了重要的理论支撑和实证数据。'
        }
        success = update_reference_with_llm_data(db, records[0]['url'], llm_data)
        print(f"更新{'成功' if success else '失败'}")
    
    # 3. 获取统计信息
    print("\n\n📊 阅读统计信息：")
    stats = get_reading_statistics(db)
    print(json.dumps(stats, indent=2, ensure_ascii=False))