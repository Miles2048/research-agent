"""Prompt templates for LLM evaluation."""

from typing import Dict, Any

class PromptTemplates:
    """Centralized prompt templates for LLM evaluation."""
    
    @staticmethod
    def get_reference_type_prompt(reference: Dict[str, Any]) -> str:
        """Get prompt for reference type classification."""
        return f"""请根据以下参考文献的特征，将其分类到合适的类型中。

参考文献信息：
- 标题：{reference.get('title', '')}
- URL：{reference.get('url', '')}
- 发布机构：{reference.get('publisher', '未知')}
- 内容摘要：{reference.get('content_snippet', '')}

可选类型：
1. 用户输入：产品信息、企业信息等直接输入的材料
2. 行业研究报告：咨询公司（如McKinsey、BCG）、市场研究机构（如Gartner、IDC）的专业报告
3. 同行评审的学术出版物：学术期刊、会议论文、研究报告等
4. 竞对公司网站和产品页面：竞争对手的官方网站、产品信息、投资者关系等
5. 政策与准入数据：法律法规、准入标准、贸易政策、监管动态等
6. 社交媒体和公共论坛：专业论坛、社交媒体讨论、评测网站、新闻媒体等

分类提示：
- 如果URL包含.gov或政府机构域名，可能是"政策与准入数据"
- 如果URL包含学术期刊或.edu域名，可能是"同行评审的学术出版物"
- 如果是知名咨询公司或市场研究机构，归类为"行业研究报告"
- 如果是公司官网或产品页面，考虑是否为"竞对公司网站和产品页面"
- 如果是论坛、社交媒体或新闻网站，归类为"社交媒体和公共论坛"

请返回JSON格式：
{{
    "reference_type": "<类型名称>",
    "confidence": <0.0-1.0的置信度>,
    "reasoning": "<分类理由>"
}}"""
# TODO 细化机构
# TODO 
    @staticmethod
    def get_comprehensive_evaluation_prompt(
        reference: Dict[str, Any], 
        research_topic: Dict[str, str]
    ) -> str:
        """Get prompt for comprehensive evaluation (credibility + relevance)."""
        # Truncate content if too long
        content = reference.get('content', '')
        if len(content) > 3000:
            content = content[:3000] + "...[内容已截断]"
            
        return f"""你是一个专业的研究文献评估助手。请对以下参考文献进行综合评估。

研究主题：{research_topic.get('title', '')}
主题说明：{research_topic.get('description', '')}
关键词：{', '.join(research_topic.get('keywords', []))}

参考文献信息：
- 标题：{reference.get('title', '')}
- URL：{reference.get('url', '')}
- 发布机构：{reference.get('publisher', '未知')}
- 内容摘要：
{content}

评估任务：

1. 可信度评估（1-3分）
   - 1分：低可信度
     * 来源不明或非官方网站
     * 缺乏作者信息或发布日期
     * 内容存在明显错误或偏见
     * 缺少引用和数据支持
   - 2分：中等可信度
     * 来源于一般商业网站或新闻媒体
     * 有基本的作者和时间信息
     * 内容基本准确但深度有限
     * 有一定的数据支持
   - 3分：高可信度
     * 来源于权威机构、学术期刊或官方网站
     * 作者具有相关领域专业背景
     * 内容经过同行评审或官方认证
     * 数据来源明确且可验证

2. 相关性评估（0.00-1.00）
   考虑以下维度：
   - 主题匹配度：内容是否直接涉及{research_topic.get('title', '研究主题')}
   - 信息价值：对研究{research_topic.get('title', '研究主题')}的贡献度
   - 内容深度：关于{', '.join(research_topic.get('keywords', []))}的分析专业性和深度
   - 时效性：信息的新旧程度和当前适用性

评分参考：
- 0.00-0.30：低相关性，与研究主题关系较远
- 0.30-0.60：中等相关性，部分内容与研究主题相关
- 0.60-0.80：较高相关性，大部分内容与研究主题相关
- 0.80-1.00：高度相关，直接回答研究问题或提供核心信息

请返回JSON格式：
{{
    "credibility": <1/2/3>,
    "credibility_assessment": "<详细说明可信度评分理由，包括来源权威性、内容专业性、数据可靠性等方面，至少100字>",
    "related_assessment": <0.00-1.00>,
    "related_assessment_text": "<详细说明相关性评分理由，从四个维度分析与研究主题的相关程度，至少100字>"
}}"""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for LLM."""
        return """你是一个专业的学术文献评估助手，具有以下特点：
1. 客观公正：基于事实进行评估，避免主观偏见
2. 专业严谨：使用学术标准评估文献质量
3. 详细准确：提供具体的评估理由和证据
4. 结构清晰：按照要求的格式输出评估结果

在评估时，请特别注意：
- 仔细分析文献来源的权威性
- 评估内容与研究主题的相关程度
- 考虑信息的时效性和准确性
- 提供充分的评估理由"""