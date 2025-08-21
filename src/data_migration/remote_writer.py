"""
远程数据库写入器
负责将转换后的数据写入PostgreSQL的research_results表
"""

import os
from typing import List, Dict, Any, Tuple
from contextlib import contextmanager
from loguru import logger

# 尝试导入dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

# 尝试导入PostgreSQL驱动
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("PostgreSQL驱动(psycopg2)未安装")


class RemoteWriter:
    """远程PostgreSQL数据库写入器"""
    
    def __init__(self, env_file: str = "database.env"):
        """
        初始化远程写入器
        
        Args:
            env_file: 环境变量文件路径
        """
        # 加载环境变量 - 修复路径计算和手动解析
        # 当前文件在 src/data_migration/remote_writer.py
        # 目标文件在 backend/database.env
        # 所以需要向上两级目录
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", env_file)
        
        # 如果相对路径找不到，尝试从当前工作目录查找
        if not os.path.exists(env_path):
            env_path = env_file
            
        env_vars = {}
        if os.path.exists(env_path):
            try:
                # 首先尝试使用dotenv
                load_dotenv(env_path)
                logger.info(f"已使用dotenv加载环境变量文件: {os.path.abspath(env_path)}")
            except Exception as e:
                logger.warning(f"dotenv加载失败: {str(e)}")
            
            # 手动解析环境文件作为备份
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key, value = key.strip(), value.strip()
                            env_vars[key] = value
                            # 如果系统环境变量中没有，则设置
                            if not os.getenv(key):
                                os.environ[key] = value
                logger.info(f"手动解析环境变量: {len(env_vars)} 个变量")
            except Exception as e:
                logger.error(f"手动解析环境文件失败: {str(e)}")
        else:
            logger.warning(f"环境变量文件未找到: {env_path}")
            logger.info("使用默认配置或系统环境变量")
        
        # PostgreSQL连接配置 - 优先使用环境变量，然后是手动解析的值，最后是默认值
        self.postgres_config = {
            "host": os.getenv("DB_HOST") or env_vars.get("DB_HOST", "8.133.247.176"),
            "port": int(os.getenv("DB_PORT") or env_vars.get("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME") or env_vars.get("DB_NAME", "foxlen_db_staging"),
            "user": os.getenv("DB_USER") or env_vars.get("DB_USER", "foxlen_staging"),
            "password": os.getenv("DB_PASSWORD") or env_vars.get("DB_PASSWORD", "")
        }
        logger.info("=."*50)
        logger.info(f"PostgreSQL配置: {self.postgres_config}")
        logger.info("=."*50)
        # 验证PostgreSQL可用性
        if not POSTGRES_AVAILABLE:
            raise ImportError("PostgreSQL驱动未安装，请执行: pip install psycopg2-binary")
        
        logger.info(f"RemoteWriter初始化完成，目标数据库: {self.postgres_config['host']}:{self.postgres_config['port']}")
    
    @contextmanager
    def get_connection(self):
        """
        获取PostgreSQL连接的上下文管理器
        
        Yields:
            PostgreSQL连接对象
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.postgres_config["host"],
                port=self.postgres_config["port"],
                database=self.postgres_config["database"],
                user=self.postgres_config["user"],
                password=self.postgres_config["password"],
                cursor_factory=RealDictCursor,
                connect_timeout=30,
                sslmode='require'
            )
            logger.debug("PostgreSQL连接建立成功")
            yield conn
            
        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("PostgreSQL连接已关闭")
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                logger.info(f"数据库连接测试成功，版本: {version['version']}")
                return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False
    
    def check_table_exists(self, table_name: str = "research_results") -> bool:
        """
        检查目标表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            表是否存在
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    ) as table_exists;
                """, (table_name,))
                
                exists = cursor.fetchone()['table_exists']
                logger.info(f"表 {table_name} {'存在' if exists else '不存在'}")
                return exists
        except Exception as e:
            logger.error(f"检查表是否存在失败: {str(e)}")
            return False
    
    def get_table_schema(self, table_name: str = "research_results") -> List[Dict[str, Any]]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            
        Returns:
            表结构信息列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table_name,))
                
                columns = cursor.fetchall()
                logger.info(f"获取表 {table_name} 结构信息: {len(columns)} 个字段")
                return [dict(col) for col in columns]
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return []
    
    def insert_single_record(self, record: Dict[str, Any], table_name: str = "research_results") -> bool:
        """
        插入单条记录
        
        Args:
            record: 要插入的记录
            table_name: 目标表名
            
        Returns:
            插入是否成功
        """
        insert_sql = f"""
        INSERT INTO {table_name} (
            company_id, artifact_id, created_by, name, url, reference_type,
            publisher, collection_time, credibility, related_assessment, status,
            word_count, reading_time, file_path, file_size, raw_content,
            created_at, updated_at, deleted_at
        ) VALUES (
            %(company_id)s, %(artifact_id)s, %(created_by)s, %(name)s, %(url)s, %(reference_type)s,
            %(publisher)s, %(collection_time)s, %(credibility)s, %(related_assessment)s, %(status)s,
            %(word_count)s, %(reading_time)s, %(file_path)s, %(file_size)s, %(raw_content)s,
            %(created_at)s, %(updated_at)s, %(deleted_at)s
        )
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, record)
                conn.commit()
                logger.debug(f"成功插入记录: {record.get('name', 'Unknown')[:50]}...")
                return True
        except Exception as e:
            logger.error(f"插入记录失败: {record.get('name', 'Unknown')[:50]}..., 错误: {str(e)}")
            return False
    
    def insert_batch_records(self, records: List[Dict[str, Any]], 
                           table_name: str = "research_results",
                           batch_size: int = 50) -> Tuple[int, int, List[str]]:
        """
        批量插入记录
        
        Args:
            records: 要插入的记录列表
            table_name: 目标表名
            batch_size: 批次大小
            
        Returns:
            (成功数量, 失败数量, 错误列表)
        """
        if not records:
            logger.warning("没有记录需要插入")
            return 0, 0, []
        
        insert_sql = f"""
        INSERT INTO {table_name} (
            company_id, artifact_id, created_by, name, url, reference_type,
            publisher, collection_time, credibility, related_assessment, status,
            word_count, reading_time, file_path, file_size, raw_content,
            created_at, updated_at, deleted_at
        ) VALUES (
            %(company_id)s, %(artifact_id)s, %(created_by)s, %(name)s, %(url)s, %(reference_type)s,
            %(publisher)s, %(collection_time)s, %(credibility)s, %(related_assessment)s, %(status)s,
            %(word_count)s, %(reading_time)s, %(file_path)s, %(file_size)s, %(raw_content)s,
            %(created_at)s, %(updated_at)s, %(deleted_at)s
        )
        """
        
        successful = 0
        failed = 0
        errors = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 分批处理
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    batch_successful = 0
                    
                    for record in batch:
                        try:
                            cursor.execute(insert_sql, record)
                            batch_successful += 1
                        except Exception as e:
                            failed += 1
                            error_msg = f"记录 '{record.get('name', 'Unknown')[:30]}...': {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                    
                    # 提交当前批次
                    conn.commit()
                    successful += batch_successful
                    
                    logger.info(f"批次 {i//batch_size + 1} 完成: 成功 {batch_successful}/{len(batch)}")
                
                logger.info(f"批量插入完成: 成功 {successful}, 失败 {failed}")
                
        except Exception as e:
            logger.error(f"批量插入过程中发生错误: {str(e)}")
            errors.append(f"批量插入错误: {str(e)}")
        
        return successful, failed, errors
    
    def get_insert_statistics(self, table_name: str = "research_results") -> Dict[str, Any]:
        """
        获取插入后的统计信息
        
        Args:
            table_name: 表名
            
        Returns:
            统计信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总记录数
                cursor.execute(f"SELECT COUNT(*) as total_count FROM {table_name};")
                total_count = cursor.fetchone()['total_count']
                
                # 按类型统计
                cursor.execute(f"""
                    SELECT reference_type, COUNT(*) as count
                    FROM {table_name}
                    GROUP BY reference_type
                    ORDER BY count DESC;
                """)
                type_stats = cursor.fetchall()
                
                # 按可信度统计
                cursor.execute(f"""
                    SELECT credibility, COUNT(*) as count
                    FROM {table_name}
                    GROUP BY credibility
                    ORDER BY credibility;
                """)
                credibility_stats = cursor.fetchall()
                
                # 最近插入的记录
                cursor.execute(f"""
                    SELECT DATE_TRUNC('hour', created_at) as created_at, COUNT(*) as count
                    FROM {table_name}
                    WHERE created_at >= NOW() - INTERVAL '1 hour'
                    GROUP BY DATE_TRUNC('hour', created_at)
                    ORDER BY DATE_TRUNC('hour', created_at) DESC;
                """)
                recent_stats = cursor.fetchall()
                
                return {
                    "total_records": total_count,
                    "type_distribution": [dict(row) for row in type_stats],
                    "credibility_distribution": [dict(row) for row in credibility_stats],
                    "recent_inserts": [dict(row) for row in recent_stats]
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    def validate_record_constraints(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证记录是否符合数据库约束
        
        Args:
            record: 要验证的记录
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查必需字段
        required_fields = ["company_id", "artifact_id", "created_by", "name", "file_path"]
        for field in required_fields:
            if not record.get(field):
                errors.append(f"必需字段 {field} 缺失或为空")
        
        # 检查枚举约束
        valid_reference_types = ["uncategorized", "official_statistics", "business_data", "real-time_data", "academic_research"]
        if record.get("reference_type") not in valid_reference_types:
            errors.append(f"reference_type 值无效: {record.get('reference_type')}")
        
        valid_credibility = [1, 2, 3]
        if record.get("credibility") not in valid_credibility:
            errors.append(f"credibility 值无效: {record.get('credibility')}")
        
        valid_status = [1, 2, 3]
        if record.get("status") not in valid_status:
            errors.append(f"status 值无效: {record.get('status')}")
        
        # 检查字段长度
        length_constraints = {
            "name": 255,
            "url": 500,
            "reference_type": 100,
            "publisher": 255,
            "file_path": 500
        }
        
        for field, max_length in length_constraints.items():
            value = record.get(field)
            if value and len(str(value)) > max_length:
                errors.append(f"{field} 长度超限: {len(str(value))} > {max_length}")
        
        return len(errors) == 0, errors


# 使用示例
if __name__ == "__main__":
    # 测试远程写入器
    writer = RemoteWriter()
    
    # 测试连接
    if writer.test_connection():
        print("✅ 数据库连接测试成功")
        
        # 检查表是否存在
        if writer.check_table_exists():
            print("✅ research_results 表存在")
            
            # 获取表结构
            schema = writer.get_table_schema()
            print(f"📋 表结构: {len(schema)} 个字段")
            
            # 获取统计信息
            stats = writer.get_insert_statistics()
            print(f"📊 当前记录数: {stats.get('total_records', 0)}")
        else:
            print("❌ research_results 表不存在")
    else:
        print("❌ 数据库连接失败")