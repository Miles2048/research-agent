#!/usr/bin/env python3
"""
评估测试器 - 测试即时字段填充功能
验证数据保存后立即进行credibility、related_assessment、publisher字段评估
"""

import asyncio
import os
import sys
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir.parent.parent))

try:
    from .config import get_database_path
    from .models import Reference
    from .database_updater import DatabaseUpdater
    from .llm_evaluator import LLMEvaluator
except ImportError:
    from config import get_database_path
    from models import Reference
    from database_updater import DatabaseUpdater
    from llm_evaluator import LLMEvaluator


class EvaluationTester:
    """评估功能测试器 - 测试即时字段填充"""
    
    def __init__(self):
        self.db_path = get_database_path()
        self.test_references = []
        
    async def run_full_test(self) -> Dict[str, Any]:
        """运行完整的评估测试"""
        print("🧪 开始评估功能测试...")
        print("=" * 50)
        
        results = {
            'setup': False,
            'immediate_evaluation': False,
            'batch_evaluation': False,
            'performance': {},
            'cleanup': False,
            'errors': [],
            'summary': {}
        }
        
        try:
            # 1. 设置测试环境
            results['setup'] = await self.setup_test_environment()
            if not results['setup']:
                return results
            
            # 2. 测试即时评估功能
            results['immediate_evaluation'] = await self.test_immediate_evaluation()
            
            # 3. 测试批量评估功能
            results['batch_evaluation'] = await self.test_batch_evaluation()
            
            # 4. 性能测试
            results['performance'] = await self.test_performance()
            
            # 5. 清理测试数据
            results['cleanup'] = await self.cleanup_test_data()
            
            # 6. 生成测试总结
            results['summary'] = self.generate_test_summary(results)
            
        except Exception as e:
            results['errors'].append(f"测试过程出错: {str(e)}")
        
        self.print_test_results(results)
        return results
    
    async def setup_test_environment(self) -> bool:
        """设置测试环境"""
        print("\n🔧 1. 设置测试环境")
        
        try:
            # 检查数据库连接
            if not os.path.exists(self.db_path):
                print(f"  ⚠️ 数据库不存在，创建: {self.db_path}")
                # 创建数据库和表
                await self.create_test_database()
            
            print(f"  ✅ 数据库路径: {self.db_path}")
            
            # 检查必要的依赖
            try:
                updater = DatabaseUpdater()
                print(f"  ✅ DatabaseUpdater初始化成功")
            except Exception as e:
                print(f"  ❌ DatabaseUpdater初始化失败: {str(e)}")
                return False
            
            try:
                evaluator = LLMEvaluator()
                print(f"  ✅ LLMEvaluator初始化成功")
            except Exception as e:
                print(f"  ❌ LLMEvaluator初始化失败: {str(e)}")
                return False
            
            # 检查API密钥
            if not os.getenv('CLAUDE_API_KEY'):
                print(f"  ⚠️ 未设置CLAUDE_API_KEY，将使用模拟评估")
            else:
                print(f"  ✅ CLAUDE_API_KEY已配置")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 环境设置失败: {str(e)}")
            return False
    
    async def create_test_database(self):
        """创建测试用数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    content TEXT,
                    credibility TEXT DEFAULT '',
                    related_assessment TEXT DEFAULT '',
                    publisher TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    async def test_immediate_evaluation(self) -> bool:
        """测试即时评估功能"""
        print("\n🔍 2. 测试即时评估功能")
        
        try:
            updater = DatabaseUpdater()
            
            # 创建测试数据
            test_data = [
                {
                    'title': '人工智能发展现状研究',
                    'url': 'https://test-ai-research.com',
                    'content': '本文深入分析了当前人工智能技术的发展现状，包括机器学习、深度学习等关键技术的进展。',
                    'topic': '人工智能发展趋势'
                },
                {
                    'title': '区块链技术在金融领域的应用',
                    'url': 'https://test-blockchain-finance.com',
                    'content': '区块链技术作为一种分布式账本技术，在金融领域展现出巨大的应用潜力。',
                    'topic': '金融科技创新'
                }
            ]
            
            evaluation_results = []
            
            for i, data in enumerate(test_data, 1):
                print(f"\n  📝 测试记录 {i}: {data['title'][:30]}...")
                
                # 插入测试记录
                test_id = await self.insert_test_reference(data)
                if not test_id:
                    print(f"    ❌ 插入失败")
                    continue
                
                self.test_references.append(test_id)
                print(f"    ✅ 记录插入成功 (ID: {test_id})")
                
                # 立即执行评估
                start_time = time.time()
                result = await updater.evaluate_and_update_reference(test_id, data['topic'])
                evaluation_time = time.time() - start_time
                
                if result:
                    print(f"    ✅ 即时评估成功 (耗时: {evaluation_time:.2f}秒)")
                    evaluation_results.append({
                        'id': test_id,
                        'success': True,
                        'time': evaluation_time,
                        'result': result
                    })
                    
                    # 验证字段是否已填充
                    if await self.verify_evaluation_result(test_id):
                        print(f"    ✅ 字段验证成功")
                    else:
                        print(f"    ❌ 字段验证失败")
                else:
                    print(f"    ❌ 即时评估失败")
                    evaluation_results.append({
                        'id': test_id,
                        'success': False,
                        'time': evaluation_time
                    })
            
            # 统计结果
            successful = sum(1 for r in evaluation_results if r['success'])
            total = len(evaluation_results)
            avg_time = sum(r['time'] for r in evaluation_results if 'time' in r) / total if total > 0 else 0
            
            print(f"\n  📊 即时评估测试结果:")
            print(f"    - 成功率: {successful}/{total} ({successful/total*100:.1f}%)")
            print(f"    - 平均耗时: {avg_time:.2f}秒")
            
            return successful == total
            
        except Exception as e:
            print(f"  ❌ 即时评估测试失败: {str(e)}")
            return False
    
    async def test_batch_evaluation(self) -> bool:
        """测试批量评估功能"""
        print("\n📦 3. 测试批量评估功能")
        
        try:
            updater = DatabaseUpdater()
            
            # 创建一批未评估的测试数据
            batch_test_data = [
                {
                    'title': f'测试文献 {i}',
                    'url': f'https://test-batch-{i}.com',
                    'content': f'这是第 {i} 篇测试文献的内容，用于验证批量评估功能。',
                    'topic': '批量评估测试'
                }
                for i in range(1, 4)  # 创建3个测试记录
            ]
            
            # 插入未评估的记录
            batch_ids = []
            for data in batch_test_data:
                test_id = await self.insert_test_reference(data, evaluate=False)
                if test_id:
                    batch_ids.append(test_id)
                    self.test_references.append(test_id)
            
            print(f"  📝 创建了 {len(batch_ids)} 条待评估记录")
            
            # 获取评估前统计
            stats_before = updater.get_evaluation_statistics()
            print(f"  📊 评估前统计: 待评估 {stats_before['pending_records']} 条")
            
            # 执行批量评估
            pending_refs = updater.get_pending_references()
            batch_pending = [ref for ref in pending_refs if ref.id in batch_ids]
            
            start_time = time.time()
            success_count = 0
            
            for ref in batch_pending:
                result = await updater.evaluate_and_update_reference(ref.id, "批量评估测试主题")
                if result:
                    success_count += 1
            
            batch_time = time.time() - start_time
            
            # 获取评估后统计
            stats_after = updater.get_evaluation_statistics()
            
            print(f"  📊 批量评估结果:")
            print(f"    - 处理记录: {len(batch_pending)} 条")
            print(f"    - 成功评估: {success_count} 条")
            print(f"    - 总耗时: {batch_time:.2f}秒")
            print(f"    - 平均耗时: {batch_time/len(batch_pending):.2f}秒/条")
            print(f"    - 评估完成率: {success_count/len(batch_pending)*100:.1f}%")
            
            return success_count == len(batch_pending)
            
        except Exception as e:
            print(f"  ❌ 批量评估测试失败: {str(e)}")
            return False
    
    async def test_performance(self) -> Dict[str, float]:
        """测试性能表现"""
        print("\n⚡ 4. 性能测试")
        
        performance_data = {}
        
        try:
            updater = DatabaseUpdater()
            
            # 测试单条记录评估性能
            test_id = await self.insert_test_reference({
                'title': '性能测试记录',
                'url': 'https://performance-test.com',
                'content': '用于性能测试的记录内容，模拟真实的学术文献摘要和内容。',
                'topic': '性能测试'
            }, evaluate=False)
            
            if test_id:
                self.test_references.append(test_id)
                
                # 多次测试取平均值
                times = []
                for i in range(3):
                    start_time = time.time()
                    result = await updater.evaluate_and_update_reference(test_id, "性能测试主题")
                    eval_time = time.time() - start_time
                    times.append(eval_time)
                    
                    if i < 2:  # 重置记录以便重新评估
                        await self.reset_evaluation_fields(test_id)
                
                performance_data['single_evaluation_avg'] = sum(times) / len(times)
                performance_data['single_evaluation_min'] = min(times)
                performance_data['single_evaluation_max'] = max(times)
                
                print(f"  📊 单条评估性能:")
                print(f"    - 平均耗时: {performance_data['single_evaluation_avg']:.3f}秒")
                print(f"    - 最快: {performance_data['single_evaluation_min']:.3f}秒")
                print(f"    - 最慢: {performance_data['single_evaluation_max']:.3f}秒")
            
            # 测试数据库操作性能
            start_time = time.time()
            stats = updater.get_evaluation_statistics()
            db_query_time = time.time() - start_time
            performance_data['database_query'] = db_query_time
            
            print(f"  📊 数据库查询性能: {db_query_time:.3f}秒")
            
        except Exception as e:
            print(f"  ❌ 性能测试失败: {str(e)}")
        
        return performance_data
    
    async def insert_test_reference(self, data: Dict[str, str], evaluate: bool = False) -> Optional[int]:
        """插入测试记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if evaluate:
                    # 插入已评估的记录（模拟值）
                    cursor.execute("""
                        INSERT INTO references (title, url, content, credibility, related_assessment, publisher)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        data['title'],
                        data['url'],
                        data['content'],
                        'high',  # 模拟评估结果
                        'highly_relevant',
                        'Test Publisher'
                    ))
                else:
                    # 插入未评估的记录
                    cursor.execute("""
                        INSERT INTO references (title, url, content, credibility, related_assessment, publisher)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        data['title'],
                        data['url'],
                        data['content'],
                        '',  # 空字段等待评估
                        '',
                        ''
                    ))
                
                test_id = cursor.lastrowid
                conn.commit()
                return test_id
                
        except Exception as e:
            print(f"    插入记录失败: {str(e)}")
            return None
    
    async def verify_evaluation_result(self, ref_id: int) -> bool:
        """验证评估结果是否正确填充"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT credibility, related_assessment, publisher 
                    FROM references WHERE id = ?
                """, (ref_id,))
                
                result = cursor.fetchone()
                if result:
                    credibility, related_assessment, publisher = result
                    # 检查是否所有字段都已填充（非空）
                    return all([
                        credibility and credibility.strip(),
                        related_assessment and related_assessment.strip(),
                        publisher and publisher.strip()
                    ])
                
                return False
                
        except Exception:
            return False
    
    async def reset_evaluation_fields(self, ref_id: int):
        """重置评估字段（用于性能测试）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE references 
                    SET credibility = '', related_assessment = '', publisher = ''
                    WHERE id = ?
                """, (ref_id,))
                conn.commit()
        except Exception:
            pass
    
    async def cleanup_test_data(self) -> bool:
        """清理测试数据"""
        print("\n🧹 5. 清理测试数据")
        
        try:
            if not self.test_references:
                print("  ✅ 无需清理")
                return True
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 删除所有测试记录
                placeholders = ','.join(['?' for _ in self.test_references])
                cursor.execute(f"DELETE FROM references WHERE id IN ({placeholders})", self.test_references)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"  ✅ 清理完成: 删除 {deleted_count} 条测试记录")
                return True
                
        except Exception as e:
            print(f"  ❌ 清理失败: {str(e)}")
            return False
    
    def generate_test_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试总结"""
        summary = {
            'total_tests': 4,  # setup, immediate, batch, performance
            'passed_tests': 0,
            'failed_tests': 0,
            'overall_success': False
        }
        
        # 计算通过的测试数量
        test_keys = ['setup', 'immediate_evaluation', 'batch_evaluation']
        passed = sum(1 for key in test_keys if results.get(key, False))
        
        summary['passed_tests'] = passed
        summary['failed_tests'] = summary['total_tests'] - passed
        summary['overall_success'] = passed >= 3  # 至少通过3个核心测试
        
        return summary
    
    def print_test_results(self, results: Dict[str, Any]):
        """打印测试结果"""
        print("\n" + "=" * 50)
        print("🧪 评估功能测试结果")
        print("=" * 50)
        
        summary = results.get('summary', {})
        
        if summary.get('overall_success', False):
            print("🎉 测试通过！即时字段填充功能正常工作")
        else:
            print("❌ 测试失败，请检查配置和依赖")
        
        print(f"\n📊 测试统计:")
        print(f"  - 总测试: {summary.get('total_tests', 0)}")
        print(f"  - 通过: {summary.get('passed_tests', 0)}")
        print(f"  - 失败: {summary.get('failed_tests', 0)}")
        
        if results.get('errors'):
            print(f"\n❌ 错误信息:")
            for error in results['errors']:
                print(f"  - {error}")
        
        perf = results.get('performance', {})
        if perf:
            print(f"\n⚡ 性能表现:")
            if 'single_evaluation_avg' in perf:
                print(f"  - 单条评估平均耗时: {perf['single_evaluation_avg']:.3f}秒")
            if 'database_query' in perf:
                print(f"  - 数据库查询耗时: {perf['database_query']:.3f}秒")


async def main():
    """主函数 - 运行评估功能测试"""
    tester = EvaluationTester()
    results = await tester.run_full_test()
    
    # 返回退出代码
    return 0 if results.get('summary', {}).get('overall_success', False) else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))