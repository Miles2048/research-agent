#!/usr/bin/env python3
"""
Enhanced Report Agent 核心报告生成器
整合所有组件，提供完整的报告生成服务
"""

import os
import shutil
import glob
import asyncio
from typing import Optional, Union
from datetime import datetime
from loguru import logger

from .config import EnhancedReportConfig, load_config
from .content_loader import ContentLoader
from .prompt_builder import PromptBuilder
from .filter_utils import filter_related_data

# 动态导入Claude客户端，处理依赖问题
try:
    from .claude_client import create_claude_client
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    logger.warning("Claude客户端不可用，将使用Mock模式")


class EnhancedReportGenerator:
    """Enhanced Report Generator - 核心生成器"""
    
    def __init__(self, config: Optional[EnhancedReportConfig] = None):
        """
        初始化Enhanced Report Generator
        
        Args:
            config: 配置对象，如果为None则自动加载
        """
        self.config = config or load_config()
        self.content_loader = ContentLoader(self.config.report_cfg_dir)
        self.prompt_builder = PromptBuilder()
        
        # 初始化Claude客户端
        if CLAUDE_AVAILABLE:
            self.claude_client = create_claude_client(
                self.config, 
                use_mock=not self.config.claude_api_key
            )
        else:
            logger.warning("将使用简化的Mock生成器")
            self.claude_client = None
        
        logger.info("Enhanced Report Generator 初始化完成")
    
    async def generate_report(self, topic_id: str) -> Optional[str]:
        """
        为指定topic生成专业报告
        
        Args:
            topic_id: topic ID，如 'topic_1'
            
        Returns:
            生成的报告文件路径，失败时返回None
        """
        try:
            logger.info(f"🚀 开始为 {topic_id} 生成专业报告")
            
            # 1. 检查前置条件
            if not self._check_prerequisites(topic_id):
                return None
            
            # 2. 确保数据源已同步
            self._sync_source_data(topic_id)
            
            # 3. 加载所有材料
            logger.info("📚 加载材料...")
            materials = self.content_loader.load_topic_materials(topic_id)

            # 3.5. 数据源筛选（如有必要）
            if (
                "source_data" in materials
                and isinstance(materials["source_data"], list)
                and hasattr(self.config, "filter_out_data_count")
                and self.config.filter_out_data_count > 0
            ):
                before_count = len(materials["source_data"])
                filtered = filter_related_data(
                    materials["source_data"], self.config.filter_out_data_count
                )
                after_count = len(filtered)
                logger.info(f"🔎 数据源筛选: {before_count} → {after_count} 篇 (filter_out_data_count={self.config.filter_out_data_count})")
                materials["source_data"] = filtered

            # 4. 构建提示
            logger.info("🔧 构建智能提示...")
            prompt = self.prompt_builder.build_claude_prompt(materials)
            
            # 5. 验证提示
            validation = self.prompt_builder.validate_prompt(prompt)
            if not validation["is_valid"]:
                logger.error(f"提示验证失败: {validation['errors']}")
                return None
            
            if validation["warnings"]:
                for warning in validation["warnings"]:
                    logger.warning(f"提示警告: {warning}")
            
            # 6. 生成报告
            logger.info("🤖 调用Claude Sonnet 4生成报告...")
            if self.claude_client:
                report_content = await self.claude_client.generate_report(prompt)
            else:
                report_content = self._generate_fallback_report(topic_id, materials)
            
            # 7. 后处理报告
            processed_content = self._post_process_report(report_content, topic_id)
            
            # 8. 保存报告
            output_path = self._save_report(topic_id, processed_content)
            
            logger.info(f"✅ {topic_id} 专业报告生成完成: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ {topic_id} 报告生成失败: {str(e)}")
            return None
    
    def generate_report_sync(self, topic_id: str) -> Optional[str]:
        """
        同步版本的报告生成
        
        Args:
            topic_id: topic ID
            
        Returns:
            生成的报告文件路径
        """
        return asyncio.run(self.generate_report(topic_id))
    
    def _check_prerequisites(self, topic_id: str) -> bool:
        """检查生成报告的前置条件"""
        
        # 检查topic配置目录
        topic_path = os.path.join(self.config.report_cfg_dir, topic_id)
        if not os.path.exists(topic_path):
            logger.warning(f"Topic配置目录不存在: {topic_path}，自动创建。")
            try:
                os.makedirs(topic_path, exist_ok=True)
                logger.info(f"已自动创建目录: {topic_path}")
            except Exception as e:
                logger.error(f"自动创建目录失败: {str(e)}")
                return False
        
        # 检查目录结构
        checks = self.content_loader.check_topic_structure(topic_id)
        if not checks["topic_dir"]:
            logger.error(f"Topic目录结构不完整")
            return False
        
        # 检查Claude客户端
        if self.claude_client and hasattr(self.claude_client, 'test_connection'):
            if not self.claude_client.test_connection():
                logger.warning("Claude API连接测试失败，将使用备用方案")
        
        return True
    
    def _sync_source_data(self, topic_id: str):
        """同步search_agent的结果到report_cfg"""
        
        # 查找results目录中对应的topic
        result_dirs = glob.glob(f"{self.config.results_dir}/topic_*")
        
        source_dir = None
        for result_dir in result_dirs:
            if topic_id in os.path.basename(result_dir):
                potential_source = os.path.join(result_dir, "source_data")
                if os.path.exists(potential_source):
                    source_dir = potential_source
                    break
        
        if not source_dir:
            logger.warning(f"⚠️ 未找到 {topic_id} 的source_data目录，跳过同步")
            return
        
        # 目标目录
        target_dir = os.path.join(self.config.report_cfg_dir, topic_id, "source_data")
        
        try:
            # 创建父目录
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            
            # 备份现有数据（如果存在）
            if os.path.exists(target_dir):
                backup_dir = f"{target_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(target_dir, backup_dir)
                logger.debug(f"已备份现有数据到: {backup_dir}")
            
            # 复制新数据
            shutil.copytree(source_dir, target_dir)
            
            # 统计文件数量
            file_count = len(glob.glob(os.path.join(target_dir, "*.md")))
            logger.info(f"📋 数据源已同步: {file_count} 个文件")
            logger.debug(f"同步路径: {source_dir} → {target_dir}")
            
        except Exception as e:
            logger.error(f"数据源同步失败: {str(e)}")
    
    def _post_process_report(self, content: str, topic_id: str) -> str:
        """后处理报告内容"""
        
        # 添加元数据头部
        metadata_header = f"""---
title: Enhanced Report - {topic_id}
generated_by: Enhanced Report Agent
model: {self.config.claude_model}
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
topic_id: {topic_id}
---

"""
        
        # 确保内容以标题开始
        if not content.strip().startswith('#'):
            content = f"# {topic_id.replace('_', ' ').title()} 专业分析报告\n\n{content}"
        
        # 添加生成信息脚注
        footer = f"""

---

**报告生成信息**
- 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 生成系统: Enhanced Report Agent v1.0
- AI模型: {self.config.claude_model}
- Topic ID: {topic_id}

*本报告由AI自动生成，基于提供的研究材料和数据源*
"""
        
        return metadata_header + content + footer
    
    def _save_report(self, topic_id: str, content: str) -> str:
        """保存报告到指定位置"""
        
        # 生成输出路径
        filename = self.config.output_filename_pattern.format(topic_id=topic_id)
        output_dir = os.path.join(self.config.results_dir, topic_id)
        output_path = os.path.join(output_dir, filename)
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 备份现有文件
        if os.path.exists(output_path):
            backup_path = f"{output_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(output_path, backup_path)
            logger.debug(f"已备份现有报告: {backup_path}")
        
        # 保存新文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 获取文件信息
            file_size = os.path.getsize(output_path)
            logger.info(f"📄 报告已保存: {output_path}")
            logger.debug(f"文件大小: {file_size:,} 字节")
            
            return output_path
            
        except Exception as e:
            logger.error(f"保存报告失败: {str(e)}")
            raise
    
    def _generate_fallback_report(self, topic_id: str, materials: dict) -> str:
        """生成备用报告（当Claude不可用时）"""
        
        logger.info("使用备用报告生成器")
        
        # 简单的模板报告
        report = f"""# {topic_id.replace('_', ' ').title()} 分析报告

## 执行摘要

本报告基于Enhanced Report Agent收集的材料生成。由于Claude Sonnet 4服务暂时不可用，本报告采用备用生成方式。

## 材料概览

### 任务指导
{self._extract_summary(materials.get('prompt', ''), 200)}

### 研究方法
{self._extract_summary(materials.get('artifacts', ''), 300)}

### 参考样例
{self._extract_summary(materials.get('example', ''), 300)}

### 数据源统计
{self._generate_source_summary(materials.get('source_data', ''))}

## 建议

基于可用材料，建议：

1. **完善配置**: 确保ANTHROPIC_API_KEY正确设置
2. **检查网络**: 验证与Claude API的连接
3. **重新生成**: 在条件满足后重新运行报告生成

## 系统信息

- 生成方式: 备用模板
- Topic: {topic_id}
- 配置状态: {'正常' if self.config.claude_api_key else 'API密钥缺失'}
- 材料完整度: {sum(1 for v in materials.values() if v.strip())}/4

*请配置Claude API后重新生成专业报告*
"""
        
        return report
    
    def _extract_summary(self, content: str, max_length: int = 200) -> str:
        """提取内容摘要"""
        if not content.strip():
            return "（内容为空）"
        
        # 清理内容
        clean_content = content.replace('#', '').replace('*', '').strip()
        
        # 截取并添加省略号
        if len(clean_content) > max_length:
            return clean_content[:max_length] + "..."
        
        return clean_content
    
    def _generate_source_summary(self, source_data: str) -> str:
        """生成数据源统计"""
        if not source_data.strip():
            return "（无数据源）"
        
        # 简单统计
        lines = source_data.split('\n')
        file_markers = [line for line in lines if line.strip().startswith('### 📄')]
        
        return f"共发现 {len(file_markers)} 个数据源文件，总内容长度: {len(source_data):,} 字符"


# 便捷函数
async def generate_enhanced_report(topic_id: str, config: Optional[EnhancedReportConfig] = None) -> Optional[str]:
    """
    便捷函数：生成Enhanced Report
    
    Args:
        topic_id: topic ID
        config: 可选的配置对象
        
    Returns:
        生成的报告文件路径
    """
    generator = EnhancedReportGenerator(config)
    return await generator.generate_report(topic_id)


def generate_enhanced_report_sync(topic_id: str, config: Optional[EnhancedReportConfig] = None) -> Optional[str]:
    """
    便捷函数：同步生成Enhanced Report  
    
    Args:
        topic_id: topic ID
        config: 可选的配置对象
        
    Returns:
        生成的报告文件路径
    """
    return asyncio.run(generate_enhanced_report(topic_id, config))


if __name__ == "__main__":
    # 测试报告生成器
    async def test_generator():
        try:
            # 创建生成器
            generator = EnhancedReportGenerator()
            
            # 生成报告
            result = await generator.generate_report("topic_1")
            
            if result:
                print(f"✅ 测试成功，报告已生成: {result}")
            else:
                print("❌ 测试失败，报告生成失败")
                
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
    
    # 运行测试
    asyncio.run(test_generator())