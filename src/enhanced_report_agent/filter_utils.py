#!/usr/bin/env python3
"""
Enhanced Report Agent - 数据源筛选工具
用于从大量source_data中筛选有限数量的有用文件
"""

import random
from typing import List, Dict

def filter_related_data(articles: List[Dict], out_data_count: int) -> List[Dict]:
    """
    从articles中筛选出out_data_count个有用的文件（当前为随机选取，后续可扩展为更智能的策略）

    Args:
        articles: 所有文章的列表，每个元素为{"title": ..., "content": ..., "length": ...}
        out_data_count: 需要输出的文件数量

    Returns:
        筛选后的文章列表
    """
    if not articles or out_data_count <= 0:
        return []

    # 如果数量足够，直接返回全部
    if len(articles) <= out_data_count:
        return articles.copy()

    # 随机选取out_data_count个文件（后续可替换为更智能的筛选逻辑）
    selected = random.sample(articles, out_data_count)
    return selected