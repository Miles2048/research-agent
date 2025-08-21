#!/usr/bin/env python3
"""
测试报告推送功能
"""

import os
import sys

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from push_report_to_pg import ReportPusher


def test_report_push():
    """测试报告推送"""
    print("🧪 测试报告推送功能")
    print("=" * 60)
    
    # 创建推送器
    pusher = ReportPusher()
    
    # 测试连接
    if not pusher.test_connection():
        print("❌ 数据库连接失败")
        return
    
    # 创建表
    pusher.create_table_if_not_exists()
    
    # 测试推送一个示例报告
    test_report_content = """# 测试报告

## 概述
这是一个测试报告，用于验证报告推送功能是否正常工作。

## 内容
- 测试项目1：数据库连接
- 测试项目2：数据插入
- 测试项目3：字段映射

## 结论
如果您能看到这个报告，说明推送功能正常。

---
生成时间：2024-08-20
"""
    
    # 从request.json获取参数
    import json
    request_json_path = "src/request.json"
    if os.path.exists(request_json_path):
        with open(request_json_path, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        
        company_id = int(request_data.get('company', {}).get('company_id', 3))
        artifact_id = request_data.get('artifact_id', 1)
        user_id = request_data.get('user_id', 3)
        
        print(f"\n📋 使用参数:")
        print(f"   company_id: {company_id}")
        print(f"   artifact_id: {artifact_id}")
        print(f"   user_id: {user_id}")
    else:
        company_id = 3
        artifact_id = 1
        user_id = 3
        print("\n⚠️ request.json不存在，使用默认参数")
    
    # 推送测试报告
    success = pusher.push_report(
        report_name="测试报告 - 功能验证",
        report_content=test_report_content,
        company_id=company_id,
        artifact_id=artifact_id,
        created_by=user_id
    )
    
    if success:
        print("\n✅ 测试成功！")
    else:
        print("\n❌ 测试失败！")
    
    # 测试从文件推送
    print("\n" + "=" * 60)
    print("📄 测试从文件推送...")
    
    # 查找一个实际的报告文件
    test_files = [
        "src/citation_report.md",
        "results/topic_1_产品国际化护照构建/topic_1_report_4.md",
        "results/topic_1_产品国际化护照构建/enhanced_report.md"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📄 找到测试文件: {test_file}")
            success = pusher.push_report_from_file(
                report_file_path=test_file,
                report_name=f"测试推送 - {os.path.basename(test_file)}",
                company_id=company_id,
                artifact_id=artifact_id,
                created_by=user_id
            )
            break
    else:
        print("⚠️ 没有找到可用的测试文件")


if __name__ == "__main__":
    test_report_push()