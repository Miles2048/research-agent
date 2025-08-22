"""Database updater for reference evaluation results."""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from database_format.config import config
from database_format.models import Reference, EvaluationResult, BatchResult
from database_format.llm_evaluator import LLMEvaluator
from database_format.update_publishers import PublisherExtractor
from database_format.concurrent_evaluator import ConcurrentEvaluator

class DatabaseUpdater:
    """Handle database operations for reference updates."""
    
    def __init__(self, use_concurrent: bool = True, max_workers: int = 5):
        """
        Initialize database updater.
        
        Args:
            use_concurrent: Whether to use concurrent evaluation (default: True)
            max_workers: Number of concurrent workers (default: 5)
        """
        self.config = config
        self.db_path = self.config.DATABASE_CONFIG['db_path']
        self.table_name = self.config.DATABASE_CONFIG['table_name']
        self.batch_size = self.config.DATABASE_CONFIG['batch_size']
        self.evaluator = LLMEvaluator()
        self.publisher_extractor = PublisherExtractor()
        
        # Initialize concurrent evaluator if needed
        self.use_concurrent = use_concurrent
        self.concurrent_evaluator = None
        if use_concurrent:
            self.concurrent_evaluator = ConcurrentEvaluator(
                max_workers=max_workers,
                rate_limit=0.2,  # Configurable
                batch_update_size=20
            )
            logger.info(f"DatabaseUpdater initialized with concurrent mode ({max_workers} workers)")
        else:
            logger.info(f"DatabaseUpdater initialized with serial mode")
        
        logger.info(f"Database: {self.db_path}")
    
    def get_references_to_update(self, limit: Optional[int] = None) -> List[Reference]:
        """Get references that need evaluation."""
        if limit is None:
            limit = self.batch_size
            
        query = f"""
        SELECT id, reference_type, url as reference_url, name as reference_title, 
               raw_content as reference_content, publisher, credibility, related_assessment
        FROM "{self.table_name}"
        WHERE reference_type = 'uncategorized'
           OR credibility = 2
           OR related_assessment = 80
           OR credibility <= 2  -- 也评估低分记录
           OR related_assessment <= 50  -- 也评估低相关性记录
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
            related_assessment = ?,
            updated_at = ?
        WHERE id = ?
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    evaluation.reference_type,
                    evaluation.credibility,
                    evaluation.related_assessment,
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
    
    def batch_update_references(self, evaluation_results: Dict[int, EvaluationResult]) -> Dict[str, int]:
        """
        Batch update multiple references with evaluation results.
        
        Args:
            evaluation_results: Dictionary mapping reference ID to evaluation result
            
        Returns:
            Dictionary with 'success' and 'failed' counts
        """
        if not evaluation_results:
            logger.warning("No evaluation results to update")
            return {'success': 0, 'failed': 0}
        
        # Prepare batch update data
        update_data = [
            (
                result.reference_type,
                result.credibility,
                result.related_assessment,
                datetime.now().isoformat(),
                ref_id
            )
            for ref_id, result in evaluation_results.items()
        ]
        
        query = f"""
        UPDATE "{self.table_name}"
        SET reference_type = ?,
            credibility = ?,
            related_assessment = ?,
            updated_at = ?
        WHERE id = ?
        """
        
        success_count = 0
        failed_count = 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Use executemany for batch update
                cursor.executemany(query, update_data)
                conn.commit()
                
                success_count = cursor.rowcount
                failed_count = len(update_data) - success_count
                
                logger.info(f"Batch update completed: {success_count} successful, {failed_count} failed")
                
        except Exception as e:
            logger.error(f"Batch update failed: {str(e)}")
            failed_count = len(update_data)
        
        return {
            'success': success_count,
            'failed': failed_count
        }
    
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
        
        # Choose evaluation method based on mode
        if self.use_concurrent and self.concurrent_evaluator:
            # Use concurrent evaluation
            evaluation_results = self.concurrent_evaluator.evaluate_batch_concurrent(references)
            
            # Use batch update for database
            update_stats = self.batch_update_references(evaluation_results)
            result.successful = update_stats['success']
            result.failed = update_stats['failed']
            result.total_processed = len(references)
            
        else:
            # Use serial evaluation (original behavior)
            evaluation_results = self.evaluator.batch_evaluate(references)
            
            # Update database one by one
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