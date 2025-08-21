#!/usr/bin/env python3
"""
数据迁移主入口脚本
提供命令行界面来执行数据迁移操作
"""

import sys
import os
from typing import Optional

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from .migration_service import MigrationService


def setup_logging(verbose: bool = False):
    """设置日志配置"""
    logger.remove()  # 移除默认处理器
    
    if verbose:
        logger.add(sys.stdout, level="DEBUG", 
                  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    else:
        logger.add(sys.stdout, level="INFO",
                  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def main():
    """主函数"""
    print("🚀 数据迁移工具")
    print("=" * 60)
    print("将 source_data.db 迁移到 PostgreSQL research_results 表")
    print("=" * 60)
    
    # 设置日志
    setup_logging(verbose=False)
    
    try:
        # 创建迁移服务 (使用默认外键值: 3, 3, 3)
        migration_service = MigrationService(
            source_db_path="../../research_data.db",
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
        
        if not all(prerequisites.values()):
            print("\n❌ 前置条件不满足，无法继续")
            missing = [k for k, v in prerequisites.items() if not v]
            print(f"缺失条件: {', '.join(missing)}")
            return False
        
        print("\n✅ 前置条件检查通过")
        
        # 显示菜单
        print("\n" + "=" * 60)
        print("选择操作:")
        print("1. 预览迁移 (查看前5条记录转换)")
        print("2. 试运行迁移 (验证但不写入)")
        print("3. 迁移少量数据 (10条记录)")
        print("4. 迁移所有数据")
        print("5. 仅测试数据映射转换")
        print("6. 查看远程数据库统计")
        print("0. 退出")
        
        while True:
            try:
                choice = input("\n请选择 (0-6): ").strip()
                
                if choice == "0":
                    print("👋 退出程序")
                    break
                
                elif choice == "1":
                    print("\n🔍 预览迁移数据...")
                    preview = migration_service.preview_migration(sample_size=5)
                    
                    if "error" in preview:
                        print(f"❌ 预览失败: {preview['error']}")
                        continue
                    
                    print(f"\n📊 预览结果:")
                    print(f"  源记录数: {preview['source_records_count']}")
                    print(f"  转换记录数: {preview['transformed_records_count']}")
                    
                    # 显示类型映射统计
                    mapping_stats = preview['mapping_statistics']
                    print(f"\n🔄 类型映射:")
                    for source_type, info in mapping_stats['reference_type_mapping'].items():
                        print(f"  • {source_type} → {info['mapped_to']}: {info['count']}条")
                    
                    # 显示样本转换
                    print(f"\n📋 转换示例:")
                    for i, sample in enumerate(preview['sample_transformations'][:3]):
                        print(f"  示例 {i+1}:")
                        print(f"    原始: {sample['source']['reference_type']} | 相关性:{sample['source']['related_assessment']} | 时间:{sample['source']['reading_time']}")
                        print(f"    转换: {sample['transformed']['reference_type']} | 相关性:{sample['transformed']['related_assessment']} | 时间:{sample['transformed']['reading_time']}分钟")
                    
                    # 显示验证结果
                    validation_results = preview['validation_results']
                    valid_count = sum(1 for r in validation_results if r['is_valid'])
                    print(f"\n✅ 验证结果: {valid_count}/{len(validation_results)} 条记录有效")
                    
                    for result in validation_results:
                        if not result['is_valid']:
                            print(f"  ❌ {result['name']}: {'; '.join(result['errors'])}")
                
                elif choice == "2":
                    print("\n🧪 试运行迁移...")
                    result = migration_service.execute_migration(dry_run=True)
                    
                    report = migration_service.get_migration_report(result)
                    print(report)
                
                elif choice == "3":
                    print("\n📦 迁移少量数据 (10条记录)...")
                    confirm = input("确认执行实际迁移? (y/N): ")
                    if confirm.lower() == 'y':
                        result = migration_service.execute_migration(limit=10, dry_run=False)
                        report = migration_service.get_migration_report(result)
                        print(report)
                    else:
                        print("❌ 用户取消操作")
                
                elif choice == "4":
                    print("\n📦 迁移所有数据...")
                    print("⚠️  这将迁移所有数据到远程数据库!")
                    confirm = input("确认执行完整迁移? (y/N): ")
                    if confirm.lower() == 'y':
                        result = migration_service.execute_migration(dry_run=False)
                        report = migration_service.get_migration_report(result)
                        print(report)
                    else:
                        print("❌ 用户取消操作")
                
                elif choice == "5":
                    print("\n🔄 测试数据映射转换...")
                    source_data = migration_service.load_source_data(limit=3)
                    transformed_data = migration_service.data_mapper.transform_batch(source_data)
                    
                    print(f"成功转换 {len(transformed_data)} 条记录")
                    for i, (source, transformed) in enumerate(zip(source_data, transformed_data)):
                        print(f"\n记录 {i+1}:")
                        print(f"  ID: {source.get('id')}")
                        print(f"  标题: {source.get('reference_title', '')[:50]}...")
                        print(f"  类型转换: {source.get('reference_type')} → {transformed['reference_type']}")
                        print(f"  相关性: {source.get('related_assessment')} → {transformed['related_assessment']}")
                        print(f"  文件大小: {source.get('file_size')} → {transformed['file_size']}字节")
                        print(f"  外键: company_id={transformed['company_id']}, artifact_id={transformed['artifact_id']}, created_by={transformed['created_by']}")
                
                elif choice == "6":
                    print("\n📊 查看远程数据库统计...")
                    try:
                        stats = migration_service.remote_writer.get_insert_statistics()
                        if "error" in stats:
                            print(f"❌ 获取统计失败: {stats['error']}")
                        else:
                            print(f"总记录数: {stats['total_records']}")
                            
                            print("\n类型分布:")
                            for item in stats['type_distribution']:
                                print(f"  • {item['reference_type']}: {item['count']}条")
                            
                            print("\n可信度分布:")
                            for item in stats['credibility_distribution']:
                                cred_name = {1: "低", 2: "中", 3: "高"}.get(item['credibility'], "未知")
                                print(f"  • {cred_name}({item['credibility']}): {item['count']}条")
                    except Exception as e:
                        print(f"❌ 查看统计失败: {str(e)}")
                
                else:
                    print("❌ 无效选择，请输入 0-6")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断程序")
                break
            except Exception as e:
                print(f"\n❌ 操作失败: {str(e)}")
                logger.error(f"操作失败: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 程序初始化失败: {str(e)}")
        logger.error(f"程序初始化失败: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)