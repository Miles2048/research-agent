#!/usr/bin/env python3
"""
测试新的本地数据库表结构
验证 research_results_local 表的创建、插入和查询功能
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.search_agent.tools.database import DatabaseManager, map_source_to_research_record

def test_database_creation():
    """测试数据库表创建"""
    print("🔧 测试1: 数据库表创建")
    print("-" * 50)
    
    # 初始化数据库管理器
    db_manager = DatabaseManager("test_research_data.db")
    
    # 创建表
    success = db_manager.create_tables()
    if success:
        print("✅ 数据库表创建成功")
        
        # 检查表是否存在
        exists = db_manager.table_exists("research_results_local")
        if exists:
            print("✅ research_results_local 表已创建")
        else:
            print("❌ research_results_local 表未找到")
            return False
    else:
        print("❌ 数据库表创建失败")
        return False
    
    return True

def test_data_insertion():
    """测试数据插入功能"""
    print("\n📝 测试2: 数据插入功能")
    print("-" * 50)
    
    db_manager = DatabaseManager("test_research_data.db")
    
    # 准备测试数据
    test_data = {
        "company_id": 3,
        "artifact_id": 1,
        "created_by": 3,
        "name": "测试研究文献标题",
        "url": "https://example.com/test-research",
        "reference_type": "business_data",
        "publisher": "测试发布商",
        "raw_content": "这是一个测试的研究内容，包含了详细的分析和数据。",
        "credibility": 2,
        "related_assessment": 85,
        "status": 1,
        "word_count": 50,
        "reading_time": 3,
        "file_size": 1024,
        "file_path": "root/test",
        "collection_time": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "deleted_at": None,
        "pushed": 0
    }
    
    # 插入数据
    success = db_manager.insert_research_result(test_data)
    if success:
        print("✅ 单条数据插入成功")
    else:
        print("❌ 单条数据插入失败")
        return False
    
    # 批量插入测试
    batch_data = []
    for i in range(3):
        data = test_data.copy()
        data["name"] = f"批量测试文献 {i+1}"
        data["url"] = f"https://example.com/batch-test-{i+1}"
        batch_data.append(data)
    
    inserted_count = db_manager.insert_research_results_batch(batch_data)
    if inserted_count == 3:
        print("✅ 批量数据插入成功")
    else:
        print(f"⚠️ 批量数据插入部分成功: {inserted_count}/3")
    
    return True

def test_data_querying():
    """测试数据查询功能"""
    print("\n🔍 测试3: 数据查询功能")
    print("-" * 50)
    
    db_manager = DatabaseManager("test_research_data.db")
    
    # 测试按URL查询
    result = db_manager.get_research_result_by_url("https://example.com/test-research")
    if result:
        print("✅ 按URL查询成功")
        print(f"   找到记录: {result['name']}")
    else:
        print("❌ 按URL查询失败")
    
    # 测试按名称查询
    results = db_manager.get_research_results_by_name("测试", exact_match=False)
    if results:
        print(f"✅ 按名称模糊查询成功，找到 {len(results)} 条记录")
    else:
        print("❌ 按名称查询失败")
    
    # 测试获取所有记录
    all_results = db_manager.get_all_research_results(limit=10)
    if all_results:
        print(f"✅ 获取所有记录成功，共 {len(all_results)} 条")
    else:
        print("❌ 获取所有记录失败")
    
    return True

def test_sync_status_management():
    """测试同步状态管理"""
    print("\n🔄 测试4: 同步状态管理")
    print("-" * 50)
    
    db_manager = DatabaseManager("test_research_data.db")
    
    # 获取未推送记录
    unpushed_records = db_manager.get_unpushed_records(limit=5)
    if unpushed_records:
        print(f"✅ 获取未推送记录成功，共 {len(unpushed_records)} 条")
        
        # 测试更新推送状态
        if unpushed_records:
            record_id = unpushed_records[0]['id']
            success = db_manager.update_pushed_status(record_id, 1)
            if success:
                print("✅ 更新推送状态成功")
            else:
                print("❌ 更新推送状态失败")
    else:
        print("⚠️ 没有找到未推送记录")
    
    # 获取同步统计
    stats = db_manager.get_sync_statistics()
    print("📊 同步统计信息:")
    print(f"   总记录数: {stats['total_records']}")
    print(f"   已推送: {stats['pushed_records']}")
    print(f"   未推送: {stats['unpushed_records']}")
    print(f"   同步进度: {stats['sync_progress']}%")
    
    return True

def test_source_mapping():
    """测试源数据映射功能"""
    print("\n🔄 测试5: 源数据映射功能")
    print("-" * 50)
    
    # 模拟从搜索结果获取的源数据
    source_data = {
        "title": "AI技术在医疗领域的应用研究",
        "url": "https://example.com/ai-medical-research",
        "content": "人工智能技术在医疗诊断、药物发现和个性化治疗方面展现出巨大潜力...",
        "full_text": "详细的研究内容，包括AI算法、数据集、实验结果等完整信息...",
        "publisher": "医疗AI研究院",
        "reference_type": "学术研究",
        "credibility": 3,
        "related_assessment": 0.92,
        "word_count": 5000
    }
    
    # 映射为新的数据库记录格式
    try:
        mapped_record = map_source_to_research_record(
            source_data, 
            company_id=3, 
            artifact_id=1, 
            created_by=3
        )
        print("✅ 源数据映射成功")
        print(f"   原始类型: {source_data['reference_type']} -> {mapped_record['reference_type']}")
        print(f"   相关性评估: {source_data['related_assessment']} -> {mapped_record['related_assessment']}")
        print(f"   推送状态: {mapped_record['pushed']}")
        
        # 尝试插入映射后的数据
        db_manager = DatabaseManager("test_research_data.db")
        success = db_manager.insert_research_result(mapped_record)
        if success:
            print("✅ 映射数据插入成功")
        else:
            print("❌ 映射数据插入失败")
            
    except Exception as e:
        print(f"❌ 源数据映射失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🧪 新数据库结构测试")
    print("=" * 60)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("数据库表创建", test_database_creation),
        ("数据插入功能", test_data_insertion),
        ("数据查询功能", test_data_querying),
        ("同步状态管理", test_sync_status_management),
        ("源数据映射", test_source_mapping)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试出错: {e}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(test_results)} 个测试通过")
    
    if passed == len(test_results):
        print("\n🎉 所有测试通过！新数据库结构工作正常。")
        print("💡 现在可以通过 FastAPI 来测试数据库功能了。")
    else:
        print(f"\n⚠️ 有 {len(test_results) - passed} 个测试失败，需要检查问题。")
    
    # 清理测试数据库
    if os.path.exists("test_research_data.db"):
        print("\n🧹 清理测试数据库文件")
        # os.remove("test_research_data.db")  # 暂时保留以便调试

if __name__ == "__main__":
    main()
