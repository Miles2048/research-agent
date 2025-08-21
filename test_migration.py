#!/usr/bin/env python3
"""
数据迁移测试脚本
"""

import sys
import os
sys.path.append('src')

from src.data_migration.data_mapper import DataMapper
from src.data_migration.remote_writer import RemoteWriter
from src.data_migration.migration_service import MigrationService


def main():
    print("🚀 数据迁移测试工具")
    print("=" * 60)
    
    try:
        # 创建迁移服务
        migration_service = MigrationService(
            source_db_path="../source_data.db",  # 指向项目根目录
            company_id=3,
            artifact_id=3,
            created_by=3
        )
        
        # 检查前置条件
        print("🔍 检查前置条件...")
        prerequisites = migration_service.check_prerequisites()
        
        print("前置条件检查结果:")
        for condition, status in prerequisites.items():
            status_icon = "✅" if status else "❌"
            condition_name = {
                "source_db_exists": "源数据库文件",
                "postgres_connection": "PostgreSQL连接",
                "target_table_exists": "目标表存在"
            }.get(condition, condition)
            print(f"  {status_icon} {condition_name}")
        
        if not prerequisites["source_db_exists"]:
            print("❌ 源数据库文件不存在")
            return
        
        if not prerequisites["postgres_connection"]:
            print("⚠️ PostgreSQL连接失败，仅测试数据映射功能")
            
            # 仅测试数据映射
            print("\n🔄 测试数据映射转换...")
            source_data = migration_service.load_source_data(limit=3)
            print(f"成功加载 {len(source_data)} 条源数据")
            
            # 显示源数据示例
            for i, record in enumerate(source_data[:2]):
                print(f"\n📋 源数据记录 {i+1}:")
                print(f"  ID: {record.get('id')}")
                print(f"  标题: {record.get('reference_title', '')[:50]}...")
                print(f"  类型: {record.get('reference_type')}")
                print(f"  相关性: {record.get('related_assessment')}")
                print(f"  阅读时间: {record.get('reading_time')}")
                print(f"  文件大小: {record.get('file_size')}")
            
            # 测试映射转换
            transformed_data = migration_service.data_mapper.transform_batch(source_data)
            print(f"\n✅ 成功转换 {len(transformed_data)} 条记录")
            
            for i, transformed in enumerate(transformed_data[:2]):
                print(f"\n🔄 转换后记录 {i+1}:")
                print(f"  company_id: {transformed['company_id']}")
                print(f"  artifact_id: {transformed['artifact_id']}")
                print(f"  created_by: {transformed['created_by']}")
                print(f"  name: {transformed['name'][:50]}...")
                print(f"  reference_type: {transformed['reference_type']}")
                print(f"  related_assessment: {transformed['related_assessment']}")
                print(f"  reading_time: {transformed['reading_time']}分钟")
                print(f"  file_size: {transformed['file_size']}字节")
            
            # 获取映射统计
            stats = migration_service.data_mapper.get_mapping_statistics(source_data)
            print(f"\n📊 映射统计:")
            print(f"  总记录数: {stats['total_records']}")
            
            print(f"\n🔄 类型映射:")
            for source_type, info in stats['reference_type_mapping'].items():
                print(f"  • {source_type} → {info['mapped_to']}: {info['count']}条")
            
            return
        
        # 如果所有条件都满足，执行预览
        if all(prerequisites.values()):
            print("\n✅ 前置条件检查通过")
            print("\n🔍 预览迁移数据...")
            
            preview = migration_service.preview_migration(sample_size=3)
            
            print(f"\n📊 预览结果:")
            print(f"  源记录数: {preview['source_records_count']}")
            print(f"  转换记录数: {preview['transformed_records_count']}")
            
            # 显示样本转换
            print(f"\n📋 转换示例:")
            for i, sample in enumerate(preview['sample_transformations']):
                print(f"  示例 {i+1}:")
                print(f"    原始: {sample['source']['reference_type']} | 相关性:{sample['source']['related_assessment']} | 时间:{sample['source']['reading_time']}")
                print(f"    转换: {sample['transformed']['reference_type']} | 相关性:{sample['transformed']['related_assessment']} | 时间:{sample['transformed']['reading_time']}分钟")
                print(f"    外键: company_id={sample['transformed']['company_id']}, artifact_id={sample['transformed']['artifact_id']}, created_by={sample['transformed']['created_by']}")
            
            # 验证结果
            validation_results = preview['validation_results']
            valid_count = sum(1 for r in validation_results if r['is_valid'])
            print(f"\n✅ 验证结果: {valid_count}/{len(validation_results)} 条记录有效")
            
            print("\n🎯 功能测试完成!")
            print("✅ 数据映射转换正常")
            print("✅ PostgreSQL连接正常") 
            print("✅ 数据验证正常")
            print("\n💡 可以执行实际迁移操作")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()