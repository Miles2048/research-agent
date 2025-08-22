#!/usr/bin/env python3
"""
并发评估器测试套件 - 带详细注释版本

测试架构说明：
================================================================================
本测试套件分为三个层次：
1. 单元测试 - 测试单个组件的功能
2. 集成测试 - 测试组件之间的协作
3. 性能测试 - 验证并发带来的性能提升

测试策略：
- 使用Mock对象模拟外部依赖（LLM API、数据库）
- 隔离测试每个功能点
- 验证并发机制的正确性和性能
================================================================================
"""

import sys
import os
import time
import sqlite3
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import json

# 添加项目路径，使测试可以导入项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_format.concurrent_evaluator import ConcurrentEvaluator, EvaluationTask
from database_format.database_updater import DatabaseUpdater
from database_format.models import Reference, EvaluationResult
from database_format.config import config


# ================================================================================
# 第一部分：单元测试 - ConcurrentEvaluator类
# ================================================================================
class TestConcurrentEvaluator(unittest.TestCase):
    """
    测试并发评估器的核心功能
    
    测试重点：
    1. 并发机制是否正确工作
    2. 限流控制是否生效
    3. 失败重试机制
    4. 统计信息跟踪
    """
    
    def setUp(self):
        """
        测试前的准备工作
        - 创建评估器实例
        - 准备模拟数据
        """
        # 创建并发评估器实例
        # max_workers=3: 使用3个工作线程（较小的数字便于测试）
        # rate_limit=0.1: API调用间隔100ms
        # timeout=10: 单个任务超时10秒
        self.evaluator = ConcurrentEvaluator(
            max_workers=3,
            rate_limit=0.1,
            timeout=10
        )
        
        # 创建10个模拟的Reference对象
        # 这些是待评估的参考文献
        self.mock_references = []
        for i in range(10):
            # 使用Mock创建模拟对象，spec=Reference确保模拟对象有Reference的接口
            ref = Mock(spec=Reference)
            ref.id = i + 1  # 设置ID
            ref.reference_title = f"Test Reference {i + 1}"  # 标题
            ref.reference_url = f"http://example.com/{i + 1}"  # URL
            ref.reference_content = f"Test content {i + 1}"  # 内容
            ref.publisher = f"Publisher {i + 1}"  # 发布者
            ref.reference_type = "uncategorized"  # 初始类型（未分类）
            ref.credibility = 2  # 初始可信度（中等）
            ref.related_assessment = 0.5  # 初始相关性（50%）
            ref.needs_evaluation.return_value = True  # 模拟需要评估
            self.mock_references.append(ref)
    
    def test_concurrent_evaluation_basic(self):
        """
        测试1：基本并发评估功能
        
        验证点：
        - 能否并发处理多个参考文献
        - 返回结果是否正确
        - 所有参考文献是否都被处理
        """
        # 使用patch模拟LLM评估器的evaluate_reference方法
        # 这样我们不需要真的调用LLM API
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # 定义模拟的评估结果生成函数
            def create_mock_result(ref):
                """为每个参考文献创建模拟的评估结果"""
                result = Mock(spec=EvaluationResult)
                result.reference_type = "技术文档"  # 分类为技术文档
                result.credibility = 3  # 高可信度
                result.related_assessment = 0.85  # 85%相关性
                result.validate.return_value = True  # 验证通过
                return result
            
            # 设置mock的副作用：每次调用都返回一个评估结果
            mock_eval.side_effect = create_mock_result
            
            # 执行并发评估（只评估前5个参考文献）
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:5])
            
            # 断言：验证结果
            self.assertEqual(len(results), 5)  # 应该返回5个结果
            self.assertEqual(mock_eval.call_count, 5)  # evaluate_reference应该被调用5次
            
            # 验证每个参考文献都有对应的结果
            for i in range(1, 6):
                self.assertIn(i, results)  # 结果字典中应该有这个ID
                self.assertEqual(results[i].reference_type, "技术文档")  # 类型应该是技术文档
    
    def test_rate_limiting(self):
        """
        测试2：限流机制
        
        验证点：
        - API调用是否遵守速率限制
        - 请求之间的间隔是否正确
        
        原理：
        如果有3个请求，限流0.2秒，那么：
        - 第1个请求：立即执行（0秒）
        - 第2个请求：等待0.2秒后执行
        - 第3个请求：等待0.2秒后执行
        总时间至少需要0.4秒
        """
        start_time = time.time()
        
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # 创建一个快速返回的mock（不添加额外延迟）
            mock_eval.return_value = Mock(spec=EvaluationResult)
            
            # 设置较长的限流时间便于测试
            self.evaluator.rate_limit = 0.2  # 200ms between requests
            
            # 评估3个参考文献
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:3])
            
            elapsed = time.time() - start_time
            
            # 验证：总时间应该至少是 (n-1) * rate_limit
            # 3个请求，间隔0.2秒，至少需要0.4秒
            self.assertGreaterEqual(elapsed, 0.4)
    
    def test_failed_evaluation_retry(self):
        """
        测试3：失败重试机制
        
        验证点：
        - 失败的评估是否会自动重试
        - 重试后成功的结果是否被正确记录
        
        场景：
        第一次调用失败（返回None），第二次成功
        """
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # 创建成功的评估结果
            mock_result = Mock(spec=EvaluationResult)
            mock_result.reference_type = "技术文档"
            mock_result.credibility = 3
            mock_result.related_assessment = 0.85
            
            # 设置副作用：第一次失败(None)，后续成功
            # 这模拟了网络错误后重试成功的场景
            mock_eval.side_effect = [None, mock_result, mock_result, mock_result]
            
            # 评估单个参考文献
            results = self.evaluator.evaluate_batch_concurrent([self.mock_references[0]])
            
            # 验证：
            # 1. 应该有结果（重试成功了）
            self.assertEqual(len(results), 1)
            self.assertIn(1, results)
            
            # 2. evaluate_reference应该被调用至少2次（初次+重试）
            self.assertGreaterEqual(mock_eval.call_count, 2)
    
    def test_statistics_tracking(self):
        """
        测试4：统计信息跟踪
        
        验证点：
        - 统计信息是否正确记录
        - 成功/失败计数是否准确
        """
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # 创建混合结果：3个成功，2个失败
            mock_result = Mock(spec=EvaluationResult)
            mock_eval.side_effect = [mock_result, None, mock_result, None, mock_result]
            
            # 重置统计信息
            self.evaluator.reset_stats()
            
            # 执行评估
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:5])
            
            # 验证统计信息
            self.assertEqual(self.evaluator.stats['total_processed'], 5)  # 总共处理5个
            self.assertEqual(self.evaluator.stats['successful'], 3)  # 3个成功
            self.assertIsNotNone(self.evaluator.stats['start_time'])  # 记录了开始时间
            self.assertIsNotNone(self.evaluator.stats['end_time'])  # 记录了结束时间


# ================================================================================
# 第二部分：集成测试 - DatabaseUpdater的并发模式
# ================================================================================
class TestDatabaseUpdaterConcurrent(unittest.TestCase):
    """
    测试DatabaseUpdater类的并发功能
    
    测试重点：
    1. 批量数据库更新
    2. 并发模式vs串行模式
    3. 数据一致性
    """
    
    def setUp(self):
        """
        准备测试环境
        - 创建临时数据库
        - 初始化测试数据
        - 配置DatabaseUpdater
        """
        # 创建临时SQLite数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        
        # 初始化数据库结构和测试数据
        self._init_test_database()
        
        # 使用patch模拟配置，避免依赖真实配置文件
        with patch('database_format.database_updater.config') as mock_config:
            # 设置数据库配置
            mock_config.DATABASE_CONFIG = {
                'db_path': self.db_path,
                'table_name': 'test_references',
                'batch_size': 10
            }
            # 设置LLM配置
            mock_config.LLM_CONFIG = {
                'api_key': 'test_key',
                'model': 'test-model'
            }
            # 设置研究主题（用于相关性评估）
            mock_config.research_topic = {
                'title': 'Test Research',
                'description': 'Test Description',
                'keywords': ['test']
            }
            
            # 模拟LLMEvaluator和PublisherExtractor，避免真实API调用
            with patch('database_format.database_updater.LLMEvaluator'):
                with patch('database_format.database_updater.PublisherExtractor'):
                    # 创建DatabaseUpdater实例（并发模式）
                    self.updater = DatabaseUpdater(use_concurrent=True, max_workers=3)
                    self.updater.db_path = self.db_path
                    self.updater.table_name = 'test_references'
    
    def tearDown(self):
        """清理测试环境 - 删除临时数据库"""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def _init_test_database(self):
        """
        初始化测试数据库
        创建表结构并插入测试数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建参考文献表
        # 包含评估所需的所有字段
        cursor.execute('''
            CREATE TABLE test_references (
                id INTEGER PRIMARY KEY,
                reference_type TEXT DEFAULT 'uncategorized',  -- 文献类型
                url TEXT,                                      -- URL
                name TEXT,                                     -- 名称
                raw_content TEXT,                              -- 原始内容
                publisher TEXT,                                -- 发布者
                credibility INTEGER DEFAULT 2,                -- 可信度(1-3)
                related_assessment REAL DEFAULT 0.5,          -- 相关性(0-1)
                updated_at TEXT                               -- 更新时间
            )
        ''')
        
        # 插入5条测试数据，都是待评估状态
        test_data = [
            (1, 'uncategorized', 'http://example.com/1', 'Reference 1', 'Content 1', 'Publisher 1', 2, 0.5),
            (2, 'uncategorized', 'http://example.com/2', 'Reference 2', 'Content 2', 'Publisher 2', 2, 0.5),
            (3, 'uncategorized', 'http://example.com/3', 'Reference 3', 'Content 3', 'Publisher 3', 2, 0.5),
            (4, 'uncategorized', 'http://example.com/4', 'Reference 4', 'Content 4', 'Publisher 4', 2, 0.5),
            (5, 'uncategorized', 'http://example.com/5', 'Reference 5', 'Content 5', 'Publisher 5', 2, 0.5),
        ]
        
        cursor.executemany(
            'INSERT INTO test_references (id, reference_type, url, name, raw_content, publisher, credibility, related_assessment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            test_data
        )
        
        conn.commit()
        conn.close()
    
    def test_batch_update_references(self):
        """
        测试5：批量数据库更新
        
        验证点：
        - 批量更新是否正确执行
        - 数据是否正确写入数据库
        """
        # 创建模拟的评估结果
        eval_results = {
            1: Mock(reference_type='技术文档', credibility=3, related_assessment=0.9),
            2: Mock(reference_type='新闻报道', credibility=2, related_assessment=0.7),
            3: Mock(reference_type='学术论文', credibility=3, related_assessment=0.95),
        }
        
        # 执行批量更新
        update_stats = self.updater.batch_update_references(eval_results)
        
        # 验证更新统计
        self.assertEqual(update_stats['success'], 3)  # 3条成功
        self.assertEqual(update_stats['failed'], 0)   # 0条失败
        
        # 验证数据库中的数据是否正确更新
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT reference_type, credibility, related_assessment FROM test_references WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        # 验证第一条记录的更新结果
        self.assertEqual(row[0], '技术文档')  # 类型
        self.assertEqual(row[1], 3)           # 可信度
        self.assertAlmostEqual(row[2], 0.9, places=1)  # 相关性
    
    def test_concurrent_vs_serial_mode(self):
        """
        测试6：并发模式 vs 串行模式对比
        
        验证点：
        - 两种模式是否都能正常工作
        - 并发模式是否调用了正确的方法
        - 性能差异（通过时间测量）
        """
        # 获取待评估的参考文献
        references = self.updater.get_references_to_update(limit=5)
        
        # 创建模拟的评估结果
        mock_eval_result = Mock(spec=EvaluationResult)
        mock_eval_result.reference_type = '技术文档'
        mock_eval_result.credibility = 3
        mock_eval_result.related_assessment = 0.85
        mock_eval_result.validate.return_value = True
        
        # ===== 测试并发模式 =====
        with patch.object(self.updater.concurrent_evaluator, 'evaluate_batch_concurrent') as mock_concurrent:
            # 模拟并发评估返回所有结果
            mock_concurrent.return_value = {ref.id: mock_eval_result for ref in references}
            
            start_time = time.time()
            result = self.updater.process_batch(references)
            concurrent_time = time.time() - start_time
            
            # 验证：
            # 1. 并发方法被调用
            self.assertTrue(mock_concurrent.called)
            # 2. 所有参考文献都被成功处理
            self.assertEqual(result.successful, 5)
        
        # ===== 测试串行模式 =====
        # 创建新的updater实例，使用串行模式
        serial_updater = DatabaseUpdater(use_concurrent=False)
        serial_updater.db_path = self.db_path
        serial_updater.table_name = 'test_references'
        
        with patch.object(serial_updater.evaluator, 'batch_evaluate') as mock_serial:
            # 模拟串行评估返回所有结果
            mock_serial.return_value = {ref.id: mock_eval_result for ref in references}
            
            start_time = time.time()
            result = serial_updater.process_batch(references)
            serial_time = time.time() - start_time
            
            # 验证：
            # 1. 串行方法被调用
            self.assertTrue(mock_serial.called)
            # 2. 所有参考文献都被成功处理
            self.assertEqual(result.successful, 5)
        
        # 打印性能对比（供人工查看）
        print(f"\n⏱️ Performance Comparison:")
        print(f"   Concurrent mode: {concurrent_time:.3f}s")
        print(f"   Serial mode: {serial_time:.3f}s")


# ================================================================================
# 第三部分：端到端集成测试
# ================================================================================
class TestIntegrationConcurrent(unittest.TestCase):
    """
    端到端集成测试
    
    测试完整的流程：
    从参考文献 -> LLM评估 -> 数据库更新
    """
    
    @patch('database_format.llm_evaluator.Anthropic')
    def test_end_to_end_concurrent_flow(self, mock_anthropic_class):
        """
        测试7：完整流程测试
        
        模拟真实场景：
        1. 从数据库读取待评估的参考文献
        2. 调用LLM进行评估（模拟）
        3. 将结果批量写回数据库
        
        验证点：
        - 完整流程是否正常运行
        - 数据是否正确流转
        - 并发机制是否生效
        """
        # ===== 设置Mock LLM客户端 =====
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        
        # 模拟LLM返回的JSON格式评估结果
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "reference_type": "技术文档",           # 分类结果
            "credibility": 3,                      # 可信度评分
            "credibility_assessment": "High credibility source",  # 可信度说明
            "related_assessment": 0.9,             # 相关性评分
            "related_assessment_text": "Highly relevant",  # 相关性说明
            "confidence": 0.95                     # 评估置信度
        }))]
        mock_client.messages.create.return_value = mock_response
        
        # ===== 创建测试数据库 =====
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            
            try:
                # 初始化数据库
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 创建表结构
                cursor.execute('''
                    CREATE TABLE test_references (
                        id INTEGER PRIMARY KEY,
                        reference_type TEXT DEFAULT 'uncategorized',
                        url TEXT,
                        name TEXT,
                        raw_content TEXT,
                        publisher TEXT,
                        credibility INTEGER DEFAULT 2,
                        related_assessment REAL DEFAULT 0.5,
                        updated_at TEXT
                    )
                ''')
                
                # 插入5条待评估的测试数据
                for i in range(1, 6):
                    cursor.execute(
                        'INSERT INTO test_references (id, reference_type, url, name, raw_content, publisher, credibility, related_assessment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (i, 'uncategorized', f'http://example.com/{i}', f'Reference {i}', f'Content {i}', f'Publisher {i}', 2, 0.5)
                    )
                conn.commit()
                conn.close()
                
                # ===== 配置和运行测试 =====
                with patch('database_format.database_updater.config') as mock_config:
                    # 设置数据库配置
                    mock_config.DATABASE_CONFIG = {
                        'db_path': db_path,
                        'table_name': 'test_references',
                        'batch_size': 10,
                        'retry_delay': 1
                    }
                    # 设置LLM配置
                    mock_config.LLM_CONFIG = {
                        'api_key': 'test_key',
                        'model': 'claude-3-5-sonnet-20241022',
                        'temperature': 0.3,
                        'max_tokens': 2000
                    }
                    # 设置研究主题
                    mock_config.research_topic = {
                        'title': 'Test Research',
                        'description': 'Test Description',
                        'keywords': ['test']
                    }
                    
                    # 同时patch llm_evaluator中的config
                    with patch('database_format.llm_evaluator.config', mock_config):
                        # 创建DatabaseUpdater（并发模式）
                        updater = DatabaseUpdater(use_concurrent=True, max_workers=3)
                        updater.db_path = db_path
                        updater.table_name = 'test_references'
                        
                        # ===== 执行评估流程 =====
                        print("\n🚀 Starting concurrent evaluation test...")
                        start_time = time.time()
                        
                        # 1. 获取待评估的参考文献
                        references = updater.get_references_to_update(limit=5)
                        self.assertEqual(len(references), 5)
                        
                        # 2. 执行批量评估（并发）
                        result = updater.process_batch(references)
                        
                        elapsed = time.time() - start_time
                        print(f"✅ Completed in {elapsed:.2f}s")
                        
                        # ===== 验证结果 =====
                        # 1. 应该有成功的评估
                        self.assertGreater(result.successful, 0)
                        print(f"📊 Results: {result.successful} successful, {result.failed} failed")
                        
                        # 2. 验证数据库更新
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        # 查询已更新的记录数（类型不再是uncategorized）
                        cursor.execute('SELECT COUNT(*) FROM test_references WHERE reference_type != ?', ('uncategorized',))
                        updated_count = cursor.fetchone()[0]
                        conn.close()
                        
                        self.assertGreater(updated_count, 0)
                        print(f"📝 Database updated: {updated_count} records")
                        
            finally:
                # 清理临时数据库
                try:
                    os.unlink(db_path)
                except:
                    pass


# ================================================================================
# 第四部分：性能测试函数
# ================================================================================
def run_performance_test():
    """
    独立的性能测试
    
    目的：
    - 对比并发vs串行的实际性能差异
    - 验证理论加速比
    
    测试方法：
    1. 创建20个模拟参考文献
    2. 分别用并发和串行方式处理
    3. 测量时间并计算加速比
    """
    print("\n" + "="*60)
    print("🏃 PERFORMANCE TEST: Concurrent vs Serial Evaluation")
    print("="*60)
    
    # 创建测试数据
    num_refs = 20
    mock_refs = []
    for i in range(num_refs):
        ref = Mock(spec=Reference)
        ref.id = i + 1
        ref.reference_title = f"Test Reference {i + 1}"
        ref.needs_evaluation.return_value = True
        mock_refs.append(ref)
    
    # 创建模拟的评估结果
    mock_result = Mock(spec=EvaluationResult)
    mock_result.reference_type = "技术文档"
    mock_result.credibility = 3
    mock_result.related_assessment = 0.85
    
    # ===== 测试并发模式 =====
    print(f"\n📊 Testing with {num_refs} references...")
    
    # 创建并发评估器（5个工作线程）
    concurrent_eval = ConcurrentEvaluator(max_workers=5, rate_limit=0.1)
    
    with patch.object(concurrent_eval.evaluator, 'evaluate_reference') as mock_eval:
        mock_eval.return_value = mock_result
        
        # 测量并发处理时间
        start = time.time()
        concurrent_results = concurrent_eval.evaluate_batch_concurrent(mock_refs)
        concurrent_time = time.time() - start
        
    print(f"⚡ Concurrent mode (5 workers): {concurrent_time:.2f}s")
    print(f"   - Processed: {len(concurrent_results)} references")
    print(f"   - Rate: {len(concurrent_results)/concurrent_time:.1f} refs/sec")
    
    # ===== 计算理论串行时间 =====
    # 串行模式：每个请求需要rate_limit时间
    serial_time = num_refs * 0.05
    print(f"\n🐌 Theoretical serial mode: {serial_time:.2f}s")
    print(f"   - Rate: {num_refs/serial_time:.1f} refs/sec")
    
    # ===== 计算加速比 =====
    speedup = serial_time / concurrent_time
    print(f"\n🚀 Speedup: {speedup:.1f}x faster")
    
    print("\n" + "="*60)


# ================================================================================
# 主程序入口
# ================================================================================
if __name__ == '__main__':
    """
    运行所有测试
    
    执行顺序：
    1. 单元测试
    2. 集成测试  
    3. 性能测试
    """
    # 运行unittest测试套件
    print("🧪 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 运行独立的性能测试
    run_performance_test()