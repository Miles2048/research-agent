"""Utility functions for database format module."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

def extract_publisher_from_url(url: str) -> Optional[str]:
    """Extract publisher name from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Common publisher patterns
        publishers = {
            'mckinsey.com': 'McKinsey & Company',
            'bcg.com': 'Boston Consulting Group',
            'deloitte.com': 'Deloitte',
            'pwc.com': 'PwC',
            'gartner.com': 'Gartner',
            'idc.com': 'IDC',
            'forrester.com': 'Forrester',
            'statista.com': 'Statista',
            'harvard.edu': 'Harvard University',
            'mit.edu': 'MIT',
            'ieee.org': 'IEEE',
            'nature.com': 'Nature',
            'sciencedirect.com': 'ScienceDirect',
            'springer.com': 'Springer',
            'wiley.com': 'Wiley',
            'acm.org': 'ACM',
            'bloomberg.com': 'Bloomberg',
            'reuters.com': 'Reuters',
            'wsj.com': 'Wall Street Journal',
            'ft.com': 'Financial Times',
            'economist.com': 'The Economist'
        }
        
        # Check known publishers
        for domain_pattern, publisher_name in publishers.items():
            if domain_pattern in domain:
                return publisher_name
                
        # Extract from domain name
        # Remove TLD
        domain_parts = domain.split('.')
        if len(domain_parts) > 1:
            return domain_parts[0].title()
            
    except Exception:
        pass
        
    return None

def truncate_content(content: str, max_length: int = 3000) -> str:
    """Truncate content to maximum length while preserving sentences."""
    if not content or len(content) <= max_length:
        return content
        
    # Try to truncate at sentence boundary
    truncated = content[:max_length]
    last_period = truncated.rfind('。')
    if last_period == -1:
        last_period = truncated.rfind('.')
        
    if last_period > max_length * 0.8:  # If we found a period in the last 20%
        return truncated[:last_period + 1] + " ...[内容已截断]"
    else:
        return truncated + "...[内容已截断]"

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and special characters."""
    if not text:
        return ""
        
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text.strip()

def calculate_reading_time(word_count: int) -> str:
    """Calculate estimated reading time based on word count."""
    if word_count <= 0:
        return "0min0sec"
        
    # Average reading speed: 200-250 words per minute
    minutes = word_count // 200
    seconds = (word_count % 200) * 60 // 200
    
    return f"{minutes}min{seconds}sec"

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_content_snippet(content: str, max_length: int = 500) -> str:
    """Get a snippet of content for preview."""
    if not content:
        return ""
        
    cleaned = clean_text(content)
    return truncate_content(cleaned, max_length)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f}MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.1f}GB"