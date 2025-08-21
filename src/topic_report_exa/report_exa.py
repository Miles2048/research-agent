#!/usr/bin/env python3
"""
Topic Report Exa Generator
使用Exa Research API生成专业的topic报告
"""

import os
import sys
import glob
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Union
from loguru import logger

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exa_py import Exa
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量 - 从backend目录的.env文件
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)


class TopicReportExaGenerator:
    """使用Exa生成Topic报告"""
    
    def __init__(self, exa_api_key: str = None):
        """
        初始化Exa报告生成器
        
        Args:
            exa_api_key: Exa API密钥，如果不提供将从环境变量读取
        """
        self.api_key = exa_api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY 未设置。请在环境变量中设置 EXA_API_KEY 或在初始化时传入 api_key 参数。")
        self.exa = Exa(api_key=self.api_key)
        
        # 初始化OpenAI客户端用于流式输出
        self.client = OpenAI(
            base_url="https://api.exa.ai",
            api_key=self.api_key,
        )
        
        # 路径配置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.result_dir = os.path.join(self.base_dir, "result")
        self.report_cfg_dir = os.path.join(self.base_dir, "report_cfg")
        self.planning_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "planning_list.md")
        
        logger.info("Topic Report Exa Generator 初始化完成")
    
    def load_topic_materials(self, topic_id: str) -> Dict[str, Union[str, List]]:
        """
        加载topic相关的所有材料
        
        Args:
            topic_id: topic标识，如 'topic_1' 或 'topic_1_市场格局分析'
            
        Returns:
            包含所有材料的字典
        """
        materials = {
            "prompt": "",
            "artifacts": "",
            "example": "",
            "source_data": [],
            "planning_info": ""
        }
        
        # 查找对应的topic目录
        topic_dirs = glob.glob(os.path.join(self.result_dir, f"{topic_id}*"))
        if not topic_dirs:
            logger.warning(f"未找到topic目录: {topic_id}")
            return materials
        
        topic_dir = topic_dirs[0]
        topic_name = os.path.basename(topic_dir)
        logger.info(f"找到topic目录: {topic_dir}")
        
        # 1. 加载source_data
        source_data_dir = os.path.join(topic_dir, "source_data")
        if os.path.exists(source_data_dir):
            source_files = glob.glob(os.path.join(source_data_dir, "*.md"))
            materials["source_data"] = []
            for file_path in sorted(source_files)[:20]:  # 限制文件数量
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        materials["source_data"].append({
                            "filename": os.path.basename(file_path),
                            "content": content[:2000]  # 限制每个文件的长度
                        })
                except Exception as e:
                    logger.error(f"读取文件失败 {file_path}: {e}")
            logger.info(f"加载了 {len(materials['source_data'])} 个数据源文件")
        
        # 2. 加载planning_list中的相关信息
        if os.path.exists(self.planning_file):
            try:
                with open(self.planning_file, 'r', encoding='utf-8') as f:
                    planning_content = f.read()
                    materials["planning_info"] = self._extract_topic_planning(planning_content, topic_name)
            except Exception as e:
                logger.error(f"读取planning_list失败: {e}")
        
        # 3. 从report_cfg加载额外配置（如果存在）
        cfg_topic_dir = os.path.join(self.report_cfg_dir, topic_id.split('_')[0] + '_' + topic_id.split('_')[1])
        if os.path.exists(cfg_topic_dir):
            # 加载prompt
            prompt_file = os.path.join(cfg_topic_dir, "prompt", "prompt.md")
            if os.path.exists(prompt_file):
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        materials["prompt"] = f.read()
                except Exception as e:
                    logger.error(f"读取prompt文件失败: {e}")
            
            # 加载example
            example_files = glob.glob(os.path.join(cfg_topic_dir, "example", "*.md"))
            if example_files:
                try:
                    with open(example_files[0], 'r', encoding='utf-8') as f:
                        materials["example"] = f.read()[:5000]  # 限制长度
                except Exception as e:
                    logger.error(f"读取example文件失败: {e}")
        
        return materials
    
    def _extract_topic_planning(self, planning_content: str, topic_name: str) -> str:
        """从planning_list中提取特定topic的信息"""
        import re
        
        # 提取topic编号
        topic_num = topic_name.split('_')[1] if '_' in topic_name else '1'
        
        # 查找对应topic的内容
        pattern = rf'### Topic {topic_num}:.*?(?=###|$)'
        match = re.search(pattern, planning_content, re.DOTALL)
        
        if match:
            topic_info = match.group(0)
            
            # 提取关键信息
            info_parts = []
            
            # 研究目标
            goal_match = re.search(r'\*\*🎯 研究目标:\*\*\s*([^*]+)', topic_info)
            if goal_match:
                info_parts.append(f"研究目标: {goal_match.group(1).strip()}")
            
            # 数据需求
            data_match = re.search(r'\*\*📋 数据需求:\*\*\s*([^*]+)', topic_info, re.DOTALL)
            if data_match:
                info_parts.append(f"数据需求:\n{data_match.group(1).strip()}")
            
            # 分析方法
            method_match = re.search(r'\*\*🔍 分析方法:\*\*\s*([^*]+)', topic_info)
            if method_match:
                info_parts.append(f"分析方法: {method_match.group(1).strip()}")
            
            # 预期洞察
            insight_match = re.search(r'\*\*💡 预期洞察:\*\*\s*([^*]+)', topic_info)
            if insight_match:
                info_parts.append(f"预期洞察: {insight_match.group(1).strip()}")
            
            return "\n\n".join(info_parts)
        
        return ""
    
    def build_exa_prompt(self, materials: Dict[str, Union[str, List]]) -> str:
        """
        构建发送给Exa的提示
        
        Args:
            materials: 包含所有材料的字典
            
        Returns:
            完整的Exa提示
        """
        sections = []
        
        # 1. 基础指令
        intro = """请你作为一位专业的研究分析师，基于以下提供的材料生成一份深度研究报告。报告需要：
- 使用中文撰写
- 保持专业、客观、数据驱动的风格
- 结构清晰，论证严密
- 字数不少于3000字"""
        sections.append(intro)
        
        # 2. 研究背景和目标
        if materials.get("planning_info"):
            sections.append(f"## 研究背景和目标\n\n{materials['planning_info']}")
        
        # 3. 任务指导（如果有）
        if materials.get("prompt"):
            sections.append(f"## 任务指导\n\n{materials['prompt'][:2000]}")  # 限制长度
        
        # 4. 报告样例（如果有）
        if materials.get("example"):
            sections.append(f"## 参考样例（请模仿其风格和结构）\n\n{materials['example'][:3000]}")
        
        # 5. 数据源
        if materials.get("source_data"):
            source_section = "## 研究数据源\n\n"
            for i, source in enumerate(materials["source_data"][:10], 1):  # 限制数量
                source_section += f"### 数据源 {i}: {source['filename']}\n"
                source_section += f"{source['content'][:1000]}\n\n"  # 限制每个源的长度
            sections.append(source_section)
        
        # 6. 具体要求
        requirements = """## 报告要求

1. **结构要求**：
   - 执行摘要（500-800字）
   - 详细分析（分多个章节，每章节800-1200字）
   - 结论与建议（500-800字）
   - 参考文献

2. **内容要求**：
   - 基于提供的数据源进行分析
   - 使用具体的数据和案例支撑观点
   - 保持客观中立的分析视角
   - 提供可行的战略建议

3. **格式要求**：
   - 使用Markdown格式
   - 适当使用标题层级（# ## ### ####）
   - 数据引用使用[数字]格式
   - 包含必要的列表和表格

请基于以上材料和要求，生成一份专业的深度研究报告。"""
        sections.append(requirements)
        
        return "\n\n".join(sections)
    
    async def generate_report(self, topic_id: str, use_stream: bool = True) -> str:
        """
        为指定topic生成报告
        
        Args:
            topic_id: topic标识
            use_stream: 是否使用流式输出
            
        Returns:
            生成的报告内容
        """
        try:
            logger.info(f"🚀 开始为 {topic_id} 生成Exa报告")
            
            # 1. 加载材料
            materials = self.load_topic_materials(topic_id)
            
            # 2. 构建提示
            prompt = self.build_exa_prompt(materials)
            
            # 3. 调用Exa生成报告
            if use_stream:
                report_content = await self._generate_with_stream(prompt)
            else:
                report_content = await self._generate_with_task(prompt)
            
            # 4. 后处理报告
            processed_content = self._post_process_report(report_content, topic_id)
            
            # 5. 保存报告
            output_path = self._save_report(topic_id, processed_content)
            
            logger.info(f"✅ {topic_id} Exa报告生成完成: {output_path}")
            return processed_content
            
        except Exception as e:
            logger.error(f"❌ {topic_id} 报告生成失败: {str(e)}")
            raise
    
    async def _generate_with_stream(self, prompt: str) -> str:
        """使用流式API生成报告"""
        logger.info("🤖 使用Exa流式API生成报告...")
        
        completion = self.client.chat.completions.create(
            model="exa-research",
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True,
        )
        
        full_content = []
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_content.append(content)
        
        return "".join(full_content)
    
    async def _generate_with_task(self, prompt: str) -> str:
        """使用任务API生成报告"""
        logger.info("🤖 使用Exa任务API生成报告...")
        
        task_stub = self.exa.research.create_task(
            instructions=prompt,
            model="exa-research",
            output_infer_schema=False
        )
        
        # 轮询任务状态
        task = self.exa.research.poll_task(task_stub.id)
        
        return task.output if hasattr(task, 'output') else str(task)
    
    def _post_process_report(self, content: str, topic_id: str) -> str:
        """后处理报告内容"""
        
        # 添加元数据头部
        metadata_header = f"""---
title: Exa Research Report - {topic_id}
generated_by: Topic Report Exa Generator
model: exa-research
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
topic_id: {topic_id}
---

"""
        
        # 确保内容以标题开始
        if not content.strip().startswith('#'):
            topic_title = topic_id.replace('_', ' ').title()
            content = f"# {topic_title} 深度研究报告\n\n{content}"
        
        # 添加生成信息脚注
        footer = f"""

---

**报告生成信息**
- 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 生成系统: Topic Report Exa Generator
- AI模型: exa-research
- Topic ID: {topic_id}

*本报告由Exa Research AI自动生成*
"""
        
        return metadata_header + content + footer
    
    def _save_report(self, topic_id: str, content: str) -> str:
        """保存报告到文件"""
        
        # 查找对应的topic目录
        topic_dirs = glob.glob(os.path.join(self.result_dir, f"{topic_id}*"))
        if topic_dirs:
            output_dir = topic_dirs[0]
        else:
            output_dir = os.path.join(self.result_dir, topic_id)
            os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        topic_num = topic_id.split('_')[1] if '_' in topic_id else '1'
        filename = f"report_topic_{topic_num}_exa.md"
        output_path = os.path.join(output_dir, filename)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"📄 报告已保存: {output_path}")
        return output_path
    
    def generate_report_sync(self, topic_id: str, use_stream: bool = True) -> str:
        """同步版本的报告生成"""
        return asyncio.run(self.generate_report(topic_id, use_stream))


def generate_all_topic_reports():
    """为所有topic生成Exa报告"""
    generator = TopicReportExaGenerator()
    
    # 查找所有topic目录
    topic_dirs = glob.glob(os.path.join(generator.result_dir, "topic_*"))
    
    for topic_dir in sorted(topic_dirs):
        topic_name = os.path.basename(topic_dir)
        # 提取topic编号
        parts = topic_name.split('_')
        if len(parts) >= 2:
            topic_id = f"{parts[0]}_{parts[1]}"
            
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"处理 {topic_name}")
                logger.info(f"{'='*60}\n")
                
                report = generator.generate_report_sync(topic_id, use_stream=True)
                print("\n\n✅ 报告生成完成！\n")
                
            except Exception as e:
                logger.error(f"生成 {topic_id} 报告失败: {e}")
                continue


if __name__ == "__main__":
    # 生成所有topic的报告
    generate_all_topic_reports()