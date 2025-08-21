"""Concurrent evaluator for reference classification and assessment."""

import concurrent.futures
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from queue import Queue
from datetime import datetime
from loguru import logger

from database_format.models import Reference, EvaluationResult
from database_format.llm_evaluator import LLMEvaluator


@dataclass
class EvaluationTask:
    """Represents a single evaluation task."""
    reference: Reference
    retry_count: int = 0
    max_retries: int = 3


class ConcurrentEvaluator:
    """
    Concurrent evaluator that processes multiple references in parallel.
    
    Features:
    - Parallel processing with configurable worker threads
    - Rate limiting to avoid API throttling
    - Automatic retry for failed evaluations
    - Progress tracking and monitoring
    """
    
    def __init__(self, 
                 max_workers: int = 5,
                 rate_limit: float = 0.2,
                 batch_update_size: int = 10,
                 timeout: int = 30):
        """
        Initialize concurrent evaluator.
        
        Args:
            max_workers: Maximum number of concurrent workers
            rate_limit: Minimum seconds between API requests
            batch_update_size: Size of batches for database updates
            timeout: Timeout for individual evaluation tasks (seconds)
        """
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self.batch_update_size = batch_update_size
        self.timeout = timeout
        
        # Initialize evaluator
        self.evaluator = LLMEvaluator()
        
        # Rate limiting controls
        self.rate_limiter = threading.Semaphore(max_workers)
        self.last_request_time = 0
        self.request_lock = threading.Lock()
        
        # Results collection
        self.results_queue = Queue()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info(f"ConcurrentEvaluator initialized with {max_workers} workers, "
                   f"rate limit: {rate_limit}s")
    
    def evaluate_batch_concurrent(self, references: List[Reference]) -> Dict[int, EvaluationResult]:
        """
        Evaluate multiple references concurrently.
        
        Args:
            references: List of references to evaluate
            
        Returns:
            Dictionary mapping reference ID to evaluation result
        """
        if not references:
            logger.warning("No references to evaluate")
            return {}
        
        logger.info(f"Starting concurrent evaluation of {len(references)} references")
        self.stats['start_time'] = time.time()
        self.stats['total_processed'] = len(references)
        
        results = {}
        failed_tasks = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ref = {
                executor.submit(self._evaluate_with_rate_limit, ref): ref 
                for ref in references if ref.needs_evaluation()
            }
            
            # Add references that don't need evaluation to results
            for ref in references:
                if not ref.needs_evaluation():
                    logger.debug(f"Reference {ref.id} already evaluated, skipping")
            
            # Collect results as they complete
            completed = 0
            total = len(future_to_ref)
            
            for future in concurrent.futures.as_completed(future_to_ref):
                ref = future_to_ref[future]
                completed += 1
                
                try:
                    result = future.result(timeout=self.timeout)
                    if result:
                        results[ref.id] = result
                        self.stats['successful'] += 1
                        logger.info(f"[{completed}/{total}] Successfully evaluated reference {ref.id}")
                    else:
                        failed_tasks.append(ref)
                        logger.warning(f"[{completed}/{total}] Failed to evaluate reference {ref.id}")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"[{completed}/{total}] Timeout evaluating reference {ref.id}")
                    failed_tasks.append(ref)
                    
                except Exception as e:
                    logger.error(f"[{completed}/{total}] Error evaluating reference {ref.id}: {str(e)}")
                    failed_tasks.append(ref)
                
                # Log progress
                if completed % 10 == 0:
                    self._log_progress(completed, total)
        
        # Retry failed tasks
        if failed_tasks:
            logger.info(f"Retrying {len(failed_tasks)} failed evaluations...")
            retry_results = self._retry_failed_tasks(failed_tasks)
            results.update(retry_results)
        
        self.stats['end_time'] = time.time()
        self.stats['failed'] = len(references) - len(results)
        
        self._log_final_stats()
        
        return results
    
    def _evaluate_with_rate_limit(self, reference: Reference) -> Optional[EvaluationResult]:
        """
        Evaluate a reference with rate limiting.
        
        Args:
            reference: Reference to evaluate
            
        Returns:
            Evaluation result or None if failed
        """
        with self.rate_limiter:
            # Enforce rate limit
            with self.request_lock:
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last < self.rate_limit:
                    sleep_time = self.rate_limit - time_since_last
                    time.sleep(sleep_time)
                
                self.last_request_time = time.time()
            
            # Perform evaluation
            try:
                result = self.evaluator.evaluate_reference(reference)
                return result
            except Exception as e:
                logger.error(f"Error in evaluation: {str(e)}")
                return None
    
    def _retry_failed_tasks(self, failed_refs: List[Reference], max_retries: int = 2) -> Dict[int, EvaluationResult]:
        """
        Retry failed evaluation tasks.
        
        Args:
            failed_refs: List of references that failed evaluation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary of successful retry results
        """
        retry_results = {}
        
        for retry_attempt in range(1, max_retries + 1):
            if not failed_refs:
                break
            
            logger.info(f"Retry attempt {retry_attempt}/{max_retries} for {len(failed_refs)} references")
            
            # Increase delay between retries
            time.sleep(self.rate_limit * retry_attempt)
            
            still_failed = []
            
            for ref in failed_refs:
                try:
                    result = self._evaluate_with_rate_limit(ref)
                    if result:
                        retry_results[ref.id] = result
                        self.stats['retried'] += 1
                        logger.info(f"Successfully evaluated reference {ref.id} on retry {retry_attempt}")
                    else:
                        still_failed.append(ref)
                except Exception as e:
                    logger.error(f"Retry failed for reference {ref.id}: {str(e)}")
                    still_failed.append(ref)
            
            failed_refs = still_failed
        
        if failed_refs:
            logger.warning(f"{len(failed_refs)} references still failed after all retries")
        
        return retry_results
    
    def _log_progress(self, completed: int, total: int):
        """Log evaluation progress."""
        progress = (completed / total) * 100
        elapsed = time.time() - self.stats['start_time']
        rate = completed / elapsed if elapsed > 0 else 0
        eta = (total - completed) / rate if rate > 0 else 0
        
        logger.info(f"Progress: {completed}/{total} ({progress:.1f}%) | "
                   f"Rate: {rate:.1f} refs/sec | ETA: {eta:.0f}s")
    
    def _log_final_stats(self):
        """Log final evaluation statistics."""
        elapsed = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0
        
        logger.info("=" * 60)
        logger.info("Concurrent Evaluation Complete")
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Retried: {self.stats['retried']}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info(f"Total time: {elapsed:.1f}s")
        logger.info(f"Average rate: {self.stats['total_processed']/elapsed:.1f} refs/sec")
        logger.info("=" * 60)
    
    def reset_stats(self):
        """Reset statistics for new batch."""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'start_time': None,
            'end_time': None
        }