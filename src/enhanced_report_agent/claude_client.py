#!/usr/bin/env python3
"""
Enhanced Report Agent Claude集成
与Claude Sonnet 4 API的集成模块
"""
# TODO 加openai

import asyncio
from typing import Optional
from loguru import logger

try:
    import anthropic
except ImportError:
    anthropic = None

from .config import EnhancedReportConfig


class ClaudeClient:
    """Claude API客户端"""
    
    def __init__(self, config: EnhancedReportConfig):
        """
        初始化Claude客户端
        
        Args:
            config: Enhanced Report配置
        """
        self.config = config
        
        if anthropic is None:
            raise ImportError(
                "anthropic库未安装。请安装: pip install anthropic"
            )
        
        self.client = anthropic.Anthropic(api_key=config.claude_api_key)
        logger.info(f"Claude客户端已初始化，模型: {config.claude_model}")
    
    async def generate_report(self, prompt: str) -> str:
        """
        使用Claude生成报告
        
        Args:
            prompt: 完整的提示内容
            
        Returns:
            Claude生成的报告内容
        """
        try:
            logger.info("开始调用Claude Sonnet 4生成报告...")
            logger.debug(f"提示长度: {len(prompt)} 字符")
            
            # 调用Claude API
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # 提取生成的内容
            if response.content and len(response.content) > 0:
                report_content = response.content[0].text
                
                logger.info("✅ Claude报告生成成功")
                logger.debug(f"生成内容长度: {len(report_content)} 字符")
                
                return report_content
            else:
                raise Exception("Claude返回了空内容")
                
        except anthropic.APIError as e:
            logger.error(f"Claude API错误: {str(e)}")
            raise Exception(f"Claude API调用失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"生成报告时发生错误: {str(e)}")
            raise Exception(f"报告生成失败: {str(e)}")
    
    def generate_report_sync(self, prompt: str) -> str:
        """
        同步版本的报告生成
        
        Args:
            prompt: 完整的提示内容
            
        Returns:
            Claude生成的报告内容
        """
        return asyncio.run(self.generate_report(prompt))
    
    def test_connection(self) -> bool:
        """
        测试Claude API连接
        
        Returns:
            连接是否成功
        """
        try:
            logger.info("测试Claude API连接...")
            
            # 发送简单的测试请求
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=50,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": "请回复'连接测试成功'"
                }]
            )
            
            if response.content and len(response.content) > 0:
                reply = response.content[0].text.strip()
                logger.info(f"✅ Claude API连接成功，回复: {reply}")
                return True
            else:
                logger.error("❌ Claude API连接失败：返回空内容")
                return False
                
        except Exception as e:
            logger.error(f"❌ Claude API连接测试失败: {str(e)}")
            return False
    
    def get_model_info(self) -> dict:
        """
        获取模型信息
        
        Returns:
            模型配置信息
        """
        return {
            "model": self.config.claude_model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "api_key_configured": bool(self.config.claude_api_key)
        }


class MockClaudeClient:
    """Mock Claude客户端，用于测试"""
    
    def __init__(self, config: EnhancedReportConfig):
        self.config = config
        logger.warning("使用Mock Claude客户端（测试模式）")
    
    async def generate_report(self, prompt: str) -> str:
        """生成模拟报告"""
        logger.info("生成模拟报告...")
        
        # 模拟处理时间
        await asyncio.sleep(2)
        
        mock_report = f"""# 专业市场分析报告

## 核心摘要

这是一份由Enhanced Report Agent生成的模拟专业报告。本报告基于提供的材料进行分析，包含以下关键发现：

- 市场规模持续增长，预计未来5年CAGR为15%
- 技术创新推动行业变革
- 用户需求呈现多样化趋势

## 第一部分：市场格局分析

### 1.1 市场规模与增长趋势

根据提供的数据分析，目标市场呈现强劲增长态势...

### 1.2 竞争格局分析

主要竞争者包括...

## 第二部分：用户画像分析

### 2.1 核心用户群体

基于用户行为数据分析...

### 2.2 需求特征分析

用户需求主要集中在...

## 第三部分：战略建议

### 3.1 市场进入策略

建议采用分阶段进入策略...

### 3.2 风险管控措施

主要风险点和应对措施...

## 结论

综合分析表明，该市场具有较大发展潜力...

---
*本报告由Enhanced Report Agent自动生成*
*基于提示长度: {len(prompt)} 字符*
"""
        
        logger.info("✅ 模拟报告生成完成")
        return mock_report
    
    def generate_report_sync(self, prompt: str) -> str:
        return asyncio.run(self.generate_report(prompt))
    
    def test_connection(self) -> bool:
        logger.info("Mock客户端连接测试（始终成功）")
        return True
    
    def get_model_info(self) -> dict:
        return {
            "model": "mock-claude",
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "api_key_configured": True,
            "mock_mode": True
        }


def create_claude_client(config: EnhancedReportConfig, use_mock: bool = False) -> ClaudeClient:
    """
    创建Claude客户端
    
    Args:
        config: 配置信息
        use_mock: 是否使用Mock客户端
        
    Returns:
        Claude客户端实例
    """
    if use_mock or anthropic is None:
        return MockClaudeClient(config)
    else:
        return ClaudeClient(config)


if __name__ == "__main__":
    # 测试Claude客户端
    from .config import load_config
    
    try:
        config = load_config()
        
        # 测试真实客户端（如果可用）
        try:
            client = create_claude_client(config, use_mock=False)
            if client.test_connection():
                print("✅ Claude API连接测试成功")
            else:
                print("❌ Claude API连接测试失败")
        except Exception as e:
            print(f"⚠️ 真实客户端测试失败: {str(e)}")
            
            # 回退到Mock客户端
            print("🔄 切换到Mock客户端测试...")
            mock_client = create_claude_client(config, use_mock=True)
            
            test_prompt = "请生成一份简短的测试报告"
            report = mock_client.generate_report_sync(test_prompt)
            print(f"✅ Mock客户端测试成功，生成报告长度: {len(report)} 字符")
    
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")