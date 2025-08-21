#!/usr/bin/env python3
"""
文件工具模块
提供文件保存、目录管理和文件名处理等功能
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from loguru import logger


def sanitize_filename(filename: str) -> str:
    """
    将字符串处理成有效的文件名
    
    Args:
        filename: 原始文件名字符串
        
    Returns:
        str: 清理后的有效文件名
    """
    # 替换无效字符
    invalid_chars = r'[<>:"/\\|?*\n\r\t]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # 移除多余的空格和点
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    sanitized = sanitized.strip('.')
    
    # 限制长度
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + '...'
    
    # 确保不为空
    if not sanitized:
        sanitized = "untitled"
        
    return sanitized


def ensure_directory_exists(directory_path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory_path: 目录路径
        
    Returns:
        bool: 成功创建或目录已存在返回True，失败返回False
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败: {directory_path}")
        return False


def safe_write_file(file_path: str, content: str) -> bool:
    """
    安全地将内容写入文件，处理潜在错误
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        
    Returns:
        bool: 写入成功返回True，失败返回False
    """
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not ensure_directory_exists(directory):
            return False
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件失败: {os.path.basename(file_path)}")
        return False


def generate_unique_filename(base_name: str, extension: str = ".md", output_dir: str = "result") -> str:
    """
    生成唯一的文件名，避免覆盖现有文件
    
    Args:
        base_name: 基础文件名
        extension: 文件扩展名
        output_dir: 输出目录
        
    Returns:
        str: 唯一的文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_name = sanitize_filename(base_name)
    
    # 生成基础文件名
    if sanitized_name.lower() == "report":
        filename = f"report_{timestamp}{extension}"
    else:
        filename = f"{sanitized_name}_{timestamp}{extension}"
    
    file_path = os.path.join(output_dir, filename)
    
    # 如果文件已存在，添加序号
    counter = 1
    original_path = file_path
    while os.path.exists(file_path):
        name_without_ext = os.path.splitext(original_path)[0]
        file_path = f"{name_without_ext}_{counter}{extension}"
        counter += 1
    
    return file_path


def save_report(report_content: str, query: str, metadata: Dict[str, Any], output_dir: str = "result", custom_filename: Optional[str] = None) -> Optional[str]:
    """
    保存研究报告到文件
    
    Args:
        report_content: 报告内容
        query: 原始查询
        metadata: 元数据信息
        output_dir: 输出目录
        
    Returns:
        Optional[str]: 成功返回文件路径，失败返回None
    """
    try:
        # 确保输出目录存在
        if not ensure_directory_exists(output_dir):
            return None
        
        # 生成文件路径
        if custom_filename:
            # 使用自定义文件名
            if not custom_filename.endswith('.md'):
                custom_filename += '.md'
            report_path = os.path.join(output_dir, custom_filename)
            
            # 如果文件已存在，添加序号避免覆盖
            counter = 1
            original_path = report_path
            while os.path.exists(report_path):
                name_without_ext = os.path.splitext(original_path)[0]
                report_path = f"{name_without_ext}_{counter}.md"
                counter += 1
        else:
            # 使用原来的自动生成逻辑
            report_path = generate_unique_filename("report", ".md", output_dir)
        
        # 构建完整的报告内容
        full_content = f"""# 深度研究分析报告

## 📋 元数据信息
- **研究主题**: {query}
- **生成时间**: {metadata.get('timestamp', datetime.now().isoformat())}
- **使用模型**: {metadata.get('model', 'Unknown')}
- **搜索查询数量**: {len(metadata.get('search_queries', []))}
- **数据源数量**: {metadata.get('sources_count', 0)}

## 🔍 搜索策略
本报告基于以下搜索查询进行深度研究：
"""
        
        # 添加搜索查询列表
        search_queries = metadata.get('search_queries', [])
        if search_queries:
            for i, sq in enumerate(search_queries, 1):
                full_content += f"{i}. `{sq}`\n"
        else:
            full_content += "无搜索查询记录\n"
        
        full_content += f"""

---

{report_content}

---

## 📊 研究统计
- **报告生成时间**: {metadata.get('timestamp', datetime.now().isoformat())}
- **数据源总数**: {metadata.get('sources_count', 0)}
- **搜索查询轮次**: {len(metadata.get('search_queries', []))}
- **AI模型**: {metadata.get('model', 'Unknown')}

*本报告由AI深度研究系统自动生成，基于多轮搜索和数据整合分析*
"""
        
        # 保存文件
        if safe_write_file(report_path, full_content):
            logger.success(f"研究报告已保存: {os.path.basename(report_path)}")
            return report_path
        else:
            return None
            
    except Exception as e:
        logger.error("保存研究报告失败")
        return None


def save_source_data(sources: List[Dict[str, Any]], output_dir: str = "result/source_data") -> List[str]:
    """
    将数据源保存为单独的文件到指定目录，自动去重
    
    Args:
        sources: 数据源列表
        output_dir: 输出目录，默认为result/source_data
        
    Returns:
        List[str]: 成功保存的文件路径列表
    """
    saved_files = []
    saved_urls = set()  # 跟踪已保存的URL，避免重复
    
    try:
        # 确保输出目录存在，如果不存在则自动创建
        if not ensure_directory_exists(output_dir):
            logger.error(f"无法创建数据源目录")
            return saved_files
        
        # 首先进行URL去重
        unique_sources = []
        seen_urls = set()
        for source in sources:
            url = source.get('value', source.get('url', ''))
            if url and url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(url)
        
        if len(unique_sources) > 0:
            logger.info(f"开始保存 {len(unique_sources)} 个唯一数据源（原始: {len(sources)} 个）")
        
        for i, source in enumerate(unique_sources):
            try:
                # 获取数据源信息
                title = source.get('title', f'数据源_{i+1}')
                # 优先使用value字段作为真实URL，如果没有则使用url字段
                real_url = source.get('value', source.get('url', ''))
                # 优先使用full_text，如果没有则使用related_content，最后使用snippet
                content_text = source.get('full_text', source.get('related_content', source.get('snippet', source.get('text', ''))))
                
                # 再次检查URL是否已保存（双重保险）
                if real_url in saved_urls:
                    logger.debug(f"跳过重复URL: {real_url[:50]}...")
                    continue
                
                # 生成当前时间
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 生成安全的文件名
                safe_title = sanitize_filename(title)
                filename = f"{safe_title}.md"
                file_path = os.path.join(output_dir, filename)
                
                # 如果文件已存在，直接跳过
                if os.path.exists(file_path):
                    logger.debug(f"文件已存在，跳过: {filename}")
                    continue
                
                # 安全地获取摘要字段和评分信息
                summary = source.get('summary', '')
                credibility = source.get('credibility', '待评估')
                related_assessment = source.get('related_assessment', '待评估')
                
                # 格式化评分显示
                credibility_display = credibility if isinstance(credibility, (int, float)) else credibility
                related_display = f"{related_assessment}%" if isinstance(related_assessment, (int, float)) else related_assessment
                
                # 按照要求的格式构建数据源内容
                content = f"""# {title}

## 基本信息
- **标题**: {title}
- **URL**: {real_url}
- **创建时间**: {current_time}
- **更新时间**: {current_time}

## 评估信息
- **可信度**: {credibility_display}
- **相关性**: {related_display}

## AI摘要
{summary if summary else '暂无摘要'}

## 内容
{content_text if content_text else '暂无内容'}

"""
                
                # 保存文件
                if safe_write_file(file_path, content):
                    saved_files.append(file_path)
                    saved_urls.add(real_url)  # 记录已保存的URL
                else:
                    logger.warning(f"数据源保存失败: {title[:30]}...")
                    
            except Exception as e:
                source_title = source.get('title', f'数据源_{i+1}')
                logger.warning(f"处理数据源时出错: {source_title[:30]}...")
                continue
        
        if len(saved_files) > 0:
            logger.success(f"数据源保存完成: {len(saved_files)} 个文件")
        return saved_files
        
    except Exception as e:
        logger.error("数据源保存过程出错")
        return saved_files


def create_summary_file(report_path: str, source_files: List[str], query: str, output_dir: str = "result") -> Optional[str]:
    """
    创建研究摘要文件，包含所有相关文件的链接
    
    Args:
        report_path: 报告文件路径
        source_files: 数据源文件路径列表
        query: 原始查询
        output_dir: 输出目录
        
    Returns:
        Optional[str]: 成功返回摘要文件路径，失败返回None
    """
    try:
        summary_path = os.path.join(output_dir, "research_summary.md")
        
        content = f"""# 研究摘要

## 查询信息
- **查询**: {query}
- **时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 文件结构

### 主报告
- [研究报告]({os.path.basename(report_path)})

### 数据源 ({len(source_files)} 个)
"""
        
        for source_file in source_files:
            filename = os.path.basename(source_file)
            # 从文件名中提取标题（去掉.md扩展名）
            title = os.path.splitext(filename)[0].replace('_', ' ')
            content += f"- [数据源: {title}](source_data/{filename})\n"
        
        content += f"""
## 目录结构
```
result/
├── research_summary.md     # 本文件
├── {os.path.basename(report_path)}           # 主研究报告
└── source_data/            # 数据源目录
"""
        
        for source_file in source_files:
            filename = os.path.basename(source_file)
            content += f"    ├── {filename}\n"
        
        content += "```\n"
        
        if safe_write_file(summary_path, content):
            logger.success(f"研究摘要已保存: {os.path.basename(summary_path)}")
            return summary_path
        else:
            return None
            
    except Exception as e:
        logger.error("创建研究摘要失败")
        return None