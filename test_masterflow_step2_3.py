#!/usr/bin/env python3
"""
自动化测试脚本 - MasterFlow步骤2.3数据同步
用于诊断为什么只有2条数据被传输到PostgreSQL的问题
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


class MasterFlowStep23Tester:
    """MasterFlow步骤2.3测试器"""
    
    def __init__(self):
        self.local_db_path = "local_source_data.db"
        self.results_dir = "results"
        self.request_json_path = "src/request.json"
        
        # PostgreSQL配置
        self.pg_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')) if os.getenv('DB_PORT') else None,
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        print("="*80)
        print("🔍 MasterFlow步骤2.3数据同步诊断工具")
        print("="*80)
    
    def run_full_diagnosis(self):
        """运行完整诊断"""
        print("\n📋 开始诊断流程...")
        
        # 1. 检查配置
        self.check_configuration()
        
        # 2. 检查本地数据库
        self.check_local_database()
        
        # 3. 检查远程数据库连接
        self.check_remote_connection()
        
        # 4. 分析数据过滤问题
        self.analyze_data_filtering()
        
        # 5. 测试实际同步
        self.test_sync_process()
        
        # 6. 生成诊断报告
        self.generate_diagnosis_report()
    
    def check_configuration(self):
        """检查配置"""
        print("\n1️⃣ 检查配置文件...")
        
        # 检查request.json
        if os.path.exists(self.request_json_path):
            with open(self.request_json_path, 'r', encoding='utf-8') as f:
                request_data = json.load(f)
            
            print(f"✅ request.json存在")
            print(f"   - artifact_id: {request_data.get('artifact_id')}")
            print(f"   - company_id: {request_data.get('company', {}).get('company_id')}")
            print(f"   - user_id: {request_data.get('user_id')}")
        else:
            print(f"❌ request.json不存在: {self.request_json_path}")
        
        # 检查环境变量
        print(f"\n   PostgreSQL配置:")
        for key, value in self.pg_config.items():
            status = "✅" if value else "❌"
            display_value = value if key != 'password' else '***'
            print(f"   {status} {key}: {display_value}")
    
    def check_local_database(self):
        """检查本地数据库"""
        print("\n2️⃣ 检查本地数据库...")
        
        if not os.path.exists(self.local_db_path):
            print(f"❌ 本地数据库不存在: {self.local_db_path}")
            return
        
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"✅ 数据库表: {[t[0] for t in tables]}")
            
            # 统计总记录数
            cursor.execute("SELECT COUNT(*) FROM source_data")
            total_count = cursor.fetchone()[0]
            print(f"📊 总记录数: {total_count}")
            
            # 统计未推送记录
            cursor.execute("SELECT COUNT(*) FROM source_data WHERE pushed = 0")
            unpushed_count = cursor.fetchone()[0]
            print(f"📊 未推送记录: {unpushed_count}")
            
            # 统计已推送记录
            cursor.execute("SELECT COUNT(*) FROM source_data WHERE pushed = 1")
            pushed_count = cursor.fetchone()[0]
            print(f"📊 已推送记录: {pushed_count}")
            
            # 按artifact_id分组统计
            cursor.execute("""
                SELECT artifact_id, COUNT(*) as count 
                FROM source_data 
                GROUP BY artifact_id
                ORDER BY artifact_id
            """)
            artifact_stats = cursor.fetchall()
            print(f"\n📊 按artifact_id分组统计:")
            for artifact_id, count in artifact_stats:
                cursor.execute("""
                    SELECT COUNT(*) FROM source_data 
                    WHERE artifact_id = ? AND pushed = 0
                """, (artifact_id,))
                unpushed = cursor.fetchone()[0]
                print(f"   - artifact_id {artifact_id}: {count}条 (未推送: {unpushed})")
            
            # 检查特定的artifact_id=35
            cursor.execute("""
                SELECT COUNT(*) FROM source_data WHERE artifact_id = 35
            """)
            artifact_35_count = cursor.fetchone()[0]
            print(f"\n🔍 artifact_id=35的记录数: {artifact_35_count}")
            
            # 显示前5条记录的详情
            cursor.execute("""
                SELECT id, name, artifact_id, company_id, pushed, created_at 
                FROM source_data 
                ORDER BY id DESC 
                LIMIT 5
            """)
            recent_records = cursor.fetchall()
            print(f"\n📋 最新5条记录:")
            for record in recent_records:
                print(f"   - ID:{record[0]}, 名称:{record[1][:30]}..., "
                      f"artifact_id:{record[2]}, company_id:{record[3]}, "
                      f"pushed:{record[4]}, 时间:{record[5]}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 检查本地数据库失败: {str(e)}")
    
    def check_remote_connection(self):
        """检查远程数据库连接"""
        print("\n3️⃣ 检查远程数据库连接...")
        
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()
            
            # 检查版本
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ 连接成功 - PostgreSQL版本: {version[0][:50]}...")
            
            # 检查表是否存在
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('research_results', 'external_search_results')
            """)
            tables = cursor.fetchall()
            print(f"📊 远程表: {[t[0] for t in tables]}")
            
            # 统计远程数据
            for table_name in ['research_results', 'external_search_results']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"   - {table_name}: {count}条记录")
                    
                    # 按artifact_id统计
                    cursor.execute(f"""
                        SELECT artifact_id, COUNT(*) 
                        FROM {table_name} 
                        GROUP BY artifact_id 
                        ORDER BY artifact_id
                    """)
                    artifact_stats = cursor.fetchall()
                    if artifact_stats:
                        print(f"     按artifact_id分组:")
                        for aid, cnt in artifact_stats[:5]:  # 只显示前5个
                            print(f"       artifact_id {aid}: {cnt}条")
                except:
                    print(f"   - {table_name}: 表不存在或无法访问")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 远程数据库连接失败: {str(e)}")
    
    def analyze_data_filtering(self):
        """分析数据过滤问题"""
        print("\n4️⃣ 分析数据过滤逻辑...")
        
        # 读取request.json获取当前配置
        try:
            with open(self.request_json_path, 'r', encoding='utf-8') as f:
                request_data = json.load(f)
            
            current_artifact_id = request_data.get('artifact_id')
            current_company_id = request_data.get('company', {}).get('company_id')
            current_user_id = request_data.get('user_id')
            
            print(f"📋 当前配置:")
            print(f"   - artifact_id: {current_artifact_id}")
            print(f"   - company_id: {current_company_id}")
            print(f"   - user_id: {current_user_id}")
            
            # 分析本地数据库中匹配当前配置的记录
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # 查询匹配的未推送记录
            cursor.execute("""
                SELECT COUNT(*) FROM source_data 
                WHERE artifact_id = ? AND company_id = ? AND pushed = 0
            """, (current_artifact_id, int(current_company_id)))
            matching_unpushed = cursor.fetchone()[0]
            
            print(f"\n🔍 匹配当前配置的未推送记录: {matching_unpushed}条")
            
            # 如果记录数很少，查看具体是哪些
            if matching_unpushed <= 10:
                cursor.execute("""
                    SELECT id, name, url, created_at 
                    FROM source_data 
                    WHERE artifact_id = ? AND company_id = ? AND pushed = 0
                    LIMIT 10
                """, (current_artifact_id, int(current_company_id)))
                records = cursor.fetchall()
                print(f"\n📋 具体记录:")
                for r in records:
                    print(f"   - ID:{r[0]}, 名称:{r[1][:40]}...")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 分析数据过滤失败: {str(e)}")
    
    def test_sync_process(self):
        """测试实际同步过程"""
        print("\n5️⃣ 测试同步过程...")
        
        try:
            # 导入同步模块
            from auto_sync_data import AutoDataSync
            
            # 创建同步器（不清理数据）
            syncer = AutoDataSync(
                local_db_path=self.local_db_path,
                results_dir=self.results_dir,
                request_json_path=self.request_json_path,
                env_path=".env",
                clean_start=False  # 不清理数据
            )
            
            # 只测试推送过程
            print("\n🔄 测试推送过程...")
            
            # 获取推送前状态
            from push_2_pg import RemoteDataPusher
            pusher = RemoteDataPusher(
                local_db_path=self.local_db_path,
                env_path=".env"
            )
            
            # 获取未推送记录
            unpushed_records = pusher.get_unpushed_records(limit=10)
            print(f"📊 发现{len(unpushed_records)}条未推送记录（限制10条）")
            
            if unpushed_records:
                print("\n📋 未推送记录示例:")
                for i, record in enumerate(unpushed_records[:3]):
                    print(f"   {i+1}. artifact_id:{record['artifact_id']}, "
                          f"company_id:{record['company_id']}, "
                          f"名称:{record['name'][:30]}...")
            
            # 测试推送一小批
            if unpushed_records:
                print("\n🚀 测试推送前3条记录...")
                test_records = unpushed_records[:3]
                success, failed = pusher.push_records_to_remote(test_records)
                print(f"✅ 推送结果: 成功{success}条, 失败{failed}条")
            
        except Exception as e:
            print(f"❌ 测试同步过程失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def generate_diagnosis_report(self):
        """生成诊断报告"""
        print("\n" + "="*80)
        print("📊 诊断报告总结")
        print("="*80)
        
        # 重新检查获取最新状态
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM source_data WHERE pushed = 0")
        unpushed_total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT artifact_id, COUNT(*) 
            FROM source_data 
            WHERE pushed = 0 
            GROUP BY artifact_id
        """)
        unpushed_by_artifact = cursor.fetchall()
        
        conn.close()
        
        print(f"\n🔍 问题诊断:")
        print(f"1. 本地数据库中有 {unpushed_total} 条未推送记录")
        print(f"2. 未推送记录按artifact_id分布:")
        for aid, count in unpushed_by_artifact:
            print(f"   - artifact_id {aid}: {count}条")
        
        print(f"\n💡 可能的原因:")
        print(f"1. request.json中的artifact_id与数据库中的不匹配")
        print(f"2. 之前的同步已经推送了大部分数据")
        print(f"3. 数据生成时使用了不同的artifact_id")
        print(f"4. 推送过程中有过滤条件限制")
        
        print(f"\n🔧 建议解决方案:")
        print(f"1. 确保request.json中的artifact_id与要推送的数据一致")
        print(f"2. 如果需要推送特定artifact_id的数据，可以修改推送逻辑")
        print(f"3. 检查是否需要重新生成数据（使用clean_start=True）")
        print(f"4. 确认远程数据库表结构是否正确")


def main():
    """主函数"""
    tester = MasterFlowStep23Tester()
    tester.run_full_diagnosis()


if __name__ == "__main__":
    main()