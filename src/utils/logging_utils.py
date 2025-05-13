"""
Logging and error handling utilities for the UBERON agent.

This module provides functions for setting up logging and handling errors
with rich context information.
"""

import logging
import traceback
import sys
import os
from typing import Dict, Any, Optional
from functools import wraps

# Configure logging format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(
    log_level: int = logging.INFO,
    log_format: str = DEFAULT_LOG_FORMAT,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_format: Format for log messages
        log_file: Optional file path to write logs to
        
    Returns:
        Configured logger
    """
    # Get the root logger
    logger = logging.getLogger("uberon_agent")
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if a log file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class CustomError(Exception):
    """
    Custom error class with context for improved debugging.
    
    This class extends the standard Exception to include additional context
    information for more meaningful error messages and easier debugging.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize with a message and optional context.
        
        Args:
            message: Error message
            context: Optional dictionary with additional context information
        """
        self.message = message
        self.context = context or {}
        self.traceback = traceback.format_exc()
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Create a detailed string representation of the error."""
        base_msg = f"{self.message}"
        
        if self.context:
            context_str = "\nContext:\n" + "\n".join(
                f"  - {key}: {value}" for key, value in self.context.items()
            )
            base_msg += context_str
        
        return base_msg


def log_exceptions(logger: Optional[logging.Logger] = None):
    """
    Decorator to log exceptions with context.
    
    This decorator catches exceptions, logs them with the provided logger,
    and re-raises them as CustomError with additional context.
    
    Args:
        logger: Logger to use (if None, creates a new logger)
        
    Returns:
        Decorated function
    """
    if logger is None:
        logger = logging.getLogger("uberon_agent")
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create context with function name and arguments
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                }
                
                # Log the exception
                logger.exception(f"Error in {func.__name__}: {str(e)}")
                
                # Re-raise as CustomError
                raise CustomError(str(e), context) from e
        
        return wrapper
    
    return decorator 