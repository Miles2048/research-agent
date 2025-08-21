"""Enhanced Report Agent - 使用Claude Sonnet 4的智能报告生成系统"""

from .config import EnhancedReportConfig, load_config
from .report_generator import (
    EnhancedReportGenerator,
    generate_enhanced_report,
    generate_enhanced_report_sync
)

__version__ = "1.0.0"
__all__ = [
    "EnhancedReportConfig",
    "load_config",
    "EnhancedReportGenerator",
    "generate_enhanced_report",
    "generate_enhanced_report_sync"
]