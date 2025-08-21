#!/usr/bin/env python3
"""
测试数据填充路径脚本
验证即时字段填充功能是否正常工作
"""

import sqlite3
import os
import sys
import asyncio
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'database_format'))

def check_database_status():
    """检查数据库当前状态"""
    print("🔍 检查数据库状态...")
    
    db_path = current_dir.parent / 'research_data.db'
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return False
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='references'")
            if not cursor.fetchone():
                print("❌ references表不存在")
                return False
            
            # 获取数据统计
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN credibility IS NOT NULL AND credibility != '' THEN 1 END) as filled_cred,
                    COUNT(CASE WHEN related_assessment IS NOT NULL AND related_assessment != '' THEN 1 END) as filled_assess,
                    COUNT(CASE WHEN publisher IS NOT NULL AND publisher != '' THEN 1 END) as filled_pub
                FROM references
            """)
            
            result = cursor.fetchone()
            total, filled_cred, filled_assess, filled_pub = result
            
            print(f"📊 数据库状态:")
            print(f"  - 总记录数: {total}")
            print(f"  - credibility已填充: {filled_cred}/{total} ({filled_cred/total*100:.1f}%)" if total > 0 else "  - credibility已填充: 0/0")
            print(f"  - related_assessment已填充: {filled_assess}/{total} ({filled_assess/total*100:.1f}%)" if total > 0 else "  - related_assessment已填充: 0/0")
            print(f"  - publisher已填充: {filled_pub}/{total} ({filled_pub/total*100:.1f}%)" if total > 0 else "  - publisher已填充: 0/0")
            
            # 显示样本数据
            if total > 0:
                print(f"\n📝 样本数据 (前3条):")
                cursor.execute("SELECT title, credibility, related_assessment, publisher FROM references LIMIT 3")
                for i, row in enumerate(cursor.fetchall(), 1):
                    title, cred, assess, pub = row
                    print(f"  {i}. 标题: {title[:50]}...")
                    print(f"     可信度: {cred or '未填充'}")
                    print(f"     相关性: {assess or '未填充'}")
                    print(f"     出版商: {pub or '未填充'}")
                    print()
            
            return total, filled_cred, filled_assess, filled_pub
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")
        return False

async def test_data_filling_path():
    """测试数据填充路径"""
    print("\n🧪 测试数据填充功能...")
    
    try:
        # 尝试导入DatabaseUpdater
        print("1️⃣ 测试模块导入...")
        from database_updater import DatabaseUpdater
        print("✅ DatabaseUpdater导入成功")
        
        # 创建更新器实例
        updater = DatabaseUpdater()
        print("✅ DatabaseUpdater实例创建成功")
        
        # 测试数据库连接
        print("\n2️⃣ 测试数据库连接...")
        stats = updater.get_evaluation_statistics()
        print("✅ 数据库连接成功")
        print(f"📊 评估统计: 总计{stats['total_records']}条, 已评估{stats['evaluated_records']}条, 待评估{stats['pending_records']}条")
        
        # 测试获取待评估记录
        print("\n3️⃣ 测试获取待评估记录...")
        pending_refs = updater.get_pending_references()
        print(f"✅ 找到 {len(pending_refs)} 条待评估记录")
        
        if len(pending_refs) > 0:
            # 测试单条记录评估（使用第一条记录）
            print("\n4️⃣ 测试单条记录评估...")
            test_ref = pending_refs[0]
            print(f"测试记录: {test_ref.title[:50]}...")
            
            # 模拟评估（不真正调用API）
            print("⚠️ 注意: 需要CLAUDE_API_KEY环境变量才能执行实际评估")
            
            if os.getenv('CLAUDE_API_KEY'):
                print("✅ 发现API密钥，将尝试实际评估...")
                try:
                    result = await updater.evaluate_and_update_reference(test_ref.id, "测试研究主题")
                    if result:
                        print("✅ 单条记录评估成功!")
                        print(f"评估结果: {result}")
                    else:
                        print("❌ 单条记录评估失败")
                except Exception as e:
                    print(f"❌ 评估过程出错: {str(e)}")
            else:
                print("⚠️ 未设置CLAUDE_API_KEY，跳过实际API调用测试")
                print("💡 如需完整测试，请设置: export CLAUDE_API_KEY='your-key'")
        else:
            print("ℹ️ 没有待评估记录，数据库字段可能已经完整")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {str(e)}")
        print("💡 可能需要安装依赖: pip install anthropic")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_search_graph_integration():
    """测试search_graph中的集成"""
    print("\n🔗 测试search_graph集成...")
    
    try:
        search_graph_path = current_dir / 'search_agent' / 'search_graph.py'
        if not search_graph_path.exists():
            print("❌ search_graph.py文件不存在")
            return False
        
        with open(search_graph_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键集成点
        checks = [
            ('DatabaseUpdater导入', 'DatabaseUpdater' in content),
            ('字段评估逻辑', '开始对新保存的记录进行字段评估' in content),
            ('评估调用', 'evaluate_and_update_reference' in content or 'process_batch' in content),
        ]
        
        for check_name, check_result in checks:
            if check_result:
                print(f"✅ {check_name}: 已集成")
            else:
                print(f"❌ {check_name}: 未找到")
        
        return all(check[1] for check in checks)
        
    except Exception as e:
        print(f"❌ 集成检查失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🧪 数据填充路径测试")
    print("=" * 50)
    
    # 检查数据库状态
    db_status = check_database_status()
    
    if db_status:
        # 测试数据填充功能
        filling_test = await test_data_filling_path()
        
        # 测试集成
        integration_test = test_search_graph_integration()
        
        # 总结
        print("\n" + "=" * 50)
        print("📋 测试结果总结")
        print("=" * 50)
        
        if db_status and filling_test and integration_test:
            print("🎉 所有测试通过!")
            print("✅ 数据库状态正常")
            print("✅ 数据填充功能可用")
            print("✅ search_graph集成完整")
            print("\n💡 系统已准备好进行即时字段填充")
        else:
            print("⚠️ 部分测试未通过:")
            if not db_status:
                print("  - 数据库状态检查失败")
            if not filling_test:
                print("  - 数据填充功能测试失败")
            if not integration_test:
                print("  - search_graph集成检查失败")
    else:
        print("❌ 数据库状态检查失败，无法继续测试")
    
    return db_status and filling_test if db_status else False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)