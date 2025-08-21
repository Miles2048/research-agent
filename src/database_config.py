"""
数据库连接配置模块
支持SQLite和PostgreSQL数据库连接
"""

import os
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Optional, Union, Any, Dict
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

# 可选导入PostgreSQL相关模块
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    POSTGRES_AVAILABLE = False
    print("⚠️  PostgreSQL驱动(psycopg2)未安装，仅支持SQLite数据库")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """数据库配置管理类"""
    
    def __init__(self, env_file: str = "database.env"):
        """
        初始化数据库配置
        
        Args:
            env_file: 环境变量文件路径
        """
        # 加载环境变量
        env_path = os.path.join(os.path.dirname(__file__), "..", env_file)
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info(f"已加载环境变量文件: {env_path}")
        else:
            logger.warning(f"环境变量文件未找到: {env_path}")
        
        # 获取数据库配置
        self.db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        # 如果请求PostgreSQL但驱动不可用，回退到SQLite
        if self.db_type == "postgresql" and not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL驱动不可用，回退到SQLite数据库")
            self.db_type = "sqlite"
        
        # PostgreSQL配置
        self.postgres_config = {
            "host": os.getenv("DB_HOST", "8.133.247.176"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", "foxlen_db_staging"),
            "user": os.getenv("DB_USER", "foxlen_staging"),
            "password": os.getenv("DB_PASSWORD", "")
        }
        
        # SQLite配置
        self.sqlite_path = os.getenv("SQLITE_DB_PATH", "research_data.db")
        if not os.path.isabs(self.sqlite_path):
            # 如果不是绝对路径，相对于backend目录
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.sqlite_path = os.path.join(backend_dir, self.sqlite_path)
    
    def get_connection_string(self) -> str:
        """获取SQLAlchemy连接字符串"""
        if self.db_type == "postgresql":
            config = self.postgres_config
            return f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        else:
            return f"sqlite:///{self.sqlite_path}"
    
    def get_sqlalchemy_engine(self) -> Engine:
        """获取SQLAlchemy引擎"""
        connection_string = self.get_connection_string()
        
        if self.db_type == "postgresql":
            # PostgreSQL配置
            engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False  # 设置为True可以看到SQL查询日志
            )
        else:
            # SQLite配置
            engine = create_engine(
                connection_string,
                pool_timeout=20,
                echo=False
            )
        
        logger.info(f"数据库引擎已创建: {self.db_type}")
        return engine
    
    @contextmanager
    def get_raw_connection(self):
        """获取原生数据库连接（上下文管理器）"""
        conn = None
        try:
            if self.db_type == "postgresql":
                if not POSTGRES_AVAILABLE:
                    raise Exception("PostgreSQL驱动(psycopg2)未安装")
                
                conn = psycopg2.connect(
                    host=self.postgres_config["host"],
                    port=self.postgres_config["port"],
                    database=self.postgres_config["database"],
                    user=self.postgres_config["user"],
                    password=self.postgres_config["password"],
                    cursor_factory=RealDictCursor  # 返回字典格式的结果
                )
                logger.info("PostgreSQL连接已建立")
            else:
                conn = sqlite3.connect(self.sqlite_path)
                conn.row_factory = sqlite3.Row  # 返回字典格式的结果
                logger.info(f"SQLite连接已建立: {self.sqlite_path}")
            
            yield conn
            
        except Exception as e:
            logger.error(f"数据库连接错误: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.info("数据库连接已关闭")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_raw_connection() as conn:
                cursor = conn.cursor()
                if self.db_type == "postgresql":
                    cursor.execute("SELECT version();")
                    result = cursor.fetchone()
                    logger.info(f"PostgreSQL版本: {result[0]}")
                else:
                    cursor.execute("SELECT sqlite_version();")
                    result = cursor.fetchone()
                    logger.info(f"SQLite版本: {result[0]}")
                
                return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        info = {
            "type": self.db_type,
            "connection_status": self.test_connection()
        }
        
        if self.db_type == "postgresql":
            info.update({
                "host": self.postgres_config["host"],
                "port": self.postgres_config["port"],
                "database": self.postgres_config["database"],
                "user": self.postgres_config["user"]
            })
        else:
            info.update({
                "path": self.sqlite_path,
                "exists": os.path.exists(self.sqlite_path)
            })
        
        return info

# 全局数据库配置实例
db_config = DatabaseConfig()

# 便捷函数
def get_database_engine() -> Engine:
    """获取数据库引擎"""
    return db_config.get_sqlalchemy_engine()

def get_database_connection():
    """获取数据库连接（上下文管理器）"""
    return db_config.get_raw_connection()

def test_database_connection() -> bool:
    """测试数据库连接"""
    return db_config.test_connection()

def get_database_info() -> Dict[str, Any]:
    """获取数据库信息"""
    return db_config.get_database_info()

if __name__ == "__main__":
    # 测试脚本
    print("=== 数据库配置测试 ===")
    
    # 显示配置信息
    info = get_database_info()
    print(f"数据库类型: {info['type']}")
    print(f"连接状态: {'✅ 成功' if info['connection_status'] else '❌ 失败'}")
    
    if info['type'] == 'postgresql':
        print(f"主机: {info['host']}:{info['port']}")
        print(f"数据库: {info['database']}")
        print(f"用户: {info['user']}")
    else:
        print(f"数据库文件: {info['path']}")
        print(f"文件存在: {'是' if info['exists'] else '否'}")
    
    # 测试连接
    if test_database_connection():
        print("\n✅ 数据库连接测试成功！")
        
        # 测试查询
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                if db_config.db_type == "postgresql":
                    cursor.execute("SELECT current_database(), current_user, now();")
                    result = cursor.fetchone()
                    print(f"当前数据库: {result[0]}")
                    print(f"当前用户: {result[1]}")
                    print(f"当前时间: {result[2]}")
                else:
                    cursor.execute("SELECT datetime('now');")
                    result = cursor.fetchone()
                    print(f"当前时间: {result[0]}")
        except Exception as e:
            print(f"❌ 查询测试失败: {str(e)}")
    else:
        print("\n❌ 数据库连接测试失败！")