import unittest
import os
import sys

# Add project root and src to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from dotenv import load_dotenv
from agent.tools.exa_search import perform_exa_search

# 加载环境变量
load_dotenv()

def test_search():
    query = "Latest developments in quantum computing"
    print(f"\n搜索查询: {query}")
    
    results = perform_exa_search(query, num_results=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"标题: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"摘要: {result['snippet'][:200]}...")

if __name__ == "__main__":
    test_search() 