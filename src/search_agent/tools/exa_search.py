#!/usr/bin/env python3
"""
Exa搜索工具模块
提供与Exa API的集成，用于执行网络搜索
"""

import os
import requests
from typing import List, Dict, Any
from exa_py import Exa

# 配置常量
SNIPPET_LENGTH = 70000  # snippet长度，增加到70k字符以保存更多内容
FULL_TEXT_LENGTH = 70000  # 完整文本长度限制，70k字符

def perform_exa_search(query: str, num_results: int = 6) -> List[Dict[str, str]]:
    """使用 Exa API 执行网络搜索
    
    Args:
        query: 搜索查询字符串
        num_results: 返回结果数量
        
    Returns:
        包含标题、URL和摘要的搜索结果列表
        
    """
    api_key = os.getenv("EXA_API_KEY")
    
    if not api_key:
        print("EXA_API_KEY not found, using fallback results")
        return get_fallback_results(query, num_results)
        

    # 初始化 Exa 客户端
    client = Exa(api_key=api_key)
    
    response = client.search_and_contents(
        query,
        text=True,
        type="auto",
        num_results=num_results,
        # summary={"query":summary_prompt} # we dont need classification in this case
        summary=True # we dont need classification in this case
        
    )
    
    # # 执行搜索
    # response = client.search(
    #     query,
    #     num_results=num_results,
    #     use_autoprompt=True,
    #     include_domains=[],
    #     exclude_domains=[],
    #     type="keyword"
    # )
    
    # 获取完整内容
   
    contents = response.results  # search_and_contents 已包含内容
    
    # 格式化结果
    results = []
    for i, result in enumerate(response.results[:num_results]):
        # 获取对应的内容
        content = contents[i] if i < len(contents) else None
        full_text = content.text if content and hasattr(content, 'text') and content.text else "No content available"
        
        # 生成snippet（使用配置的长度）和保存完整文本
        # 限制full_text的长度到50k字符
        truncated_full_text = full_text[:FULL_TEXT_LENGTH] if len(full_text) > FULL_TEXT_LENGTH else full_text
        snippet = truncated_full_text[:SNIPPET_LENGTH] + "..." if len(truncated_full_text) > SNIPPET_LENGTH else truncated_full_text
        
        results.append({
            "title": result.title or "No Title",
            "url": result.url or "No URL",
            "snippet": snippet,
            "full_text": truncated_full_text  # 保存限制长度后的完整文本（最多50k字符）
        })
        
    print(f"✅ Exa search successful: found {len(results)} results")
    return results
        


def get_fallback_results(query: str, num_results: int) -> List[Dict[str, str]]:
    """生成模拟的搜索结果
    
    Args:
        query: 搜索查询
        num_results: 结果数量
        
    Returns:
        模拟的搜索结果列表
    """
    return [
        {
            "title": f"Search Result {i+1} for: {query}",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"This is a simulated search result snippet for query '{query}'. This would contain relevant information about the topic. " * 10,  # 重复10次以模拟更长的内容
            "full_text": f"This is a simulated full text content for query '{query}'. In a real scenario, this would contain the complete webpage content with much more detailed information about the topic, including comprehensive explanations, examples, and related information that would be useful for research purposes. " * 20  # 重复20次以模拟完整内容
        }
        for i in range(num_results)
    ]