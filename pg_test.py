import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor

# 你的数据库配置（去掉前面的注释 #）
DB_HOST = "8.133.247.176"
DB_PORT = 5432
DB_NAME = "foxlen_db_staging"
DB_USER = "foxlen_staging"
DB_PASSWORD = "Cc201819.."

def test_postgres_connection():
    """测试 PostgreSQL 数据库连接"""
    conn = None
    try:
        # 尝试建立数据库连接
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor,
            connect_timeout=10,  # 10秒超时
            sslmode="require"    # 启用 SSL
        )
        
        # 如果连接成功，执行一个简单查询（例如获取当前数据库版本）
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        print("✅ 数据库连接成功！")
        print("PostgreSQL 版本:", db_version["version"])
        
    except OperationalError as e:
        print(f"❌ 数据库连接失败: {e}")
        print("请检查：")
        print("- 数据库IP、端口是否正确？")
        print("- 用户名和密码是否正确？")
        print("- 远程访问是否已启用（pg_hba.conf）？")
        print("- 防火墙是否开放 5432 端口？")
        
    finally:
        # 无论如何都关闭连接
        if conn:
            conn.close()
            print("\n🔌 连接已关闭")

if __name__ == "__main__":
    print("正在测试 PostgreSQL 连接...")
    test_postgres_connection()
