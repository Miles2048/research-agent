#!/usr/bin/env python3
"""
真实数据迁移测试 - 从source_data.db写入到远程PostgreSQL
"""

import sys
sys.path.append('src')

from src.data_migration.data_mapper import DataMapper
import sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from datetime import datetime

def main():
    print("🚀 真实数据迁移测试")
    print("=" * 60)
    
    # 第1步: 验证PostgreSQL连接
    print("🔗 第1步: 验证PostgreSQL连接...")
    env_path = Path(__file__).parent / 'database.env'
    load_dotenv(env_path)
    
    config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    print(f"连接目标: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    
    try:
        # 测试连接
        conn = psycopg2.connect(
            cursor_factory=RealDictCursor,
            connect_timeout=15,
            **config
        )
        cursor = conn.cursor()
        
        # 获取数据库版本
        cursor.execute("SELECT version();")
        version = cursor.fetchone()['version']
        print(f"✅ PostgreSQL连接成功!")
        print(f"   版本: {version[:50]}...")
        
        # 检查目标表
        cursor.execute("SELECT COUNT(*) as count FROM research_results;")
        existing_count = cursor.fetchone()['count']
        print(f"   research_results表现有记录: {existing_count}条")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {str(e)}")
        return False
    
    # 第2步: 加载source_data.db数据
    print(f"\n📖 第2步: 加载source_data.db数据...")
    source_db_path = Path("../source_data.db").resolve()
    
    if not source_db_path.exists():
        print(f"❌ 源数据库文件不存在: {source_db_path}")
        return False
    
    print(f"源数据库路径: {source_db_path}")
    
    try:
        conn = sqlite3.connect(source_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) as count FROM "references"')
        total_count = cursor.fetchone()['count']
        print(f"✅ 源数据库连接成功，总记录数: {total_count}")
        
        # 加载测试数据(前3条)
        cursor.execute('SELECT * FROM "references" ORDER BY id LIMIT 3')
        test_records = cursor.fetchall()
        
        print(f"📋 加载测试记录:")
        for record in test_records:
            print(f"   ID={record['id']}: {record['reference_title'][:40]}...")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 源数据库连接失败: {str(e)}")
        return False
    
    # 第3步: 数据映射转换
    print(f"\n🔄 第3步: 数据映射转换...")
    mapper = DataMapper(company_id=3, artifact_id=3, created_by=3)
    
    transformed_records = []
    for record in test_records:
        try:
            source_dict = dict(record)
            transformed = mapper.transform_record(source_dict)
            transformed_records.append(transformed)
            
            print(f"✅ 转换成功 ID={record['id']}:")
            print(f"   类型: {record['reference_type']} → {transformed['reference_type']}")
            print(f"   相关性: {record['related_assessment']} → {transformed['related_assessment']}")
            print(f"   阅读时间: {record['reading_time']} → {transformed['reading_time']}分钟")
            
        except Exception as e:
            print(f"❌ 转换失败 ID={record['id']}: {str(e)}")
    
    if not transformed_records:
        print("❌ 没有成功转换的记录")
        return False
    
    print(f"✅ 成功转换 {len(transformed_records)} 条记录")
    
    # 第4步: 写入PostgreSQL
    print(f"\n💾 第4步: 写入PostgreSQL数据库...")
    
    try:
        # 重新连接PostgreSQL
        conn = psycopg2.connect(
            cursor_factory=RealDictCursor,
            connect_timeout=15,
            **config
        )
        cursor = conn.cursor()
        
        # 准备插入SQL
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
            ) RETURNING id, name;
        """
        
        successful_inserts = 0
        
        for i, transformed in enumerate(transformed_records):
            try:
                # 检查是否已存在相同记录(基于name)
                cursor.execute(
                    "SELECT id FROM research_results WHERE name = %s LIMIT 1",
                    (transformed['name'],)
                )
                existing = cursor.fetchone()
                
                if existing:
                    print(f"⚠️  记录已存在，跳过: ID={existing['id']}")
                    continue
                
                # 执行插入
                cursor.execute(insert_sql, transformed)
                result = cursor.fetchone()
                new_id = result['id']
                
                print(f"✅ 插入成功: 新ID={new_id}, 原ID={test_records[i]['id']}")
                print(f"   标题: {result['name'][:50]}...")
                
                successful_inserts += 1
                
            except Exception as e:
                print(f"❌ 插入失败 (原ID={test_records[i]['id']}): {str(e)}")
                conn.rollback()  # 回滚当前事务
                
                # 重新开始事务
                conn.commit()
        
        # 提交所有成功的插入
        conn.commit()
        print(f"\n🎉 插入完成: {successful_inserts}/{len(transformed_records)} 条记录成功")
        
        # 验证插入结果
        cursor.execute("SELECT COUNT(*) as count FROM research_results;")
        final_count = cursor.fetchone()['count']
        print(f"📊 数据库现在总共有: {final_count} 条记录")
        
        # 显示最新插入的记录
        if successful_inserts > 0:
            cursor.execute("""
                SELECT id, name, reference_type, company_id, artifact_id, created_by
                FROM research_results 
                WHERE company_id = 3 AND artifact_id = 3 AND created_by = 3
                ORDER BY id DESC 
                LIMIT %s
            """, (successful_inserts,))
            
            latest_records = cursor.fetchall()
            print(f"\n📋 最新插入的记录:")
            for record in latest_records:
                print(f"   ID={record['id']}: {record['name'][:40]}... (类型:{record['reference_type']})")
        
        conn.close()
        
        return successful_inserts > 0
        
    except Exception as e:
        print(f"❌ PostgreSQL写入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    print(f"\n" + "="*60)
    if success:
        print("🎯 真实数据迁移测试成功!")
        print("✅ 确认可以从source_data.db写入到远程PostgreSQL")
        print("💡 现在可以执行完整的70条记录迁移")
    else:
        print("❌ 真实数据迁移测试失败")
        print("🔧 请检查连接和配置问题")