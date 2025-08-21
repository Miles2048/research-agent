"""
Error handling and logging utilities for the planning agent.

This module provides comprehensive error handling, retry mechanisms, and logging
functionality to ensure robust operation of the planning agent.
"""

import time
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger
from pydantic import BaseModel


# Type definitions
F = TypeVar('F', bound=Callable[..., Any])


class ErrorType(str, Enum):
    """Classification of error types for monitoring and statistics."""
    LLM_API_ERROR = "llm_api_error"
    JSON_VALIDATION_ERROR = "json_validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    STATE_ERROR = "state_error"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """Error severity levels for prioritization and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorStats:
    """Statistics tracking for error monitoring."""
    total_errors: int = 0
    errors_by_type: Dict[ErrorType, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    last_error_time: Optional[datetime] = None
    error_rate_per_hour: float = 0.0
    
    def record_error(self, error_type: ErrorType, severity: ErrorSeverity) -> None:
        """Record an error occurrence for statistics."""
        self.total_errors += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.errors_by_severity[severity] = self.errors_by_severity.get(severity, 0) + 1
        self.last_error_time = datetime.now()
        
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of error statistics."""
        return {
            "total_errors": self.total_errors,
            "errors_by_type": dict(self.errors_by_type),
            "errors_by_severity": dict(self.errors_by_severity),
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "error_rate_per_hour": self.error_rate_per_hour
        }


class PlanningAgentError(Exception):
    """Base exception class for planning agent errors."""
    
    def __init__(
        self, 
        message: str, 
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now()


class LLMAPIError(PlanningAgentError):
    """Exception for LLM API related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.LLM_API_ERROR, 
            ErrorSeverity.HIGH,
            context
        )


class JSONValidationError(PlanningAgentError):
    """Exception for JSON validation errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.JSON_VALIDATION_ERROR, 
            ErrorSeverity.MEDIUM,
            context
        )


class ConfigurationError(PlanningAgentError):
    """Exception for configuration related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.CONFIGURATION_ERROR, 
            ErrorSeverity.HIGH,
            context
        )


class TimeoutError(PlanningAgentError):
    """Exception for timeout related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message, 
            ErrorType.TIMEOUT_ERROR, 
            ErrorSeverity.MEDIUM,
            context
        )


# Global error statistics instance
_error_stats = ErrorStats()


def get_error_stats() -> ErrorStats:
    """Get the global error statistics instance."""
    return _error_stats


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    error_type: Optional[ErrorType] = None,
    severity: Optional[ErrorSeverity] = None
) -> None:
    """
    Log an error with comprehensive context and update statistics.
    
    Args:
        error: The exception that occurred
        context: Additional context information
        error_type: Classification of the error type
        severity: Severity level of the error
    """
    # Determine error type and severity
    if isinstance(error, PlanningAgentError):
        error_type = error.error_type
        severity = error.severity
        context = {**(context or {}), **error.context}
    else:
        error_type = error_type or ErrorType.UNKNOWN_ERROR
        severity = severity or ErrorSeverity.MEDIUM
    
    # Update statistics
    _error_stats.record_error(error_type, severity)
    
    # Prepare log context
    log_context = {
        "error_type": error_type.value,
        "severity": severity.value,
        "error_class": error.__class__.__name__,
        "traceback": traceback.format_exc(),
        **(context or {})
    }
    
    # Log based on severity
    if severity == ErrorSeverity.CRITICAL:
        logger.critical(f"CRITICAL ERROR: {str(error)}", **log_context)
    elif severity == ErrorSeverity.HIGH:
        logger.error(f"HIGH SEVERITY ERROR: {str(error)}", **log_context)
    elif severity == ErrorSeverity.MEDIUM:
        logger.warning(f"MEDIUM SEVERITY ERROR: {str(error)}", **log_context)
    else:
        logger.info(f"LOW SEVERITY ERROR: {str(error)}", **log_context)


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Callable[[F], F]:
    """
    Decorator for implementing retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff calculation
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed, log and re-raise
                        log_error(
                            e,
                            context={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "final_attempt": True
                            },
                            severity=ErrorSeverity.HIGH
                        )
                        raise
                    
                    # Calculate backoff delay
                    delay = backoff_factor * (2 ** attempt)
                    
                    # Log retry attempt
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error_type=type(e).__name__
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def timeout_handler(timeout_seconds: int) -> Callable[[F], F]:
    """
    Decorator for implementing timeout handling.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Decorated function with timeout handling
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_signal_handler(signum, frame):
                raise TimeoutError(
                    f"Function {func.__name__} timed out after {timeout_seconds} seconds",
                    context={
                        "function": func.__name__,
                        "timeout_seconds": timeout_seconds
                    }
                )
            
            # Set up timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(timeout_seconds)
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Cancel the alarm
                return result
            except Exception as e:
                signal.alarm(0)  # Cancel the alarm
                if isinstance(e, TimeoutError):
                    log_error(e, severity=ErrorSeverity.HIGH)
                raise
            finally:
                signal.signal(signal.SIGALRM, old_handler)
                
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    fallback_value: Any = None,
    log_errors: bool = True,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, Any]:
    """
    Safely execute a function with comprehensive error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        fallback_value: Value to return if function fails
        log_errors: Whether to log errors that occur
        context: Additional context for error logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Tuple of (success: bool, result: Any)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        if log_errors:
            log_error(
                e,
                context={
                    "function": func.__name__ if hasattr(func, '__name__') else str(func),
                    **(context or {})
                }
            )
        return False, fallback_value


def performance_monitor(func: F) -> F:
    """
    Decorator for monitoring function performance and logging metrics.
    
    Args:
        func: Function to monitor
        
    Returns:
        Decorated function with performance monitoring
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(
                f"Performance: {func.__name__} completed successfully",
                function=func.__name__,
                execution_time=execution_time,
                success=True
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.warning(
                f"Performance: {func.__name__} failed after {execution_time:.2f}s",
                function=func.__name__,
                execution_time=execution_time,
                success=False,
                error_type=type(e).__name__
            )
            
            raise
            
    return wrapper


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json_logging: bool = False
) -> None:
    """
    Configure the loguru logging system for the planning agent.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_json_logging: Whether to use JSON format for logs
    """
    # Remove default handler
    logger.remove()
    
    # Configure format
    if enable_json_logging:
        log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message} | {extra}"
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "{extra}"
        )
    
    # Add console handler
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format=log_format,
        level=log_level,
        colorize=not enable_json_logging
    )
    
    # Add file handler if specified
    if log_file:
        logger.add(
            sink=log_file,
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="gz"
        )
    
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")


# Initialize logging configuration
configure_logging()


# Export main classes and functions
__all__ = [
    'ErrorType',
    'ErrorSeverity', 
    'ErrorStats',
    'PlanningAgentError',
    'LLMAPIError',
    'JSONValidationError',
    'ConfigurationError',
    'TimeoutError',
    'get_error_stats',
    'log_error',
    'retry_with_backoff',
    'timeout_handler',
    'safe_execute',
    'performance_monitor',
    'configure_logging'
]