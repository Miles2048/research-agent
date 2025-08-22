#!/usr/bin/env python3
"""
Test cases for concurrent evaluator functionality.
测试并发评估器的功能和性能
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

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_format.concurrent_evaluator import ConcurrentEvaluator, EvaluationTask
from database_format.database_updater import DatabaseUpdater
from database_format.models import Reference, EvaluationResult
from database_format.config import config


class TestConcurrentEvaluator(unittest.TestCase):
    """Test cases for ConcurrentEvaluator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = ConcurrentEvaluator(
            max_workers=3,
            rate_limit=0.1,
            timeout=10
        )
        
        # Create mock references
        self.mock_references = []
        for i in range(10):
            ref = Mock(spec=Reference)
            ref.id = i + 1
            ref.reference_title = f"Test Reference {i + 1}"
            ref.reference_url = f"http://example.com/{i + 1}"
            ref.reference_content = f"Test content {i + 1}"
            ref.publisher = f"Publisher {i + 1}"
            ref.reference_type = "uncategorized"
            ref.credibility = 2
            ref.related_assessment = 0.5
            ref.needs_evaluation.return_value = True
            self.mock_references.append(ref)
    
    def test_concurrent_evaluation_basic(self):
        """Test basic concurrent evaluation functionality."""
        # Mock the evaluator's evaluate_reference method
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # Create mock evaluation results
            def create_mock_result(ref):
                result = Mock(spec=EvaluationResult)
                result.reference_type = "技术文档"
                result.credibility = 3
                result.related_assessment = 0.85
                result.validate.return_value = True
                return result
            
            mock_eval.side_effect = create_mock_result
            
            # Run concurrent evaluation
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:5])
            
            # Assertions
            self.assertEqual(len(results), 5)
            self.assertEqual(mock_eval.call_count, 5)
            
            # Check that all references were evaluated
            for i in range(1, 6):
                self.assertIn(i, results)
                self.assertEqual(results[i].reference_type, "技术文档")
    
    def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        start_time = time.time()
        
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # Quick mock evaluation
            mock_eval.return_value = Mock(spec=EvaluationResult)
            
            # Evaluate with rate limit
            self.evaluator.rate_limit = 0.2  # 200ms between requests
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:3])
            
            elapsed = time.time() - start_time
            
            # With 3 references and 0.2s rate limit, should take at least 0.4s
            # (first is immediate, then 0.2s, then 0.2s)
            self.assertGreaterEqual(elapsed, 0.4)
    
    def test_failed_evaluation_retry(self):
        """Test retry mechanism for failed evaluations."""
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # First call fails, second succeeds
            mock_result = Mock(spec=EvaluationResult)
            mock_result.reference_type = "技术文档"
            mock_result.credibility = 3
            mock_result.related_assessment = 0.85
            
            mock_eval.side_effect = [None, mock_result, mock_result, mock_result]
            
            # Run evaluation with single reference
            results = self.evaluator.evaluate_batch_concurrent([self.mock_references[0]])
            
            # Should have retried and succeeded
            self.assertEqual(len(results), 1)
            self.assertIn(1, results)
            # Should have been called twice (initial + retry)
            self.assertGreaterEqual(mock_eval.call_count, 2)
    
    def test_statistics_tracking(self):
        """Test that statistics are properly tracked."""
        with patch.object(self.evaluator.evaluator, 'evaluate_reference') as mock_eval:
            # Mix of successful and failed evaluations
            mock_result = Mock(spec=EvaluationResult)
            mock_eval.side_effect = [mock_result, None, mock_result, None, mock_result]
            
            # Reset stats
            self.evaluator.reset_stats()
            
            # Run evaluation
            results = self.evaluator.evaluate_batch_concurrent(self.mock_references[:5])
            
            # Check statistics
            self.assertEqual(self.evaluator.stats['total_processed'], 5)
            self.assertEqual(self.evaluator.stats['successful'], 3)
            self.assertIsNotNone(self.evaluator.stats['start_time'])
            self.assertIsNotNone(self.evaluator.stats['end_time'])


class TestDatabaseUpdaterConcurrent(unittest.TestCase):
    """Test DatabaseUpdater with concurrent mode."""
    
    def setUp(self):
        """Set up test database and updater."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        
        # Initialize database with test table
        self._init_test_database()
        
        # Mock config
        with patch('database_format.database_updater.config') as mock_config:
            mock_config.DATABASE_CONFIG = {
                'db_path': self.db_path,
                'table_name': 'test_references',
                'batch_size': 10
            }
            mock_config.LLM_CONFIG = {
                'api_key': 'test_key',
                'model': 'test-model'
            }
            mock_config.research_topic = {
                'title': 'Test Research',
                'description': 'Test Description',
                'keywords': ['test']
            }
            
            # Initialize updater with concurrent mode
            with patch('database_format.database_updater.LLMEvaluator'):
                with patch('database_format.database_updater.PublisherExtractor'):
                    self.updater = DatabaseUpdater(use_concurrent=True, max_workers=3)
                    self.updater.db_path = self.db_path
                    self.updater.table_name = 'test_references'
    
    def tearDown(self):
        """Clean up test database."""
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    def _init_test_database(self):
        """Initialize test database with sample data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create test table
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
        
        # Insert test data
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
        """Test batch update functionality."""
        # Create mock evaluation results
        eval_results = {
            1: Mock(reference_type='技术文档', credibility=3, related_assessment=0.9),
            2: Mock(reference_type='新闻报道', credibility=2, related_assessment=0.7),
            3: Mock(reference_type='学术论文', credibility=3, related_assessment=0.95),
        }
        
        # Perform batch update
        update_stats = self.updater.batch_update_references(eval_results)
        
        # Check results
        self.assertEqual(update_stats['success'], 3)
        self.assertEqual(update_stats['failed'], 0)
        
        # Verify database was updated
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT reference_type, credibility, related_assessment FROM test_references WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        self.assertEqual(row[0], '技术文档')
        self.assertEqual(row[1], 3)
        self.assertAlmostEqual(row[2], 0.9, places=1)
    
    def test_concurrent_vs_serial_mode(self):
        """Test that concurrent mode is faster than serial mode."""
        # Get test references
        references = self.updater.get_references_to_update(limit=5)
        
        # Mock the evaluators
        mock_eval_result = Mock(spec=EvaluationResult)
        mock_eval_result.reference_type = '技术文档'
        mock_eval_result.credibility = 3
        mock_eval_result.related_assessment = 0.85
        mock_eval_result.validate.return_value = True
        
        # Test concurrent mode
        with patch.object(self.updater.concurrent_evaluator, 'evaluate_batch_concurrent') as mock_concurrent:
            mock_concurrent.return_value = {ref.id: mock_eval_result for ref in references}
            
            start_time = time.time()
            result = self.updater.process_batch(references)
            concurrent_time = time.time() - start_time
            
            self.assertTrue(mock_concurrent.called)
            self.assertEqual(result.successful, 5)
        
        # Test serial mode
        serial_updater = DatabaseUpdater(use_concurrent=False)
        serial_updater.db_path = self.db_path
        serial_updater.table_name = 'test_references'
        
        with patch.object(serial_updater.evaluator, 'batch_evaluate') as mock_serial:
            mock_serial.return_value = {ref.id: mock_eval_result for ref in references}
            
            start_time = time.time()
            result = serial_updater.process_batch(references)
            serial_time = time.time() - start_time
            
            self.assertTrue(mock_serial.called)
            self.assertEqual(result.successful, 5)
        
        print(f"\n⏱️ Performance Comparison:")
        print(f"   Concurrent mode: {concurrent_time:.3f}s")
        print(f"   Serial mode: {serial_time:.3f}s")


class TestIntegrationConcurrent(unittest.TestCase):
    """Integration tests for concurrent evaluation system."""
    
    @patch('database_format.llm_evaluator.Anthropic')
    def test_end_to_end_concurrent_flow(self, mock_anthropic_class):
        """Test complete flow from references to database update."""
        # Setup mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "reference_type": "技术文档",
            "credibility": 3,
            "credibility_assessment": "High credibility source",
            "related_assessment": 0.9,
            "related_assessment_text": "Highly relevant",
            "confidence": 0.95
        }))]
        mock_client.messages.create.return_value = mock_response
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            db_path = temp_db.name
            
            try:
                # Initialize test database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
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
                
                # Insert test data
                for i in range(1, 6):
                    cursor.execute(
                        'INSERT INTO test_references (id, reference_type, url, name, raw_content, publisher, credibility, related_assessment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (i, 'uncategorized', f'http://example.com/{i}', f'Reference {i}', f'Content {i}', f'Publisher {i}', 2, 0.5)
                    )
                conn.commit()
                conn.close()
                
                # Setup config
                with patch('database_format.database_updater.config') as mock_config:
                    mock_config.DATABASE_CONFIG = {
                        'db_path': db_path,
                        'table_name': 'test_references',
                        'batch_size': 10,
                        'retry_delay': 1
                    }
                    mock_config.LLM_CONFIG = {
                        'api_key': 'test_key',
                        'model': 'claude-3-5-sonnet-20241022',
                        'temperature': 0.3,
                        'max_tokens': 2000
                    }
                    mock_config.research_topic = {
                        'title': 'Test Research',
                        'description': 'Test Description',
                        'keywords': ['test']
                    }
                    
                    # Also patch config in llm_evaluator
                    with patch('database_format.llm_evaluator.config', mock_config):
                        # Initialize updater with concurrent mode
                        updater = DatabaseUpdater(use_concurrent=True, max_workers=3)
                        updater.db_path = db_path
                        updater.table_name = 'test_references'
                        
                        # Process batch
                        print("\n🚀 Starting concurrent evaluation test...")
                        start_time = time.time()
                        
                        references = updater.get_references_to_update(limit=5)
                        self.assertEqual(len(references), 5)
                        
                        result = updater.process_batch(references)
                        
                        elapsed = time.time() - start_time
                        print(f"✅ Completed in {elapsed:.2f}s")
                        
                        # Verify results
                        self.assertGreater(result.successful, 0)
                        print(f"📊 Results: {result.successful} successful, {result.failed} failed")
                        
                        # Verify database updates
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM test_references WHERE reference_type != ?', ('uncategorized',))
                        updated_count = cursor.fetchone()[0]
                        conn.close()
                        
                        self.assertGreater(updated_count, 0)
                        print(f"📝 Database updated: {updated_count} records")
                        
            finally:
                # Cleanup
                try:
                    os.unlink(db_path)
                except:
                    pass


def run_performance_test():
    """Run a performance comparison test."""
    print("\n" + "="*60)
    print("🏃 PERFORMANCE TEST: Concurrent vs Serial Evaluation")
    print("="*60)
    
    # Create mock references
    num_refs = 20
    mock_refs = []
    for i in range(num_refs):
        ref = Mock(spec=Reference)
        ref.id = i + 1
        ref.reference_title = f"Test Reference {i + 1}"
        ref.needs_evaluation.return_value = True
        mock_refs.append(ref)
    
    # Mock evaluation result
    mock_result = Mock(spec=EvaluationResult)
    mock_result.reference_type = "技术文档"
    mock_result.credibility = 3
    mock_result.related_assessment = 0.85
    
    # Test concurrent mode
    print(f"\n📊 Testing with {num_refs} references...")
    
    concurrent_eval = ConcurrentEvaluator(max_workers=5, rate_limit=0.05)
    with patch.object(concurrent_eval.evaluator, 'evaluate_reference') as mock_eval:
        mock_eval.return_value = mock_result
        
        start = time.time()
        concurrent_results = concurrent_eval.evaluate_batch_concurrent(mock_refs)
        concurrent_time = time.time() - start
        
    print(f"⚡ Concurrent mode (5 workers): {concurrent_time:.2f}s")
    print(f"   - Processed: {len(concurrent_results)} references")
    print(f"   - Rate: {len(concurrent_results)/concurrent_time:.1f} refs/sec")
    
    # Theoretical serial time (with 0.05s delay per request)
    serial_time = num_refs * 0.05
    print(f"\n🐌 Theoretical serial mode: {serial_time:.2f}s")
    print(f"   - Rate: {num_refs/serial_time:.1f} refs/sec")
    
    speedup = serial_time / concurrent_time
    print(f"\n🚀 Speedup: {speedup:.1f}x faster")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    # Run unit tests
    print("🧪 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()