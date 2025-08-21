"""Database updater for reference evaluation results."""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from .config import config
from .models import Reference, EvaluationResult, BatchResult
from .llm_evaluator import LLMEvaluator
from .update_publishers import PublisherExtractor

class DatabaseUpdater:
    """Handle database operations for reference updates."""
    
    def __init__(self):
        """Initialize database updater."""
        self.config = config
        self.db_path = self.config.DATABASE_CONFIG['db_path']
        self.table_name = self.config.DATABASE_CONFIG['table_name']
        self.batch_size = self.config.DATABASE_CONFIG['batch_size']
        self.evaluator = LLMEvaluator()
        self.publisher_extractor = PublisherExtractor()
        
        logger.info(f"DatabaseUpdater initialized with database: {self.db_path}")
    
    def get_references_to_update(self, limit: Optional[int] = None) -> List[Reference]:
        """Get references that need evaluation."""
        if limit is None:
            limit = self.batch_size
            
        query = f"""
        SELECT id, reference_type, reference_url, reference_title, 
               reference_content, publisher, credibility, related_assessment,
               credibility_assessment, related_assessment_text
        FROM "{self.table_name}"
        WHERE reference_type = '未分类'
           OR credibility = 2
           OR related_assessment = 0.80
           OR credibility_assessment IS NULL
           OR related_assessment_text IS NULL
        LIMIT ?
        """
        
        references = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                
                for row in rows:
                    ref = Reference.from_db_row(row)
                    # Try to extract publisher if not present
                    if not ref.publisher:
                        record_dict = {
                            'reference_url': ref.reference_url,
                            'publisher': ref.publisher
                        }
                        ref.publisher = self.publisher_extractor.extract_publisher(record_dict)
                    references.append(ref)
                    
                logger.info(f"Found {len(references)} references to update")
                
        except Exception as e:
            logger.error(f"Error fetching references: {str(e)}")
            
        return references
    
    def update_reference(self, ref_id: int, evaluation: EvaluationResult) -> bool:
        """Update a single reference with evaluation results."""
        query = f"""
        UPDATE "{self.table_name}"
        SET reference_type = ?,
            credibility = ?,
            credibility_assessment = ?,
            related_assessment = ?,
            related_assessment_text = ?,
            reference_update_time = ?
        WHERE id = ?
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    evaluation.reference_type,
                    evaluation.credibility,
                    evaluation.credibility_assessment,
                    evaluation.related_assessment,
                    evaluation.related_assessment_text,
                    datetime.now().isoformat(),
                    ref_id
                ))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"Updated reference {ref_id} successfully")
                    return True
                else:
                    logger.warning(f"No rows updated for reference {ref_id}")
                    
        except Exception as e:
            logger.error(f"Error updating reference {ref_id}: {str(e)}")
            
        return False
    
    def process_batch(self, references: Optional[List[Reference]] = None) -> BatchResult:
        """Process a batch of references."""
        result = BatchResult()
        
        # Get references if not provided
        if references is None:
            references = self.get_references_to_update()
            
        if not references:
            logger.info("No references to process")
            return result
            
        logger.info(f"Processing batch of {len(references)} references")
        
        # Evaluate references
        evaluation_results = self.evaluator.batch_evaluate(references)
        
        # Update database
        for ref_id, evaluation in evaluation_results.items():
            if self.update_reference(ref_id, evaluation):
                result.add_success()
            else:
                result.add_failure(f"Failed to update reference {ref_id} in database")
                
        # Handle references that failed evaluation
        for ref in references:
            if ref.id not in evaluation_results:
                result.add_failure(f"Failed to evaluate reference {ref.id}")
                
        logger.info(result.summary())
        return result
    
    def process_all(self) -> Dict[str, int]:
        """Process all references that need evaluation."""
        total_processed = 0
        total_successful = 0
        total_failed = 0
        
        while True:
            # Get next batch
            references = self.get_references_to_update()
            if not references:
                break
                
            # Process batch
            batch_result = self.process_batch(references)
            
            # Update totals
            total_processed += batch_result.total_processed
            total_successful += batch_result.successful
            total_failed += batch_result.failed
            
            logger.info(f"Total progress: {total_processed} processed, "
                       f"{total_successful} successful, {total_failed} failed")
            
        return {
            'total_processed': total_processed,
            'successful': total_successful,
            'failed': total_failed,
            'success_rate': (total_successful / total_processed * 100) if total_processed > 0 else 0
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about current database state."""
        stats_query = f"""
        SELECT 
            COUNT(*) as total_references,
            SUM(CASE WHEN reference_type = '未分类' THEN 1 ELSE 0 END) as unclassified,
            SUM(CASE WHEN credibility = 1 THEN 1 ELSE 0 END) as low_credibility,
            SUM(CASE WHEN credibility = 2 THEN 1 ELSE 0 END) as medium_credibility,
            SUM(CASE WHEN credibility = 3 THEN 1 ELSE 0 END) as high_credibility,
            SUM(CASE WHEN related_assessment < 0.3 THEN 1 ELSE 0 END) as low_relevance,
            SUM(CASE WHEN related_assessment >= 0.3 AND related_assessment < 0.6 THEN 1 ELSE 0 END) as medium_relevance,
            SUM(CASE WHEN related_assessment >= 0.6 AND related_assessment < 0.8 THEN 1 ELSE 0 END) as high_relevance,
            SUM(CASE WHEN related_assessment >= 0.8 THEN 1 ELSE 0 END) as very_high_relevance
        FROM "{self.table_name}"
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(stats_query)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'total_references': row[0],
                        'unclassified': row[1],
                        'credibility': {
                            'low': row[2],
                            'medium': row[3],
                            'high': row[4]
                        },
                        'relevance': {
                            'low': row[5],
                            'medium': row[6],
                            'high': row[7],
                            'very_high': row[8]
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            
        return {}