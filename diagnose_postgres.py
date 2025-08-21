#!/usr/bin/env python3
"""
PostgreSQL连接诊断工具
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from pathlib import Path

def main():
    print("🔍 PostgreSQL连接诊断工具")
    print("=" * 50)
    
    # 加载环境变量
    env_path = Path(__file__).parent / 'database.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"❌ 环境变量文件不存在: {env_path}")
        return
    
    # 读取配置
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "mydatabase"),
        "user": os.getenv("DB_USER", "user"),
        "password": os.getenv("DB_PASSWORD", "password")
    }
    
    print("\n📋 连接配置:")
    print(f"  主机: {config['host']}")
    print(f"  端口: {config['port']}")
    print(f"  数据库: {config['database']}")
    print(f"  用户: {config['user']}")
    print(f"  密码: {'*' * len(config['password'])}")
    
    # 测试1: 基础连接
    print("\n🔗 测试1: 基础连接...")
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            connect_timeout=10
        )
        print("✅ 基础连接成功")
        conn.close()
    except Exception as e:
        print(f"❌ 基础连接失败: {str(e)}")
        return
    
    # 测试2: 带cursor的连接
    print("\n📝 测试2: 带cursor的连接...")
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )
        cursor = conn.cursor()
        print("✅ Cursor创建成功")
        conn.close()
    except Exception as e:
        print(f"❌ Cursor连接失败: {str(e)}")
        return
    
    # 测试3: 执行简单查询
    print("\n🔍 测试3: 执行查询...")
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ 数据库版本: {version[0]}")
        conn.close()
    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试4: 检查目标表
    print("\n📊 测试4: 检查research_results表...")
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            cursor_factory=RealDictCursor,
            connect_timeout=10
        )
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'research_results'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ research_results表存在")
            
            # 获取表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'research_results'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            print("📋 表结构:")
            for col in columns:
                print(f"  • {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
                
            # 检查表中现有数据
            cursor.execute("SELECT COUNT(*) FROM research_results;")
            count = cursor.fetchone()[0]
            print(f"📊 现有记录数: {count}")
            
        else:
            print("❌ research_results表不存在")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 表检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🎯 诊断完成！")
    if table_exists:
        print("✅ 数据库连接正常，可以开始数据迁移")
    else:
        print("⚠️ 需要先创建research_results表")

if __name__ == "__main__":
    main()