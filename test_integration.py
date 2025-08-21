#!/usr/bin/env python3
"""
测试集成效果 - 仅测试自动化数据同步步骤
"""

import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'master_flow'))

async def test_auto_data_sync():
    """测试自动化数据同步步骤"""
    
    # 从master_flow导入新的自动化数据同步函数
    from master_flow import step2_3_auto_data_sync
    
    # 使用测试参数
    test_artifact_id = 12
    test_company_id = 4
    test_user_id = 4
    
    print("🧪 测试自动化数据同步集成")
    print("="*60)
    print(f"测试参数: artifact_id={test_artifact_id}, company_id={test_company_id}, user_id={test_user_id}")
    print("="*60)
    
    # 确保有测试数据（results目录）
    results_dir = "results"
    if not os.path.exists(results_dir):
        print(f"❌ 测试失败: {results_dir} 目录不存在")
        return
    
    # 检查topic目录
    topic_dirs = [d for d in os.listdir(results_dir) if d.startswith("topic_")]
    if not topic_dirs:
        print(f"❌ 测试失败: {results_dir} 中没有topic_*目录")
        return
    
    print(f"✅ 发现测试数据: {topic_dirs}")
    
    # 执行自动化数据同步
    try:
        success = await step2_3_auto_data_sync(
            artifact_id=test_artifact_id, 
            company_id=test_company_id, 
            user_id=test_user_id
        )
        
        if success:
            print("\n✅ 自动化数据同步集成测试成功！")
        else:
            print("\n⚠️ 自动化数据同步集成测试完成，但可能有问题")
            
    except Exception as e:
        print(f"\n❌ 自动化数据同步集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_auto_data_sync())