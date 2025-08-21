#!/usr/bin/env python3
"""
推送本地源数据到远程PostgreSQL数据库
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv


class RemoteDataPusher:
    """远程数据推送器"""
    
    def __init__(self, local_db_path: str = "local_source_data.db", env_path: str = ".env"):
        """
        初始化推送器
        
        Args:
            local_db_path: 本地SQLite数据库路径
            env_path: 环境变量文件路径
        """
        self.local_db_path = local_db_path
        
        # 加载环境变量
        load_dotenv(env_path)
        
        # PostgreSQL配置 - 从环境变量读取，不使用硬编码默认值
        self.pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')) if os.getenv('DB_PORT') else None,
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # 验证必需的配置是否存在
        missing_configs = []
        for key, value in self.pg_config.items():
            if value is None:
                missing_configs.append(f"DB_{key.upper()}")
        
        if missing_configs:
            raise ValueError(f"缺少必需的数据库配置: {', '.join(missing_configs)}。请检查 {env_path} 文件")
        
        print(f"📡 远程数据库配置:")
        print(f"   Host: {self.pg_config['host']}")
        print(f"   Port: {self.pg_config['port']}")
        print(f"   Database: {self.pg_config['database']}")
        print(f"   User: {self.pg_config['user']}")
    
    def get_unpushed_records(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取未推送的记录
        
        Args:
            limit: 限制获取的记录数
            
        Returns:
            未推送的记录列表
        """
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM source_data WHERE pushed = 0"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        records = []
        for row in rows:
            record = dict(row)
            records.append(record)
        
        conn.close()
        
        print(f"📊 找到 {len(records)} 条未推送记录")
        return records
    
    def test_remote_connection(self) -> bool:
        """
        测试远程数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ 远程数据库连接成功")
            print(f"   PostgreSQL版本: {version[0]}")
            conn.close()
            return True
        except Exception as e:
            print(f"❌ 远程数据库连接失败: {str(e)}")
            return False
    
    def create_remote_table_if_not_exists(self):
        """在远程数据库创建表（如果不存在）"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS research_results (
            id SERIAL PRIMARY KEY,
            
            -- API传入字段
            company_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            
            -- 内容字段
            name VARCHAR(255) NOT NULL,
            url VARCHAR(500) NOT NULL,
            raw_content TEXT,
            
            -- 分类字段
            reference_type VARCHAR(100),
            publisher VARCHAR(255),
            
            -- 评估字段
            credibility INTEGER DEFAULT 2,
            related_assessment INTEGER DEFAULT 80,
            status INTEGER DEFAULT 1,
            
            -- 统计字段
            word_count INTEGER DEFAULT 0,
            reading_time INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_path VARCHAR(500) DEFAULT 'NA',
            
            -- 时间字段
            collection_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP
        );
        """
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            
            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_company_artifact ON research_results(company_id, artifact_id);",
                "CREATE INDEX IF NOT EXISTS idx_url ON research_results(url);",
                "CREATE INDEX IF NOT EXISTS idx_reference_type ON research_results(reference_type);",
                "CREATE INDEX IF NOT EXISTS idx_created_at ON research_results(created_at);"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            print("✅ 远程数据库表结构检查完成")
        except Exception as e:
            print(f"⚠️ 创建远程表时出错: {str(e)}")
    
    def push_records_to_remote(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        推送记录到远程数据库
        
        Args:
            records: 要推送的记录列表
            
        Returns:
            (成功数, 失败数)
        """
        if not records:
            print("⚠️ 没有记录需要推送")
            return 0, 0
        
        success_count = 0
        failed_count = 0
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            # 准备插入数据
            insert_sql = """
            INSERT INTO research_results (
                company_id, artifact_id, created_by,
                name, url, raw_content,
                reference_type, publisher,
                credibility, related_assessment, status,
                word_count, reading_time, file_size, file_path,
                collection_time, created_at, updated_at, deleted_at
            ) VALUES (
                %(company_id)s, %(artifact_id)s, %(created_by)s,
                %(name)s, %(url)s, %(raw_content)s,
                %(reference_type)s, %(publisher)s,
                %(credibility)s, %(related_assessment)s, %(status)s,
                %(word_count)s, %(reading_time)s, %(file_size)s, %(file_path)s,
                %(collection_time)s, %(created_at)s, %(updated_at)s, %(deleted_at)s
            )
            """
            
            # 记录成功推送的ID
            pushed_ids = []
            
            for record in records:
                try:
                    # 移除本地特有的字段
                    remote_record = record.copy()
                    remote_record.pop('id', None)  # 移除本地ID
                    remote_record.pop('pushed', None)  # 移除pushed字段
                    
                    # 强制覆盖指定字段值
                    remote_record['company_id'] = 4
                    remote_record['artifact_id'] = 36
                    remote_record['created_by'] = 8
                    
                    # 处理credibility值映射：5->3, 其他->2
                    if 'credibility' in remote_record:
                        if remote_record['credibility'] == 5:
                            remote_record['credibility'] = 3
                        else:
                            remote_record['credibility'] = 2
                    
                    # 处理空值 - 为必填字段提供默认值
                    if remote_record.get('reference_type') is None:
                        remote_record['reference_type'] = 'uncategorized'
                    if remote_record.get('publisher') is None:
                        remote_record['publisher'] = 'Unknown'
                    
                    # 额外检查：如果publisher在黑名单中，也设为Unknown
                    # 这是为了处理已经存在的数据
                    if remote_record.get('publisher'):
                        publisher_lower = str(remote_record['publisher']).lower()
                        blacklist = {
                            'made in china', 'example', 'example.com', 'test', 'test.com',
                            'demo', 'demo.com', 'localhost', '127.0.0.1', 'sample', 'sample.com',
                            'unknown', 'none', 'null', 'undefined', 'placeholder', 'temp',
                            'temporary', 'dummy', 'fake', 'invalid'
                        }
                        if publisher_lower in blacklist:
                            remote_record['publisher'] = 'Unknown'
                    
                    cursor.execute(insert_sql, remote_record)
                    
                    if cursor.rowcount > 0:
                        success_count += 1
                        pushed_ids.append(record['id'])
                    else:
                        # URL已存在，也算成功
                        success_count += 1
                        pushed_ids.append(record['id'])
                        
                except Exception as e:
                    failed_count += 1
                    # 简化错误日志，只在需要时显示详细错误
                    if "duplicate" not in str(e).lower() and "conflict" not in str(e).lower():
                        print(f"    ⚠️ 错误: {str(e)[:60]}...")
            
            conn.commit()
            conn.close()
            
            # 更新本地数据库的pushed状态
            if pushed_ids:
                self.update_pushed_status(pushed_ids)
            
        except Exception as e:
            print(f"❌ 推送过程出错: {str(e)}")
            failed_count = len(records)
        
        return success_count, failed_count
    
    def update_pushed_status(self, record_ids: List[int]):
        """
        更新本地数据库的pushed状态
        
        Args:
            record_ids: 已推送的记录ID列表
        """
        if not record_ids:
            return
        
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # 批量更新
        placeholders = ','.join('?' * len(record_ids))
        update_sql = f"UPDATE source_data SET pushed = 1 WHERE id IN ({placeholders})"
        
        cursor.execute(update_sql, record_ids)
        conn.commit()
        conn.close()
        
        # 简化日志，不再显示每次更新状态的信息
    
    def push_all(self, batch_size: int = 100, max_retries: int = 2):
        """
        推送所有未推送的记录（一条条推送，失败就跳过）
        
        Args:
            batch_size: 每批次获取的记录数（仍然批量获取，但一条条推送）
            max_retries: 最大重试次数（默认2次），避免无限循环
        """
        print("="*60)
        print("🚀 开始推送数据到远程数据库（一条条推送）")
        print("="*60)
        
        # 测试连接
        if not self.test_remote_connection():
            return
        
        # 创建远程表（如果不存在）
        self.create_remote_table_if_not_exists()
        
        total_success = 0
        total_failed = 0
        consecutive_failures = 0  # 连续失败次数
        processed_count = 0
        
        while True:
            # 获取一批未推送的记录
            records = self.get_unpushed_records(limit=batch_size)
            
            if not records:
                break
            
            # 一条条推送记录
            for i, record in enumerate(records, 1):
                processed_count += 1
                name = record.get('name', 'Unknown')[:40]
                
                # 推送单条记录
                success, failed = self.push_records_to_remote([record])
                
                if success > 0:
                    total_success += success
                    consecutive_failures = 0  # 重置连续失败计数器
                    print(f"[{processed_count:3d}] ✅ {name}")
                else:
                    total_failed += failed
                    consecutive_failures += 1
                    print(f"[{processed_count:3d}] ❌ {name}")
                    
                    # 检查是否连续失败过多
                    if consecutive_failures >= max_retries:
                        print(f"\n❌ 连续失败 {max_retries} 条，停止推送")
                        return  # 直接返回，不再继续
            
            # 如果这批记录处理完了，继续下一批
        
        print("\n" + "="*60)
        print(f"📊 推送完成统计:")
        print(f"   总成功: {total_success} 条")
        print(f"   总失败: {total_failed} 条")
        print(f"   批次数: {batch_num}")
        print("="*60)
    
    def get_sync_status(self) -> Dict[str, int]:
        """获取同步状态统计"""
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM source_data")
        total = cursor.fetchone()[0]
        
        # 已推送记录数
        cursor.execute("SELECT COUNT(*) FROM source_data WHERE pushed = 1")
        pushed = cursor.fetchone()[0]
        
        # 未推送记录数
        unpushed = total - pushed
        
        conn.close()
        
        return {
            "total_records": total,
            "pushed_records": pushed,
            "unpushed_records": unpushed,
            "sync_percentage": round((pushed / total * 100) if total > 0 else 0, 2)
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="推送本地数据到远程PostgreSQL数据库")
    parser.add_argument("--local-db", default="local_source_data.db", help="本地数据库路径")
    parser.add_argument("--env-file", default=".env", help="环境变量文件路径")
    parser.add_argument("--batch-size", type=int, default=100, help="每批次处理的记录数")
    parser.add_argument("--test", action="store_true", help="仅测试连接")
    parser.add_argument("--status", action="store_true", help="显示同步状态")
    parser.add_argument("--limit", type=int, help="限制推送的记录数")
    
    args = parser.parse_args()
    
    pusher = RemoteDataPusher(local_db_path=args.local_db, env_path=args.env_file)
    
    if args.test:
        # 仅测试连接
        pusher.test_remote_connection()
    elif args.status:
        # 显示同步状态
        status = pusher.get_sync_status()
        print("\n📊 同步状态:")
        print(f"   总记录数: {status['total_records']}")
        print(f"   已推送: {status['pushed_records']}")
        print(f"   未推送: {status['unpushed_records']}")
        print(f"   同步进度: {status['sync_percentage']}%")
    else:
        # 执行推送
        if args.limit:
            # 限制推送数量
            records = pusher.get_unpushed_records(limit=args.limit)
            if records:
                pusher.push_records_to_remote(records)
        else:
            # 推送所有
            pusher.push_all(batch_size=args.batch_size)


if __name__ == "__main__":
    main()