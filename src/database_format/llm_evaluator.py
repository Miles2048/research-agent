"""LLM evaluator for reference classification and assessment."""

import json
import time
from typing import Dict, Any, Optional, Tuple
from anthropic import Anthropic
from loguru import logger

from database_format.config import config
from database_format.models import Reference, EvaluationResult
from database_format.prompts import PromptTemplates

class LLMEvaluator:
    """LLM evaluator using Claude for reference evaluation."""
    
    def __init__(self):
        """Initialize LLM evaluator."""
        self.config = config
        self.prompts = PromptTemplates()
        
        # Initialize Anthropic client
        api_key = self.config.LLM_CONFIG.get('api_key')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        self.client = Anthropic(api_key=api_key)
        self.model = self.config.LLM_CONFIG.get('model', 'claude-3-5-sonnet-20241022')
        self.temperature = self.config.LLM_CONFIG.get('temperature', 0.3)
        self.max_tokens = self.config.LLM_CONFIG.get('max_tokens', 2000)
        
        logger.info(f"LLMEvaluator initialized with model: {self.model}")
    
    def evaluate_reference(self, reference: Reference) -> Optional[EvaluationResult]:
        """Evaluate a single reference."""
        try:
            # Step 1: Classify reference type
            reference_type, type_confidence = self._classify_reference_type(reference)
            
            # Step 2: Comprehensive evaluation (credibility + relevance)
            eval_result = self._comprehensive_evaluation(reference)
            
            if eval_result:
                # Update reference type from classification
                eval_result.reference_type = reference_type
                eval_result.confidence = type_confidence
                
                # Validate result
                if eval_result.validate():
                    return eval_result
                else:
                    logger.warning(f"Invalid evaluation result for reference {reference.id}")
                    
        except Exception as e:
            logger.error(f"Error evaluating reference {reference.id}: {str(e)}")
            
        return None
    
    def _classify_reference_type(self, reference: Reference) -> Tuple[str, float]:
        """Classify reference type using LLM."""
        try:
            # Prepare reference data
            ref_data = {
                'title': reference.reference_title,
                'url': reference.reference_url,
                'publisher': reference.publisher or '未知',
                'content_snippet': (reference.reference_content or '')[:5000]
            }
            
            # Get prompt
            prompt = self.prompts.get_reference_type_prompt(ref_data)
            
            # Call LLM
            response = self._call_llm(prompt)
            
            if response:
                result = self._parse_json_response(response)
                if result and 'reference_type' in result:
                    return result['reference_type'], result.get('confidence', 0.8)
                    
        except Exception as e:
            logger.error(f"Error classifying reference type: {str(e)}")
            
        return '未分类', 0.0
    
    def _comprehensive_evaluation(self, reference: Reference) -> Optional[EvaluationResult]:
        """Perform comprehensive evaluation of reference."""
        try:
            # Prepare reference data
            ref_data = {
                'title': reference.reference_title,
                'url': reference.reference_url,
                'publisher': reference.publisher or '未知',
                'content': reference.reference_content or ''
            }
            
            # Get research topic
            research_topic = self.config.research_topic or {
                'title': '研究主题',
                'description': '研究描述',
                'keywords': []
            }
            
            # Get prompt
            prompt = self.prompts.get_comprehensive_evaluation_prompt(ref_data, research_topic)
            
            # Call LLM
            response = self._call_llm(prompt)
            
            if response:
                result = self._parse_json_response(response)
                
                if result and all(key in result for key in ['credibility', 'credibility_assessment', 
                                                              'related_assessment', 'related_assessment_text']):
                    return EvaluationResult(
                        reference_type='未分类',  # Will be updated later
                        credibility=int(result['credibility']),
                        credibility_assessment=result['credibility_assessment'],
                        related_assessment=float(result['related_assessment']),
                        related_assessment_text=result['related_assessment_text']
                    )
                    
        except Exception as e:
            logger.error(f"Error in comprehensive evaluation: {str(e)}")
            
        return None
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Call LLM with retry logic."""
        system_prompt = self.prompts.get_system_prompt()
        
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    system=system_prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                return response.content[0].text
                
            except Exception as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(self.config.DATABASE_CONFIG.get('retry_delay', 2))
                else:
                    logger.error(f"All LLM call attempts failed")
                    
        return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            # Find JSON content in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                
                # 首先尝试直接解析
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # 如果失败，尝试修复常见问题
                    import re
                    
                    # 修复：仅替换字符串值内的换行符（在引号内的）
                    # 使用正则表达式找到所有字符串值
                    def fix_string_value(match):
                        # 获取引号内的内容
                        content = match.group(1)
                        # 替换控制字符
                        content = content.replace('\n', '\\n')
                        content = content.replace('\r', '\\r')
                        content = content.replace('\t', '\\t')
                        return f'"{content}"'
                    
                    # 匹配JSON字符串值（简化版，处理大多数情况）
                    json_str_fixed = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', fix_string_value, json_str)
                    
                    return json.loads(json_str_fixed)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content (first 500 chars): {response[:500]}")
            
        return None
    
    def batch_evaluate(self, references: list[Reference]) -> Dict[int, EvaluationResult]:
        """Evaluate multiple references in batch."""
        results = {}
        
        for ref in references:
            if ref.needs_evaluation():
                logger.info(f"Evaluating reference {ref.id}: {ref.reference_title[:50]}...")
                result = self.evaluate_reference(ref)
                
                if result:
                    results[ref.id] = result
                    logger.info(f"Successfully evaluated reference {ref.id}")
                else:
                    logger.warning(f"Failed to evaluate reference {ref.id}")
                    
                # Add delay between requests to avoid rate limiting
                time.sleep(0.5)
            else:
                logger.info(f"Reference {ref.id} already evaluated, skipping")
                
        return results