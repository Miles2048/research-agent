#!/usr/bin/env python3
"""
Topic Report Perplexity Generator
使用Perplexity Sonar API生成专业的topic报告
"""

import os
import sys
import glob
import json
import asyncio
import requests
from datetime import datetime
from typing import Dict, Optional, List, Union
from loguru import logger
from dotenv import load_dotenv

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量 - 从backend目录的.env文件
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

# 导入 prompt 构建器
try:
    # 作为模块导入时使用相对导入
    from .prompt_builder import PromptBuilder
    from .perplexity_prompts import PerplexityPrompts
except ImportError:
    # 直接运行时使用绝对导入
    from prompt_builder import PromptBuilder
    from perplexity_prompts import PerplexityPrompts


class TopicReportPerplexityGenerator:
    """使用Perplexity生成Topic报告"""
    
    def __init__(self, perplexity_api_key: str = None, report_type: str = "standard"):
        """
        初始化Perplexity报告生成器
        
        Args:
            perplexity_api_key: Perplexity API密钥，如果不提供将从环境变量读取
            report_type: 报告类型 (standard, simple, detailed)
        """
        self.api_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY 未设置。请在环境变量中设置 PERPLEXITY_API_KEY 或在初始化时传入 api_key 参数。")
        
        # API配置
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"  # 可选: llama-3.1-sonar-small, llama-3.1-sonar-large, llama-3.1-sonar-huge
        
        # 路径配置 - 修正路径
        # backend/src/topic_report_perplexity -> backend
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 设置结果输出目录为 results_perplexity
        self.result_dir = os.path.join(backend_dir, "results")  # 用于读取source_data
        self.output_dir = os.path.join(backend_dir, "results_perplexity")  # 用于保存报告
        self.report_cfg_dir = os.path.join(backend_dir, "report_cfg")
        self.planning_file = os.path.join(backend_dir, "src", "planning_list.md")
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化 prompt 构建器
        self.prompt_builder = PromptBuilder()
        self.report_type = report_type
        
        logger.info("Topic Report Perplexity Generator 初始化完成")
    
    def load_topic_materials(self, topic_id: str) -> Dict[str, Union[str, List]]:
        """
        加载topic相关的所有材料
        
        Args:
            topic_id: topic标识，如 'topic_1' 或 'topic_1_市场格局分析'
            
        Returns:
            包含所有材料的字典
        """
        materials = {
            "methodology": "",      # 研究方法论 (A1.md)
            "template": "",         # 报告模板 (example/*.md)
            "source_data": [],      # 数据源
            "planning_info": ""     # 规划信息（可选）
        }
        
        # 查找对应的topic目录 - 在results目录下
        topic_dirs = glob.glob(os.path.join(self.result_dir, f"{topic_id}*"))
        if not topic_dirs:
            logger.warning(f"未找到topic目录: {topic_id} in {self.result_dir}")
            return materials
        
        topic_dir = topic_dirs[0]
        topic_name = os.path.basename(topic_dir)
        logger.info(f"找到topic目录: {topic_dir}")
        
        # 1. 加载source_data
        source_data_dir = os.path.join(topic_dir, "source_data")
        if os.path.exists(source_data_dir):
            source_files = glob.glob(os.path.join(source_data_dir, "*.md"))
            materials["source_data"] = []
            for file_path in sorted(source_files)[:10]:  # 限制文件数量
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
        
        # 3. 从report_cfg加载方法论和模板
        # 提取topic编号，如 topic_1_产品国际化护照构建 -> topic_1
        topic_num = topic_id.split('_')[0] + '_' + topic_id.split('_')[1] if '_' in topic_id else topic_id
        cfg_topic_dir = os.path.join(self.report_cfg_dir, topic_num)
        
        logger.info(f"查找report_cfg目录: {cfg_topic_dir}")
        
        if os.path.exists(cfg_topic_dir):
            # 加载研究方法论 (A1.md)
            methodology_file = os.path.join(cfg_topic_dir, "artifacts", "A1.md")
            if os.path.exists(methodology_file):
                try:
                    with open(methodology_file, 'r', encoding='utf-8') as f:
                        materials["methodology"] = f.read()
                    logger.info(f"加载了研究方法论: {methodology_file}")
                except Exception as e:
                    logger.error(f"读取方法论文件失败: {e}")
            else:
                logger.warning(f"未找到方法论文件: {methodology_file}")
            
            # 加载报告模板 - 优先查找 topic_X_perplexity.md
            template_pattern = f"{topic_num}_perplexity.md"
            template_file = os.path.join(cfg_topic_dir, "example", template_pattern)
            
            if os.path.exists(template_file):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        materials["template"] = f.read()[:15000]  # 增加长度限制
                    logger.info(f"加载了Perplexity报告模板: {template_file}")
                except Exception as e:
                    logger.error(f"读取模板文件失败: {e}")
            else:
                # 如果没有perplexity模板，查找其他模板
                template_files = glob.glob(os.path.join(cfg_topic_dir, "example", "*.md"))
                if template_files:
                    try:
                        with open(template_files[0], 'r', encoding='utf-8') as f:
                            materials["template"] = f.read()[:15000]
                        logger.info(f"加载了通用报告模板: {template_files[0]}")
                    except Exception as e:
                        logger.error(f"读取模板文件失败: {e}")
                else:
                    logger.warning(f"未找到任何模板文件在: {os.path.join(cfg_topic_dir, 'example')}")
        
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
    
    def build_perplexity_prompt(self, materials: Dict[str, Union[str, List]], topic_id: str = "") -> str:
        """
        使用 prompt 构建器构建提示
        
        Args:
            materials: 包含所有材料的字典
            topic_id: topic 标识，用于确定报告类型
            
        Returns:
            完整的Perplexity提示
        """
        # 使用新的 build_research_prompt 方法
        return self.prompt_builder.build_research_prompt(
            methodology=materials.get('methodology', ''),
            template=materials.get('template', ''),
            source_data=materials.get('source_data', []),
            planning_info=materials.get('planning_info', '')
        )
    
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
            logger.info(f"🚀 开始为 {topic_id} 生成Perplexity报告")
            
            # 1. 加载材料
            materials = self.load_topic_materials(topic_id)
            
            # 2. 构建提示
            prompt = self.build_perplexity_prompt(materials, topic_id)
            
            # 打印 prompt 内容（用于调试）
            logger.info("=" * 80)
            logger.info("📝 生成的 Perplexity Prompt:")
            logger.info("=" * 80)
            print("\n" + prompt + "\n")
            logger.info("=" * 80)
            logger.info(f"Prompt 长度: {len(prompt)} 字符")
            logger.info("=" * 80)
            
            # 3. 调用Perplexity生成报告
            if use_stream:
                report_content = await self._generate_with_stream(prompt)
            else:
                report_content = await self._generate_without_stream(prompt)
            
            # 4. 后处理报告
            processed_content = self._post_process_report(report_content, topic_id)
            
            # 5. 保存报告和prompt
            output_path = self._save_report(topic_id, processed_content)
            self._save_prompt(topic_id, prompt)
            
            logger.info(f"✅ {topic_id} Perplexity报告生成完成: {output_path}")
            return processed_content
            
        except Exception as e:
            logger.error(f"❌ {topic_id} 报告生成失败: {str(e)}")
            raise
    
    async def _generate_with_stream(self, prompt: str) -> str:
        """使用流式API生成报告"""
        logger.info("🤖 使用Perplexity流式API生成报告...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            "temperature": 0.3,
            "max_tokens": 8192  # 增加到8192以支持7000字的报告
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload, stream=True)
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
        
        full_content = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if 'choices' in data and data['choices']:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                # print(content, end='', flush=True)  # 注释掉流式输出到终端
                                full_content.append(content)
                    except json.JSONDecodeError:
                        continue
        
        return "".join(full_content)
    
    async def _generate_without_stream(self, prompt: str) -> str:
        """使用非流式API生成报告"""
        logger.info("🤖 使用Perplexity非流式API生成报告...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 8192  # 增加到8192以支持7000字的报告
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
        
        data = response.json()
        return data['choices'][0]['message']['content']
    
    def _post_process_report(self, content: str, topic_id: str) -> str:
        """后处理报告内容"""
        
        # 添加元数据头部
        metadata_header = f"""---
title: Perplexity Research Report - {topic_id}
generated_by: Topic Report Perplexity Generator
model: {self.model}
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
- 生成系统: Topic Report Perplexity Generator
- AI模型: {self.model}
- Topic ID: {topic_id}

*本报告由Perplexity AI自动生成，包含实时搜索和验证的信息*
"""
        
        return metadata_header + content + footer
    
    def _save_report(self, topic_id: str, content: str) -> str:
        """保存报告到文件"""
        
        # 在results_perplexity下创建topic目录
        # 先尝试从results目录获取完整的topic名称
        topic_dirs = glob.glob(os.path.join(self.result_dir, f"{topic_id}*"))
        if topic_dirs:
            # 使用找到的完整topic名称
            topic_full_name = os.path.basename(topic_dirs[0])
            output_dir = os.path.join(self.output_dir, topic_full_name)
        else:
            # 如果没找到，使用原始topic_id
            output_dir = os.path.join(self.output_dir, topic_id)
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        topic_num = topic_id.split('_')[1] if '_' in topic_id else '1'
        filename = f"report_topic_{topic_num}_perplexity.md"
        output_path = os.path.join(output_dir, filename)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"📄 报告已保存: {output_path}")
        return output_path
    
    def _save_prompt(self, topic_id: str, prompt: str) -> str:
        """保存原始prompt到文件"""
        
        # 在results_perplexity下创建topic目录（与报告保存在同一位置）
        # 先尝试从results目录获取完整的topic名称
        topic_dirs = glob.glob(os.path.join(self.result_dir, f"{topic_id}*"))
        if topic_dirs:
            # 使用找到的完整topic名称
            topic_full_name = os.path.basename(topic_dirs[0])
            output_dir = os.path.join(self.output_dir, topic_full_name)
        else:
            # 如果没找到，使用原始topic_id
            output_dir = os.path.join(self.output_dir, topic_id)
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成prompt文件名
        prompt_filename = "prompt_raw.md"
        prompt_path = os.path.join(output_dir, prompt_filename)
        
        # 添加元数据头部
        prompt_with_metadata = f"""---
title: Raw Prompt for Perplexity Report Generation
topic_id: {topic_id}
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
model: {self.model}
api_used: Perplexity Sonar API
---

# 原始 Prompt 内容

以下是生成 {topic_id} 报告时发送给 Perplexity AI 的完整 prompt：

---

{prompt}

---

*此文件记录了完整的 prompt 内容，用于调试和优化报告生成过程*
"""
        
        # 保存prompt文件
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt_with_metadata)
        
        logger.info(f"📝 Prompt已保存: {prompt_path}")
        return prompt_path
    
    def generate_report_sync(self, topic_id: str, use_stream: bool = True) -> str:
        """同步版本的报告生成"""
        return asyncio.run(self.generate_report(topic_id, use_stream))


def generate_all_topic_reports():
    """为所有topic生成Perplexity报告"""
    generator = TopicReportPerplexityGenerator()
    
    # 查找所有topic目录 - 在results目录下
    topic_dirs = glob.glob(os.path.join(generator.result_dir, "topic_*"))
    
    logger.info(f"在 {generator.result_dir} 中找到 {len(topic_dirs)} 个topic目录")
    
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


def test_single_topic(topic_id: str = "topic_1"):
    """测试单个topic的报告生成"""
    try:
        generator = TopicReportPerplexityGenerator()
        report = generator.generate_report_sync(topic_id, use_stream=True)
        print("\n\n✅ 测试报告生成成功！")
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 如果提供了参数，测试特定的topic
        test_single_topic(sys.argv[1])
    else:
        # 否则生成所有topic的报告
        generate_all_topic_reports()