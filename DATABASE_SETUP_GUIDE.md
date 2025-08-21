# PostgreSQL 数据库连接配置指南

本指南将帮助您配置和使用远程PostgreSQL数据库连接。

## 📋 配置概览

您的数据库配置信息：
- **主机**: 8.133.247.176
- **端口**: 5432
- **数据库**: foxlen_db_staging
- **用户**: foxlen_staging
- **密码**: Cc201819..

## 🚀 快速开始

### 1. 环境配置

数据库配置已保存在 `backend/database.env` 文件中：

```env
# 远程PostgreSQL数据库配置
DB_HOST=8.133.247.176
DB_PORT=5432
DB_NAME=foxlen_db_staging
DB_USER=foxlen_staging
DB_PASSWORD=Cc201819..

# 数据库类型配置 (sqlite 或 postgresql)
DB_TYPE=postgresql

# 本地SQLite数据库路径 (备用选项)
SQLITE_DB_PATH=research_data.db
```

### 2. 依赖安装

PostgreSQL驱动程序已安装：
```bash
# 在虚拟环境中安装PostgreSQL驱动
source .venv/bin/activate
pip install psycopg2-binary
```

### 3. 数据库配置模块

已创建 `backend/src/database_config.py` 模块，提供统一的数据库连接接口。

## 📖 使用方法

### 基础使用

```python
from src.database_config import get_database_connection, get_database_info

# 获取数据库信息
info = get_database_info()
print(f"数据库类型: {info['type']}")
print(f"连接状态: {info['connection_status']}")

# 使用连接上下文管理器
with get_database_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    result = cursor.fetchone()
    print(f"数据库版本: {result[0]}")
```

### SQLAlchemy集成

```python
from src.database_config import get_database_engine
from sqlalchemy import text

engine = get_database_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT current_database()"))
    print(f"当前数据库: {result.fetchone()[0]}")
```

### 实际应用示例

```python
from src.database_config import get_database_connection

def save_research_data(topic, content, source_url):
    """保存研究数据到数据库"""
    with get_database_connection() as conn:
        cursor = conn.cursor()
        
        # PostgreSQL语法
        cursor.execute("""
            INSERT INTO research_data (topic, content, source_url, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
        """, (topic, content, source_url))
        
        research_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"研究数据已保存，ID: {research_id}")
        return research_id

def get_research_by_topic(topic, limit=10):
    """根据主题获取研究数据"""
    with get_database_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, topic, content, source_url, created_at
            FROM research_data
            WHERE topic ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (f"%{topic}%", limit))
        
        return cursor.fetchall()
```

## 🔧 在主应用中集成

### 修改 main.py

您可以在 `src/api/main.py` 中使用新的数据库配置：

```python
# 替换原有的SQLite连接
# 原来的代码:
# import sqlite3
# conn = sqlite3.connect(DB_PATH)

# 新的代码:
from database_config import get_database_connection

# 使用统一的数据库连接
with get_database_connection() as conn:
    cursor = conn.cursor()
    # 您的数据库操作...
```

### 数据库类型切换

通过修改 `database.env` 中的 `DB_TYPE` 可以在PostgreSQL和SQLite之间切换：

```env
# 使用PostgreSQL
DB_TYPE=postgresql

# 或使用SQLite (备用)
DB_TYPE=sqlite
```

## 🧪 测试连接

运行连接测试脚本：

```bash
cd backend
source .venv/bin/activate
python test_postgres_connection.py
```

这个脚本会：
1. 测试网络连接
2. 验证PostgreSQL连接
3. 执行基本查询
4. 显示诊断信息

## ⚠️ 故障排除

### 当前状态

根据测试结果：
- ✅ 网络连接成功
- ✅ PostgreSQL驱动已安装
- ❌ 数据库查询执行失败

### 可能的问题

1. **权限问题**: 用户可能没有足够的权限执行某些查询
2. **SSL配置**: 可能需要SSL连接配置
3. **数据库schema**: 可能没有相应的表结构

### 解决方案

1. **联系数据库管理员**验证：
   - 用户权限设置
   - 数据库schema是否正确
   - 是否需要SSL连接

2. **暂时使用SQLite**作为备用方案：
   ```env
   DB_TYPE=sqlite
   ```

3. **添加SSL支持**（如果需要）：
   ```python
   # 在database_config.py中修改连接参数
   conn = psycopg2.connect(
       host=config['host'],
       port=config['port'],
       database=config['database'],
       user=config['user'],
       password=config['password'],
       sslmode='require'  # 添加SSL支持
   )
   ```

## 📁 文件结构

```
backend/
├── database.env                 # 数据库配置文件
├── src/
│   └── database_config.py      # 数据库配置模块
├── test_postgres_connection.py # 连接测试脚本
└── DATABASE_SETUP_GUIDE.md     # 本指南文档
```

## 🔗 相关资源

- [PostgreSQL官方文档](https://www.postgresql.org/docs/)
- [psycopg2文档](https://www.psycopg.org/docs/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)

## 📞 技术支持

如果遇到问题，请检查：
1. 网络连接是否稳定
2. 数据库服务器是否正常运行
3. 认证信息是否正确
4. 防火墙设置是否允许连接

---

**注意**: 目前PostgreSQL连接可以建立，但查询执行时遇到问题。建议联系数据库管理员确认用户权限和数据库配置。作为备用方案，系统会自动回退到SQLite数据库。