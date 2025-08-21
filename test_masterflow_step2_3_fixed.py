#!/usr/bin/env python3
"""
修正版测试脚本 - MasterFlow步骤2.3数据同步诊断
专门用于诊断artifact_id=35只有2条数据的问题
"""

import os
import sys
import sqlite3
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import json

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# 加载环境变量
load_dotenv('.env')


class DataSyncDiagnostics:
    """数据同步诊断工具"""
    
    def __init__(self, artifact_id: int = 35, company_id: int = 3, user_id: int = 8):
        self.artifact_id = artifact_id
        self.company_id = company_id
        self.user_id = user_id
        self.local_db_path = "local_source_data.db"
        
        # PostgreSQL配置
        self.pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')) if os.getenv('DB_PORT') else None,
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        print("="*80)
        print(f"🔍 数据同步诊断 - artifact_id={artifact_id}")
        print("="*80)
    
    def diagnose_data_sync_issue(self):
        """诊断数据同步问题"""
        print(f"\n目标参数:")
        print(f"  - artifact_id: {self.artifact_id}")
        print(f"  - company_id: {self.company_id}")
        print(f"  - user_id: {self.user_id}")
        
        # 1. 检查本地数据库
        self.check_local_data()
        
        # 2. 检查远程数据库所有相关表
        self.check_remote_data()
        
        # 3. 分析差异
        self.analyze_sync_gap()
        
        # 4. 检查推送逻辑
        self.check_push_logic()
    
    def check_local_data(self):
        """检查本地数据库中的数据"""
        print("\n" + "="*60)
        print("📊 本地数据库分析 (local_source_data.db)")
        print("="*60)
        
        if not os.path.exists(self.local_db_path):
            print(f"❌ 本地数据库不存在: {self.local_db_path}")
            return
        
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # 1. 检查表结构
        cursor.execute("PRAGMA table_info(source_data)")
        columns = cursor.fetchall()
        print(f"\n表结构包含 {len(columns)} 个字段")
        
        # 2. 统计总体数据
        cursor.execute("SELECT COUNT(*) FROM source_data")
        total = cursor.fetchone()[0]
        print(f"\n总记录数: {total}")
        
        # 3. 按artifact_id统计
        cursor.execute("""
            SELECT artifact_id, COUNT(*), 
                   SUM(CASE WHEN pushed = 1 THEN 1 ELSE 0 END) as pushed_count
            FROM source_data 
            GROUP BY artifact_id
            ORDER BY artifact_id
        """)
        artifact_stats = cursor.fetchall()
        print(f"\n按artifact_id分组统计:")
        for aid, count, pushed in artifact_stats:
            print(f"  artifact_id {aid}: 总计{count}条 (已推送{pushed}条, 未推送{count-pushed}条)")
        
        # 4. 重点检查artifact_id=35
        cursor.execute("""
            SELECT COUNT(*) FROM source_data 
            WHERE artifact_id = ?
        """, (self.artifact_id,))
        target_total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM source_data 
            WHERE artifact_id = ? AND pushed = 0
        """, (self.artifact_id,))
        target_unpushed = cursor.fetchone()[0]
        
        print(f"\n🎯 artifact_id={self.artifact_id}的详细情况:")
        print(f"  - 总记录数: {target_total}")
        print(f"  - 未推送: {target_unpushed}")
        print(f"  - 已推送: {target_total - target_unpushed}")
        
        # 5. 显示具体记录
        if target_total > 0:
            cursor.execute("""
                SELECT id, name, company_id, pushed, created_at 
                FROM source_data 
                WHERE artifact_id = ?
                ORDER BY id
                LIMIT 10
            """, (self.artifact_id,))
            records = cursor.fetchall()
            print(f"\n前{min(10, len(records))}条记录:")
            for r in records:
                pushed_status = "✅已推送" if r[3] else "❌未推送"
                print(f"  ID:{r[0]}, {pushed_status}, company_id:{r[2]}, {r[1][:40]}...")
        
        conn.close()
    
    def check_remote_data(self):
        """检查远程数据库中的数据"""
        print("\n" + "="*60)
        print("☁️ 远程PostgreSQL数据库分析")
        print("="*60)
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            # 检查可能的表名
            possible_tables = [
                'research_results',
                'external_search_results',
                'research_data',
                'source_data'
            ]
            
            for table_name in possible_tables:
                try:
                    # 检查表是否存在
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table_name,))
                    exists = cursor.fetchone()[0]
                    
                    if not exists:
                        print(f"\n❌ 表 {table_name} 不存在")
                        continue
                    
                    # 统计数据
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total = cursor.fetchone()[0]
                    print(f"\n✅ 表 {table_name}: 总计 {total} 条记录")
                    
                    # 检查是否有artifact_id字段
                    cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND column_name = 'artifact_id'
                    """)
                    has_artifact = cursor.fetchone() is not None
                    
                    if has_artifact:
                        # 按artifact_id统计
                        cursor.execute(f"""
                            SELECT artifact_id, COUNT(*) 
                            FROM {table_name}
                            WHERE artifact_id IS NOT NULL
                            GROUP BY artifact_id
                            ORDER BY COUNT(*) DESC
                            LIMIT 10
                        """)
                        artifact_stats = cursor.fetchall()
                        
                        if artifact_stats:
                            print(f"  按artifact_id分组 (前10):")
                            for aid, cnt in artifact_stats:
                                marker = "🎯" if aid == self.artifact_id else "  "
                                print(f"    {marker} artifact_id {aid}: {cnt}条")
                        
                        # 特别检查目标artifact_id
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {table_name}
                            WHERE artifact_id = %s
                        """, (self.artifact_id,))
                        target_count = cursor.fetchone()[0]
                        
                        if target_count > 0:
                            print(f"\n  🎯 artifact_id={self.artifact_id}在此表中有 {target_count} 条记录")
                            
                            # 显示具体记录
                            cursor.execute(f"""
                                SELECT id, name, company_id, created_at
                                FROM {table_name}
                                WHERE artifact_id = %s
                                ORDER BY id
                                LIMIT 5
                            """, (self.artifact_id,))
                            records = cursor.fetchall()
                            print(f"    前{len(records)}条记录:")
                            for r in records:
                                print(f"      ID:{r[0]}, company_id:{r[2]}, {r[1][:40]}...")
                        
                except Exception as e:
                    print(f"\n⚠️ 检查表 {table_name} 时出错: {str(e)}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 连接远程数据库失败: {str(e)}")
    
    def analyze_sync_gap(self):
        """分析同步差距"""
        print("\n" + "="*60)
        print("🔍 同步差距分析")
        print("="*60)
        
        # 获取本地数据统计
        local_stats = self.get_local_stats()
        
        # 获取远程数据统计
        remote_stats = self.get_remote_stats()
        
        print(f"\n📊 artifact_id={self.artifact_id}的同步状态:")
        print(f"  本地总记录: {local_stats['total']}")
        print(f"  本地已推送: {local_stats['pushed']}")
        print(f"  本地未推送: {local_stats['unpushed']}")
        print(f"  远程记录数: {remote_stats['total']}")
        
        gap = local_stats['total'] - remote_stats['total']
        if gap > 0:
            print(f"\n⚠️ 发现同步差距: 本地比远程多 {gap} 条记录")
            if gap == 2:
                print("  🎯 这就是为什么只有2条数据被传输的原因!")
        elif gap < 0:
            print(f"\n⚠️ 异常: 远程比本地多 {-gap} 条记录")
        else:
            print(f"\n✅ 数据已完全同步")
    
    def get_local_stats(self):
        """获取本地统计"""
        stats = {'total': 0, 'pushed': 0, 'unpushed': 0}
        
        if os.path.exists(self.local_db_path):
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN pushed = 1 THEN 1 ELSE 0 END)
                FROM source_data 
                WHERE artifact_id = ?
            """, (self.artifact_id,))
            result = cursor.fetchone()
            
            stats['total'] = result[0] or 0
            stats['pushed'] = result[1] or 0
            stats['unpushed'] = stats['total'] - stats['pushed']
            
            conn.close()
        
        return stats
    
    def get_remote_stats(self):
        """获取远程统计"""
        stats = {'total': 0}
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            # 检查多个可能的表
            for table in ['research_results', 'external_search_results']:
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {table}
                        WHERE artifact_id = %s
                    """, (self.artifact_id,))
                    count = cursor.fetchone()[0]
                    stats['total'] = max(stats['total'], count)
                except:
                    pass
            
            conn.close()
            
        except:
            pass
        
        return stats
    
    def check_push_logic(self):
        """检查推送逻辑"""
        print("\n" + "="*60)
        print("🔧 推送逻辑检查")
        print("="*60)
        
        # 模拟推送逻辑
        print("\n测试推送逻辑:")
        
        try:
            from push_2_pg import RemoteDataPusher
            
            pusher = RemoteDataPusher(
                local_db_path=self.local_db_path,
                env_path=".env"
            )
            
            # 获取未推送记录
            unpushed = pusher.get_unpushed_records(limit=None)
            
            # 过滤目标artifact_id
            target_unpushed = [r for r in unpushed if r['artifact_id'] == self.artifact_id]
            
            print(f"\n1. get_unpushed_records() 返回:")
            print(f"   - 总未推送记录: {len(unpushed)}")
            print(f"   - artifact_id={self.artifact_id}的未推送记录: {len(target_unpushed)}")
            
            if target_unpushed:
                print(f"\n2. 目标记录详情:")
                for i, record in enumerate(target_unpushed[:5], 1):
                    print(f"   {i}. ID:{record['id']}, {record['name'][:40]}...")
            
            # 检查推送的目标表
            print(f"\n3. 推送目标表检查:")
            print(f"   - push_2_pg.py使用的表名: research_results")
            print(f"   - 实际应该使用的表名: external_search_results (根据master_flow.py)")
            print(f"\n⚠️ 这可能是问题的根源: 表名不匹配!")
            
        except Exception as e:
            print(f"❌ 检查推送逻辑失败: {str(e)}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="诊断MasterFlow步骤2.3数据同步问题")
    parser.add_argument("--artifact-id", type=int, default=35, help="要检查的artifact_id")
    parser.add_argument("--company-id", type=int, default=3, help="公司ID")
    parser.add_argument("--user-id", type=int, default=8, help="用户ID")
    
    args = parser.parse_args()
    
    diagnostics = DataSyncDiagnostics(
        artifact_id=args.artifact_id,
        company_id=args.company_id,
        user_id=args.user_id
    )
    
    diagnostics.diagnose_data_sync_issue()


if __name__ == "__main__":
    main()