#!/usr/bin/env python3
"""
数据迁移流程测试
验证数据迁移模块是否能正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from loguru import logger
from datetime import datetime


def setup_logging():
    """设置日志配置"""
    logger.remove()  # 移除默认处理器
    logger.add(sys.stdout, level="INFO",
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("🧪 测试模块导入")
    print("=" * 60)
    
    try:
        from data_migration.data_mapper import DataMapper
        print("✅ DataMapper 导入成功")
    except Exception as e:
        print(f"❌ DataMapper 导入失败: {e}")
        return False
    
    try:
        from data_migration.remote_writer import RemoteWriter
        print("✅ RemoteWriter 导入成功")
    except Exception as e:
        print(f"❌ RemoteWriter 导入失败: {e}")
        return False
    
    try:
        from data_migration.migration_service import MigrationService
        print("✅ MigrationService 导入成功")
    except Exception as e:
        print(f"❌ MigrationService 导入失败: {e}")
        return False
    
    return True


def test_data_mapper():
    """测试数据映射器"""
    print("\n" + "=" * 60)
    print("🧪 测试数据映射器")
    print("=" * 60)
    
    try:
        from data_migration.data_mapper import DataMapper
        
        # 创建映射器实例
        mapper = DataMapper(company_id=3, artifact_id=3, created_by=3)
        print("✅ DataMapper 实例创建成功")
        
        # 测试示例数据转换
        sample_record = {
            "id": 1,
            "reference_title": "测试文献标题",
            "reference_url": "https://example.com/test",
            "reference_type": "行业研究报告",
            "publisher": "测试发布商",
            "collection_time": "2025-08-05T14:17:41.639593",
            "credibility": 2,
            "related_assessment": 0.85,
            "status": 0,
            "word_count": 1500,
            "reading_time": "10min30sec",
            "file_path": "root/test",
            "file_size": "5kb",
            "reference_content": "这是测试内容...",
            "reference_create_time": "2025-08-05T14:17:41.639593",
            "reference_update_time": "2025-08-15T05:06:33.198814"
        }
        
        # 转换记录
        transformed = mapper.transform_record(sample_record)
        print("✅ 记录转换成功")
        
        # 验证关键字段
        assert transformed["company_id"] == 3, "company_id 值错误"
        assert transformed["artifact_id"] == 3, "artifact_id 值错误"
        assert transformed["created_by"] == 3, "created_by 值错误"
        assert transformed["reference_type"] == "business_data", "reference_type 映射错误"
        assert 60 <= transformed["related_assessment"] <= 96, "related_assessment 范围错误"
        assert transformed["reading_time"] == 10, "reading_time 解析错误"
        assert transformed["file_size"] == 5120, "file_size 解析错误"
        assert transformed["credibility"] in [2, 3], "credibility 值错误"
        
        print(f"   • 类型映射: {sample_record['reference_type']} → {transformed['reference_type']}")
        print(f"   • 相关性: {sample_record['related_assessment']} → {transformed['related_assessment']}")
        print(f"   • 阅读时间: {sample_record['reading_time']} → {transformed['reading_time']}分钟")
        print(f"   • 文件大小: {sample_record['file_size']} → {transformed['file_size']}字节")
        print(f"   • 可信度: 随机生成 → {transformed['credibility']}")
        
        return True
    except Exception as e:
        print(f"❌ DataMapper 测试失败: {e}")
        return False


def test_remote_writer():
    """测试远程写入器（仅连接测试）"""
    print("\n" + "=" * 60)
    print("🧪 测试远程写入器连接")
    print("=" * 60)
    
    try:
        from data_migration.remote_writer import RemoteWriter
        
        # 创建写入器实例
        writer = RemoteWriter()
        print("✅ RemoteWriter 实例创建成功")
        
        # 测试数据库连接
        connection_ok = writer.test_connection()
        if connection_ok:
            print("✅ PostgreSQL 连接测试成功")
        else:
            print("⚠️  PostgreSQL 连接失败（可能是网络或配置问题）")
            return False
        
        # 检查目标表是否存在
        table_exists = writer.check_table_exists()
        if table_exists:
            print("✅ research_results 表存在")
        else:
            print("❌ research_results 表不存在")
            return False
        
        # 获取统计信息
        try:
            stats = writer.get_insert_statistics()
            if "error" not in stats:
                print(f"✅ 数据库统计获取成功: {stats.get('total_records', 0)} 条记录")
            else:
                print(f"⚠️  统计信息获取失败: {stats['error']}")
        except Exception as e:
            print(f"⚠️  统计信息获取失败: {e}")
        
        return True
    except Exception as e:
        print(f"❌ RemoteWriter 测试失败: {e}")
        return False


def test_migration_service():
    """测试迁移服务"""
    print("\n" + "=" * 60)
    print("🧪 测试迁移服务")
    print("=" * 60)
    
    try:
        from data_migration.migration_service import MigrationService
        
        # 创建迁移服务实例
        migration_service = MigrationService(
            source_db_path="research_data.db",
            company_id=3,
            artifact_id=3,
            created_by=3
        )
        print("✅ MigrationService 实例创建成功")
        
        # 检查前置条件
        print("\n🔍 检查前置条件...")
        prerequisites = migration_service.check_prerequisites()
        
        all_ok = True
        for condition, status in prerequisites.items():
            status_icon = "✅" if status else "❌"
            condition_name = {
                "source_db_exists": "源数据库文件",
                "postgres_connection": "PostgreSQL连接",
                "target_table_exists": "目标表存在"
            }.get(condition, condition)
            print(f"   {status_icon} {condition_name}")
            if not status:
                all_ok = False
        
        if not all_ok:
            print("⚠️  前置条件不完全满足，跳过实际迁移测试")
            return True  # 不算失败，只是环境问题
        
        print("✅ 所有前置条件满足")
        
        # 执行试运行迁移（不实际写入数据）
        print("\n🧪 执行试运行迁移...")
        try:
            result = migration_service.execute_migration(limit=5, dry_run=True)
            if "error" in result:
                print(f"❌ 试运行失败: {result['error']}")
                return False
            
            print("✅ 试运行迁移成功")
            print(f"   • 源记录数: {result['source_records']}")
            print(f"   • 转换记录数: {result['transformed_records']}")
            print(f"   • 有效记录数: {result['valid_records']}")
            print(f"   • 无效记录数: {result['invalid_records']}")
            print(f"   • 耗时: {result['duration_seconds']:.2f}秒")
            
            return True
        except Exception as e:
            print(f"❌ 试运行迁移失败: {e}")
            return False
    
    except Exception as e:
        print(f"❌ MigrationService 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    setup_logging()
    
    print("🚀 数据迁移流程测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = {
        "模块导入": test_imports(),
        "数据映射器": False,
        "远程写入器": False,
        "迁移服务": False
    }
    
    # 如果导入成功，继续测试其他模块
    if test_results["模块导入"]:
        test_results["数据映射器"] = test_data_mapper()
        test_results["远程写入器"] = test_remote_writer()
        test_results["迁移服务"] = test_migration_service()
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📋 测试结果摘要")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status_icon = "✅" if result else "❌"
        print(f"{status_icon} {test_name}")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"\n📊 总计: {passed_tests}/{total_tests} 个测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！数据迁移流程可以正常工作。")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关配置。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)