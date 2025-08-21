#!/usr/bin/env python3
"""
简单数据库测试脚本
"""

import sqlite3
import os
from pathlib import Path

def test_database():
    """测试数据库状态"""
    print("🔍 测试数据库状态...")
    
    # 数据库路径
    db_path = Path(__file__).parent.parent / 'research_data.db'
    print(f"数据库路径: {db_path}")
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        # 连接数据库
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 检查所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"数据库中的表: {[t[0] for t in tables]}")
            
            if ('references',) in tables:
                # 检查references表结构
                cursor.execute("PRAGMA table_info(references)")
                columns = cursor.fetchall()
                print(f"references表字段: {[col[1] for col in columns]}")
                
                # 简单统计
                cursor.execute("SELECT COUNT(*) FROM references")
                total = cursor.fetchone()[0]
                print(f"总记录数: {total}")
                
                if total > 0:
                    # 检查字段填充情况
                    cursor.execute("SELECT COUNT(*) FROM references WHERE credibility IS NOT NULL AND credibility != ''")
                    cred_filled = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM references WHERE related_assessment IS NOT NULL AND related_assessment != ''")
                    assess_filled = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM references WHERE publisher IS NOT NULL AND publisher != ''")
                    pub_filled = cursor.fetchone()[0]
                    
                    print(f"字段填充状态:")
                    print(f"  credibility: {cred_filled}/{total} ({cred_filled/total*100:.1f}%)")
                    print(f"  related_assessment: {assess_filled}/{total} ({assess_filled/total*100:.1f}%)")
                    print(f"  publisher: {pub_filled}/{total} ({pub_filled/total*100:.1f}%)")
                    
                    # 显示前3条记录
                    cursor.execute("SELECT title, credibility, related_assessment, publisher FROM references LIMIT 3")
                    rows = cursor.fetchall()
                    print(f"\n前3条记录:")
                    for i, (title, cred, assess, pub) in enumerate(rows, 1):
                        print(f"  {i}. {title[:40]}...")
                        print(f"     credibility: {cred or '空'}")
                        print(f"     related_assessment: {assess or '空'}")
                        print(f"     publisher: {pub or '空'}")
                        print()
                else:
                    print("数据库为空")
            else:
                print("❌ 没有找到references表")
                
    except Exception as e:
        print(f"❌ 数据库操作失败: {str(e)}")

def test_module_import():
    """测试模块导入"""
    print("\n🧪 测试模块导入...")
    
    import sys
    sys.path.append('src/database_format')
    
    try:
        from database_format.database_updater import DatabaseUpdater
        print("✅ DatabaseUpdater导入成功")
        
        updater = DatabaseUpdater()
        print("✅ DatabaseUpdater实例创建成功")
        
        # 测试获取统计
        stats = updater.get_evaluation_statistics()
        print(f"✅ 获取统计成功: {stats}")
        
    except Exception as e:
        print(f"❌ 模块测试失败: {str(e)}")

if __name__ == "__main__":
    test_database()
    test_module_import()