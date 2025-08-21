#!/usr/bin/env python3
"""
搜索功能对比：模拟搜索 vs 真实搜索
"""

import os
import requests
from typing import List, Dict


def demo_current_search_behavior():
    """演示当前的搜索行为"""
    print("🔍 当前搜索系统分析")
    print("=" * 50)
    
    # 检查是否有SerpAPI密钥
    serpapi_key = os.getenv("SERPAPI_KEY")
    
    if serpapi_key:
        print("✅ 检测到 SERPAPI_KEY")
        print("   - 会尝试使用真实的Google搜索")
        print("   - 如果失败，会回退到模拟搜索")
    else:
        print("❌ 未检测到 SERPAPI_KEY")
        print("   - 直接使用模拟搜索结果")
        print("   - 搜索结果是预设的示例数据")
    
    return serpapi_key is not None


def show_fake_search_results():
    """展示模拟搜索结果"""
    print("\n🎭 模拟搜索结果示例:")
    print("-" * 30)
    
    query = "artificial intelligence trends"
    fake_results = [
        {
            "title": f"Search Result {i+1} for: {query}",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"This is a simulated search result snippet for query '{query}'. This would contain relevant information about the topic."
        }
        for i in range(3)
    ]
    
    for i, result in enumerate(fake_results, 1):
        print(f"{i}. 标题: {result['title']}")
        print(f"   链接: {result['url']}")
        print(f"   摘要: {result['snippet'][:80]}...")
        print()


def show_real_search_example():
    """展示真实搜索的示例（需要API密钥）"""
    print("\n🌐 真实搜索结果示例:")
    print("-" * 30)
    
    serpapi_key = os.getenv("SERPAPI_KEY")
    
    if not serpapi_key:
        print("❌ 需要 SERPAPI_KEY 才能演示真实搜索")
        print("💡 设置方法:")
        print("   1. 注册 https://serpapi.com/")
        print("   2. 获取API密钥")
        print("   3. 在 .env 文件中添加: SERPAPI_KEY=your_key_here")
        return
    
    try:
        print("🔍 正在执行真实搜索...")
        url = "https://serpapi.com/search"
        params = {
            "q": "artificial intelligence trends 2024",
            "api_key": serpapi_key,
            "engine": "google",
            "num": 3
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        results = []
        for result in data.get("organic_results", [])[:3]:
            results.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", "")
            })
        
        if results:
            print("✅ 真实搜索结果:")
            for i, result in enumerate(results, 1):
                print(f"{i}. 标题: {result['title'][:60]}...")
                print(f"   链接: {result['url']}")
                print(f"   摘要: {result['snippet'][:80]}...")
                print()
        else:
            print("❌ 没有获得搜索结果")
            
    except Exception as e:
        print(f"❌ 搜索失败: {e}")


def compare_search_quality():
    """对比搜索质量"""
    print("\n📊 搜索质量对比")
    print("=" * 50)
    
    print("🎭 模拟搜索:")
    print("   ✅ 优点:")
    print("      - 无需API密钥，免费使用")
    print("      - 响应速度快")
    print("      - 适合开发和测试")
    print("   ❌ 缺点:")
    print("      - 搜索结果是假的")
    print("      - 无法获得真实信息")
    print("      - AI分析基于虚假数据")
    
    print("\n🌐 真实搜索 (SerpAPI):")
    print("   ✅ 优点:")
    print("      - 真实的Google搜索结果")
    print("      - 最新的网络信息")
    print("      - AI分析基于真实数据")
    print("      - 研究结果更准确")
    print("   ❌ 缺点:")
    print("      - 需要付费API密钥")
    print("      - 有请求限制")
    print("      - 网络延迟")


def setup_serpapi_guide():
    """SerpAPI设置指南"""
    print("\n🚀 如何设置真实搜索 (SerpAPI)")
    print("=" * 50)
    
    print("1. 📝 注册账户:")
    print("   - 访问: https://serpapi.com/")
    print("   - 注册免费账户")
    print("   - 每月有100次免费搜索")
    
    print("\n2. 🔑 获取API密钥:")
    print("   - 登录后访问: https://serpapi.com/manage-api-key")
    print("   - 复制您的API密钥")
    
    print("\n3. ⚙️ 配置环境:")
    print("   - 编辑 backend/.env 文件")
    print("   - 添加: SERPAPI_KEY=your_api_key_here")
    
    print("\n4. 🧪 测试:")
    print("   - 重新运行研究代理")
    print("   - 检查是否获得真实搜索结果")
    
    print("\n💰 定价信息:")
    print("   - 免费: 100次搜索/月")
    print("   - 付费: $50/月 5000次搜索")
    print("   - 按需付费: $0.01/次搜索")


if __name__ == "__main__":
    has_serpapi = demo_current_search_behavior()
    show_fake_search_results()
    
    if has_serpapi:
        show_real_search_example()
    
    compare_search_quality()
    setup_serpapi_guide()