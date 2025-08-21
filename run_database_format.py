#!/usr/bin/env python3
"""
运行 Database Format 模块的简化脚本
用于处理 source_data.db 中的参考文献数据
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加路径
sys.path.append('src')

# 加载环境变量
load_dotenv('.env')

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查数据库文件
    db_path = Path("../source_data.db")
    if not db_path.exists():
        print("❌ 未找到 source_data.db 文件")
        return False
    
    print(f"✅ 找到数据库文件: {db_path.absolute()}")
    
    # 检查API密钥
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ 未设置 ANTHROPIC_API_KEY 环境变量")
        print("💡 请设置API密钥:")
        print("   export ANTHROPIC_API_KEY=your_api_key_here")
        return False
    
    print("✅ API密钥已设置")
    return True

def show_current_data():
    """显示当前数据库状态"""
    print("\n📊 查看当前数据库状态...")
    
    import sqlite3
    
    try:
        conn = sqlite3.connect("../source_data.db")
        cursor = conn.cursor()
        
        # 总数统计
        cursor.execute('SELECT COUNT(*) FROM "references";')
        total = cursor.fetchone()[0]
        print(f"📚 总参考文献数量: {total}")
        
        # 分类统计
        cursor.execute('SELECT reference_type, COUNT(*) FROM "references" GROUP BY reference_type;')
        types = cursor.fetchall()
        print("\n📋 当前分类分布:")
        for ref_type, count in types:
            print(f"  - {ref_type or '未分类'}: {count}")
        
        # 可信度统计
        cursor.execute('SELECT credibility, COUNT(*) FROM "references" GROUP BY credibility;')
        credibility = cursor.fetchall()
        print("\n⭐ 可信度分布:")
        for cred, count in credibility:
            cred_text = {1: "低", 2: "中", 3: "高"}.get(cred, f"未知({cred})")
            print(f"  - {cred_text}: {count}")
        
        # 需要处理的数据
        cursor.execute("""
            SELECT COUNT(*) FROM "references" 
            WHERE reference_type IS NULL 
               OR reference_type = '未分类' 
               OR credibility = 2 
               OR related_assessment = 0.80
               OR credibility_assessment IS NULL
        """)
        need_processing = cursor.fetchone()[0]
        print(f"\n🔄 需要AI评估的记录: {need_processing}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 读取数据库失败: {str(e)}")

def run_database_format():
    """运行database format处理"""
    print("\n🚀 开始运行 Database Format 模块...")
    
    try:
        # 导入模块
        from src.database_format.main import main
        
        print("选择运行模式:")
        print("1. 查看统计信息")
        print("2. 预览模式（不实际更新）")
        print("3. 处理5条记录（测试）")
        print("4. 处理所有记录")
        
        choice = input("\n请选择 (1-4): ").strip()
        
        # 模拟命令行参数
        original_argv = sys.argv.copy()
        
        if choice == "1":
            sys.argv = ["main.py", "--stats"]
            print("\n📊 显示数据库统计信息...")
            
        elif choice == "2": 
            sys.argv = ["main.py", "--dry-run", "--limit", "10"]
            print("\n👀 预览模式 - 查看前10条需要处理的记录...")
            
        elif choice == "3":
            sys.argv = ["main.py", "--limit", "5", "--verbose"]
            print("\n🧪 测试模式 - 处理5条记录...")
            
        elif choice == "4":
            confirm = input("⚠️  这将处理所有需要评估的记录，可能耗时较长。确认继续? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ 用户取消操作")
                return
            sys.argv = ["main.py", "--verbose"]
            print("\n🔄 处理所有记录...")
            
        else:
            print("❌ 无效选择")
            return
        
        # 运行主函数
        result = main()
        
        # 恢复命令行参数
        sys.argv = original_argv
        
        if result == 0:
            print("\n✅ Database Format 处理完成！")
        else:
            print("\n❌ 处理过程中出现错误")
            
    except ImportError as e:
        print(f"❌ 导入模块失败: {str(e)}")
        print("💡 请确保在 backend 目录下运行此脚本")
    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")

def main():
    """主函数"""
    print("=" * 60)
    print("🧠 Database Format 模块运行器")
    print("📋 用于智能评估和分类参考文献")
    print("=" * 60)
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，无法继续")
        return 1
    
    # 显示当前数据
    show_current_data()
    
    # 询问是否继续
    print("\n" + "=" * 60)
    continue_choice = input("🤔 是否继续运行 Database Format 处理? (y/N): ")
    
    if continue_choice.lower() != 'y':
        print("👋 退出程序")
        return 0
    
    # 运行处理
    run_database_format()
    
    # 显示处理后的结果
    print("\n" + "=" * 60)
    print("📊 处理后的数据状态:")
    show_current_data()
    
    return 0

if __name__ == "__main__":
    exit(main())