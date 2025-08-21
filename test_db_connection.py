#!/usr/bin/env python3
"""
简单的数据库连接测试脚本
不依赖SQLAlchemy，直接使用psycopg2
"""

import os
import sys
from dotenv import load_dotenv

# 尝试导入psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("❌ psycopg2未安装，无法连接PostgreSQL")
    print("请运行: pip install psycopg2-binary")
    sys.exit(1)

def test_connection():
    """测试PostgreSQL数据库连接"""
    
    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), "database.env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ 已加载配置文件: {env_path}")
    else:
        print(f"❌ 配置文件不存在: {env_path}")
        return False
    
    # 读取数据库配置
    config = {
        "host": os.getenv("DB_HOST", "8.133.247.176"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "foxlen_db_staging"),
        "user": os.getenv("DB_USER", "foxlen_staging"),
        "password": os.getenv("DB_PASSWORD", "")
    }
    
    print("\n📊 数据库配置:")
    print(f"  主机: {config['host']}")
    print(f"  端口: {config['port']}")
    print(f"  数据库: {config['database']}")
    print(f"  用户: {config['user']}")
    print(f"  密码: {'*' * len(config['password']) if config['password'] else '(空)'}")
    
    # 尝试连接
    print("\n🔄 正在连接数据库...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            connect_timeout=10
        )
        
        print("✅ 数据库连接成功！")
        
        # 获取数据库版本
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n📋 PostgreSQL版本:\n  {version}")
        
        # 获取当前数据库信息
        cursor.execute("SELECT current_database(), current_user, now();")
        result = cursor.fetchone()
        print(f"\n📍 连接信息:")
        print(f"  当前数据库: {result[0]}")
        print(f"  当前用户: {result[1]}")
        print(f"  服务器时间: {result[2]}")
        
        # 检查research_results表
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'research_results'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print(f"\n✅ research_results表存在")
            
            # 获取表的记录数
            cursor.execute("SELECT COUNT(*) FROM research_results;")
            count = cursor.fetchone()[0]
            print(f"  记录数: {count}")
            
            # 获取表结构信息
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = 'research_results'
                ORDER BY ordinal_position
                LIMIT 5;
            """)
            columns = cursor.fetchall()
            print(f"  前5个字段:")
            for col in columns:
                nullable = "可空" if col[2] == 'YES' else "非空"
                print(f"    - {col[0]}: {col[1]} ({nullable})")
        else:
            print(f"\n⚠️  research_results表不存在")
        
        cursor.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ 连接失败 - 操作错误:")
        print(f"  {str(e)}")
        if "timeout" in str(e).lower():
            print("  可能原因: 网络连接超时，请检查网络或防火墙设置")
        elif "password authentication failed" in str(e).lower():
            print("  可能原因: 用户名或密码错误")
        elif "could not connect to server" in str(e).lower():
            print("  可能原因: 服务器地址或端口错误，或服务器未启动")
        return False
        
    except Exception as e:
        print(f"\n❌ 连接失败 - 未知错误:")
        print(f"  {type(e).__name__}: {str(e)}")
        return False
        
    finally:
        if conn:
            conn.close()
            print("\n🔒 数据库连接已关闭")

if __name__ == "__main__":
    print("=== PostgreSQL数据库连接测试 ===\n")
    
    # 检查psycopg2是否可用
    if not POSTGRES_AVAILABLE:
        sys.exit(1)
    
    # 运行测试
    success = test_connection()
    
    if success:
        print("\n✅ 测试完成: 数据库连接正常")
    else:
        print("\n❌ 测试完成: 数据库连接失败")
        print("\n💡 故障排查建议:")
        print("  1. 检查网络连接是否正常")
        print("  2. 确认数据库服务器是否在运行")
        print("  3. 验证database.env中的配置是否正确")
        print("  4. 检查防火墙是否允许连接到数据库端口")