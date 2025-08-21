#!/usr/bin/env python3
"""
运行数据库参考文献评估
对数据库中的参考文献进行可信度和相关性评估
"""

import asyncio
import sys
import os
import argparse
import json

# 添加路径
sys.path.insert(0, 'src')

from database_evaluator import DatabaseEvaluator


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='评估数据库中的参考文献')
    parser.add_argument('topic', type=str, help='研究主题')
    parser.add_argument('--limit', type=int, default=None, help='限制处理数量')
    parser.add_argument('--stats', action='store_true', help='仅显示统计信息')
    
    args = parser.parse_args()
    
    print("🚀 数据库参考文献评估工具")
    print("=" * 60)
    
    # 初始化评估器
    evaluator = DatabaseEvaluator()
    
    # 显示评估前统计
    stats = evaluator.get_evaluation_stats()
    print("\n📊 当前统计信息:")
    print(f"  - 总记录数: {stats.get('total_references', 0)}")
    print(f"  - 待评估: {stats.get('pending_evaluation', 0)}")
    print(f"  - 已评估: {stats.get('evaluated', 0)}")
    
    if stats.get('evaluated', 0) > 0:
        print(f"  - 平均可信度: {stats.get('average_credibility', 0)}")
        print(f"  - 平均相关性: {stats.get('average_relevance', 0)}")
        
        dist = stats.get('credibility_distribution', {})
        print(f"  - 可信度分布: 低={dist.get('low', 0)}, 中={dist.get('medium', 0)}, 高={dist.get('high', 0)}")
    
    if args.stats:
        # 仅显示统计信息
        return
    
    if stats.get('pending_evaluation', 0) == 0:
        print("\n✅ 没有待评估的记录")
        return
    
    # 执行评估
    print(f"\n🔍 研究主题: {args.topic}")
    print(f"📝 开始评估 {args.limit or '所有'} 条记录...")
    print("-" * 60)
    
    success_count = await evaluator.evaluate_batch(args.topic, args.limit)
    
    print("-" * 60)
    print(f"\n✅ 评估完成!")
    print(f"  - 成功处理: {success_count} 条")
    
    # 显示评估后统计
    if success_count > 0:
        stats = evaluator.get_evaluation_stats()
        print(f"\n📊 更新后的统计:")
        print(f"  - 已评估: {stats.get('evaluated', 0)}")
        print(f"  - 待评估: {stats.get('pending_evaluation', 0)}")
        print(f"  - 平均可信度: {stats.get('average_credibility', 0)}")
        print(f"  - 平均相关性: {stats.get('average_relevance', 0)}")


async def interactive_mode():
    """交互式评估模式"""
    print("🚀 数据库参考文献评估工具 - 交互模式")
    print("=" * 60)
    
    evaluator = DatabaseEvaluator()
    
    while True:
        print("\n选择操作:")
        print("1. 查看统计信息")
        print("2. 评估参考文献")
        print("3. 查看低可信度记录")
        print("4. 查看高相关性记录")
        print("5. 退出")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '1':
            stats = evaluator.get_evaluation_stats()
            print("\n📊 统计信息:")
            print(json.dumps(stats, indent=2, ensure_ascii=False))
            
        elif choice == '2':
            topic = input("请输入研究主题: ").strip()
            limit = input("处理数量限制 (留空处理所有): ").strip()
            limit = int(limit) if limit else None
            
            success_count = await evaluator.evaluate_batch(topic, limit)
            print(f"\n✅ 成功处理 {success_count} 条记录")
            
        elif choice == '3':
            # 查询低可信度记录
            query_sql = """
            SELECT reference_title, reference_url, credibility_assessment
            FROM "references"
            WHERE credibility = 1 AND status = 1
            LIMIT 5
            """
            try:
                with evaluator.db_manager.get_connection() as conn:
                    cursor = conn.execute(query_sql)
                    rows = cursor.fetchall()
                    
                print("\n📋 低可信度记录:")
                for row in rows:
                    print(f"\n标题: {row['reference_title']}")
                    print(f"URL: {row['reference_url']}")
                    print(f"评估: {row['credibility_assessment']}")
            except Exception as e:
                print(f"查询失败: {str(e)}")
                
        elif choice == '4':
            # 查询高相关性记录
            query_sql = """
            SELECT reference_title, reference_url, related_assessment, related_assessment_text
            FROM "references"
            WHERE related_assessment >= 0.8 AND status = 1
            ORDER BY related_assessment DESC
            LIMIT 5
            """
            try:
                with evaluator.db_manager.get_connection() as conn:
                    cursor = conn.execute(query_sql)
                    rows = cursor.fetchall()
                    
                print("\n📋 高相关性记录:")
                for row in rows:
                    print(f"\n标题: {row['reference_title']}")
                    print(f"相关性: {row['related_assessment']}")
                    print(f"评估: {row['related_assessment_text']}")
            except Exception as e:
                print(f"查询失败: {str(e)}")
                
        elif choice == '5':
            print("\n👋 再见!")
            break
        
        else:
            print("\n❌ 无效选择，请重试")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式
        asyncio.run(main())
    else:
        # 交互模式
        asyncio.run(interactive_mode())