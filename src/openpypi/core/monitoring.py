"""Production monitoring and logging utilities."""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional


class ProductionLogger:
    """Production-ready logging utility."""

    def __init__(self, name: str = "openpypi"):
        self.logger = logging.getLogger(name)
        self.setup_logging()

    def setup_logging(self):
        """Setup structured logging for production."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """Log operation with structured data."""
        details = details or {}
        self.logger.info(f"Operation: {operation}", extra=details)

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context."""
        context = context or {}
        self.logger.error(f"Error: {str(error)}", extra=context, exc_info=True)


def performance_monitor(func):
    """Decorator to monitor function performance."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logging.info(f"Function {func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"Function {func.__name__} failed after {duration:.2f}s: {e}")
            raise

    return wrapper


@contextmanager
def operation_context(operation_name: str):
    """Context manager for tracking operations."""
    logger = ProductionLogger()
    start_time = time.time()

    try:
        logger.log_operation(f"Starting {operation_name}")
        yield logger
        duration = time.time() - start_time
        logger.log_operation(f"Completed {operation_name}", {"duration": duration})
    except Exception as e:
        duration = time.time() - start_time
        logger.log_error(e, {"operation": operation_name, "duration": duration})
        raise
