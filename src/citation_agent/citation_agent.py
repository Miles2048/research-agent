#!/usr/bin/env python3
"""
简单Citation Agent - 整合多个topic报告生成最终深度研究报告
功能：
1. 读取所有topic报告
2. 结合planning_list的结构和要求
3. 使用LLM生成最终的deepResearchReport.md
"""

import os
import glob
from datetime import datetime

from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class SimpleCitationAgent:
    """简单的Citation Agent - 负责整合报告"""
    
    def __init__(self, results_dir=None, planning_file=None):
        """
        初始化Citation Agent
        
        Args:
            results_dir: topic报告结果目录
            planning_file: 规划文件路径
        """
        # 动态设置路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        
        self.results_dir = results_dir or os.path.join(base_dir, "result")
        self.planning_file = planning_file or os.path.join(os.path.dirname(script_dir), "planning_list.md")
        
        self.llm = ChatAnthropic(
            model_name="claude-4-sonnet-20250514",
            temperature=0.3,
            max_tokens=4096,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    def read_topic_reports(self):
        """读取所有topic报告"""
        
        topic_reports = {}
        
        # 使用绝对路径查找
        print(f"查找目录: {self.results_dir}")
        
        if os.path.exists(self.results_dir):
            topic_dirs = glob.glob(os.path.join(self.results_dir, "topic_*"))
            print(f"找到 {len(topic_dirs)} 个topic目录")
            
            for topic_dir in sorted(topic_dirs):
                topic_name = os.path.basename(topic_dir)
                
                # 读取topic报告 - 匹配不同的命名模式
                report_patterns = [
                    f"{topic_name}_report.md",
                    f"topic_*_report.md",
                    "*_report.md"
                ]
                
                report_file = None
                for pattern in report_patterns:
                    potential_files = glob.glob(os.path.join(topic_dir, pattern))
                    if potential_files:
                        report_file = potential_files[0]
                        break
                
                summary_file = os.path.join(topic_dir, "research_summary.md")
                
                topic_data = {
                    'name': topic_name,
                    'report': '',
                    'summary': '',
                    'path': topic_dir
                }
                
                # 读取报告文件
                if report_file and os.path.exists(report_file):
                    with open(report_file, 'r', encoding='utf-8') as f:
                        topic_data['report'] = f.read()
                    print(f"  找到报告文件: {os.path.basename(report_file)}")
                
                # 读取摘要文件
                if os.path.exists(summary_file):
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        topic_data['summary'] = f.read()
                
                # 如果报告或摘要存在，添加到结果中
                if topic_data['report'] or topic_data['summary']:
                    topic_reports[topic_name] = topic_data
                    print(f"✓ 读取了 {topic_name}")
        else:
            print(f"❌ 目录不存在: {self.results_dir}")
        
        return topic_reports
    
    def read_planning_list(self):
        """读取planning_list"""
        
        if not os.path.exists(self.planning_file):
            print(f"❌ 找不到规划文件: {self.planning_file}")
            return ""
        
        with open(self.planning_file, 'r', encoding='utf-8') as f:
            planning_content = f.read()
        
        print(f"✓ 读取了规划文件: {self.planning_file}")
        return planning_content
    
    def generate_final_report(self, topic_reports, planning_content):
        """使用LLM生成最终报告"""
        
        # 构建prompt
        prompt = self._build_report_prompt(topic_reports, planning_content)
        
        print("🤖 正在生成最终深度研究报告...")
        
        # 调用LLM
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        return response.content
    
    def _build_report_prompt(self, topic_reports, planning_content):
        """构建LLM的prompt - 根据planning_list动态生成"""
        
        # 解析planning_list的关键信息
        planning_info = self._parse_planning_content(planning_content)
        
        # 构建topic报告完整内容（不截取）
        topics_full_content = self._build_topics_full_content(topic_reports, planning_info)
        
        # 提取所有引用信息
        citations_info = self._extract_citations(topic_reports)
        
        # 构建报告结构指导
        report_structure = self._build_enhanced_report_structure(planning_info)
        
        # 分析现有报告风格
        style_analysis = self._analyze_report_style(topic_reports)
        
        prompt = f"""
你是一个专业的学术研究分析师，需要基于已完成的多个topic深度研究，生成一份高质量的学术级深度研究报告。

# 研究背景与要求
**报告标题**: {planning_info.get('title', '深度研究报告')}
**核心研究问题**: {planning_info.get('research_question', '待定义')}
**目标受众**: {planning_info.get('target_audience', '专业投资者和决策者')}
**分析深度**: {planning_info.get('analysis_depth', '深度战略研究')}

# 执行摘要重点
{planning_info.get('executive_summary', '请提供基于数据驱动的客观分析和战略建议')}

# 各Topic完整研究结果
{topics_full_content}

# 引用资源信息
{citations_info}

# 报告生成要求

## 1. 报告结构
{report_structure}

## 2. 写作风格（重要：请严格模仿现有topic报告的风格）
{style_analysis}
- **学术标准**: 面向{planning_info.get('target_audience', '专业读者')}的高质量学术分析
- **数据驱动**: 基于研究结果的客观判断，严格引用来源，不编造数据
- **逻辑严密**: 结构清晰，论证有力，每个观点都有数据支撑
- **洞察深刻**: 提供战略性的分析和建议，结合多重视角

## 3. 内容要求（关键）
- **每个Topic章节不少于1500字**：深度分析，详细展开
- **充分利用Topic研究结果**：基于提供的完整research内容进行分析
- **文献引用规范**：每个Topic章节必须包含相关文献引用
- **数据引用标准**：所有数据、统计信息、市场调研结果都需要标注来源
- 回应核心研究问题: {planning_info.get('research_question', '')}
- 突出{planning_info.get('analysis_depth', '深度')}分析的价值
- 为{planning_info.get('target_audience', '目标受众')}提供可行的洞察

## 4. 引用格式要求
- **文中引用**: 使用[数字]格式，如[1]、[2]等
- **引用标准**: 引用要对应到实际的网页链接、研究报告、数据来源
- **引用分布**: 每个Topic章节至少包含5-10个引用
- **最终引用表**: 报告最后必须包含完整的"文献引用"部分

## 5. 格式要求
- 使用markdown格式
- 包含数据表格和关键发现
- 适当的标题层级结构（# ## ### ####）
- **总长度要求：15000-20000字**（比原来更长更详细）
- 每个Topic部分独立成章，结构完整

## 6. 特别要求
- 在报告最后，单独列出"## 文献引用"部分
- 按照学术标准格式列出所有引用的来源
- 确保每个引用都能追溯到具体的URL或来源

请严格按照以上要求生成完整的学术级深度研究报告。特别注意每个Topic章节的字数要求和引用要求。

        """
        
        return prompt
    
    def _parse_planning_content(self, planning_content):
        """解析planning_list中的关键信息"""
        import re
        
        info = {}
        
        # 提取报告标题
        title_match = re.search(r'### 🎯 报告标题\s*\*\*([^*]+)\*\*', planning_content)
        if title_match:
            info['title'] = title_match.group(1).strip()
        
        # 提取核心研究问题
        question_match = re.search(r'### ❓ 核心研究问题\s*([^\n]+)', planning_content)
        if question_match:
            info['research_question'] = question_match.group(1).strip()
        
        # 提取执行摘要重点
        summary_match = re.search(r'### 📊 执行摘要重点\s*([^#]+?)(?=###|$)', planning_content, re.DOTALL)
        if summary_match:
            info['executive_summary'] = summary_match.group(1).strip()
        
        # 提取目标受众
        audience_match = re.search(r'### 👥 目标受众\s*([^\n]+)', planning_content)
        if audience_match:
            info['target_audience'] = audience_match.group(1).strip()
        
        # 提取分析深度
        depth_match = re.search(r'### 📖 分析深度\s*([^\n]+)', planning_content)
        if depth_match:
            info['analysis_depth'] = depth_match.group(1).strip()
        
        # 提取所有topic信息
        info['topics'] = self._extract_topics_info(planning_content)
        
        return info
    
    def _extract_topics_info(self, planning_content):
        """提取所有topic的信息"""
        import re
        
        topics = []
        
        # 匹配所有topic
        topic_pattern = r'### (Topic \d+: [^\n]+)\s*\*\*([^*]+)\*\*\s*\*\*🎯 研究目标:\*\*\s*([^*]+?)(?=\*\*📋|\*\*🔍|###|$)'
        matches = re.finditer(topic_pattern, planning_content, re.DOTALL)
        
        for match in matches:
            topic_info = {
                'title': match.group(1).strip(),
                'subtitle': match.group(2).strip(),
                'goal': match.group(3).strip()
            }
            topics.append(topic_info)
        
        return topics
    
    def _build_topics_full_content(self, topic_reports, planning_info):
        """构建topic报告完整内容（不截取）"""
        full_contents = []
        
        for topic_name, data in topic_reports.items():
            # 从planning_info中找到对应的topic信息
            topic_info = None
            for topic in planning_info.get('topics', []):
                if topic_name.lower().replace('_', ' ') in topic['title'].lower():
                    topic_info = topic
                    break
            
            content = f"## {topic_name}"
            if topic_info:
                content += f"\n**研究目标**: {topic_info['goal']}"
            
            # 提供完整的报告内容和摘要
            content += f"\n\n**完整研究报告**:\n{data['report']}"
            
            if data['summary']:
                content += f"\n\n**研究摘要**:\n{data['summary']}"
            
            full_contents.append(content)
        
        return "\n\n" + "="*80 + "\n\n".join(full_contents)
    
    def _extract_citations(self, topic_reports):
        """提取所有topic中的引用信息"""
        import re
        
        all_citations = []
        citation_patterns = [
            r'https?://[^\s\)]+',  # HTTP/HTTPS URLs
            r'www\.[^\s\)]+',      # www URLs
            r'\[([^\]]+)\]\(([^)]+)\)',  # Markdown links
            r'来源[:：]\s*([^\n]+)',      # 来源: 格式
            r'参考[:：]\s*([^\n]+)',      # 参考: 格式
            r'引用[:：]\s*([^\n]+)'       # 引用: 格式
        ]
        
        for topic_name, data in topic_reports.items():
            topic_citations = []
            full_text = data['report'] + ' ' + data['summary']
            
            for pattern in citation_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                topic_citations.extend(matches)
            
            if topic_citations:
                citation_summary = f"### {topic_name} 引用来源\n"
                for i, citation in enumerate(topic_citations[:10], 1):  # 限制每个topic最多10个引用
                    if isinstance(citation, tuple):  # Markdown链接格式
                        citation_summary += f"{i}. [{citation[0]}]({citation[1]})\n"
                    else:
                        citation_summary += f"{i}. {citation}\n"
                all_citations.append(citation_summary)
        
        if all_citations:
            return "以下是各Topic中发现的引用来源，请在生成报告时充分利用：\n\n" + "\n\n".join(all_citations)
        else:
            return "注意：请在生成报告时，为每个topic的关键观点添加合理的引用标注。"
    
    def _analyze_report_style(self, topic_reports):
        """分析现有报告的风格特征"""
        
        if not topic_reports:
            return "请保持专业、客观、数据驱动的写作风格"
        
        # 从第一个报告中提取风格特征
        first_report = list(topic_reports.values())[0]['report']
        
        style_features = []
        
        # 检查标题格式
        if '###' in first_report:
            style_features.append("- 使用三级标题(###)作为主要章节标题")
        if '####' in first_report:
            style_features.append("- 使用四级标题(####)作为子章节标题")
        
        # 检查数据引用格式
        if '[' in first_report and ']' in first_report:
            style_features.append("- 使用方括号[数字]格式进行文献引用")
        
        # 检查列表格式
        if '1.' in first_report or '- ' in first_report:
            style_features.append("- 使用编号列表和符号列表展示结构化信息")
        
        # 检查数据展示
        if '$' in first_report or '%' in first_report:
            style_features.append("- 精确展示数据，包括货币金额和百分比")
        
        return "\n".join(style_features) if style_features else "请保持专业、客观、数据驱动的写作风格"
    
    def _build_enhanced_report_structure(self, planning_info):
        """根据planning_info构建增强的报告结构指导"""
        
        structure = """请严格按以下结构组织报告：

1. **核心摘要** (1000-1500字)
   - 执行摘要，回应核心研究问题
   - 突出关键发现和战略建议
   - 明确投资机会与风险评估
   - 各Topic的核心发现总结

"""
        
        # 根据topics动态构建主体结构，强调字数和引用要求
        topics = planning_info.get('topics', [])
        for i, topic in enumerate(topics, 2):
            structure += f"{i}. **{topic['subtitle']}** (≥1500字，含5-10个引用)\n"
            structure += f"   - 基于{topic['title']}的完整研究结果进行深度分析\n"
            structure += f"   - 研究目标: {topic['goal']}\n"
            structure += f"   - 必须包含：数据分析、市场洞察、具体案例、引用来源\n"
            structure += f"   - 引用格式：文中使用[1]、[2]等编号引用\n\n"
        
        structure += f"{len(topics)+2}. **综合分析与结论** (1000-1500字)\n"
        structure += "   - 整合各Topic分析的战略结论\n"
        structure += "   - 跨Topic的关联性分析\n"
        structure += "   - 核心研究问题的最终回答\n\n"
        
        structure += f"{len(topics)+3}. **战略建议与风险管控** (800-1000字)\n"
        structure += "   - 基于分析结果的具体行动建议\n"
        structure += "   - 风险识别与管控策略\n"
        structure += "   - 实施路径与优先级排序\n\n"
        
        structure += f"{len(topics)+4}. **文献引用**\n"
        structure += "   - 按照学术标准格式列出所有引用\n"
        structure += "   - 格式：[编号] 作者/来源名称. 标题. URL (访问日期)\n"
        structure += "   - 确保每个引用都可追溯\n"
        
        return structure
    
    def _build_report_structure(self, planning_info):
        """兼容性方法，调用增强版本"""
        return self._build_enhanced_report_structure(planning_info)
    
    def save_report(self, report_content, output_file="deepResearchReport.md"):
        """保存最终报告"""
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 添加元数据
        header = f"""---
title: 深度研究报告
generated_time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
agent: SimpleCitationAgent
model: claude-4-sonnet-20250514
topics_analyzed: {len(glob.glob(os.path.join(self.results_dir, "topic_*")))}
---

"""
        
        full_content = header + report_content
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"💾 报告已保存到: {output_file}")
        return output_file

def generate_citation_report(results_dir=None, planning_file=None, output_file=None):
    """
    主函数：生成citation报告
    
    Args:
        results_dir: topic报告目录
        planning_file: 规划文件路径  
        output_file: 输出文件名
        
    Returns:
        str: 输出文件路径
    """
    
    # 动态设置默认路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    results_dir = results_dir or os.path.join(base_dir, "result")
    planning_file = planning_file or os.path.join(os.path.dirname(script_dir), "planning_list.md")
    output_file = output_file or os.path.join(base_dir, "result", "deepResearchReport.md")
    
    print("🚀 开始生成深度研究报告")
    print("=" * 60)
    
    # 初始化agent
    agent = SimpleCitationAgent(results_dir, planning_file)
    
    # 1. 读取topic报告
    print("\n📖 读取topic报告...")
    topic_reports = agent.read_topic_reports()
    
    if not topic_reports:
        print("❌ 没有找到任何topic报告")
        return None
    
    # 2. 读取规划文件
    print("\n📋 读取规划文件...")
    planning_content = agent.read_planning_list()
    
    # 3. 生成最终报告
    print("\n🤖 生成最终报告...")
    final_report = agent.generate_final_report(topic_reports, planning_content)
    
    # 4. 保存报告
    print("\n💾 保存报告...")
    output_path = agent.save_report(final_report, output_file)
    
    print(f"\n✅ 深度研究报告生成完成！")
    print(f"📄 文件: {os.path.abspath(output_path)}")
    print(f"📊 分析了 {len(topic_reports)} 个topic")
    
    return output_path


if __name__ == "__main__":
    generate_citation_report()