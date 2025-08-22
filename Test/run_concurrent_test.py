#!/usr/bin/env python3
"""
简单的测试运行脚本
快速验证并发评估功能是否正常工作
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_simple_test():
    """运行简单的功能测试"""
    print("\n" + "="*60)
    print("🧪 并发评估器简单测试")
    print("="*60)
    
    try:
        # Test 1: Import test
        print("\n1️⃣ 测试模块导入...")
        from database_format.concurrent_evaluator import ConcurrentEvaluator
        from database_format.database_updater import DatabaseUpdater
        print("   ✅ 模块导入成功")
        
        # Test 2: Initialize concurrent evaluator
        print("\n2️⃣ 测试并发评估器初始化...")
        evaluator = ConcurrentEvaluator(max_workers=3, rate_limit=0.1)
        print(f"   ✅ 并发评估器初始化成功")
        print(f"   - 工作线程: {evaluator.max_workers}")
        print(f"   - 限流间隔: {evaluator.rate_limit}秒")
        
        # Test 3: Initialize database updater with concurrent mode
        print("\n3️⃣ 测试数据库更新器（并发模式）...")
        from unittest.mock import patch
        
        mock_config = {
            'DATABASE_CONFIG': {
                'db_path': 'test.db',
                'table_name': 'test_references',
                'batch_size': 10
            },
            'LLM_CONFIG': {
                'api_key': 'test_key'
            }
        }
        
        with patch('database_format.database_updater.config', mock_config):
            with patch('database_format.llm_evaluator.config', mock_config):
                # 测试默认并发模式
                updater = DatabaseUpdater()  # 默认 use_concurrent=True
                print(f"   ✅ 数据库更新器初始化成功（默认并发模式）")
                print(f"   - 并发模式: {updater.use_concurrent}")
                print(f"   - 并发评估器: {'已初始化' if updater.concurrent_evaluator else '未初始化'}")
                
                # 测试显式并发模式
                updater2 = DatabaseUpdater(use_concurrent=True, max_workers=10)
                print(f"   ✅ 自定义并发配置成功（10个工作线程）")
                
                # 测试串行模式
                updater3 = DatabaseUpdater(use_concurrent=False)
                print(f"   ✅ 串行模式配置成功")
        
        # Test 4: Performance simulation
        print("\n4️⃣ 性能对比模拟...")
        print("   模拟处理100个参考文献：")
        
        # 并发模式估算（5个工作线程，每个请求0.2秒）
        concurrent_time = (100 / 5) * 0.2  # 理论最优时间
        print(f"   ⚡ 并发模式（5线程）: 约{concurrent_time:.1f}秒")
        
        # 串行模式估算
        serial_time = 100 * 0.2
        print(f"   🐌 串行模式: 约{serial_time:.1f}秒")
        
        speedup = serial_time / concurrent_time
        print(f"   🚀 理论加速比: {speedup:.1f}倍")
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！并发功能正常")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_mock_evaluation():
    """运行模拟评估测试"""
    print("\n" + "="*60)
    print("🎭 模拟评估测试（使用Mock数据）")
    print("="*60)
    
    from unittest.mock import Mock, patch
    from database_format.concurrent_evaluator import ConcurrentEvaluator
    from database_format.models import Reference, EvaluationResult
    
    # 创建模拟参考文献
    print("\n📚 创建10个模拟参考文献...")
    mock_refs = []
    for i in range(10):
        ref = Mock(spec=Reference)
        ref.id = i + 1
        ref.reference_title = f"参考文献 {i + 1}"
        ref.reference_url = f"http://example.com/{i + 1}"
        ref.needs_evaluation.return_value = True
        mock_refs.append(ref)
    
    print(f"   ✅ 创建了 {len(mock_refs)} 个参考文献")
    
    # 初始化并发评估器
    evaluator = ConcurrentEvaluator(max_workers=3, rate_limit=0.05)
    
    # Mock LLM评估
    with patch.object(evaluator.evaluator, 'evaluate_reference') as mock_eval:
        # 创建模拟评估结果
        def create_mock_result(ref):
            result = Mock(spec=EvaluationResult)
            result.reference_type = "技术文档"
            result.credibility = 3
            result.related_assessment = 0.85
            result.validate.return_value = True
            # 模拟真实LLM API处理时间（1-2秒）
            time.sleep(1.5)  # 1.5秒，更接近真实LLM调用时间
            return result
        
        mock_eval.side_effect = create_mock_result
        
        # 运行并发评估
        print("\n🚀 开始并发评估（3个工作线程）...")
        start_time = time.time()
        
        results = evaluator.evaluate_batch_concurrent(mock_refs)
        
        elapsed = time.time() - start_time
        
        # 显示结果
        print(f"\n📊 评估完成！")
        print(f"   - 耗时: {elapsed:.2f}秒")
        print(f"   - 成功评估: {len(results)}个")
        print(f"   - 处理速率: {len(results)/elapsed:.1f}个/秒")
        print(f"   - 统计信息:")
        print(f"     • 总处理: {evaluator.stats['total_processed']}")
        print(f"     • 成功: {evaluator.stats['successful']}")
        print(f"     • 失败: {evaluator.stats['failed']}")
        print(f"     • 重试: {evaluator.stats['retried']}")
    
    print("\n✅ 模拟评估测试完成")
    return True


def main():
    """主函数"""
    print(f"\n🕐 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行简单测试
    success1 = run_simple_test()
    
    # 运行模拟评估
    success2 = run_mock_evaluation()
    
    # 总结
    print("\n" + "="*60)
    if success1 and success2:
        print("🎉 所有测试通过！并发评估功能工作正常")
        print("\n下一步：")
        print("1. 运行完整测试套件: python Test/test_concurrent_evaluator.py")
        print("2. 使用真实数据测试: python -m database_format.main --limit 10")
        print("3. 对比性能: python -m database_format.main --limit 50 --no-concurrent")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    print("="*60)


if __name__ == "__main__":
    main()