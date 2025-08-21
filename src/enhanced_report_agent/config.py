#!/usr/bin/env python3
"""
Enhanced Report Agent 配置管理
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EnhancedReportConfig:
    """Enhanced Report Agent配置"""
    
    # Claude配置
    claude_model: str = "claude-3-7-sonnet-20250219"
    claude_api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 8192
    max_retries: int = 3
    
    # 路径配置
    report_cfg_base: str = "report_cfg"
    report_cfg_dir: str = "report_cfg"  # 兼容性别名
    results_base: str = "results"
    results_dir: str = "results"  # 兼容性别名
    
    # 输出配置
    output_filename_pattern: str = "{topic_id}_search_report.md"

    # 数据源筛选配置
    filter_out_data_count: int = 8  # 默认最多选10篇source_data用于报告
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.claude_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY未设置。请设置环境变量: export ANTHROPIC_API_KEY='your_key'"
            )
        
        # 设置兼容性属性
        self.report_cfg_dir = self.report_cfg_base
        self.results_dir = self.results_base
        
        # 如果在backend目录下运行，调整路径指向项目根目录
        if os.path.basename(os.getcwd()) == "backend":
            self.report_cfg_dir = f"../{self.report_cfg_base}"
            self.results_dir = f"../{self.results_base}"


def load_config() -> EnhancedReportConfig:
    """加载配置"""
    return EnhancedReportConfig()


def check_config() -> bool:
    """检查配置是否有效"""
    try:
        config = load_config()
        return bool(config.claude_api_key)
    except ValueError:
        return False


if __name__ == "__main__":
    # 测试配置
    try:
        config = load_config()
        print(f"✅ 配置加载成功")
        print(f"Claude模型: {config.claude_model}")
        print(f"API密钥: {'已设置' if config.claude_api_key else '未设置'}")
        print(f"输出路径: {config.results_base}")
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")