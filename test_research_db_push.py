#!/usr/bin/env python3
"""
测试直接推送 research_data.db 到远程数据库
"""

import sys
import os
sys.path.insert(0, 'src')

from push_2_pg import RemoteDataPusher

def test_push_research_db():
    """测试推送 research_data.db"""
    print("="*60)
    print("测试推送 research_data.db 到远程数据库")
    print("="*60)
    
    # 创建推送器，使用 research_data.db
    pusher = RemoteDataPusher(
        local_db_path="research_data.db",
        env_path=".env"
    )
    
    # 设置正确的表名
    pusher.local_table_name = "research_results_local"
    
    # 测试连接
    print("\n1. 测试远程连接...")
    if not pusher.test_remote_connection():
        print("❌ 无法连接到远程数据库")
        return False
    
    # 获取待推送记录
    print("\n2. 获取待推送记录...")
    try:
        records = pusher.get_unpushed_records(limit=5)
        print(f"   找到 {len(records)} 条记录")
        
        if records:
            # 显示第一条记录的信息
            first = records[0]
            print(f"\n   示例记录:")
            print(f"   - ID: {first.get('id')}")
            print(f"   - Name: {first.get('name', 'N/A')[:50]}...")
            print(f"   - URL: {first.get('url', 'N/A')[:50]}...")
            print(f"   - Publisher: {first.get('publisher', 'N/A')}")
            print(f"   - Reference Type: {first.get('reference_type', 'N/A')}")
            print(f"   - Artifact ID: {first.get('artifact_id')}")
            print(f"   - Created By: {first.get('created_by')}")
    except Exception as e:
        print(f"❌ 获取记录失败: {str(e)}")
        return False
    
    print("\n✅ 测试通过！可以推送 research_data.db")
    return True

if __name__ == "__main__":
    test_push_research_db()