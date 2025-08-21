#!/usr/bin/env python3
"""
自动化数据同步示例
演示如何使用 quick_sync 函数
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from auto_sync_data import quick_sync, AutoDataSync

def example1_incremental_sync():
    """示例1: 增量同步（默认行为，不清理旧数据）"""
    print("\n🔄 示例1: 增量同步（保留现有数据）")
    print("-" * 40)
    
    # 默认不清理，直接增量更新
    result = quick_sync()
    
    print(f"✅ 本地生成: {result.get('local_generated', 0)} 条")
    print(f"☁️  远程推送: {result.get('remote_pushed', 0)} 条")
    

def example2_clean_sync():
    """示例2: 清理后重新同步"""
    print("\n🗑️  示例2: 清理后重新同步")
    print("-" * 40)
    
    # 明确指定 clean_start=True 才会清理
    result = quick_sync(clean_start=True)
    
    print(f"✅ 本地生成: {result.get('local_generated', 0)} 条")
    print(f"☁️  远程推送: {result.get('remote_pushed', 0)} 条")


def example3_local_only():
    """示例3: 只生成本地数据，不推送"""
    print("\n💾 示例3: 只生成本地数据")
    print("-" * 40)
    
    # 只生成本地，不推送到远程
    result = quick_sync(push_to_remote=False)
    
    print(f"✅ 本地生成: {result.get('local_generated', 0)} 条")
    print("⏭️  跳过远程推送")


def example4_custom_sync():
    """示例4: 使用自定义配置"""
    print("\n⚙️  示例4: 自定义配置同步")
    print("-" * 40)
    
    # 创建自定义同步器
    syncer = AutoDataSync(
        local_db_path="custom_local.db",
        results_dir="results",
        request_json_path="src/request.json",
        clean_start=False  # 不清理
    )
    
    # 查看状态
    status = syncer.check_status()
    print(f"📊 当前状态:")
    print(f"   本地记录: {status.get('local_records', 0)}")
    print(f"   已推送: {status.get('pushed_records', 0)}")
    print(f"   未推送: {status.get('unpushed_records', 0)}")
    
    # 执行同步
    result = syncer.run(push_to_remote=True, batch_size=50)
    
    print(f"\n✅ 执行结果:")
    print(f"   本地生成: {result.get('local_generated', 0)} 条")
    print(f"   远程推送: {result.get('remote_pushed', 0)} 条")


def main():
    """主函数"""
    print("="*60)
    print("🚀 自动化数据同步示例")
    print("="*60)
    
    # 运行示例1 - 增量同步（默认）
    example1_incremental_sync()
    
    # 其他示例可以根据需要取消注释
    # example2_clean_sync()  # 清理重建
    # example3_local_only()  # 只本地
    # example4_custom_sync() # 自定义


if __name__ == "__main__":
    main()