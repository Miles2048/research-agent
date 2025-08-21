"""
Planning List File Operations

用于处理planning_list.md文件的读写操作模块
支持计划的创建、读取、更新和追加操作
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger


def get_planning_file_path() -> str:
    """获取planning_list.md文件的完整路径"""
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(src_dir, "planning_list.md")


def ensure_planning_file_exists() -> str:
    """确保planning_list.md文件存在，如果不存在则创建"""
    file_path = get_planning_file_path()
    
    if not os.path.exists(file_path):
        logger.info(f"创建新的planning文件: {file_path}")
        create_initial_planning_file(file_path)
    
    return file_path


def create_initial_planning_file(file_path: str):
    """创建初始的planning_list.md文件"""
    initial_content = """# 研究计划列表

> 这个文件包含所有的研究计划和搜索策略
> 
> 更新时间: {timestamp}

## 使用说明

- **方案一**: 通过对话修改计划，AI会自动更新这个文件
- **方案二**: 直接编辑这个文件，手动修改计划内容

---

""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(initial_content)
    
    logger.info("初始planning文件创建完成")


def read_planning_file() -> str:
    """读取planning_list.md文件内容"""
    file_path = ensure_planning_file_exists()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info("成功读取planning文件")
        return content
    except Exception as e:
        logger.error(f"读取planning文件失败: {str(e)}")
        return ""


def write_planning_file(content: str):
    """写入planning_list.md文件"""
    file_path = ensure_planning_file_exists()
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info("成功写入planning文件")
    except Exception as e:
        logger.error(f"写入planning文件失败: {str(e)}")
        raise


def append_planning_to_file(planning_data: Dict[str, Any], query: str):
    """将新的计划追加到planning_list.md文件"""
    file_path = ensure_planning_file_exists()
    
    # 生成计划的Markdown格式
    planning_md = format_planning_as_markdown(planning_data, query)
    
    try:
        # 读取现有内容
        existing_content = read_planning_file()
        
        # 追加新计划
        if existing_content.strip():
            updated_content = existing_content + "\n" + planning_md
        else:
            # 如果文件为空，创建初始结构
            create_initial_planning_file(file_path)
            existing_content = read_planning_file()
            updated_content = existing_content + "\n" + planning_md
        
        # 更新时间戳
        updated_content = update_timestamp_in_content(updated_content)
        
        # 写入文件
        write_planning_file(updated_content)
        
        logger.info(f"成功追加新计划到文件: {query[:50]}...")
        
    except Exception as e:
        logger.error(f"追加计划到文件失败: {str(e)}")
        raise


def overwrite_planning_to_file(planning_data: Dict[str, Any], query: str):
    """用新的计划覆盖planning_list.md文件"""
    
    # 确保文件存在
    file_path = ensure_planning_file_exists()
    
    try:
        # 生成新的完整文件内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建新的文件内容，包含头部信息
        file_content = f"""# 研究计划列表

> 这是一个动态更新的研究计划文档  
> 更新时间: {timestamp}

---

"""
        
        # 生成计划的Markdown格式
        planning_md = format_planning_as_markdown(planning_data, query)
        
        # 组合完整内容
        updated_content = file_content + planning_md
        
        # 写入文件（覆盖原有内容）
        write_planning_file(updated_content)
        
        logger.info(f"成功覆盖计划到文件: {query[:50]}...")
        
    except Exception as e:
        logger.error(f"覆盖计划到文件失败: {str(e)}")
        raise


def format_planning_as_markdown(planning_data: Dict[str, Any], query: str) -> str:
    """将报告规划数据格式化为Markdown"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 检查是否为新的ReportPlan格式
    if 'report_title' in planning_data and 'research_topics' in planning_data:
        return format_report_plan_as_markdown(planning_data, query, timestamp)
    else:
        # 向后兼容旧格式
        return format_legacy_planning_as_markdown(planning_data, query, timestamp)


def format_report_plan_as_markdown(planning_data: Dict[str, Any], query: str, timestamp: str) -> str:
    """将ReportPlan格式化为Markdown"""
    
    md_content = f"""## 📋 研究报告规划 - {timestamp}

### 🎯 报告标题
**{planning_data.get('report_title', '未定义标题')}**

### 🔍 原始查询
```
{query}
```

### ❓ 核心研究问题
{planning_data.get('core_research_question', '未定义研究问题')}

### 📊 执行摘要重点
{planning_data.get('executive_summary_focus', '未定义摘要重点')}

### 👥 目标受众
{planning_data.get('target_audience', '决策者和相关利益方')}

### 📖 分析深度
{planning_data.get('analysis_depth', '深度研究')}

---

## 🔬 研究主题设计

"""
    
    # 研究主题
    research_topics = planning_data.get('research_topics', [])
    for i, topic in enumerate(research_topics, 1):
        md_content += f"""### Topic {i}: {topic.get('topic_name', f'主题{i}')}
**{topic.get('topic_subtitle', '未定义副标题')}**

**🎯 研究目标:**
{topic.get('research_objective', '未定义研究目标')}

**📋 数据需求:**
"""
        for req in topic.get('data_requirements', []):
            md_content += f"- {req}\n"
        
        md_content += f"""
**🔍 分析方法:**
{topic.get('analysis_approach', '未定义分析方法')}

**💡 预期洞察:**
{topic.get('expected_insights', '未定义预期洞察')}

**📦 交付物:**
"""
        for deliverable in topic.get('deliverables', []):
            md_content += f"- {deliverable}\n"
        
        md_content += f"""
**🔎 Search Agent指导:**
{topic.get('search_instructions', '未定义搜索指导')}

---

"""
    
    # 综合分析
    md_content += f"""## 🔗 跨主题综合分析
{planning_data.get('cross_topic_synthesis', '未定义综合分析方法')}

## 📄 最终交付类型
{planning_data.get('final_deliverable_type', '数据驱动的战略分析报告')}

---
*规划生成时间: {timestamp}*
"""
    
    return md_content


def format_legacy_planning_as_markdown(planning_data: Dict[str, Any], query: str, timestamp: str) -> str:
    """格式化旧版planning数据为Markdown（向后兼容）"""
    
    md_content = f"""## 📋 计划 - {timestamp}

### 🔍 原始查询
```
{query}
```

### 🎯 搜索分类
"""
    
    # 搜索分类
    if 'search_categories' in planning_data:
        for i, category in enumerate(planning_data['search_categories'], 1):
            md_content += f"{i}. {category}\n"
    
    # 关键词
    md_content += "\n### 🔑 关键词\n"
    if 'keywords' in planning_data:
        keywords_text = ", ".join(planning_data['keywords'])
        md_content += f"```\n{keywords_text}\n```\n"
    
    # 搜索角度
    md_content += "\n### 🔍 搜索角度\n"
    if 'search_angles' in planning_data:
        for i, angle in enumerate(planning_data['search_angles'], 1):
            md_content += f"{i}. {angle}\n"
    
    # 数据源
    md_content += "\n### 📚 数据源分类\n"
    if 'data_sources' in planning_data:
        data_sources = planning_data['data_sources']
        source_types = {
            'academic_sources': '🎓 学术数据源',
            'industry_sources': '🏢 行业数据源',
            'regulatory_sources': '📜 政策法规数据源',
            'market_sources': '📈 市场数据源'
        }
        
        for source_type, sources in data_sources.items():
            if sources:  # 只显示非空的数据源
                type_name = source_types.get(source_type, source_type)
                md_content += f"\n**{type_name}:**\n"
                for source in sources:
                    md_content += f"- {source}\n"
    
    # 计划属性
    md_content += "\n### ⚙️ 计划属性\n"
    md_content += f"- **优先级**: {planning_data.get('priority', '未设置')}\n"
    md_content += f"- **复杂度**: {planning_data.get('estimated_complexity', '未设置')}\n"
    
    # 研究范围
    if 'scope' in planning_data and planning_data['scope']:
        md_content += f"\n### 📖 研究范围\n{planning_data['scope']}\n"
    
    md_content += "\n---\n"
    
    return md_content


def update_timestamp_in_content(content: str) -> str:
    """更新内容中的时间戳"""
    import re
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 查找并替换时间戳
    pattern = r'> 更新时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    replacement = f'> 更新时间: {current_time}'
    
    updated_content = re.sub(pattern, replacement, content)
    
    return updated_content


def get_all_planning_entries() -> List[Dict[str, Any]]:
    """解析planning_list.md文件，提取所有计划条目"""
    content = read_planning_file()
    
    # 这里可以实现Markdown解析逻辑
    # 返回计划条目列表，每个条目包含查询、分类、关键词等信息
    # 目前返回空列表，后续可以根据需要实现
    return []


def update_planning_entry(entry_index: int, updated_data: Dict[str, Any]):
    """更新指定的计划条目"""
    # 这里可以实现特定条目的更新逻辑
    # 目前为占位符，后续可以根据需要实现
    logger.info(f"更新计划条目 {entry_index}")
    pass


def backup_planning_file():
    """备份当前的planning文件"""
    file_path = get_planning_file_path()
    
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"创建备份文件: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            return None
    
    return None


def get_planning_file_info() -> Dict[str, Any]:
    """获取planning文件的信息"""
    file_path = get_planning_file_path()
    
    if os.path.exists(file_path):
        stat = os.stat(file_path)
        return {
            "file_path": file_path,
            "exists": True,
            "size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "readable": os.access(file_path, os.R_OK),
            "writable": os.access(file_path, os.W_OK)
        }
    else:
        return {
            "file_path": file_path,
            "exists": False
        }


# 对话式修改功能
def process_conversation_update(user_message: str, current_content: str) -> str:
    """
    处理用户通过对话修改计划的请求
    
    Args:
        user_message: 用户的修改请求
        current_content: 当前planning文件内容
        
    Returns:
        更新后的文件内容
    """
    # 这里可以集成LLM来理解用户的修改意图
    # 并生成相应的Markdown更新
    # 目前返回原内容，后续可以实现智能更新逻辑
    
    logger.info(f"处理对话更新请求: {user_message[:100]}...")
    
    # 简单的示例：在文件末尾添加用户的注释
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_note = f"\n### 💬 用户更新 - {timestamp}\n{user_message}\n\n---\n"
    
    updated_content = current_content + update_note
    updated_content = update_timestamp_in_content(updated_content)
    
    return updated_content 