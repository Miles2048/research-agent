"""
数据库迁移脚本
用于升级 references 表结构，添加新字段
"""

import sqlite3
import logging
from typing import List, Tuple
from datetime import datetime
import math

logger = logging.getLogger(__name__)


def calculate_word_count(content: str, related_content: str) -> int:
    """
    计算总字数
    
    Args:
        content: 主要内容
        related_content: 相关内容
        
    Returns:
        int: 总字数
    """
    total_text = (content or "") + (related_content or "")
    # 简单计算：按空格分词，同时考虑中文字符
    # 中文每个字符算一个字，英文按空格分词
    chinese_chars = len([c for c in total_text if '\u4e00' <= c <= '\u9fff'])
    english_words = len(total_text.split())
    return max(chinese_chars, english_words)


def migrate_database(db_path: str = "research_data.db") -> bool:
    """
    执行数据库迁移，添加新字段
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        bool: 迁移成功返回 True，失败返回 False
    """
    try:
        logger.info(f"开始数据库迁移: {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取当前表结构
        cursor.execute("PRAGMA table_info(references)")
        existing_columns = {column[1] for column in cursor.fetchall()}
        logger.info(f"现有字段: {existing_columns}")
        
        # 2. 定义需要添加的新字段
        new_columns = [
            ("publisher", "TEXT"),
            ("collection_time", "DATETIME"),
            ("credibility", "INTEGER DEFAULT 2"),
            ("related_assessment", "REAL DEFAULT 0.80"),
            ("word_count", "INTEGER DEFAULT 0"),
            ("reading_time", "TEXT DEFAULT '0min0sec'"),
            ("file_path", "TEXT NOT NULL DEFAULT 'root'"),
            ("file_size", "TEXT DEFAULT '0kb'"),
            ("status", "INTEGER DEFAULT 0"),
            ("credibility_assessment", "TEXT"),
            ("related_assessment_text", "TEXT")
        ]
        
        # 3. 添加新字段
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    alter_sql = f'ALTER TABLE "references" ADD COLUMN {column_name} {column_def}'
                    cursor.execute(alter_sql)
                    logger.info(f"成功添加字段: {column_name}")
                except sqlite3.Error as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.error(f"添加字段 {column_name} 失败: {str(e)}")
                        raise
            else:
                logger.info(f"字段已存在，跳过: {column_name}")
        
        # 4. 创建新索引
        new_indexes = [
            ("idx_credibility", "credibility"),
            ("idx_publisher", "publisher"),
            ("idx_file_path", "file_path"),
            ("idx_collection_time", "collection_time"),
            ("idx_status", "status")
        ]
        
        for index_name, column_name in new_indexes:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON "references"({column_name})')
                logger.info(f"创建索引: {index_name}")
            except sqlite3.Error as e:
                logger.warning(f"创建索引 {index_name} 失败（可能已存在）: {str(e)}")
        
        # 5. 提交更改
        conn.commit()
        logger.info("数据库结构迁移完成")
        
        # 6. 更新现有数据的默认值
        logger.info("开始更新现有数据...")
        update_existing_data(conn)
        
        conn.close()
        logger.info("数据库迁移成功完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def update_existing_data(conn: sqlite3.Connection) -> None:
    """
    为现有数据更新新字段的值
    
    Args:
        conn: 数据库连接
    """
    cursor = conn.cursor()
    
    try:
        # 获取所有现有记录
        cursor.execute("SELECT id, reference_content, reference_related_content, reference_create_time FROM references")
        rows = cursor.fetchall()
        
        logger.info(f"需要更新 {len(rows)} 条记录")
        
        for row in rows:
            record_id = row['id']
            content = row['reference_content'] or ""
            related_content = row['reference_related_content'] or ""
            create_time = row['reference_create_time']
            
            # 计算字段值
            word_count = calculate_word_count(content, related_content)
            reading_time = math.ceil(word_count / 200) if word_count > 0 else 0
            file_size = len((content + related_content).encode('utf-8'))
            
            # 更新记录
            update_sql = """
            UPDATE "references" 
            SET collection_time = ?,
                word_count = ?,
                reading_time = ?,
                file_size = ?
            WHERE id = ?
            """
            
            cursor.execute(update_sql, (
                create_time,  # collection_time = create_time
                word_count,
                reading_time,
                file_size,
                record_id
            ))
        
        conn.commit()
        logger.info(f"成功更新 {len(rows)} 条记录的默认值")
        
    except Exception as e:
        logger.error(f"更新现有数据失败: {str(e)}")
        conn.rollback()
        raise


def verify_migration(db_path: str = "research_data.db") -> bool:
    """
    验证迁移是否成功
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        bool: 验证通过返回 True
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查所有必需字段是否存在
        cursor.execute("PRAGMA table_info(references)")
        columns = {column[1] for column in cursor.fetchall()}
        
        required_columns = {
            'publisher', 'collection_time', 'credibility', 
            'related_assessment', 'word_count', 'reading_time',
            'file_path', 'file_size', 'status'
        }
        
        missing = required_columns - columns
        if missing:
            logger.error(f"缺少字段: {missing}")
            return False
        
        # 检查默认值是否正确
        cursor.execute("SELECT credibility, related_assessment, file_path FROM references LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            if row[0] != 2:  # credibility
                logger.warning("credibility 默认值不是 2")
            if abs(row[1] - 0.80) > 0.001:  # related_assessment
                logger.warning("related_assessment 默认值不是 0.80")
            if row[2] != 'root':  # file_path
                logger.warning("file_path 默认值不是 'root'")
        
        conn.close()
        logger.info("数据库迁移验证通过")
        return True
        
    except Exception as e:
        logger.error(f"迁移验证失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 执行迁移
    if migrate_database():
        print("✅ 数据库迁移成功")
        
        # 验证迁移
        if verify_migration():
            print("✅ 迁移验证通过")
        else:
            print("❌ 迁移验证失败")
    else:
        print("❌ 数据库迁移失败")