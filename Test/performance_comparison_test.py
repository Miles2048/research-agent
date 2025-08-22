#!/usr/bin/env python3
"""
性能对比测试：直观展示并发vs串行的差异
模拟真实LLM调用的1.5秒延迟
"""

import sys
import os
import time
from datetime import datetime
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_format.concurrent_evaluator import ConcurrentEvaluator
from database_format.llm_evaluator import LLMEvaluator
from database_format.models import Reference, EvaluationResult


def create_mock_references(count: int):
    """创建指定数量的模拟参考文献"""
    refs = []
    for i in range(count):
        ref = Mock(spec=Reference)
        ref.id = i + 1
        ref.reference_title = f"参考文献 {i + 1}: 人工智能在医疗领域的应用研究"
        ref.reference_url = f"http://example.com/research/{i + 1}"
        ref.reference_content = f"这是关于AI在医疗领域应用的研究内容 {i + 1}..."
        ref.publisher = f"医学期刊 {i + 1}"
        ref.needs_evaluation.return_value = True
        refs.append(ref)
    return refs


def create_mock_evaluator_result():
    """创建模拟的评估结果"""
    def mock_evaluate(ref):
        # 模拟真实LLM API的处理时间（1.5秒）
        time.sleep(1.5)
        
        result = Mock(spec=EvaluationResult)
        result.reference_type = "学术论文"
        result.credibility = 3
        result.related_assessment = 0.92
        result.validate.return_value = True
        return result
    
    return mock_evaluate


def test_concurrent_performance():
    """测试并发模式性能"""
    print("🚀 并发模式测试")
    print("-" * 40)
    
    # 创建测试数据
    refs = create_mock_references(12)  # 12个参考文献
    
    # 创建并发评估器（4个工作线程）
    evaluator = ConcurrentEvaluator(
        max_workers=4,      # 4个工作线程
        rate_limit=0.1      # 0.1秒间隔（测试用）
    )
    
    # 模拟LLM调用
    with patch.object(evaluator.evaluator, 'evaluate_reference') as mock_eval:
        mock_eval.side_effect = create_mock_evaluator_result()
        
        print(f"📚 评估 {len(refs)} 个参考文献（4个工作线程）...")
        start_time = time.time()
        
        results = evaluator.evaluate_batch_concurrent(refs)
        
        end_time = time.time()
        elapsed = end_time - start_time
    
    print(f"✅ 并发模式完成:")
    print(f"   ⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"   🎯 成功处理: {len(results)} 个")
    print(f"   📈 处理速率: {len(results)/elapsed:.1f} 个/秒")
    print(f"   🧵 工作线程: 4 个")
    
    return elapsed, len(results)


def test_serial_performance():
    """测试串行模式性能（模拟）"""
    print("\n🐌 串行模式测试")
    print("-" * 40)
    
    # 创建测试数据
    refs = create_mock_references(12)  # 相同数量的参考文献
    
    print(f"📚 评估 {len(refs)} 个参考文献（逐个处理）...")
    start_time = time.time()
    
    # 模拟串行处理：逐个调用，每个1.5秒
    results = []
    mock_evaluate = create_mock_evaluator_result()
    
    for i, ref in enumerate(refs, 1):
        print(f"   [{i}/{len(refs)}] 处理参考文献 {ref.id}...", end="", flush=True)
        result = mock_evaluate(ref)
        results.append(result)
        print(" ✓")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"✅ 串行模式完成:")
    print(f"   ⏱️  总耗时: {elapsed:.1f} 秒") 
    print(f"   🎯 成功处理: {len(results)} 个")
    print(f"   📈 处理速率: {len(results)/elapsed:.1f} 个/秒")
    print(f"   🧵 工作线程: 1 个")
    
    return elapsed, len(results)


def main():
    """主测试函数"""
    print("=" * 60)
    print("🔬 LLM并发评估性能对比测试")
    print(f"🕐 开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    print("\n💡 测试场景:")
    print("   - 模拟真实LLM API调用时间: 1.5秒/次")
    print("   - 评估12个参考文献") 
    print("   - 对比并发vs串行处理")
    
    # 测试并发模式
    concurrent_time, concurrent_count = test_concurrent_performance()
    
    # 测试串行模式
    serial_time, serial_count = test_serial_performance()
    
    # 性能对比分析
    print("\n" + "=" * 60)
    print("📊 性能对比分析")
    print("=" * 60)
    
    speedup = serial_time / concurrent_time
    time_saved = serial_time - concurrent_time
    efficiency = (speedup / 4) * 100  # 4个工作线程的理论效率
    
    print(f"📈 加速比: {speedup:.1f}x")
    print(f"⏰ 节省时间: {time_saved:.1f} 秒 ({time_saved/60:.1f} 分钟)")
    print(f"🎯 并发效率: {efficiency:.1f}%")
    
    # 成本分析（假设每次调用$0.01）
    cost_per_call = 0.01
    total_cost = len(refs) * cost_per_call
    print(f"💰 节省的等待时间价值: ${time_saved * 0.1:.2f} (按$0.1/秒计算)")
    
    print("\n🏆 结论:")
    if speedup >= 2.0:
        print(f"   ✅ 并发模式显著提升性能 ({speedup:.1f}倍加速)")
        print(f"   ✅ 实际应用中建议使用并发模式")
    elif speedup >= 1.5:
        print(f"   ⚡ 并发模式适度提升性能 ({speedup:.1f}倍加速)")
        print(f"   💡 可根据API限制调整线程数")
    else:
        print(f"   ⚠️  并发优势不明显，可能需要调整参数")
    
    print(f"\n📝 推荐设置:")
    print(f"   - 工作线程数: 4-8 个")
    print(f"   - API调用间隔: 1.0-2.0 秒")
    print(f"   - 适用场景: 批量评估 >10 个参考文献")


if __name__ == "__main__":
    main()