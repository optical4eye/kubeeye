#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced logging configuration with structured logging and error tracking
"""

import logging
import logging.handlers
import json
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
cluster_name: ContextVar[Optional[str]] = ContextVar("cluster_name", default=None)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""

    def format(self, record: logging.LogRecord) -> str:
        # Add structured fields
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add context variables
        if request_id.get():
            log_entry["request_id"] = request_id.get()
        if user_id.get():
            log_entry["user_id"] = user_id.get()
        if cluster_name.get():
            log_entry["cluster_name"] = cluster_name.get()

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class ErrorTracker:
    """Error tracking and aggregation"""

    def __init__(self):
        self.errors = []
        self.max_errors = 1000

    def add_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Add error to tracking"""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        self.errors.append(error_info)

        # Keep only recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors :]

    def get_recent_errors(self, limit: int = 50) -> list:
        """Get recent errors"""
        return self.errors[-limit:]

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        stats = {}
        for error in self.errors:
            error_type = error["type"]
            stats[error_type] = stats.get(error_type, 0) + 1
        return stats


# Global error tracker
error_tracker = ErrorTracker()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_structured: bool = True,
    enable_console: bool = True,
) -> logging.Logger:
    """Setup enhanced logging configuration"""

    # Create logger
    logger = logging.getLogger("kubeeye")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatters
    if enable_structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_execution_time(func):
    """Decorator to log function execution time"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()

        try:
            logger.debug(f"Starting execution of {func.__name__}")
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Completed execution of {func.__name__}",
                extra={
                    "extra_fields": {
                        "execution_time": execution_time,
                        "function": func.__name__,
                        "status": "success",
                    }
                },
            )
            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_tracker.add_error(
                e,
                {
                    "function": func.__name__,
                    "execution_time": execution_time,
                },
            )

            logger.error(
                f"Failed execution of {func.__name__}: {str(e)}",
                extra={
                    "extra_fields": {
                        "execution_time": execution_time,
                        "function": func.__name__,
                        "status": "error",
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )
            raise

    return wrapper


def log_api_request(func):
    """Decorator to log API requests"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger("api")
        start_time = datetime.now()

        # Extract request info (assuming FastAPI)
        request = None
        for arg in args:
            if hasattr(arg, "method") and hasattr(arg, "url"):
                request = arg
                break

        if request:
            logger.info(
                f"API request: {request.method} {request.url.path}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "query": str(request.url.query),
                        "endpoint": func.__name__,
                    }
                },
            )

        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"API response: {func.__name__} completed",
                extra={
                    "extra_fields": {
                        "execution_time": execution_time,
                        "endpoint": func.__name__,
                        "status": "success",
                    }
                },
            )
            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_tracker.add_error(
                e,
                {
                    "endpoint": func.__name__,
                    "execution_time": execution_time,
                },
            )

            logger.error(
                f"API error in {func.__name__}: {str(e)}",
                extra={
                    "extra_fields": {
                        "execution_time": execution_time,
                        "endpoint": func.__name__,
                        "status": "error",
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )
            raise

    return wrapper


class ErrorBoundary:
    """Context manager for error boundary handling"""

    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = (datetime.now() - self.start_time).total_seconds()

        if exc_type:
            error_tracker.add_error(
                exc_val,
                {
                    "operation": self.operation,
                    "execution_time": execution_time,
                },
            )

            self.logger.error(
                f"Operation failed: {self.operation} - {str(exc_val)}",
                extra={
                    "extra_fields": {
                        "operation": self.operation,
                        "execution_time": execution_time,
                        "status": "error",
                        "error_type": exc_type.__name__,
                    }
                },
                exc_info=(exc_type, exc_val, exc_tb),
            )
            return False  # Re-raise exception

        self.logger.info(
            f"Operation completed: {self.operation}",
            extra={
                "extra_fields": {
                    "operation": self.operation,
                    "execution_time": execution_time,
                    "status": "success",
                }
            },
        )
        return True


def get_error_summary() -> Dict[str, Any]:
    """Get error summary for monitoring"""
    return {
        "total_errors": len(error_tracker.errors),
        "error_stats": error_tracker.get_error_stats(),
        "recent_errors": error_tracker.get_recent_errors(10),
    }


# Initialize logging on import
logger = setup_logging(
    log_level="INFO",
    log_file="logs/kubeeye.log",
    enable_structured=True,
    enable_console=True,
)
