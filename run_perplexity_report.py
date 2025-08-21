#!/usr/bin/env python3
"""
运行 Perplexity 报告生成器的脚本
解决相对导入问题
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# 导入并运行
from topic_report_perplexity.report_perplexity_sonar import test_single_topic, generate_all_topic_reports

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 如果提供了参数，测试特定的topic
        topic_id = sys.argv[1]
        print(f"生成 {topic_id} 的 Perplexity 报告...")
        test_single_topic(topic_id)
    else:
        # 否则生成所有topic的报告
        print("生成所有 topic 的 Perplexity 报告...")
        generate_all_topic_reports()