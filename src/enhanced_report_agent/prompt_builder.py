#!/usr/bin/env python3
"""
Enhanced Report Agent 智能提示构建器
将加载的材料组织成Claude友好的提示格式
"""

from typing import Dict, Union, Any
from loguru import logger


class PromptBuilder:
    """智能提示构建器 - 不硬编码任何格式指导"""
    
    def __init__(self):
        """初始化提示构建器"""
        self.max_source_data_length = 30000  # 限制数据源长度，为其他内容留空间
        self.max_total_length = 60000  # 总体长度限制
    
    def build_claude_prompt(self, materials: Dict[str, Union[str, list]]) -> str:
        """
        构建发送给Claude的完整提示
        
        Args:
            materials: 包含所有材料的字典
            
        Returns:
            完整的Claude提示
        """
        logger.info("开始构建Claude提示...")
        
        sections = []
        
        # 基础说明 - 简洁而智能
        intro = """你是一位专业的研究分析师。我将为你提供以下材料，请你分析这些材料并生成一份专业报告。"""
        sections.append(intro)
        
        # 动态添加各个部分
        section_count = 0
        
        # 1. 任务指导
        # 1. 任务指导
        prompt_val = materials.get("prompt")
        if isinstance(prompt_val, str) and prompt_val.strip():
            sections.append(f"## 任务指导\n{prompt_val}")
            section_count += 1
            logger.debug("✅ 任务指导部分已添加")
        
        # 2. 研究方法参考
        artifacts_val = materials.get("artifacts")
        if isinstance(artifacts_val, str) and artifacts_val.strip():
            sections.append(artifacts_val)  # artifacts已包含标题
            section_count += 1
            logger.debug("✅ 研究方法参考部分已添加")
        
        # 3. 报告样例
        example_val = materials.get("example")
        if isinstance(example_val, str) and example_val.strip():
            sections.append(example_val)  # example已包含标题
            section_count += 1
            logger.debug("✅ 报告样例部分已添加")
        
        # 4. 数据源 - 均衡截取
        if materials.get("source_data") and materials["source_data"]:
            source_data = materials["source_data"]
            
            # 处理新的文章列表格式
            if isinstance(source_data, list):
                # 只要是list，直接均衡压缩
                source_content = self._compress_source_data_balanced(source_data, self.max_source_data_length)
                if source_content:
                    sections.append(f"## 原始数据源\n\n{source_content}")
                    section_count += 1
                    logger.debug("✅ 原始数据源部分已添加")
            else:
                # 兼容旧格式（字符串）
                if len(source_data) > self.max_source_data_length:
                    source_content = source_data[:self.max_source_data_length]
                    source_content += "\n\n... [数据源内容已截取以适应处理限制] ..."
                    logger.warning(f"数据源内容过长，已截取至 {self.max_source_data_length} 字符")
                else:
                    source_content = source_data
                if source_content:
                    sections.append(f"## 原始数据源\n\n{source_content}")
                    section_count += 1
                    logger.debug("✅ 原始数据源部分已添加")
        
        # 5. 生成请求 - 智能而简洁
        request = self._build_intelligent_request(section_count)
        sections.append(request)
        
        # 组合最终提示
        final_prompt = "\n\n".join(sections)
        
        # 检查总长度，如需要进行二次压缩
        if len(final_prompt) > self.max_total_length:
            logger.warning(f"提示过长({len(final_prompt)}字符)，进行智能压缩...")
            # 只传递字符串类型的材料给压缩函数，避免类型报错
            str_materials = {k: v for k, v in materials.items() if isinstance(v, str)}
            final_prompt = self._compress_prompt(final_prompt, sections, str_materials)
        
        logger.info(f"✅ Claude提示构建完成:")
        logger.info(f"  - 总长度: {len(final_prompt)} 字符")
        logger.info(f"  - 包含部分: {section_count + 1} 个")
        
        return final_prompt
    
    def _build_intelligent_request(self, available_sections: int) -> str:
        """
        构建智能的生成请求 - 根据可用材料动态调整
        
        Args:
            available_sections: 可用的材料部分数量
            
        Returns:
            智能生成请求
        """
        base_request = """## 请求

请基于上述提供的所有材料："""
        
        instructions = []
        
        # 根据可用材料动态调整指导
        if available_sections >= 3:  # 有足够材料
            instructions.extend([
                "1. 深入分析任务要求和研究目标",
                "2. 参考提供的研究方法和报告样例",
                "3. 严格基于数据源进行客观分析",
                "4. 生成结构完整、内容丰富的专业报告"
            ])
        else:  # 材料较少时的指导
            instructions.extend([
                "1. 分析任务要求和可用信息",
                "2. 基于现有材料生成专业报告",
                "3. 确保内容准确、结构清晰"
            ])
        
        # 核心原则 - 始终包含
        principles = [
            "",
            "**核心原则**:",
            "- 不要编造任何不在提供材料中的信息",
            "- 自主决定最佳的报告结构和风格", 
            "- 确保报告具有专业性和实用价值",
            "- 输出格式为完整的Markdown文档"
        ]
        
        return base_request + "\n" + "\n".join(instructions) + "\n" + "\n".join(principles)
    
    def _compress_source_data_balanced(self, articles: list, max_total_length: int) -> str:
        """
        平均分配字符配额给每篇文章
        
        Args:
            articles: 文章列表，每个元素包含title, content, length
            max_total_length: 最大总长度限制
            
        Returns:
            压缩后的数据源内容
        """
        if not articles:
            return ""
        
        # 平均分配配额
        article_count = len(articles)
        base_quota = max_total_length // article_count
        
        # 预留标题和分隔符空间 (### 📄 title + 换行符)
        separator_overhead = len("### 📄 ") + 50  # 标题和换行符开销
        content_quota = max(base_quota - separator_overhead, 200)  # 每篇至少200字符
        
        logger.info(f"均衡分配: {article_count}篇文章, 每篇配额{content_quota}字符")
        
        compressed_articles = []
        total_compressed_length = 0
        
        for article in articles:
            title = article["title"]
            content = article["content"]
            original_length = len(content)
            
            # 截取内容
            if original_length > content_quota:
                content = content[:content_quota] + "..."
                logger.debug(f"文章 {title}: {original_length} → {len(content)} 字符")
            
            article_section = f"### 📄 {title}\n\n{content}"
            compressed_articles.append(article_section)
            total_compressed_length += len(article_section)
        
        result = "\n\n".join(compressed_articles)
        logger.info(f"数据源均衡压缩完成: {article_count}篇文章, 总长度{total_compressed_length}字符")
        
        return result
    
    def _compress_prompt(self, prompt: str, sections: list, materials: Dict[str, str]) -> str:
        """
        智能压缩提示内容，保留核心信息
        
        Args:
            prompt: 原始提示
            sections: 提示各部分
            materials: 原始材料
            
        Returns:
            压缩后的提示
        """
        logger.info("开始智能压缩提示内容...")
        
        # 重新构建，采用更激进的压缩策略
        compressed_sections = []
        
        # 保留核心介绍
        intro = "你是专业研究分析师。基于以下材料生成专业报告："
        compressed_sections.append(intro)
        
        # 任务指导 - 保留核心要求
        if materials.get("prompt"):
            prompt_content = materials["prompt"][:2000]  # 限制长度
            compressed_sections.append(f"## 任务要求\n{prompt_content}")
        
        # 参考材料 - 仅保留关键信息
        if materials.get("artifacts"):
            artifacts_content = materials["artifacts"][:1500]
            compressed_sections.append(f"## 参考方法\n{artifacts_content}")
        
        # 数据源 - 均衡压缩
        if materials.get("source_data"):
            source_data = materials["source_data"]
            
            if isinstance(source_data, list):
                # 使用均衡压缩方法，更激进的限制
                compressed_source = self._compress_source_data_balanced(source_data, 15000)
                if compressed_source:
                    compressed_sections.append(f"## 数据源\n\n{compressed_source}")
            else:
                # 兼容旧格式
                compressed_source = source_data[:15000]
                compressed_source += "\n\n... [其余数据源已省略，请基于已提供内容进行分析] ..."
                compressed_sections.append(compressed_source)
        
        # 简化的生成请求
        request = """## 要求
基于上述材料生成专业分析报告。请：
1. 深入分析核心问题
2. 基于数据源客观分析
3. 生成结构清晰的Markdown报告
4. 不编造材料中没有的信息"""
        
        compressed_sections.append(request)
        
        compressed_prompt = "\n\n".join(compressed_sections)
        
        logger.info(f"压缩完成: {len(prompt)} → {len(compressed_prompt)} 字符")
        return compressed_prompt
    
    def estimate_token_usage(self, prompt: str) -> Dict[str, Union[int, float]]:
        """
        估算token使用量
        
        Args:
            prompt: 构建的提示
            
        Returns:
            token使用估算
        """
        # 粗略估算：英文约4字符=1token，中文约1.5字符=1token
        char_count = len(prompt)
        
        # 统计中英文比例进行更准确估算
        chinese_chars = sum(1 for char in prompt if '\u4e00' <= char <= '\u9fff')
        english_chars = char_count - chinese_chars
        
        estimated_tokens = int(english_chars / 4 + chinese_chars / 1.5)
        
        return {
            "total_chars": char_count,
            "chinese_chars": chinese_chars,
            "english_chars": english_chars,
            "estimated_tokens": estimated_tokens,
            "token_limit": 8192,
            "usage_ratio": estimated_tokens / 8192
        }
    
    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        验证提示是否有效
        
        Args:
            prompt: 构建的提示
            
        Returns:
            验证结果
        """
        token_info = self.estimate_token_usage(prompt)
        
        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "token_info": token_info
        }
        
        # 检查长度
        if token_info["estimated_tokens"] > 8000:
            validation["warnings"].append("提示可能接近token限制")
        
        if token_info["estimated_tokens"] > 8192:
            validation["is_valid"] = False
            validation["errors"].append("提示超出token限制")
        
        # 检查内容
        if len(prompt.strip()) < 100:
            validation["warnings"].append("提示内容可能过短")
        
        if "任务指导" not in prompt and "请求" not in prompt:
            validation["warnings"].append("提示可能缺少关键部分")
        
        return validation


if __name__ == "__main__":
    # 测试提示构建器
    builder = PromptBuilder()
    
    # 模拟材料
    test_materials = {
        "prompt": "生成一份关于市场分析的专业报告",
        "artifacts": "## 研究方法参考\n### 分析框架\n使用SWOT分析方法",
        "example": "## 报告样例\n# 市场分析报告\n## 执行摘要\n...",
        "source_data": "## 原始数据源\n### 数据1\n市场规模为100亿美元..."
    }
    
    try:
        # 构建提示
        prompt = builder.build_claude_prompt(test_materials)  # type: ignore
        print(f"📝 提示构建成功，长度: {len(prompt)} 字符")
        
        # 验证提示
        validation = builder.validate_prompt(prompt)
        print(f"✅ 提示验证: {'通过' if validation['is_valid'] else '失败'}")
        
        if validation["warnings"]:
            print("⚠️ 警告:", validation["warnings"])
        
        if validation["errors"]:
            print("❌ 错误:", validation["errors"])
        
        # 显示token信息
        token_info = validation["token_info"]
        print(f"📊 Token估算: {token_info['estimated_tokens']}/{token_info['token_limit']} ({token_info['usage_ratio']:.1%})")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")