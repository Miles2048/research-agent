#!/usr/bin/env python3
"""
测试本地源数据生成功能
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from generate_local_source_data import LocalSourceDataGenerator


def test_generate():
    """测试生成本地源数据"""
    print("="*60)
    print("🧪 测试本地源数据生成")
    print("="*60)
    
    # 创建生成器实例
    generator = LocalSourceDataGenerator(db_path="test_local_source_data.db")
    
    try:
        # 生成数据
        generator.generate(
            results_dir="results",
            request_json_path="src/request.json"
        )
        
        # 显示统计信息
        stats = generator.get_statistics()
        print("\n📊 生成结果统计:")
        print(f"   总记录数: {stats['total_records']}")
        print(f"   未推送记录: {stats['unpushed_records']}")
        print(f"   已推送记录: {stats['pushed_records']}")
        
        if stats['type_distribution']:
            print("\n   类型分布:")
            for ref_type, count in stats['type_distribution'].items():
                print(f"     {ref_type}: {count}")
        
        if stats['credibility_distribution']:
            print("\n   可信度分布:")
            for cred, count in stats['credibility_distribution'].items():
                print(f"     Level {cred}: {count}")
        
        print("\n✅ 测试完成！数据库文件: test_local_source_data.db")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_generate()