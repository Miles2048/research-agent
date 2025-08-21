"""Prompt templates for LLM evaluation."""

from typing import Dict, Any

class PromptTemplates:
    """Centralized prompt templates for LLM evaluation."""
    
    @staticmethod
    def get_reference_type_prompt(reference: Dict[str, Any]) -> str:
        """Get prompt for reference type classification."""
        return f"""请根据以下参考文献的特征，将其分类到最合适的类型中。

参考文献信息：
- 标题：{reference.get('title', '')}
- URL：{reference.get('url', '')}
- 发布机构：{reference.get('publisher', '未知')}
- 内容摘要：{reference.get('content_snippet', '')}

分类类型（必须严格使用以下英文标识，共5种）：
1. official_statistics - 官方统计数据
   * 政府统计局、央行、国际组织（UN、WHO、World Bank等）发布的官方统计数据
   * 官方经济指标、人口普查、贸易数据等
   * 政府部门的统计报告和数据公报
   
2. business_data - 商业数据
   * 企业财报、年报、投资者关系资料
   * 行业协会数据、市场份额报告
   * 商业数据库（Bloomberg、Wind等）的数据
   * 咨询公司的市场研究报告（McKinsey、BCG、Gartner等）
   * 新闻报道、媒体文章、专栏评论
   * 公司官网的产品介绍、技术文档
   * 行业分析文章、专家访谈
   * 政策解读、法规条文、标准规范
   
3. real-time_data - 实时数据
   * 股票价格、汇率、商品期货等金融市场数据
   * 实时监测数据（天气、交通、能源等）
   * 社交媒体热度、搜索趋势
   * IoT设备和传感器数据
   
4. academic_research - 学术研究
   * 同行评审的学术期刊论文
   * 学术会议论文、研究报告
   * 博士/硕士学位论文
   * 大学或研究机构的研究成果
   
5. uncategorized - 未分类（备选）
   * 仅当内容无法归入上述4个类别时使用
   * 内容模糊不清或信息不足
   * 混合多种类型难以明确归类

分类原则：
- 优先考虑内容的主要性质和来源权威性
- 如果URL包含.gov、.org或国际组织域名，优先考虑official_statistics
- 如果是企业官方发布、商业机构报告、新闻媒体文章，考虑business_data
- 如果强调时效性和动态更新，归为real-time_data
- 如果有明确的学术特征（引用、摘要、方法论），归为academic_research
- 只有确实无法归类时才使用uncategorized

请返回JSON格式：
{{
    "reference_type": "<英文类型标识>",
    "confidence": <0.0-1.0的置信度>,
    "reasoning": "<分类理由，说明为什么归入此类>"
}}

注意：reference_type字段必须严格使用上述5个英文标识之一，不要使用中文。"""
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

1. 可信度评估（1-5分）
   
   **重要提示**：1分和2分仅用于极端情况（少于10%的情况），大多数正常的网络资源应该在3-5分范围内。
   
   - 1分：极低可信度（极端极少使用）
     * 明显的虚假信息或诈骗网站
     * 恶意传播错误信息
     * 完全无法验证的来源
     * 仅在内容明显有害或虚假时使用
     
   - 2分：低可信度（极少使用）
     * 个人博客或论坛的未经证实言论
     * 明显带有强烈偏见的内容
     * 缺乏任何可信来源支持
     * 信息严重过时或与事实不符
     
   - 3分：一般可信度（常见）
     * 一般商业网站或新闻媒体
     * 行业内普通企业的官方信息
     * 有基本信息来源但深度有限
     * 内容基本准确但可能存在小偏差
     
   - 4分：较高可信度（常见）
     * 知名媒体或行业权威网站
     * 大型企业官方发布的信息
     * 专业机构的研究报告
     * 政府部门的一般性文件
     * 有明确作者和引用来源
     
   - 5分：极高可信度（适度使用）
     * 政府官方统计数据
     * 顶级学术期刊的同行评审论文
     * 国际组织（UN、WHO、World Bank）的官方报告
     * 行业标准制定机构的正式文件
     * 法律法规原文

2. 相关性评估（0-100分）
   
   **重要提示**：0-50分仅用于极端情况，50-70分较少使用，大多数相关资源应该在70-90分范围内。打分时打整5整10的分数，如75，，80，85，，90，95，他们的概率和其他的分数的概率相同，而不是优先打这些整5整10 的分数
   
   考虑以下维度：
   - 主题匹配度：内容是否直接涉及{research_topic.get('title', '研究主题')}
   - 信息价值：对研究{research_topic.get('title', '研究主题')}的贡献度
   - 内容深度：关于{', '.join(research_topic.get('keywords', []))}的分析专业性和深度
   - 时效性：信息的新旧程度和当前适用性

   评分标准：
   - 0-30分：极低相关（极端极少使用）
     * 内容完全无关或误导性信息
     * 仅在明显错误匹配时使用
     
   - 30-50分：低相关性（极少使用）
     * 内容边缘相关，仅有极少信息点涉及主题
     * 信息价值极低
     
   - 50-70分：中等相关性（较少使用）
     * 部分内容与主题相关但不是核心内容
     * 提供了一些背景信息但缺乏深度
     
   - 70-90分：高相关性（常见）
     * 内容主要围绕研究主题展开
     * 提供了有价值的信息和见解
     * 大多数正常搜索结果应在此范围
     
   - 90-95分：极高相关性（适度使用）
     * 内容高度聚焦于研究主题
     * 提供了关键数据或核心见解
     * 直接回答研究问题
     
   - 95-100分：完美相关（很少使用）
     * 内容完全针对研究主题定制
     * 提供了独特且关键的信息
     * 仅对最核心的参考资料使用

请返回JSON格式：
{{
    "credibility": <1/2/3/4/5的整数>,
    "credibility_assessment": "<详细说明可信度评分理由，包括来源权威性、内容专业性、数据可靠性等方面，至少100字>",
    "related_assessment": <0-100的整数>,
    "related_assessment_text": "<详细说明相关性评分理由，从四个维度分析与研究主题的相关程度，至少100字>"
}}

**评分原则提醒**：
- credibility必须是1-5的整数，90%以上应该评为3、4或5分
- related_assessment必须是0-100的整数
- 相关性评分分布：70-90分（常见）、90-95分（适度）、50-70分（较少）、0-50分（极少）
- 避免极端评分，大多数正常搜索结果的相关性应在70-90分范围内"""

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