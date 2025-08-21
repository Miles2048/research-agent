import unittest
import os
import sys
from dotenv import load_dotenv

# 确保能找到 agent 模块
try:
    from agent.graph import perform_web_search
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"Python 路径: {sys.path}")
    raise

# 加载环境变量
try:
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    print(f"尝试加载环境变量文件: {env_path}")
    load_dotenv(dotenv_path=env_path)
except Exception as e:
    print(f"加载环境变量失败: {e}")
    raise

class TestExaSearch(unittest.TestCase):
    def setUp(self):
        """测试前的设置"""
        # 确保有 EXA_API_KEY 环境变量
        self.api_key = os.getenv("EXA_API_KEY")
        if not self.api_key:
            print("警告: 没有设置 EXA_API_KEY 环境变量")
            self.skipTest("没有设置 EXA_API_KEY 环境变量")
        else:
            print(f"找到 EXA_API_KEY: {self.api_key[:5]}...")

    def test_perform_web_search_basic(self):
        """测试基本的搜索功能"""
        try:
            query = "Python programming language"
            print(f"\n执行基本搜索测试: {query}")
            results = perform_web_search(query, num_results=3)
            
            # 验证返回结果
            self.assertIsInstance(results, list)
            self.assertLessEqual(len(results), 3)
            
            # 验证每个结果的结构
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"标题: {result.get('title', 'No title')}")
                print(f"URL: {result.get('url', 'No URL')}")
                
                self.assertIn("title", result)
                self.assertIn("url", result)
                self.assertIn("snippet", result)
                
                # 验证字段类型
                self.assertIsInstance(result["title"], str)
                self.assertIsInstance(result["url"], str)
                self.assertIsInstance(result["snippet"], str)
                
                # 验证 URL 格式
                self.assertTrue(result["url"].startswith("http"))
        except Exception as e:
            print(f"测试过程中出错: {e}")
            raise

    def test_perform_web_search_chinese(self):
        """测试中文搜索功能"""
        try:
            query = "人工智能发展历史"
            print(f"\n执行中文搜索测试: {query}")
            results = perform_web_search(query, num_results=3)
            
            # 验证基本结构
            self.assertIsInstance(results, list)
            self.assertLessEqual(len(results), 3)
            
            # 打印结果
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"标题: {result.get('title', 'No title')}")
                print(f"URL: {result.get('url', 'No URL')}")
                print(f"摘要: {result.get('snippet', 'No snippet')[:200]}...")
                
                # 验证内容不为空
                self.assertTrue(len(result["title"]) > 0)
                self.assertTrue(len(result["snippet"]) > 0)
                self.assertTrue(result["url"].startswith("http"))
        except Exception as e:
            print(f"测试过程中出错: {e}")
            raise

    def test_perform_web_search_error_handling(self):
        """测试错误处理"""
        try:
            # 测试空查询
            print("\n测试空查询")
            empty_results = perform_web_search("", num_results=1)
            self.assertIsInstance(empty_results, list)
            
            # 测试无效的结果数量
            print("\n测试无效的结果数量")
            invalid_num_results = perform_web_search("test", num_results=0)
            self.assertIsInstance(invalid_num_results, list)
        except Exception as e:
            print(f"测试过程中出错: {e}")
            raise

if __name__ == '__main__':
    print("当前 Python 路径:")
    for path in sys.path:
        print(f"  - {path}")
    unittest.main() 