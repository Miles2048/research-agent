#!/usr/bin/env python3
"""
Enhanced Report Agent 内容加载器
动态加载report_cfg中的所有材料
"""

import os
import glob
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger


class ContentLoader:
    """灵活的内容加载器，动态读取report_cfg中的材料"""
    
    def __init__(self, base_path: str = "report_cfg"):
        """
        初始化内容加载器
        
        Args:
            base_path: report_cfg基础路径
        """
        self.base_path = base_path
    
    def load_topic_materials(self, topic_id: str) -> Dict[str, str]:
        """
        加载指定topic的所有材料
        
        Args:
            topic_id: topic ID，如 'topic_1'
            
        Returns:
            包含所有材料的字典
        """
        topic_path = os.path.join(self.base_path, topic_id)
        
        if not os.path.exists(topic_path):
            raise FileNotFoundError(f"Topic配置目录不存在: {topic_path}")
        
        logger.info(f"开始加载 {topic_id} 的材料...")
        
        materials = {
            "prompt": self._load_prompt(topic_path),
            "artifacts": self._load_artifacts(topic_path),
            "example": self._load_example(topic_path),
            "source_data": self._load_source_data(topic_path)
        }
        
        # 统计加载结果（兼容新的list格式）
        loaded_count = 0
        for key, content in materials.items():
            if key == "source_data":
                # source_data现在是列表格式
                if isinstance(content, list) and content:
                    loaded_count += 1
                elif isinstance(content, str) and content.strip():
                    loaded_count += 1
            else:
                # 其他材料仍然是字符串格式
                if content and content.strip():
                    loaded_count += 1
        
        logger.info(f"✅ {topic_id} 材料加载完成: {loaded_count}/4 个部分有内容")
        
        return materials
    
    def _load_prompt(self, topic_path: str) -> str:
        """加载prompt.md"""
        prompt_file = os.path.join(topic_path, "prompt", "prompt.md")
        content = self._read_file_safely(prompt_file)
        
        if content:
            logger.debug("✅ prompt.md 加载成功")
        else:
            logger.warning("⚠️ prompt.md 未找到或为空")
        
        return content
    
    def _load_artifacts(self, topic_path: str) -> str:
        """加载artifacts目录下所有文件"""
        artifacts_dir = os.path.join(topic_path, "artifacts")
        content = self._load_directory_content(artifacts_dir, "研究方法参考")
        
        if content:
            logger.debug("✅ artifacts 目录加载成功")
        else:
            logger.warning("⚠️ artifacts 目录未找到或为空")
        
        return content
    
    def _load_example(self, topic_path: str) -> str:
        """加载example目录下所有文件"""  
        example_dir = os.path.join(topic_path, "example")
        content = self._load_directory_content(example_dir, "报告样例")
        
        if content:
            logger.debug("✅ example 目录加载成功")
        else:
            logger.warning("⚠️ example 目录未找到或为空")
        
        return content
    
    def _load_source_data(self, topic_path: str) -> List[Dict[str, str]]:
        """加载source_data目录下的所有文件，保持文章独立性"""
        source_dir = os.path.join(topic_path, "source_data")
        
        if not os.path.exists(source_dir):
            logger.warning("⚠️ source_data 目录未找到")
            return []
        
        # 获取所有markdown文件
        md_files = glob.glob(os.path.join(source_dir, "*.md"))
        
        if not md_files:
            logger.warning("⚠️ source_data 目录为空")
            return []
        
        # 保存每篇文章的信息
        articles = []
        
        for file_path in sorted(md_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    
                if content:  # 只添加非空文件
                    file_name = os.path.basename(file_path)
                    articles.append({
                        "title": file_name,
                        "content": content,
                        "length": len(content)
                    })
                    
            except Exception as e:
                logger.error(f"加载文件失败: {file_path}, 错误: {str(e)}")
        
        if articles:
            logger.debug(f"✅ source_data 目录加载成功 ({len(articles)} 个文件)")
        else:
            logger.warning("⚠️ source_data 目录中没有有效内容")
        
        return articles
    
    def _load_directory_content(self, directory: str, content_type: str = "内容") -> str:
        """
        加载目录下所有.md文件的内容
        
        Args:
            directory: 目录路径
            content_type: 内容类型描述
            
        Returns:
            合并后的文件内容
        """
        if not os.path.exists(directory):
            return ""
        
        content_parts = []
        md_files = glob.glob(os.path.join(directory, "*.md"))
        
        if not md_files:
            return ""
        
        for file_path in sorted(md_files):
            filename = os.path.basename(file_path)
            file_content = self._read_file_safely(file_path)
            
            if file_content:
                # 添加文件标识
                content_parts.append(f"### 📄 {filename}\n{file_content}")
        
        if content_parts:
            return f"## {content_type}\n\n" + "\n\n".join(content_parts)
        
        return ""
    
    def _read_file_safely(self, file_path: str) -> str:
        """
        安全读取文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容，失败时返回空字符串
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    return content
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {str(e)}")
        
        return ""
    
    def check_topic_structure(self, topic_id: str) -> Dict[str, bool]:
        """
        检查topic目录结构是否完整
        
        Args:
            topic_id: topic ID
            
        Returns:
            各部分存在情况的字典
        """
        topic_path = os.path.join(self.base_path, topic_id)
        
        checks = {
            "topic_dir": os.path.exists(topic_path),
            "prompt_dir": os.path.exists(os.path.join(topic_path, "prompt")),
            "artifacts_dir": os.path.exists(os.path.join(topic_path, "artifacts")),
            "example_dir": os.path.exists(os.path.join(topic_path, "example")),
            "source_data_dir": os.path.exists(os.path.join(topic_path, "source_data")),
            "prompt_file": os.path.exists(os.path.join(topic_path, "prompt", "prompt.md"))
        }
        
        return checks


if __name__ == "__main__":
    # 测试内容加载器
    loader = ContentLoader()
    
    try:
        # 检查结构
        checks = loader.check_topic_structure("topic_1")
        print("📋 Topic结构检查:")
        for item, exists in checks.items():
            status = "✅" if exists else "❌"
            print(f"  {status} {item}")
        
        # 加载材料
        if checks["topic_dir"]:
            materials = loader.load_topic_materials("topic_1")
            print(f"\n📄 材料加载结果:")
            for key, content in materials.items():
                length = len(content)
                print(f"  {key}: {length} 字符")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")