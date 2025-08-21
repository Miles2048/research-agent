#!/usr/bin/env python3
"""
数据库字段填充系统的Python函数接口
可以直接在Python代码中调用这些函数
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def run_evaluation(limit=None, verbose=False):
    """
    运行数据库评估
    
    Args:
        limit (int, optional): 处理记录数限制，None表示处理所有
        verbose (bool): 是否启用详细日志
    
    Returns:
        int: 返回码，0表示成功
    """
    from run_database_format import run_database_format
    return run_database_format(limit=limit, verbose=verbose)

def get_stats():
    """
    获取数据库统计信息
    
    Returns:
        int: 返回码，0表示成功
    """
    from run_database_format import show_stats
    return show_stats()

def preview_data(limit=10):
    """
    预览要处理的数据
    
    Args:
        limit (int): 预览记录数
    
    Returns:
        int: 返回码，0表示成功
    """
    from run_database_format import preview_records
    return preview_records(limit=limit)

# 便捷函数
def process_all():
    """处理所有记录"""
    return run_evaluation()

def process_batch(count=20):
    """处理指定数量的记录"""
    return run_evaluation(limit=count)

def quick_stats():
    """快速查看统计"""
    return get_stats()

if __name__ == "__main__":
    # 示例用法
    print("=== 数据库统计 ===")
    quick_stats()
    
    print("\n=== 预览5条记录 ===")
    preview_data(5)
    
    print("\n=== 处理10条记录 ===")
    process_batch(10)