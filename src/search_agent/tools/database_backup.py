"""
数据库工具模块
提供数据源持久化的数据库操作功能
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import os
import re
from urllib.parse import urlparse
import time
import math

logger = logging.getLogger(__name__)

# 创建专门的数据库操作日志记录器
db_logger = logging.getLogger(f"{__name__}.database_operations")
db_connection_logger = logging.getLogger(f"{__name__}.connection")
db_performance_logger = logging.getLogger(f"{__name__}.performance")


def format_reading_time(seconds: int) -> str:
    """
    将秒数格式化为 xminysec 格式
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化的时间字符串，如 "1min16sec"
    """
    if seconds < 0:
        return "0min0sec"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    return f"{minutes}min{remaining_seconds}sec"


def format_file_size(bytes_size: int) -> str:
    """
    将字节数格式化为 xkb 格式
    
    Args:
        bytes_size: 字节数
        
    Returns:
        str: 格式化的文件大小字符串，如 "256kb"
    """
    if bytes_size < 0:
        return "0kb"
    
    kb = math.ceil(bytes_size / 1024)  # 向上取整
    
    return f"{kb}kb"


class DatabaseManager:
    """数据库管理器类，负责数据源的持久化操作"""
    
    def __init__(self, db_path: str = "research_data.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，默认为 research_data.db
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._connection_count = 0
        self._operation_stats = {
            'connections': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'records_deleted': 0,
            'records_queried': 0
        }
        
        # 记录数据库管理器初始化
        db_logger.info(f"数据库管理器初始化完成 - 数据库路径: {self.db_path}")
        
        # 测试初始连接
        if self.test_connection():
            db_connection_logger.info("数据库初始连接测试成功")
        else:
            db_connection_logger.error("数据库初始连接测试失败")
        
    def _ensure_db_directory(self):
        """确保数据库文件目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        Yields:
            sqlite3.Connection: 数据库连接对象
        """
        conn = None
        connection_start_time = time.time()
        connection_id = self._connection_count + 1
        
        try:
            db_connection_logger.debug(f"[连接-{connection_id}] 尝试建立数据库连接")
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
            
            self._connection_count += 1
            self._operation_stats['connections'] += 1
            
            connection_time = time.time() - connection_start_time
            db_connection_logger.info(f"[连接-{connection_id}] 数据库连接建立成功 - 耗时: {connection_time:.3f}s")
            db_performance_logger.debug(f"连接建立耗时: {connection_time:.3f}s")
            
            yield conn
            
        except sqlite3.Error as e:
            self._operation_stats['failed_operations'] += 1
            db_connection_logger.error(f"[连接-{connection_id}] 数据库连接错误: {str(e)}")
            logger.error(f"数据库连接错误: {str(e)}")
            if conn:
                try:
                    conn.rollback()
                    db_connection_logger.debug(f"[连接-{connection_id}] 事务回滚成功")
                except Exception as rollback_error:
                    db_connection_logger.error(f"[连接-{connection_id}] 事务回滚失败: {str(rollback_error)}")
            raise
        except Exception as e:
            self._operation_stats['failed_operations'] += 1
            db_connection_logger.error(f"[连接-{connection_id}] 数据库连接发生未知错误: {str(e)}")
            logger.error(f"数据库连接发生未知错误: {str(e)}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                    close_time = time.time() - connection_start_time
                    db_connection_logger.debug(f"[连接-{connection_id}] 数据库连接关闭 - 总耗时: {close_time:.3f}s")
                except Exception as close_error:
                    db_connection_logger.error(f"[连接-{connection_id}] 关闭数据库连接时发生错误: {str(close_error)}")
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            bool: 连接成功返回 True，失败返回 False
        """
        test_start_time = time.time()
        try:
            db_connection_logger.info("开始数据库连接测试")
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                test_time = time.time() - test_start_time
                db_connection_logger.info(f"数据库连接测试成功 - 耗时: {test_time:.3f}s")
                db_performance_logger.debug(f"连接测试耗时: {test_time:.3f}s")
                return True
        except Exception as e:
            test_time = time.time() - test_start_time
            db_connection_logger.error(f"数据库连接测试失败 - 耗时: {test_time:.3f}s - 错误: {str(e)}")
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False 
   
    def create_tables(self) -> bool:
        """
        创建数据库表
        
        Returns:
            bool: 创建成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        db_logger.info("[表创建] 开始创建数据库表和索引")
        
        create_references_table_sql = """
        CREATE TABLE IF NOT EXISTS "references" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_type TEXT NOT NULL DEFAULT '未分类',
            reference_url TEXT NOT NULL,
            reference_content TEXT,
            reference_create_time DATETIME NOT NULL,
            reference_update_time DATETIME NOT NULL,
            reference_version INTEGER NOT NULL DEFAULT 1,
            reference_title TEXT NOT NULL,
            reference_related_content TEXT,
            verified BOOLEAN NOT NULL DEFAULT 0,
            publisher TEXT,
            collection_time DATETIME,
            credibility INTEGER DEFAULT 2,
            related_assessment REAL DEFAULT 0.80,
            word_count INTEGER DEFAULT 0,
            reading_time TEXT DEFAULT '0min0sec',
            file_path TEXT NOT NULL DEFAULT 'root',
            file_size TEXT DEFAULT '0kb',
            status INTEGER DEFAULT 0,
            credibility_assessment TEXT,
            related_assessment_text TEXT,
            artifact_id INTEGER DEFAULT 1,
            UNIQUE(reference_url)
        )
        """
        
        # 创建索引的 SQL 语句
        create_indexes_sql = [
            'CREATE INDEX IF NOT EXISTS idx_reference_url ON "references"(reference_url);',
            'CREATE INDEX IF NOT EXISTS idx_reference_title ON "references"(reference_title);',
            'CREATE INDEX IF NOT EXISTS idx_reference_create_time ON "references"(reference_create_time);',
            'CREATE INDEX IF NOT EXISTS idx_verified ON "references"(verified);',
            'CREATE INDEX IF NOT EXISTS idx_credibility ON "references"(credibility);',
            'CREATE INDEX IF NOT EXISTS idx_publisher ON "references"(publisher);',
            'CREATE INDEX IF NOT EXISTS idx_file_path ON "references"(file_path);',
            'CREATE INDEX IF NOT EXISTS idx_collection_time ON "references"(collection_time);',
            'CREATE INDEX IF NOT EXISTS idx_status ON "references"(status);',
            'CREATE INDEX IF NOT EXISTS idx_artifact_id ON "references"(artifact_id);'
        ]
        
        try:
            with self.get_connection() as conn:
                # 创建表
                db_logger.debug("[表创建] 执行创建 references 表的 SQL")
                conn.execute(create_references_table_sql)
                db_logger.info("[表创建] 数据表 references 创建成功或已存在")
                logger.info("数据表 references 创建成功或已存在")
                
                # 创建索引
                db_logger.debug(f"[表创建] 开始创建 {len(create_indexes_sql)} 个索引")
                for i, index_sql in enumerate(create_indexes_sql, 1):
                    conn.execute(index_sql)
                    db_logger.debug(f"[表创建] 索引 {i}/{len(create_indexes_sql)} 创建完成")
                
                conn.commit()
                operation_time = time.time() - operation_start_time
                
                self._operation_stats['successful_operations'] += 1
                db_logger.info(f"[表创建] 数据库表和索引创建完成 - 耗时: {operation_time:.3f}s")
                db_performance_logger.info(f"表创建操作耗时: {operation_time:.3f}s")
                logger.info("数据库索引创建完成")
                return True
                
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[表创建] 创建数据表失败 - 耗时: {operation_time:.3f}s - 错误: {str(e)}")
            logger.error(f"创建数据表失败: {str(e)}")
            return False
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[表创建] 创建数据表时发生未知错误 - 耗时: {operation_time:.3f}s - 错误: {str(e)}")
            logger.error(f"创建数据表时发生未知错误: {str(e)}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 表存在返回 True，不存在返回 False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查表存在性时发生错误: {str(e)}")
            return False
    
    def insert_reference(self, reference_data: Dict[str, Any]) -> bool:
        """
        插入单条数据源记录
        
        Args:
            reference_data: 数据源记录字典，包含所有必要字段
            
        Returns:
            bool: 插入成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        url = reference_data.get('reference_url', 'Unknown')
        
        db_logger.debug(f"[单条插入] 开始插入记录: {url}")
        
        insert_sql = """
        INSERT OR REPLACE INTO "references" (
            reference_type, reference_url, reference_content,
            reference_create_time, reference_update_time, reference_version,
            reference_title, reference_related_content, verified,
            publisher, collection_time, credibility, related_assessment,
            word_count, reading_time, file_path, file_size, status,
            credibility_assessment, related_assessment_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            # 设置默认值和当前时间
            current_time = datetime.now().isoformat()
            
            # 计算字数和阅读时间
            content = reference_data.get('reference_content', '')
            related_content = reference_data.get('reference_related_content', '')
            word_count = reference_data.get('word_count', len(content) + len(related_content))
            
            # 计算阅读时间（秒）并格式化
            reading_seconds = max(1, math.ceil(word_count / 200 * 60))  # 200字/分钟
            reading_time_str = reference_data.get('reading_time', format_reading_time(reading_seconds))
            
            # 计算文件大小并格式化
            bytes_size = len((content + related_content).encode('utf-8'))
            file_size_str = reference_data.get('file_size', format_file_size(bytes_size))
            
            values = (
                reference_data.get('reference_type', '未分类'),
                reference_data['reference_url'],  # 必需字段
                reference_data.get('reference_content', ''),
                reference_data.get('reference_create_time', current_time),
                current_time,  # 总是更新 update_time
                reference_data.get('reference_version', 1),
                reference_data['reference_title'],  # 必需字段
                reference_data.get('reference_related_content', ''),
                reference_data.get('verified', False),
                reference_data.get('publisher', None),  # 新字段
                reference_data.get('collection_time', current_time),  # 等于 create_time
                reference_data.get('credibility', 2),  # 默认中等可信度
                reference_data.get('related_assessment', 0.80),  # 默认相关性评分
                word_count,  # 计算的字数
                reading_time_str,  # 格式化的阅读时间
                reference_data.get('file_path', 'root'),  # 默认文件路径
                file_size_str,  # 格式化的文件大小
                reference_data.get('status', 0),  # 默认状态为0
                reference_data.get('credibility_assessment', None),  # 可信度评估文本
                reference_data.get('related_assessment_text', None)  # 相关性评估文本
            )
            
            with self.get_connection() as conn:
                conn.execute(insert_sql, values)
                conn.commit()
                
                operation_time = time.time() - operation_start_time
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_inserted'] += 1
                
                db_logger.info(f"[单条插入] 成功插入记录: {url} - 耗时: {operation_time:.3f}s")
                db_performance_logger.debug(f"单条插入耗时: {operation_time:.3f}s")
                logger.info(f"成功插入数据源记录: {reference_data['reference_url']}")
                return True
                
        except KeyError as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[单条插入] 缺少必需字段: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"缺少必需字段: {str(e)}")
            return False
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[单条插入] 数据库错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"插入数据源记录失败: {str(e)}")
            return False
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[单条插入] 未知错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"插入数据源记录时发生未知错误: {str(e)}")
            return False
    
    def insert_references_batch(self, references_list: List[Dict[str, Any]]) -> int:
        """
        批量插入数据源记录
        
        Args:
            references_list: 数据源记录列表
            
        Returns:
            int: 成功插入的记录数量
        """
        operation_start_time = time.time()
        
        if not references_list:
            db_logger.warning("[批量插入] 数据列表为空，跳过操作")
            logger.warning("批量插入的数据列表为空")
            return 0
        
        db_logger.info(f"[批量插入] 开始批量插入 {len(references_list)} 条记录")
            
        insert_sql = """
        INSERT OR REPLACE INTO "references" (
            reference_type, reference_url, reference_content,
            reference_create_time, reference_update_time, reference_version,
            reference_title, reference_related_content, verified,
            publisher, collection_time, credibility, related_assessment,
            word_count, reading_time, file_path, file_size, status,
            credibility_assessment, related_assessment_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        successful_count = 0
        failed_count = 0
        skipped_count = 0
        current_time = datetime.now().isoformat()
        
        try:
            with self.get_connection() as conn:
                # 使用事务确保数据一致性
                db_logger.debug("[批量插入] 开始事务")
                conn.execute("BEGIN TRANSACTION")
                
                for i, reference_data in enumerate(references_list, 1):
                    try:
                        # 验证必需字段
                        if 'reference_url' not in reference_data or 'reference_title' not in reference_data:
                            skipped_count += 1
                            url = reference_data.get('reference_url', 'Unknown')
                            db_logger.warning(f"[批量插入] 跳过记录 {i}/{len(references_list)} - 缺少必需字段: {url}")
                            logger.warning(f"跳过缺少必需字段的记录: {reference_data}")
                            continue
                            
                        # 计算字数和阅读时间
                        content = reference_data.get('reference_content', '')
                        related_content = reference_data.get('reference_related_content', '')
                        word_count = reference_data.get('word_count', len(content) + len(related_content))
                        
                        # 计算阅读时间（秒）并格式化
                        reading_seconds = max(1, math.ceil(word_count / 200 * 60))  # 200字/分钟
                        reading_time_str = reference_data.get('reading_time', format_reading_time(reading_seconds))
                        
                        # 计算文件大小并格式化
                        bytes_size = len((content + related_content).encode('utf-8'))
                        file_size_str = reference_data.get('file_size', format_file_size(bytes_size))
                        
                        values = (
                            reference_data.get('reference_type', '未分类'),
                            reference_data['reference_url'],
                            reference_data.get('reference_content', ''),
                            reference_data.get('reference_create_time', current_time),
                            current_time,  # 总是更新 update_time
                            reference_data.get('reference_version', 1),
                            reference_data['reference_title'],
                            reference_data.get('reference_related_content', ''),
                            reference_data.get('verified', False),
                            reference_data.get('publisher', None),  # 新字段
                            reference_data.get('collection_time', current_time),  # 等于 create_time
                            reference_data.get('credibility', 2),  # 默认中等可信度
                            reference_data.get('related_assessment', 0.80),  # 默认相关性评分
                            word_count,  # 计算的字数
                            reading_time_str,  # 格式化的阅读时间
                            reference_data.get('file_path', 'root'),  # 默认文件路径
                            file_size_str,  # 格式化的文件大小
                            reference_data.get('status', 0),  # 默认状态为0
                            reference_data.get('credibility_assessment', None),  # 可信度评估文本
                            reference_data.get('related_assessment_text', None)  # 相关性评估文本
                        )
                        
                        conn.execute(insert_sql, values)
                        successful_count += 1
                        
                        if i % 10 == 0:  # 每10条记录记录一次进度
                            db_logger.debug(f"[批量插入] 进度: {i}/{len(references_list)} - 成功: {successful_count}")
                        
                    except Exception as e:
                        failed_count += 1
                        url = reference_data.get('reference_url', 'Unknown')
                        db_logger.error(f"[批量插入] 记录 {i}/{len(references_list)} 插入失败: {str(e)} - URL: {url}")
                        logger.error(f"插入单条记录失败: {str(e)}, 数据: {reference_data}")
                        continue
                
                conn.commit()
                operation_time = time.time() - operation_start_time
                
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_inserted'] += successful_count
                
                db_logger.info(f"[批量插入] 事务提交成功 - 总计: {len(references_list)}, 成功: {successful_count}, 失败: {failed_count}, 跳过: {skipped_count} - 耗时: {operation_time:.3f}s")
                db_performance_logger.info(f"批量插入操作耗时: {operation_time:.3f}s - 记录数: {len(references_list)} - 平均: {operation_time/len(references_list):.4f}s/条")
                logger.info(f"批量插入完成: 成功 {successful_count} 条，总计 {len(references_list)} 条")
                
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[批量插入] 事务失败: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"批量插入事务失败: {str(e)}")
            try:
                conn.rollback()
                db_logger.debug("[批量插入] 事务回滚成功")
            except Exception as rollback_error:
                db_logger.error(f"[批量插入] 事务回滚失败: {str(rollback_error)}")
            return 0
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[批量插入] 未知错误: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"批量插入时发生未知错误: {str(e)}")
            try:
                conn.rollback()
                db_logger.debug("[批量插入] 事务回滚成功")
            except Exception as rollback_error:
                db_logger.error(f"[批量插入] 事务回滚失败: {str(rollback_error)}")
            return 0
            
        return successful_count
    
    def get_reference_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        根据URL查询数据源记录
        
        Args:
            url: 数据源URL
            
        Returns:
            Optional[Dict[str, Any]]: 找到的记录字典，未找到返回 None
        """
        operation_start_time = time.time()
        db_logger.debug(f"[URL查询] 开始查询记录: {url}")
        
        select_sql = """
        SELECT * FROM "references" WHERE reference_url = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, (url,))
                row = cursor.fetchone()
                
                operation_time = time.time() - operation_start_time
                self._operation_stats['records_queried'] += 1
                
                if row:
                    # 将 sqlite3.Row 转换为字典
                    result = dict(row)
                    self._operation_stats['successful_operations'] += 1
                    db_logger.info(f"[URL查询] 找到记录: {url} - 耗时: {operation_time:.3f}s")
                    db_performance_logger.debug(f"URL查询耗时: {operation_time:.3f}s")
                    logger.debug(f"找到URL对应的记录: {url}")
                    return result
                else:
                    self._operation_stats['successful_operations'] += 1
                    db_logger.debug(f"[URL查询] 未找到记录: {url} - 耗时: {operation_time:.3f}s")
                    logger.debug(f"未找到URL对应的记录: {url}")
                    return None
                    
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[URL查询] 数据库错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"根据URL查询记录失败: {str(e)}")
            return None
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[URL查询] 未知错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"根据URL查询记录时发生未知错误: {str(e)}")
            return None
    
    def get_references_by_title(self, title: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        根据标题查询数据源记录
        
        Args:
            title: 数据源标题
            exact_match: 是否精确匹配，False 时使用模糊匹配
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        if exact_match:
            select_sql = """
            SELECT * FROM "references" WHERE reference_title = ?
            ORDER BY reference_create_time DESC
            """
            params = (title,)
        else:
            select_sql = """
            SELECT * FROM "references" WHERE reference_title LIKE ?
            ORDER BY reference_create_time DESC
            """
            params = (f"%{title}%",)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, params)
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                logger.debug(f"根据标题找到 {len(results)} 条记录: {title}")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"根据标题查询记录失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"根据标题查询记录时发生未知错误: {str(e)}")
            return []
    
    def get_references_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        根据日期范围查询数据源记录
        
        Args:
            start_date: 开始日期 (ISO格式字符串)
            end_date: 结束日期 (ISO格式字符串)
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        select_sql = """
        SELECT * FROM "references" 
        WHERE reference_create_time >= ? AND reference_create_time <= ?
        ORDER BY reference_create_time DESC
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, (start_date, end_date))
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                logger.debug(f"根据日期范围找到 {len(results)} 条记录: {start_date} 到 {end_date}")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"根据日期范围查询记录失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"根据日期范围查询记录时发生未知错误: {str(e)}")
            return []
    
    def get_all_references(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有数据源记录
        
        Args:
            limit: 限制返回记录数量，None 表示不限制
            offset: 偏移量，用于分页
            
        Returns:
            List[Dict[str, Any]]: 记录列表
        """
        if limit is not None:
            select_sql = """
            SELECT * FROM "references" 
            ORDER BY reference_create_time DESC
            LIMIT ? OFFSET ?
            """
            params = (limit, offset)
        else:
            select_sql = """
            SELECT * FROM "references" 
            ORDER BY reference_create_time DESC
            """
            params = ()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, params)
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                logger.debug(f"获取到 {len(results)} 条记录")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"获取所有记录失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取所有记录时发生未知错误: {str(e)}")
            return []
    
    def update_reference_verification(self, url: str, verified: bool) -> bool:
        """
        更新数据源的验证状态
        
        Args:
            url: 数据源URL
            verified: 验证状态
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        db_logger.debug(f"[验证更新] 开始更新验证状态: {url} -> {verified}")
        
        update_sql = """
        UPDATE "references" 
        SET verified = ?, reference_update_time = ?
        WHERE reference_url = ?
        """
        
        try:
            current_time = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.execute(update_sql, (verified, current_time, url))
                conn.commit()
                
                operation_time = time.time() - operation_start_time
                
                if cursor.rowcount > 0:
                    self._operation_stats['successful_operations'] += 1
                    self._operation_stats['records_updated'] += 1
                    db_logger.info(f"[验证更新] 成功更新验证状态: {url} -> {verified} - 耗时: {operation_time:.3f}s")
                    db_performance_logger.debug(f"验证状态更新耗时: {operation_time:.3f}s")
                    logger.info(f"成功更新验证状态: {url} -> {verified}")
                    return True
                else:
                    self._operation_stats['successful_operations'] += 1  # 操作成功但无记录更新
                    db_logger.warning(f"[验证更新] 未找到要更新的记录: {url} - 耗时: {operation_time:.3f}s")
                    logger.warning(f"未找到要更新的记录: {url}")
                    return False
                    
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[验证更新] 数据库错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新验证状态失败: {str(e)}")
            return False
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[验证更新] 未知错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新验证状态时发生未知错误: {str(e)}")
            return False
    
    def update_reference_content(self, url: str, related_content: str) -> bool:
        """
        更新数据源的相关内容
        
        Args:
            url: 数据源URL
            related_content: 相关内容
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        update_sql = """
        UPDATE "references" 
        SET reference_related_content = ?, reference_update_time = ?
        WHERE reference_url = ?
        """
        
        try:
            current_time = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.execute(update_sql, (related_content, current_time, url))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"成功更新相关内容: {url}")
                    return True
                else:
                    logger.warning(f"未找到要更新的记录: {url}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"更新相关内容失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"更新相关内容时发生未知错误: {str(e)}")
            return False
    
    def update_reference(self, url: str, update_data: Dict[str, Any]) -> bool:
        """
        更新数据源记录的多个字段
        
        Args:
            url: 数据源URL
            update_data: 要更新的字段字典
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        if not update_data:
            logger.warning("更新数据为空")
            return False
            
        # 构建动态更新SQL
        allowed_fields = {
            'reference_type', 'reference_content', 'reference_version',
            'reference_title', 'reference_related_content', 'verified',
            'publisher', 'credibility', 'related_assessment',
            'word_count', 'reading_time', 'file_path', 'file_size', 'status',
            'credibility_assessment', 'related_assessment_text'
        }
        
        # 过滤允许更新的字段
        valid_updates = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not valid_updates:
            logger.warning("没有有效的更新字段")
            return False
        
        # 总是更新 update_time
        valid_updates['reference_update_time'] = datetime.now().isoformat()
        
        # 构建SQL语句
        set_clause = ", ".join([f"{field} = ?" for field in valid_updates.keys()])
        update_sql = f'UPDATE "references" SET {set_clause} WHERE reference_url = ?'
        
        # 构建参数列表
        params = list(valid_updates.values()) + [url]
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(update_sql, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"成功更新记录: {url}, 字段: {list(valid_updates.keys())}")
                    return True
                else:
                    logger.warning(f"未找到要更新的记录: {url}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"更新记录失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"更新记录时发生未知错误: {str(e)}")
            return False
    
    def delete_reference_by_url(self, url: str, soft_delete: bool = False) -> bool:
        """
        根据URL删除数据源记录
        
        Args:
            url: 数据源URL
            soft_delete: 是否软删除（标记为已删除而不是物理删除）
            
        Returns:
            bool: 删除成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        delete_type = "软删除" if soft_delete else "硬删除"
        db_logger.debug(f"[{delete_type}] 开始删除记录: {url}")
        
        if soft_delete:
            # 软删除：添加删除标记字段
            # 首先检查是否存在 deleted 字段，如果不存在则添加
            try:
                with self.get_connection() as conn:
                    # 检查 deleted 字段是否存在
                    cursor = conn.execute("PRAGMA table_info(references)")
                    columns = [column[1] for column in cursor.fetchall()]
                    
                    if 'deleted' not in columns:
                        # 添加 deleted 字段
                        db_logger.debug(f"[{delete_type}] 添加 deleted 字段")
                        conn.execute('ALTER TABLE "references" ADD COLUMN deleted BOOLEAN DEFAULT 0')
                        conn.commit()
                        db_logger.info(f"[{delete_type}] 添加了 deleted 字段用于软删除")
                        logger.info("添加了 deleted 字段用于软删除")
                    
                    # 执行软删除
                    update_sql = """
                    UPDATE "references" 
                    SET deleted = 1, reference_update_time = ?
                    WHERE reference_url = ? AND (deleted = 0 OR deleted IS NULL)
                    """
                    current_time = datetime.now().isoformat()
                    cursor = conn.execute(update_sql, (current_time, url))
                    conn.commit()
                    
                    operation_time = time.time() - operation_start_time
                    
                    if cursor.rowcount > 0:
                        self._operation_stats['successful_operations'] += 1
                        self._operation_stats['records_deleted'] += 1
                        db_logger.info(f"[{delete_type}] 成功删除记录: {url} - 耗时: {operation_time:.3f}s")
                        db_performance_logger.debug(f"软删除操作耗时: {operation_time:.3f}s")
                        logger.info(f"成功软删除记录: {url}")
                        return True
                    else:
                        self._operation_stats['successful_operations'] += 1  # 操作成功但无记录删除
                        db_logger.warning(f"[{delete_type}] 未找到要删除的记录或记录已被删除: {url} - 耗时: {operation_time:.3f}s")
                        logger.warning(f"未找到要删除的记录或记录已被删除: {url}")
                        return False
                        
            except sqlite3.Error as e:
                operation_time = time.time() - operation_start_time
                self._operation_stats['failed_operations'] += 1
                db_logger.error(f"[{delete_type}] 数据库错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
                logger.error(f"软删除记录失败: {str(e)}")
                return False
            except Exception as e:
                operation_time = time.time() - operation_start_time
                self._operation_stats['failed_operations'] += 1
                db_logger.error(f"[{delete_type}] 未知错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
                logger.error(f"软删除记录时发生未知错误: {str(e)}")
                return False
        else:
            # 硬删除：物理删除记录
            delete_sql = 'DELETE FROM "references" WHERE reference_url = ?'
            
            try:
                with self.get_connection() as conn:
                    cursor = conn.execute(delete_sql, (url,))
                    conn.commit()
                    
                    operation_time = time.time() - operation_start_time
                    
                    if cursor.rowcount > 0:
                        self._operation_stats['successful_operations'] += 1
                        self._operation_stats['records_deleted'] += 1
                        db_logger.info(f"[{delete_type}] 成功删除记录: {url} - 耗时: {operation_time:.3f}s")
                        db_performance_logger.debug(f"硬删除操作耗时: {operation_time:.3f}s")
                        logger.info(f"成功删除记录: {url}")
                        return True
                    else:
                        self._operation_stats['successful_operations'] += 1  # 操作成功但无记录删除
                        db_logger.warning(f"[{delete_type}] 未找到要删除的记录: {url} - 耗时: {operation_time:.3f}s")
                        logger.warning(f"未找到要删除的记录: {url}")
                        return False
                        
            except sqlite3.Error as e:
                operation_time = time.time() - operation_start_time
                self._operation_stats['failed_operations'] += 1
                db_logger.error(f"[{delete_type}] 数据库错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
                logger.error(f"删除记录失败: {str(e)}")
                return False
            except Exception as e:
                operation_time = time.time() - operation_start_time
                self._operation_stats['failed_operations'] += 1
                db_logger.error(f"[{delete_type}] 未知错误: {str(e)} - URL: {url} - 耗时: {operation_time:.3f}s")
                logger.error(f"删除记录时发生未知错误: {str(e)}")
                return False
    
    def delete_references_by_date_range(self, start_date: str, end_date: str, soft_delete: bool = False) -> int:
        """
        根据日期范围删除数据源记录
        
        Args:
            start_date: 开始日期 (ISO格式字符串)
            end_date: 结束日期 (ISO格式字符串)
            soft_delete: 是否软删除
            
        Returns:
            int: 删除的记录数量
        """
        if soft_delete:
            try:
                with self.get_connection() as conn:
                    # 检查并添加 deleted 字段
                    cursor = conn.execute("PRAGMA table_info(references)")
                    columns = [column[1] for column in cursor.fetchall()]
                    
                    if 'deleted' not in columns:
                        conn.execute('ALTER TABLE "references" ADD COLUMN deleted BOOLEAN DEFAULT 0')
                        conn.commit()
                    
                    # 执行软删除
                    update_sql = """
                    UPDATE "references" 
                    SET deleted = 1, reference_update_time = ?
                    WHERE reference_create_time >= ? AND reference_create_time <= ?
                    AND (deleted = 0 OR deleted IS NULL)
                    """
                    current_time = datetime.now().isoformat()
                    cursor = conn.execute(update_sql, (current_time, start_date, end_date))
                    conn.commit()
                    
                    deleted_count = cursor.rowcount
                    logger.info(f"成功软删除 {deleted_count} 条记录，日期范围: {start_date} 到 {end_date}")
                    return deleted_count
                    
            except sqlite3.Error as e:
                logger.error(f"批量软删除记录失败: {str(e)}")
                return 0
            except Exception as e:
                logger.error(f"批量软删除记录时发生未知错误: {str(e)}")
                return 0
        else:
            # 硬删除
            delete_sql = """
            DELETE FROM "references" 
            WHERE reference_create_time >= ? AND reference_create_time <= ?
            """
            
            try:
                with self.get_connection() as conn:
                    cursor = conn.execute(delete_sql, (start_date, end_date))
                    conn.commit()
                    
                    deleted_count = cursor.rowcount
                    logger.info(f"成功删除 {deleted_count} 条记录，日期范围: {start_date} 到 {end_date}")
                    return deleted_count
                    
            except sqlite3.Error as e:
                logger.error(f"批量删除记录失败: {str(e)}")
                return 0
            except Exception as e:
                logger.error(f"批量删除记录时发生未知错误: {str(e)}")
                return 0
    
    def get_record_count(self, include_deleted: bool = False) -> int:
        """
        获取记录总数
        
        Args:
            include_deleted: 是否包含已软删除的记录
            
        Returns:
            int: 记录总数
        """
        operation_start_time = time.time()
        db_logger.debug(f"[记录统计] 开始统计记录数量 - 包含已删除: {include_deleted}")
        
        try:
            with self.get_connection() as conn:
                if include_deleted:
                    count_sql = 'SELECT COUNT(*) FROM "references"'
                    cursor = conn.execute(count_sql)
                else:
                    # 检查 deleted 字段是否存在
                    cursor = conn.execute('PRAGMA table_info("references")')
                    columns = [column[1] for column in cursor.fetchall()]
                    
                    if 'deleted' in columns:
                        count_sql = 'SELECT COUNT(*) FROM "references" WHERE deleted = 0 OR deleted IS NULL'
                    else:
                        # 如果没有 deleted 字段，返回所有记录
                        count_sql = 'SELECT COUNT(*) FROM "references"'
                    
                    cursor = conn.execute(count_sql)
                
                count = cursor.fetchone()[0]
                operation_time = time.time() - operation_start_time
                
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_queried'] += 1
                
                db_logger.info(f"[记录统计] 统计完成 - 记录数: {count} - 耗时: {operation_time:.3f}s")
                db_performance_logger.debug(f"记录统计耗时: {operation_time:.3f}s")
                return count
                
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[记录统计] 数据库错误: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"获取记录总数失败: {str(e)}")
            return 0
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[记录统计] 未知错误: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"获取记录总数时发生未知错误: {str(e)}")
            return 0
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """
        获取数据库操作统计信息
        
        Returns:
            Dict[str, Any]: 操作统计信息
        """
        stats = self._operation_stats.copy()
        stats['connection_count'] = self._connection_count
        stats['success_rate'] = (
            stats['successful_operations'] / max(stats['successful_operations'] + stats['failed_operations'], 1) * 100
        )
        return stats
    
    def log_operation_summary(self):
        """
        记录操作统计摘要
        """
        stats = self.get_operation_stats()
        db_logger.info(f"[操作统计] 数据库操作摘要:")
        db_logger.info(f"  - 连接次数: {stats['connection_count']}")
        db_logger.info(f"  - 成功操作: {stats['successful_operations']}")
        db_logger.info(f"  - 失败操作: {stats['failed_operations']}")
        db_logger.info(f"  - 成功率: {stats['success_rate']:.2f}%")
        db_logger.info(f"  - 插入记录: {stats['records_inserted']}")
        db_logger.info(f"  - 更新记录: {stats['records_updated']}")
        db_logger.info(f"  - 删除记录: {stats['records_deleted']}")
        db_logger.info(f"  - 查询记录: {stats['records_queried']}")
    
    def reset_operation_stats(self):
        """
        重置操作统计信息
        """
        db_logger.info("[操作统计] 重置操作统计信息")
        self._operation_stats = {
            'connections': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'records_deleted': 0,
            'records_queried': 0
        }
        self._connection_count = 0

# 数据映射和转换功能

def map_source_to_db_record(source: Dict[str, Any], artifact_id: int = 1) -> Dict[str, Any]:
    """
    将源数据映射为数据库记录
    
    Args:
        source: 源数据字典，包含从搜索结果获取的数据
        
    Returns:
        Dict[str, Any]: 映射后的数据库记录字典
        
    映射规则：
    - reference_type: 默认 "未分类"
    - reference_url: source["value"] (完整真实URL)
    - reference_content: source["snippet"]
    - reference_create_time: 当前系统时间
    - reference_update_time: 当前系统时间
    - reference_version: 默认 1
    - reference_title: source["title"]
    - reference_related_content: source["related_content"]
    - verified: source["verified"]
    - publisher: source["publisher"] 发布机构
    - collection_time: 等于 reference_create_time
    - credibility: 默认 2 (中等可信度)
    - related_assessment: 默认 0.80
    - word_count: 计算总字数
    - reading_time: 计算阅读时间
    - file_path: 默认 "root"
    - file_size: 计算文件大小
    - status: 默认 0
    """
    current_time = datetime.now().isoformat()
    
    # 获取真实URL，优先使用value字段，回退到url字段
    reference_url = source.get("value") or source.get("url", "")
    
    # 清理和验证URL
    reference_url = clean_and_validate_url(reference_url)
    
    # 清理标题
    reference_title = clean_text_field(source.get("title", ""))
    if not reference_title:
        reference_title = "未命名"
    
    # 清理内容字段
    # 对于reference_content，仍使用snippet作为摘要
    reference_content = clean_text_field(source.get("snippet", ""))
    # 对于reference_related_content，优先使用full_text，然后是related_content
    reference_related_content = clean_text_field(
        source.get("full_text", source.get("related_content", ""))
    )
    
    # 计算字数和阅读时间
    total_content = reference_content + reference_related_content
    word_count = len(total_content)
    
    # 计算阅读时间（秒）并格式化
    reading_seconds = max(1, math.ceil(word_count / 200 * 60))  # 200字/分钟
    reading_time_str = format_reading_time(reading_seconds)
    
    # 计算文件大小并格式化
    bytes_size = len(total_content.encode('utf-8'))
    file_size_str = format_file_size(bytes_size)
    
    db_record = {
        "reference_type": source.get("reference_type", "未分类"),
        "reference_url": reference_url,
        "reference_content": reference_content,
        "reference_create_time": current_time,
        "reference_update_time": current_time,
        "reference_version": source.get("reference_version", 1),
        "reference_title": reference_title,
        "reference_related_content": reference_related_content,
        "verified": source.get("verified", False),
        "publisher": source.get("publisher", None),
        "collection_time": current_time,  # 等于 create_time
        "credibility": source.get("credibility", 2),  # 默认中等可信度
        "related_assessment": source.get("related_assessment", 0.80),  # 默认相关性评分
        "word_count": word_count,
        "reading_time": reading_time_str,  # 格式化的时间字符串
        "file_path": source.get("file_path", "root"),
        "file_size": file_size_str,  # 格式化的文件大小字符串
        "status": source.get("status", 0),  # 默认状态为0
        "credibility_assessment": source.get("credibility_assessment", None),  # 可信度评估文本
        "related_assessment_text": source.get("related_assessment_text", None),  # 相关性评估文本
        "artifact_id": artifact_id  # 工件ID
    }
    
    return db_record


def clean_and_validate_url(url: str) -> str:
    """
    清理和验证URL格式
    
    Args:
        url: 原始URL字符串
        
    Returns:
        str: 清理后的URL，如果无效则返回空字符串
    """
    if not url or not isinstance(url, str):
        return ""
    
    # 去除首尾空白字符
    url = url.strip()
    
    if not url:
        return ""
    
    # 如果URL不以http://或https://开头，添加https://
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # 使用urlparse验证URL格式
        parsed = urlparse(url)
        
        # 检查是否有有效的scheme和netloc
        if parsed.scheme in ('http', 'https') and parsed.netloc:
            # 进一步验证netloc是否包含有效的域名格式
            if '.' in parsed.netloc or parsed.netloc == 'localhost':
                return url
            else:
                logger.warning(f"无效的域名格式: {url}")
                return ""
        else:
            logger.warning(f"无效的URL格式: {url}")
            return ""
            
    except Exception as e:
        logger.warning(f"URL验证失败: {url} - {str(e)}")
        return ""


def clean_text_field(text: Any) -> str:
    """
    清理文本字段，处理空值和特殊字符
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    if text is None:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # 去除首尾空白字符
    text = text.strip()
    
    # 替换多个连续的空白字符为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 移除或转义可能导致问题的特殊字符
    # 保留基本的标点符号和Unicode字符
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def validate_db_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证数据库记录的完整性和有效性
    
    Args:
        record: 数据库记录字典
        
    Returns:
        tuple[bool, List[str]]: (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查必需字段
    required_fields = ["reference_url", "reference_title"]
    for field in required_fields:
        if not record.get(field):
            errors.append(f"缺少必需字段: {field}")
    
    # 验证URL格式
    if record.get("reference_url"):
        cleaned_url = clean_and_validate_url(record["reference_url"])
        if not cleaned_url:
            errors.append("URL格式无效")
    
    # 验证标题长度
    title = record.get("reference_title", "")
    if len(title) > 500:  # 假设标题最大长度为500字符
        errors.append("标题长度超过限制")
    
    # 验证内容长度 - 放宽限制到 500000 字符（约 500KB）
    content = record.get("reference_content", "")
    if len(content) > 500000:  # 内容最大长度为500000字符
        errors.append("内容长度超过限制")
    
    # 验证版本号
    version = record.get("reference_version", 1)
    if not isinstance(version, int) or version < 1:
        errors.append("版本号必须是大于0的整数")
    
    # 验证布尔字段
    verified = record.get("verified", False)
    if not isinstance(verified, bool):
        errors.append("verified字段必须是布尔值")
    
    return len(errors) == 0, errors


def batch_map_sources_to_db_records(sources: List[Dict[str, Any]], artifact_id: int = 1) -> List[Dict[str, Any]]:
    """
    批量将源数据映射为数据库记录
    
    Args:
        sources: 源数据列表
        
    Returns:
        List[Dict[str, Any]]: 映射后的有效数据库记录列表
    """
    valid_records = []
    invalid_count = 0
    
    for i, source in enumerate(sources):
        try:
            # 映射数据
            db_record = map_source_to_db_record(source, artifact_id)
            
            # 验证记录
            is_valid, errors = validate_db_record(db_record)
            
            if is_valid:
                valid_records.append(db_record)
            else:
                invalid_count += 1
                logger.warning(f"跳过无效记录 {i+1}: {', '.join(errors)}")
                
        except Exception as e:
            invalid_count += 1
            logger.error(f"映射记录 {i+1} 时发生错误: {str(e)}")
    
    logger.info(f"批量映射完成: {len(valid_records)} 条有效记录, {invalid_count} 条无效记录")
    return valid_records