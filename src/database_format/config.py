"""Configuration management for database format module."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Config:
    """Configuration manager for database evaluation system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.backend_root = Path(__file__).parent.parent.parent
        
        # Load environment variables from .env file
        env_path = self.backend_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        # Database configuration
        self.DATABASE_CONFIG = {
            'db_path': str(self.project_root / 'research_data.db'),  # 使用正确的数据库文件名
            'batch_size': 10,
            'max_retries': 3,
            'retry_delay': 2,
            'table_name': 'references'
        }
        
        # LLM configuration
        self.LLM_CONFIG = {
            'model': 'claude-3-5-sonnet-20241022',
            'temperature': 0.3,
            'max_tokens': 2000,
            'api_key': os.getenv('ANTHROPIC_API_KEY')
        }
        
        # Research topic (will be loaded from planning_list.md)
        self.research_topic: Optional[Dict[str, str]] = None
        
        # Reference types
        self.REFERENCE_TYPES = [
            "用户输入",
            "行业研究报告", 
            "同行评审的学术出版物",
            "竞对公司网站和产品页面",
            "政策与准入数据",
            "社交媒体和公共论坛"
        ]
        
        # Load configurations
        self._load_evaluation_criteria()
        self._load_research_topic()
    
    def _load_evaluation_criteria(self):
        """Load evaluation criteria from configuration file."""
        criteria_path = self.project_root / 'database_cfg' / 'evaluation_criteria.json'
        try:
            with open(criteria_path, 'r', encoding='utf-8') as f:
                self.evaluation_criteria = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load evaluation criteria: {e}")
            self.evaluation_criteria = {}
    
    def _load_research_topic(self):
        """Load current research topic from planning_list.md."""
        planning_path = self.backend_root / 'src' / 'planning_list.md'
        try:
            with open(planning_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract research topic information
            lines = content.split('\n')
            topic_info = {
                'title': '',
                'description': '',
                'keywords': []
            }
            
            for i, line in enumerate(lines):
                if '报告标题' in line and i + 1 < len(lines):
                    topic_info['title'] = lines[i + 1].strip('*').strip()
                elif '核心研究问题' in line and i + 1 < len(lines):
                    topic_info['description'] = lines[i + 1].strip()
                elif 'Topic' in line and ':' in line:
                    # Extract topic keywords
                    topic_text = line.split(':', 1)[1].strip()
                    if 'AWG' in topic_text or '空气制水机' in topic_text:
                        topic_info['keywords'].extend(['AWG', '空气制水机', '水处理', '美国市场'])
                        
            self.research_topic = topic_info
            
        except Exception as e:
            print(f"Warning: Could not load research topic: {e}")
            # Default research topic
            self.research_topic = {
                'title': '空气制水机(AWG)市场战略深度研究',
                'description': '空气制水机技术在美国水处理市场中的真实商业价值、竞争定位和投资风险',
                'keywords': ['AWG', '空气制水机', '水处理', '美国市场']
            }
    
    def get_prompt_template(self, template_name: str) -> str:
        """Get prompt template from evaluation criteria."""
        if template_name == 'credibility':
            return self.evaluation_criteria.get('credibility_evaluation', {}).get('prompt_template', '')
        elif template_name == 'relevance':
            return self.evaluation_criteria.get('relevance_evaluation', {}).get('prompt_template', '')
        return ''
    
    def get_credibility_levels(self) -> Dict[str, Dict[str, Any]]:
        """Get credibility evaluation levels."""
        return self.evaluation_criteria.get('credibility_evaluation', {}).get('levels', {})
    
    def get_relevance_ranges(self) -> Dict[str, str]:
        """Get relevance score ranges."""
        return self.evaluation_criteria.get('relevance_evaluation', {}).get('score_ranges', {})

# Create singleton instance
config = Config()