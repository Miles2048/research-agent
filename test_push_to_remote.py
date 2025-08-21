#!/usr/bin/env python3
"""
测试推送到远程数据库功能
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from push_to_remote_db import RemoteDataPusher


def test_push():
    """测试推送功能"""
    print("="*60)
    print("🧪 测试推送到远程数据库")
    print("="*60)
    
    # 创建推送器实例
    pusher = RemoteDataPusher(
        local_db_path="local_source_data.db",
        env_path=".env"
    )
    
    # 1. 测试连接
    print("\n1️⃣ 测试远程数据库连接:")
    if not pusher.test_remote_connection():
        print("❌ 无法连接到远程数据库，请检查配置")
        return
    
    # 2. 显示同步状态
    print("\n2️⃣ 当前同步状态:")
    status = pusher.get_sync_status()
    print(f"   总记录数: {status['total_records']}")
    print(f"   已推送: {status['pushed_records']}")
    print(f"   未推送: {status['unpushed_records']}")
    print(f"   同步进度: {status['sync_percentage']}%")
    
    # 3. 如果有未推送的记录，询问是否推送
    if status['unpushed_records'] > 0:
        print(f"\n3️⃣ 发现 {status['unpushed_records']} 条未推送记录")
        response = input("是否推送到远程数据库? (y/n): ")
        
        if response.lower() == 'y':
            # 先推送少量测试
            print("\n先推送5条记录进行测试...")
            test_records = pusher.get_unpushed_records(limit=5)
            success, failed = pusher.push_records_to_remote(test_records)
            
            if success > 0:
                print(f"\n✅ 测试推送成功！")
                print(f"   成功: {success} 条")
                print(f"   失败: {failed} 条")
                
                # 显示更新后的状态
                new_status = pusher.get_sync_status()
                print(f"\n更新后的同步状态:")
                print(f"   已推送: {new_status['pushed_records']}")
                print(f"   未推送: {new_status['unpushed_records']}")
                print(f"   同步进度: {new_status['sync_percentage']}%")
                
                if new_status['unpushed_records'] > 0:
                    response2 = input(f"\n是否推送剩余的 {new_status['unpushed_records']} 条记录? (y/n): ")
                    if response2.lower() == 'y':
                        pusher.push_all(batch_size=100)
            else:
                print("\n❌ 测试推送失败，请检查错误信息")
    else:
        print("\n✅ 所有记录已同步，无需推送")


if __name__ == "__main__":
    test_push()