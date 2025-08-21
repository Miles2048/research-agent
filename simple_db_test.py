#!/usr/bin/env python3
"""
最简单的数据库连接测试
不依赖任何第三方库，只使用内置的psycopg2
"""

import sys

# 尝试导入psycopg2
try:
    import psycopg2
    print("✅ psycopg2已安装")
except ImportError:
    print("❌ psycopg2未安装")
    print("请运行: pip install psycopg2-binary")
    sys.exit(1)

# 直接硬编码配置（从database.env读取）
config = {
    "host": "8.133.247.176",
    "port": 5432,
    "database": "foxlen_db_staging",
    "user": "foxlen_staging",
    "password": "Cc201819.."
}

print("\n📊 尝试连接到PostgreSQL:")
print(f"  主机: {config['host']}:{config['port']}")
print(f"  数据库: {config['database']}")
print(f"  用户: {config['user']}")

try:
    # 尝试连接
    print("\n🔄 正在连接...")
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        database=config["database"],
        user=config["user"],
        password=config["password"],
        connect_timeout=10
    )
    
    print("✅ 连接成功！")
    
    # 简单查询
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"\n数据库版本: {version}")
    
    # 检查research_results表
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'research_results';
    """)
    count = cursor.fetchone()[0]
    
    if count > 0:
        print("\n✅ research_results表存在")
        cursor.execute("SELECT COUNT(*) FROM research_results;")
        records = cursor.fetchone()[0]
        print(f"   记录数: {records}")
    else:
        print("\n⚠️  research_results表不存在")
    
    cursor.close()
    conn.close()
    
    print("\n✅ 测试成功！数据库可以正常连接")
    
except Exception as e:
    print(f"\n❌ 连接失败:")
    print(f"   {type(e).__name__}: {str(e)}")
    print("\n可能的原因:")
    print("  1. 网络无法访问数据库服务器")
    print("  2. 防火墙阻止了连接")
    print("  3. 数据库服务未启动")
    print("  4. 认证信息错误")