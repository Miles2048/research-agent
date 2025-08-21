"""
Agent tools and schemas module - imports from search_agent
"""

from search_agent.tools_and_schemas import *

# 确保导入特定的类和函数
try:
    from search_agent.tools_and_schemas import SearchQueryList, Reflection, web_search, knowledge_search
except ImportError as e:
    print(f"Warning: Could not import some tools_and_schemas: {e}")
    
    # 定义fallback类
    class SearchQueryList:
        pass
    
    class Reflection:
        pass
    
    def web_search(*args, **kwargs):
        raise NotImplementedError("web_search not available")
    
    def knowledge_search(*args, **kwargs):
        raise NotImplementedError("knowledge_search not available") 