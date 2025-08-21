#!/usr/bin/env python3
"""检查publisher字段"""

import sqlite3

conn = sqlite3.connect("local_source_data.db")
cursor = conn.cursor()

# 统计publisher字段情况
cursor.execute("SELECT COUNT(*) FROM source_data")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM source_data WHERE publisher IS NOT NULL")
with_publisher = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM source_data WHERE publisher IS NULL")
without_publisher = cursor.fetchone()[0]

print(f"📊 Publisher字段统计:")
print(f"   总记录数: {total}")
print(f"   有publisher: {with_publisher}")
print(f"   无publisher: {without_publisher}")

# 显示前10条有publisher的记录
print(f"\n📝 前10条有publisher的记录:")
cursor.execute("SELECT name, publisher, url FROM source_data WHERE publisher IS NOT NULL LIMIT 10")
for i, (name, publisher, url) in enumerate(cursor.fetchall(), 1):
    print(f"\n{i}. {name[:50]}...")
    print(f"   Publisher: {publisher}")
    print(f"   URL: {url[:80]}...")

# 按publisher分组统计
print(f"\n🏢 Publisher分布:")
cursor.execute("SELECT publisher, COUNT(*) FROM source_data WHERE publisher IS NOT NULL GROUP BY publisher ORDER BY COUNT(*) DESC")
for publisher, count in cursor.fetchall():
    print(f"   {publisher}: {count} 条")

conn.close()