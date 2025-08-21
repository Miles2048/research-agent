#!/usr/bin/env python3
"""
测试单条记录写入到远程PostgreSQL数据库
"""

import sys
sys.path.append('src')

from src.data_migration.data_mapper import DataMapper
from src.data_migration.remote_writer import RemoteWriter
import sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

def main():
    print("🔍 测试单条记录写入")
    print("=" * 50)
    
    try:
        # 1. 加载一条源数据
        print("📖 加载源数据...")
        source_db_path = Path("../source_data.db").resolve()
        
        conn = sqlite3.connect(source_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM "references" WHERE id = 2 LIMIT 1')
        source_record = cursor.fetchone()
        conn.close()
        
        if not source_record:
            print("❌ 未找到测试记录")
            return
        
        print(f"✅ 源记录: ID={source_record['id']}, 标题='{source_record['reference_title'][:30]}...'")
        
        # 2. 数据映射转换
        print("\n🔄 数据映射转换...")
        mapper = DataMapper(company_id=3, artifact_id=3, created_by=3)
        
        # 将Row对象转换为字典
        source_dict = dict(source_record)
        transformed = mapper.transform_record(source_dict)
        
        print(f"✅ 转换完成:")
        print(f"  • reference_type: {transformed['reference_type']}")
        print(f"  • related_assessment: {transformed['related_assessment']}")
        print(f"  • reading_time: {transformed['reading_time']}分钟")
        print(f"  • file_size: {transformed['file_size']}字节")
        print(f"  • company_id: {transformed['company_id']}")
        print(f"  • artifact_id: {transformed['artifact_id']}")
        print(f"  • created_by: {transformed['created_by']}")
        
        # 3. 连接PostgreSQL并写入
        print("\n💾 连接远程数据库...")
        env_path = Path(__file__).parent / 'database.env'
        load_dotenv(env_path)
        
        config = {
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }
        
        conn = psycopg2.connect(
            cursor_factory=RealDictCursor,
            sslmode='disable',
            connect_timeout=30,
            **config
        )
        cursor = conn.cursor()
        
        print("✅ 远程连接成功")
        
        # 4. 检查记录是否已存在 (基于name和url)
        print("\n🔍 检查重复记录...")
        cursor.execute("""
            SELECT id, name FROM research_results 
            WHERE name = %s OR url = %s
            LIMIT 1
        """, (transformed['name'], transformed['url']))
        
        existing = cursor.fetchone()
        if existing:
            print(f"⚠️ 记录已存在: ID={existing['id']}, name='{existing['name'][:30]}...'")
            print("跳过插入，使用UPDATE测试...")
            
            # 更新现有记录的reading_time作为测试
            original_reading_time = transformed['reading_time']
            test_reading_time = original_reading_time + 999  # 添加测试标记
            
            cursor.execute("""
                UPDATE research_results 
                SET reading_time = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, reading_time
            """, (test_reading_time, existing['id']))
            
            updated_record = cursor.fetchone()
            conn.commit()
            
            print(f"✅ 更新成功: ID={updated_record['id']}, reading_time={updated_record['reading_time']}分钟")
            
            # 恢复原值
            cursor.execute("""
                UPDATE research_results 
                SET reading_time = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (original_reading_time, existing['id']))
            conn.commit()
            print(f"✅ 已恢复原值: reading_time={original_reading_time}分钟")
            
        else:
            print("✅ 无重复记录，可以插入")
            
            # 5. 执行插入
            print("\n📝 执行插入操作...")
            
            insert_sql = """
                INSERT INTO research_results (
                    company_id, artifact_id, created_by, name, url, reference_type,
                    publisher, collection_time, credibility, related_assessment, 
                    status, word_count, reading_time, file_path, file_size, raw_content,
                    created_at, updated_at
                ) VALUES (
                    %(company_id)s, %(artifact_id)s, %(created_by)s, %(name)s, %(url)s, %(reference_type)s,
                    %(publisher)s, %(collection_time)s, %(credibility)s, %(related_assessment)s,
                    %(status)s, %(word_count)s, %(reading_time)s, %(file_path)s, %(file_size)s, %(raw_content)s,
                    %(created_at)s, %(updated_at)s
                ) RETURNING id;
            """
            
            cursor.execute(insert_sql, transformed)
            new_id = cursor.fetchone()['id']
            conn.commit()
            
            print(f"✅ 插入成功! 新记录ID: {new_id}")
            
            # 验证插入的数据
            cursor.execute("SELECT * FROM research_results WHERE id = %s", (new_id,))
            inserted_record = cursor.fetchone()
            
            print(f"📋 验证插入的记录:")
            print(f"  • ID: {inserted_record['id']}")
            print(f"  • name: {inserted_record['name'][:50]}...")
            print(f"  • reference_type: {inserted_record['reference_type']}")
            print(f"  • related_assessment: {inserted_record['related_assessment']}")
            print(f"  • company_id: {inserted_record['company_id']}")
        
        conn.close()
        print("\n🎉 单条记录写入测试成功!")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()