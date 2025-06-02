"""
Logging utilities for OpenPypi.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union


def get_logger(
    name: str,
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level
        log_file: Optional log file path
        format_string: Optional custom format string
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers to the same logger
    if logger.handlers:
        return logger
    
    # Set level
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Set up basic logging configuration for the entire application.
    
    Args:
        level: Logging level
        log_file: Optional log file path
        format_string: Optional custom format string
    """
    # Convert string level to int
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Basic config
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    ) 