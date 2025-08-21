"""
Citation Agent Module
"""

from .citation_agent import SimpleCitationAgent, generate_citation_report
from .interface import create_final_report, quick_citation, run_citation, EasyCitationAgent

__all__ = [
    "SimpleCitationAgent", 
    "generate_citation_report",
    "create_final_report", 
    "quick_citation", 
    "run_citation",
    "EasyCitationAgent"
] 