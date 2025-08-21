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
        创建数据库表 - 新的统一表结构（与远程数据库对应）
        
        Returns:
            bool: 创建成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        db_logger.info("[表创建] 开始创建数据库表和索引")
        
        # 新的统一表结构，与远程 research_results 表对应
        create_research_results_table_sql = """
        CREATE TABLE IF NOT EXISTS "research_results_local" (
            -- 主键
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- 外键字段（从API获取）
            company_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            
            -- 基础信息字段
            name VARCHAR(255) NOT NULL,
            url VARCHAR(500) NOT NULL,
            reference_type VARCHAR(100) NOT NULL DEFAULT 'uncategorized',
            publisher VARCHAR(255),
            
            -- 内容字段
            raw_content TEXT,
            
            -- 评估字段
            credibility INTEGER DEFAULT 2,
            related_assessment INTEGER DEFAULT 80,
            status INTEGER DEFAULT 1,
            
            -- 统计字段
            word_count INTEGER DEFAULT 0,
            reading_time INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_path VARCHAR(500) DEFAULT 'root',
            
            -- 时间字段
            collection_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            
            -- 同步状态字段（新增）
            pushed INTEGER DEFAULT 0,
            
            -- 约束
            UNIQUE(url)
        )
        """
        
        # 创建索引的 SQL 语句
        create_indexes_sql = [
            # 基础查询索引
            'CREATE INDEX IF NOT EXISTS idx_url ON "research_results_local"(url);',
            'CREATE INDEX IF NOT EXISTS idx_name ON "research_results_local"(name);',
            'CREATE INDEX IF NOT EXISTS idx_company_artifact ON "research_results_local"(company_id, artifact_id);',
            'CREATE INDEX IF NOT EXISTS idx_created_by ON "research_results_local"(created_by);',
            
            # 类型和状态索引
            'CREATE INDEX IF NOT EXISTS idx_reference_type ON "research_results_local"(reference_type);',
            'CREATE INDEX IF NOT EXISTS idx_credibility ON "research_results_local"(credibility);',
            'CREATE INDEX IF NOT EXISTS idx_status ON "research_results_local"(status);',
            
            # 时间索引
            'CREATE INDEX IF NOT EXISTS idx_collection_time ON "research_results_local"(collection_time);',
            'CREATE INDEX IF NOT EXISTS idx_created_at ON "research_results_local"(created_at);',
            
            # 同步状态索引（重要）
            'CREATE INDEX IF NOT EXISTS idx_pushed ON "research_results_local"(pushed);',
            'CREATE INDEX IF NOT EXISTS idx_unpushed ON "research_results_local"(pushed, created_at);'
        ]
        
        try:
            with self.get_connection() as conn:
                # 创建表
                db_logger.debug("[表创建] 执行创建 research_results_local 表的 SQL")
                conn.execute(create_research_results_table_sql)
                db_logger.info("[表创建] 数据表 research_results_local 创建成功或已存在")
                logger.info("数据表 research_results_local 创建成功或已存在")
                
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
    
    def insert_research_result(self, research_data: Dict[str, Any]) -> bool:
        """
        插入单条研究结果记录（新的统一结构）
        
        Args:
            research_data: 研究结果记录字典，包含所有必要字段
            
        Returns:
            bool: 插入成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        url = research_data.get('url', 'Unknown')
        
        db_logger.debug(f"[单条插入] 开始插入记录: {url}")
        
        insert_sql = """
        INSERT OR REPLACE INTO "research_results_local" (
            company_id, artifact_id, created_by, name, url, reference_type,
            publisher, raw_content, credibility, related_assessment, status,
            word_count, reading_time, file_size, file_path, collection_time,
            created_at, updated_at, deleted_at, pushed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            # 设置默认值和当前时间
            current_time = datetime.now().isoformat()
            
            # 计算字数和阅读时间
            content = research_data.get('raw_content', '')
            word_count = research_data.get('word_count', len(content))
            
            # 计算阅读时间（分钟）
            reading_minutes = research_data.get('reading_time')
            if reading_minutes is None:
                reading_minutes = max(1, math.ceil(word_count / 200))  # 200字/分钟
            
            # 计算文件大小（字节）
            file_size_bytes = research_data.get('file_size')
            if file_size_bytes is None:
                file_size_bytes = len(content.encode('utf-8'))
            
            values = (
                research_data['company_id'],           # 必需字段
                research_data['artifact_id'],          # 必需字段
                research_data['created_by'],           # 必需字段
                research_data['name'][:255],           # 限制长度
                research_data['url'][:500],            # 必需字段，限制长度
                research_data.get('reference_type', 'uncategorized'),  # 使用英文枚举
                research_data.get('publisher'),       # 可为空
                research_data.get('raw_content', ''), # 原始内容
                research_data.get('credibility', 2),  # 默认中等可信度
                research_data.get('related_assessment', 80),  # 默认相关性评分（整数）
                research_data.get('status', 1),       # 默认状态为1
                word_count,                            # 字数统计
                reading_minutes,                       # 阅读时间（分钟）
                file_size_bytes,                       # 文件大小（字节）
                research_data.get('file_path', 'root'),  # 文件路径
                research_data.get('collection_time', current_time),  # 收集时间
                research_data.get('created_at', current_time),       # 创建时间
                current_time,                          # 更新时间
                research_data.get('deleted_at'),      # 删除时间（可空）
                research_data.get('pushed', 0)        # 同步状态，默认未推送
            )
            
            with self.get_connection() as conn:
                conn.execute(insert_sql, values)
                conn.commit()
                
                operation_time = time.time() - operation_start_time
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_inserted'] += 1
                
                db_logger.info(f"[单条插入] 成功插入记录: {url} - 耗时: {operation_time:.3f}s")
                db_performance_logger.debug(f"单条插入耗时: {operation_time:.3f}s")
                logger.info(f"成功插入研究结果记录: {research_data['url']}")
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
    
    def insert_research_results_batch(self, research_list: List[Dict[str, Any]]) -> int:
        """
        批量插入研究结果记录（新的统一结构）
        
        Args:
            research_list: 研究结果记录列表
            
        Returns:
            int: 成功插入的记录数量
        """
        operation_start_time = time.time()
        
        if not research_list:
            db_logger.warning("[批量插入] 数据列表为空，跳过操作")
            logger.warning("批量插入的数据列表为空")
            return 0
        
        db_logger.info(f"[批量插入] 开始批量插入 {len(research_list)} 条记录")
            
        insert_sql = """
        INSERT OR REPLACE INTO "research_results_local" (
            company_id, artifact_id, created_by, name, url, reference_type,
            publisher, raw_content, credibility, related_assessment, status,
            word_count, reading_time, file_size, file_path, collection_time,
            created_at, updated_at, deleted_at, pushed
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
                
                for i, research_data in enumerate(research_list, 1):
                    try:
                        # 验证必需字段
                        required_fields = ['company_id', 'artifact_id', 'created_by', 'name', 'url']
                        missing_fields = [field for field in required_fields if field not in research_data]
                        if missing_fields:
                            skipped_count += 1
                            url = research_data.get('url', 'Unknown')
                            db_logger.warning(f"[批量插入] 跳过记录 {i}/{len(research_list)} - 缺少必需字段: {missing_fields} - URL: {url}")
                            logger.warning(f"跳过缺少必需字段的记录: {missing_fields}")
                            continue
                            
                        # 计算字数和阅读时间
                        content = research_data.get('raw_content', '')
                        word_count = research_data.get('word_count', len(content))
                        
                        # 计算阅读时间（分钟）
                        reading_minutes = research_data.get('reading_time')
                        if reading_minutes is None:
                            reading_minutes = max(1, math.ceil(word_count / 200))  # 200字/分钟
                        
                        # 计算文件大小（字节）
                        file_size_bytes = research_data.get('file_size')
                        if file_size_bytes is None:
                            file_size_bytes = len(content.encode('utf-8'))
                        
                        values = (
                            research_data['company_id'],
                            research_data['artifact_id'],
                            research_data['created_by'],
                            research_data['name'][:255],
                            research_data['url'][:500],
                            research_data.get('reference_type', 'uncategorized'),
                            research_data.get('publisher'),
                            research_data.get('raw_content', ''),
                            research_data.get('credibility', 2),
                            research_data.get('related_assessment', 80),
                            research_data.get('status', 1),
                            word_count,
                            reading_minutes,
                            file_size_bytes,
                            research_data.get('file_path', 'root'),
                            research_data.get('collection_time', current_time),
                            research_data.get('created_at', current_time),
                            current_time,  # updated_at
                            research_data.get('deleted_at'),
                            research_data.get('pushed', 0)
                        )
                        
                        conn.execute(insert_sql, values)
                        successful_count += 1
                        
                        if i % 10 == 0:  # 每10条记录记录一次进度
                            db_logger.debug(f"[批量插入] 进度: {i}/{len(research_list)} - 成功: {successful_count}")
                        
                    except Exception as e:
                        failed_count += 1
                        url = research_data.get('url', 'Unknown')
                        db_logger.error(f"[批量插入] 记录 {i}/{len(research_list)} 插入失败: {str(e)} - URL: {url}")
                        logger.error(f"插入单条记录失败: {str(e)}, 数据: {research_data}")
                        continue
                
                conn.commit()
                operation_time = time.time() - operation_start_time
                
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_inserted'] += successful_count
                
                db_logger.info(f"[批量插入] 事务提交成功 - 总计: {len(research_list)}, 成功: {successful_count}, 失败: {failed_count}, 跳过: {skipped_count} - 耗时: {operation_time:.3f}s")
                db_performance_logger.info(f"批量插入操作耗时: {operation_time:.3f}s - 记录数: {len(research_list)} - 平均: {operation_time/len(research_list):.4f}s/条")
                logger.info(f"批量插入完成: 成功 {successful_count} 条，总计 {len(research_list)} 条")
                
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
    
    # ========== 新增的同步状态管理方法 ==========
    
    def get_unpushed_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取未推送到远程的记录
        
        Args:
            limit: 限制返回记录数量
            
        Returns:
            List[Dict[str, Any]]: 未推送的记录列表
        """
        operation_start_time = time.time()
        db_logger.debug(f"[同步查询] 开始查询未推送记录 - 限制: {limit}")
        
        if limit is not None:
            select_sql = """
            SELECT * FROM "research_results_local" 
            WHERE pushed = 0 AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT ?
            """
            params = (limit,)
        else:
            select_sql = """
            SELECT * FROM "research_results_local" 
            WHERE pushed = 0 AND deleted_at IS NULL
            ORDER BY created_at ASC
            """
            params = ()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, params)
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                operation_time = time.time() - operation_start_time
                
                self._operation_stats['successful_operations'] += 1
                self._operation_stats['records_queried'] += len(results)
                
                db_logger.info(f"[同步查询] 查询完成 - 未推送记录数: {len(results)} - 耗时: {operation_time:.3f}s")
                logger.info(f"获取到 {len(results)} 条未推送记录")
                return results
                
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[同步查询] 数据库错误: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"获取未推送记录失败: {str(e)}")
            return []
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[同步查询] 未知错误: {str(e)} - 耗时: {operation_time:.3f}s")
            logger.error(f"获取未推送记录时发生未知错误: {str(e)}")
            return []
    
    def update_pushed_status(self, record_id: int, pushed: int = 1) -> bool:
        """
        更新记录的推送状态
        
        Args:
            record_id: 记录ID
            pushed: 推送状态 (0=未推送, 1=已推送)
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        operation_start_time = time.time()
        db_logger.debug(f"[同步更新] 开始更新推送状态: ID={record_id}, pushed={pushed}")
        
        update_sql = """
        UPDATE "research_results_local" 
        SET pushed = ?, updated_at = ?
        WHERE id = ?
        """
        
        try:
            current_time = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.execute(update_sql, (pushed, current_time, record_id))
                conn.commit()
                
                operation_time = time.time() - operation_start_time
                
                if cursor.rowcount > 0:
                    self._operation_stats['successful_operations'] += 1
                    self._operation_stats['records_updated'] += 1
                    db_logger.info(f"[同步更新] 成功更新推送状态: ID={record_id}, pushed={pushed} - 耗时: {operation_time:.3f}s")
                    logger.info(f"成功更新记录推送状态: ID={record_id} -> pushed={pushed}")
                    return True
                else:
                    self._operation_stats['successful_operations'] += 1
                    db_logger.warning(f"[同步更新] 未找到要更新的记录: ID={record_id} - 耗时: {operation_time:.3f}s")
                    logger.warning(f"未找到要更新的记录: ID={record_id}")
                    return False
                    
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[同步更新] 数据库错误: {str(e)} - ID: {record_id} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新推送状态失败: {str(e)}")
            return False
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[同步更新] 未知错误: {str(e)} - ID: {record_id} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新推送犴态时发生未知错误: {str(e)}")
            return False
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        获取同步统计信息
        
        Returns:
            Dict[str, Any]: 同步统计信息
        """
        try:
            with self.get_connection() as conn:
                # 统计总记录数
                cursor = conn.execute('SELECT COUNT(*) FROM "research_results_local" WHERE deleted_at IS NULL')
                total_records = cursor.fetchone()[0]
                
                # 统计已推送记录数
                cursor = conn.execute('SELECT COUNT(*) FROM "research_results_local" WHERE pushed = 1 AND deleted_at IS NULL')
                pushed_records = cursor.fetchone()[0]
                
                # 统计未推送记录数
                cursor = conn.execute('SELECT COUNT(*) FROM "research_results_local" WHERE pushed = 0 AND deleted_at IS NULL')
                unpushed_records = cursor.fetchone()[0]
                
                # 计算同步进度
                sync_progress = (pushed_records / total_records * 100) if total_records > 0 else 0
                
                stats = {
                    "total_records": total_records,
                    "pushed_records": pushed_records,
                    "unpushed_records": unpushed_records,
                    "sync_progress": round(sync_progress, 2),
                    "sync_status": "completed" if unpushed_records == 0 else "pending"
                }
                
                logger.info(f"同步统计: 总计{total_records}条, 已推送{pushed_records}条, 未推送{unpushed_records}条, 进度{sync_progress:.1f}%")
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"获取同步统计信息失败: {str(e)}")
            return {
                "total_records": 0,
                "pushed_records": 0,
                "unpushed_records": 0,
                "sync_progress": 0,
                "sync_status": "error"
            }
        except Exception as e:
            logger.error(f"获取同步统计信息时发生未知错误: {str(e)}")
            return {
                "total_records": 0,
                "pushed_records": 0,
                "unpushed_records": 0,
                "sync_progress": 0,
                "sync_status": "error"
            }
    
    def get_research_result_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        根据URL查询研究结果记录
        
        Args:
            url: 研究结果URL
            
        Returns:
            Optional[Dict[str, Any]]: 找到的记录字典，未找到返回 None
        """
        operation_start_time = time.time()
        db_logger.debug(f"[URL查询] 开始查询记录: {url}")
        
        select_sql = """
        SELECT * FROM "research_results_local" WHERE url = ?
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
    
    def get_research_results_by_name(self, name: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        根据名称查询研究结果记录
        
        Args:
            name: 研究结果名称
            exact_match: 是否精确匹配，False 时使用模糊匹配
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        if exact_match:
            select_sql = """
            SELECT * FROM "research_results_local" WHERE name = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            """
            params = (name,)
        else:
            select_sql = """
            SELECT * FROM "research_results_local" WHERE name LIKE ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            """
            params = (f"%{name}%",)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(select_sql, params)
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                logger.debug(f"根据名称找到 {len(results)} 条记录: {name}")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"根据名称查询记录失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"根据名称查询记录时发生未知错误: {str(e)}")
            return []
    
    def get_research_results_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        根据日期范围查询研究结果记录
        
        Args:
            start_date: 开始日期 (ISO格式字符串)
            end_date: 结束日期 (ISO格式字符串)
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        select_sql = """
        SELECT * FROM "research_results_local" 
        WHERE created_at >= ? AND created_at <= ? AND deleted_at IS NULL
        ORDER BY created_at DESC
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
    
    def get_all_research_results(self, limit: Optional[int] = None, offset: int = 0, include_pushed: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有研究结果记录
        
        Args:
            limit: 限制返回记录数量，None 表示不限制
            offset: 偏移量，用于分页
            include_pushed: 是否包含已推送的记录
            
        Returns:
            List[Dict[str, Any]]: 记录列表
        """
        where_clause = "WHERE deleted_at IS NULL"
        if not include_pushed:
            where_clause += " AND pushed = 0"
            
        if limit is not None:
            select_sql = f"""
            SELECT * FROM "research_results_local" 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            params = (limit, offset)
        else:
            select_sql = f"""
            SELECT * FROM "research_results_local" 
            {where_clause}
            ORDER BY created_at DESC
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
    
    def update_research_result(self, record_id: int, update_data: Dict[str, Any]) -> bool:
        """
        更新研究结果记录的多个字段
        
        Args:
            record_id: 记录ID
            update_data: 要更新的字段字典
            
        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        if not update_data:
            logger.warning("更新数据为空")
            return False
            
        operation_start_time = time.time()
        db_logger.debug(f"[记录更新] 开始更新记录: ID={record_id}, 字段={list(update_data.keys())}")
        
        # 允许更新的字段
        allowed_fields = {
            'name', 'url', 'reference_type', 'publisher', 'raw_content',
            'credibility', 'related_assessment', 'status', 'word_count',
            'reading_time', 'file_size', 'file_path', 'collection_time'
        }
        
        # 过滤允许更新的字段
        valid_updates = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not valid_updates:
            logger.warning("没有有效的更新字段")
            return False
        
        # 总是更新 updated_at
        valid_updates['updated_at'] = datetime.now().isoformat()
        
        # 构建 SQL 语句
        set_clause = ", ".join([f"{field} = ?" for field in valid_updates.keys()])
        update_sql = f'UPDATE "research_results_local" SET {set_clause} WHERE id = ?'
        
        # 构建参数列表
        params = list(valid_updates.values()) + [record_id]
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(update_sql, params)
                conn.commit()
                
                operation_time = time.time() - operation_start_time
                
                if cursor.rowcount > 0:
                    self._operation_stats['successful_operations'] += 1
                    self._operation_stats['records_updated'] += 1
                    db_logger.info(f"[记录更新] 成功更新记录: ID={record_id}, 字段={list(valid_updates.keys())} - 耗时: {operation_time:.3f}s")
                    logger.info(f"成功更新记录: ID={record_id}, 字段: {list(valid_updates.keys())}")
                    return True
                else:
                    self._operation_stats['successful_operations'] += 1
                    db_logger.warning(f"[记录更新] 未找到要更新的记录: ID={record_id} - 耗时: {operation_time:.3f}s")
                    logger.warning(f"未找到要更新的记录: ID={record_id}")
                    return False
                    
        except sqlite3.Error as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[记录更新] 数据库错误: {str(e)} - ID: {record_id} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新记录失败: {str(e)}")
            return False
        except Exception as e:
            operation_time = time.time() - operation_start_time
            self._operation_stats['failed_operations'] += 1
            db_logger.error(f"[记录更新] 未知错误: {str(e)} - ID: {record_id} - 耗时: {operation_time:.3f}s")
            logger.error(f"更新记录时发生未知错误: {str(e)}")
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

def map_source_to_research_record(source: Dict[str, Any], company_id: int, artifact_id: int, created_by: int) -> Dict[str, Any]:
    """
    将源数据映射为新的研究结果记录格式
    
    Args:
        source: 源数据字典，包含从搜索结果获取的数据
        company_id: 公司ID
        artifact_id: 工件ID
        created_by: 创建者ID
        
    Returns:
        Dict[str, Any]: 映射后的研究结果记录字典
        
    新的映射规则（直接对应远程表结构）：
    - company_id: 从参数获取
    - artifact_id: 从参数获取
    - created_by: 从参数获取
    - name: source["title"] -> 直接使用
    - url: source["value"] or source["url"]
    - reference_type: 直接使用英文枚举值
    - publisher: source["publisher"]
    - raw_content: source["full_text"] or source["content"]
    - credibility: 默认 2
    - related_assessment: 直接使用整数值 (0-100)
    - status: 默认 1
    - word_count: 计算总字数
    - reading_time: 计算阅读时间（分钟）
    - file_size: 计算文件大小（字节）
    - file_path: 默认 "root"
    - collection_time: 当前时间
    - created_at: 当前时间
    - updated_at: 当前时间
    - deleted_at: NULL
    - pushed: 0 (未推送)
    """
    current_time = datetime.now().isoformat()
    
    # 获取真实URL，优先使用value字段，回退到url字段
    url = source.get("value") or source.get("url", "")
    
    # 清理和验证URL
    url = clean_and_validate_url(url)
    
    # 清理标题
    name = clean_text_field(source.get("title", ""))
    if not name:
        name = "未命名"
    
    # 清理内容字段 - 优先使用 full_text，回退到 content 或 snippet
    raw_content = clean_text_field(
        source.get("full_text") or source.get("content") or source.get("snippet", "")
    )
    
    # 计算字数和阅读时间
    word_count = source.get('word_count', len(raw_content))
    
    # 计算阅读时间（分钟）
    reading_minutes = max(1, math.ceil(word_count / 200))  # 200字/分钟
    
    # 计算文件大小（字节）
    file_size_bytes = len(raw_content.encode('utf-8'))
    
    # 处理 reference_type - 直接使用英文枚举值
    reference_type = source.get("reference_type", "uncategorized")
    # 如果是中文，进行简单映射
    if reference_type in ["未分类", "用户输入"]:
        reference_type = "uncategorized"
    elif reference_type == "行业研究报告":
        reference_type = "business_data"
    elif reference_type == "学术研究":
        reference_type = "academic_research"
    elif reference_type == "官方统计":
        reference_type = "official_statistics"
    elif reference_type == "实时数据":
        reference_type = "real-time_data"
    
    # 处理 related_assessment - 直接使用整数值
    related_assessment = source.get("related_assessment", 80)
    if isinstance(related_assessment, float) and related_assessment <= 1.0:
        related_assessment = int(related_assessment * 100)  # 0.8 -> 80
    
    research_record = {
        # 外键字段
        "company_id": company_id,
        "artifact_id": artifact_id,
        "created_by": created_by,
        
        # 基础信息字段
        "name": name[:255],  # 限制长度
        "url": url[:500],   # 限制长度
        "reference_type": reference_type,
        "publisher": source.get("publisher"),
        
        # 内容字段
        "raw_content": raw_content,
        
        # 评估字段
        "credibility": source.get("credibility", 2),
        "related_assessment": related_assessment,
        "status": source.get("status", 1),  # 默认状态为1
        
        # 统计字段
        "word_count": word_count,
        "reading_time": reading_minutes,
        "file_size": file_size_bytes,
        "file_path": source.get("file_path", "root"),
        
        # 时间字段
        "collection_time": source.get("collection_time", current_time),
        "created_at": current_time,
        "updated_at": current_time,
        "deleted_at": None,
        
        # 同步状态字段
        "pushed": 0  # 默认未推送
    }
    
    return research_record


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


def validate_research_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证研究结果记录的完整性和有效性
    
    Args:
        record: 研究结果记录字典
        
    Returns:
        tuple[bool, List[str]]: (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查必需字段
    required_fields = ["company_id", "artifact_id", "created_by", "name", "url"]
    for field in required_fields:
        if not record.get(field):
            errors.append(f"缺少必需字段: {field}")
    
    # 验证URL格式
    if record.get("url"):
        cleaned_url = clean_and_validate_url(record["url"])
        if not cleaned_url:
            errors.append("URL格式无效")
    
    # 验证名称长度
    name = record.get("name", "")
    if len(name) > 255:
        errors.append("名称长度超过限制(255字符)")
    
    # 验证内容长度
    content = record.get("raw_content", "")
    if len(content) > 1000000:  # 内容最大长度为1MB
        errors.append("内容长度超过限制")
    
    # 验证数值字段
    credibility = record.get("credibility", 2)
    if not isinstance(credibility, int) or credibility < 1 or credibility > 3:
        errors.append("可信度必须是1-3之间的整数")
    
    related_assessment = record.get("related_assessment", 80)
    if not isinstance(related_assessment, int) or related_assessment < 0 or related_assessment > 100:
        errors.append("相关性评估必须是0-100之间的整数")
    
    status = record.get("status", 1)
    if not isinstance(status, int) or status < 1 or status > 3:
        errors.append("状态必须是1-3之间的整数")
    
    # 验证reference_type枚举值
    valid_reference_types = ['uncategorized', 'official_statistics', 'business_data', 'real-time_data', 'academic_research']
    reference_type = record.get("reference_type", "uncategorized")
    if reference_type not in valid_reference_types:
        errors.append(f"reference_type必须是以下值之一: {valid_reference_types}")
    
    return len(errors) == 0, errors


def batch_map_sources_to_research_records(sources: List[Dict[str, Any]], company_id: int, artifact_id: int, created_by: int) -> List[Dict[str, Any]]:
    """
    批量将源数据映射为新的研究结果记录
    
    Args:
        sources: 源数据列表
        company_id: 公司ID
        artifact_id: 工件ID
        created_by: 创建者ID
        
    Returns:
        List[Dict[str, Any]]: 映射后的有效研究结果记录列表
    """
    valid_records = []
    invalid_count = 0
    
    for i, source in enumerate(sources):
        try:
            # 映射数据
            research_record = map_source_to_research_record(source, company_id, artifact_id, created_by)
            
            # 验证记录
            is_valid, errors = validate_research_record(research_record)
            
            if is_valid:
                valid_records.append(research_record)
            else:
                invalid_count += 1
                logger.warning(f"跳过无效记录 {i+1}: {', '.join(errors)}")
                
        except Exception as e:
            invalid_count += 1
            logger.error(f"映射记录 {i+1} 时发生错误: {str(e)}")
    
    logger.info(f"批量映射完成: {len(valid_records)} 条有效记录, {invalid_count} 条无效记录")
    return valid_records