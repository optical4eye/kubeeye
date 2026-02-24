#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced logging configuration with structured logging and error tracking using loguru
"""

import json
import sys
import traceback
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

from loguru import logger
from core.config.settings import settings


class StructuredFormatter:
    """Structured JSON formatter for standard logging (compatibility layer)"""

    def format(self, record):
        """Format log record as JSON"""
        import json
        import traceback
        from datetime import datetime

        # Add structured fields
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": getattr(record, "module", "unknown"),
            "message": record.getMessage(),
        }

        # Add debug fields only in DEBUG level or lower
        if record.levelno <= 10:  # DEBUG level
            log_entry.update(
                {
                    "function": getattr(record, "funcName", "unknown"),
                    "line": getattr(record, "lineno", 0),
                }
            )

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
        if resource_name.get():
            log_entry["resource_name"] = resource_name.get()
        if resource_type.get():
            log_entry["resource_type"] = resource_type.get()
        if resource_id.get():
            log_entry["resource_id"] = resource_id.get()

        # Add extra fields from record
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


# Python 3.14+ sys.monitoring for performance profiling
try:
    import sys.monitoring

    HAS_SYS_MONITORING = True
except ImportError:
    HAS_SYS_MONITORING = False

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
cluster_name: ContextVar[Optional[str]] = ContextVar("cluster_name", default=None)
resource_name: ContextVar[Optional[str]] = ContextVar("resource_name", default=None)
resource_type: ContextVar[Optional[str]] = ContextVar("resource_type", default=None)
resource_id: ContextVar[Optional[str]] = ContextVar("resource_id", default=None)
# Client connection info (set by middleware)
client_ip: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
client_user_agent: ContextVar[Optional[str]] = ContextVar("client_user_agent", default=None)


def structured_formatter(record):
    """Minimal structured JSON formatter for loguru logs"""

    log_entry = {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "module": record["module"],
        "message": record["message"],
    }

    return json.dumps(log_entry, ensure_ascii=False)


def colored_formatter(record):
    """Colored formatter for console output"""

    # ANSI escape codes for colors
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    # Add color to level name
    level_color = COLORS.get(record["level"].name, COLORS["RESET"])
    reset_color = COLORS["RESET"]

    # Special highlighting for database connection messages
    message = record["message"]
    if "Database connection check: FAILED" in message or "Database connection check error" in message:
        # Make database errors more prominent with bright red
        level_color = "\033[1;91m"  # Bright red
        # Add highlighting to the connection info part
        if "(Host:" in message and "Port:" in message:
            message = (
                message.replace("(Host:", "\033[1;97m(Host:")
                .replace("Port:", "Port:")
                .replace(")", f"){reset_color}{level_color}")
            )
    elif "Database connection check: SUCCESS" in message or "Database connection established successfully" in message:
        # Make database success messages prominent with bright green
        level_color = "\033[1;92m"  # Bright green
        # Add highlighting to the connection info part
        if "(Host:" in message and "Port:" in message:
            message = (
                message.replace("(Host:", "\033[1;97m(Host:")
                .replace("Port:", "Port:")
                .replace(")", f"){reset_color}{level_color}")
            )

    # Format with colors
    formatted = f"{level_color}[{record['level'].name}]{reset_color} {record['name']}: {message}"

    # Add exception info if present
    if record["exception"]:
        formatted += f"\n{''.join(traceback.format_exception(record['exception'].type, record['exception'].value, record['exception'].traceback))}"

    return formatted


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
    enable_colors: bool = True,
):
    """Setup enhanced logging configuration"""

    # Remove all existing handlers
    logger.remove()

    # Set log level
    logger.level(log_level.upper())

    # Console handler
    if enable_console:
        if enable_structured:
            # Use minimal structured JSON output
            logger.add(
                sys.stdout,
                format='{{ "time": "{time}", "level": "{level}", "module": "{module}", "message": "{message}" }}',
                level=log_level.upper(),
            )
        elif enable_colors:
            # Use colored formatter for non-structured console output
            logger.add(sys.stdout, format=colored_formatter, level=log_level.upper())
        else:
            # Use minimal formatter
            logger.add(sys.stdout, format="{time} {module} {message}", level=log_level.upper())

    # File handler (if specified)
    if log_file:
        logger.add(log_file, rotation="10 MB", retention="1 week", level=log_level.upper())

    return logger


def log_execution_time(func):
    """Decorator to log function execution time"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        log = logger.bind(module=func.__module__)
        start_time = datetime.now()

        try:
            log.debug(f"Starting execution of {func.__name__}")
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            log.info(
                f"Completed execution of {func.__name__}",
                extra={
                    "execution_time": execution_time,
                    "function": func.__name__,
                    "status": "success",
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

            log.error(
                f"Failed execution of {func.__name__}: {str(e)}",
                extra={
                    "execution_time": execution_time,
                    "function": func.__name__,
                    "status": "error",
                    "error_type": type(e).__name__,
                },
            )
            raise

    return wrapper


def log_api_request(func):
    """Decorator to log API requests"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        log = logger.bind(module="api")
        start_time = datetime.now()

        # Extract request info (assuming FastAPI)
        request = None
        for arg in args:
            if hasattr(arg, "method") and hasattr(arg, "url"):
                request = arg
                break

        if request:
            log.info(
                f"API request: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "endpoint": func.__name__,
                },
            )

        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()

            log.info(
                f"API response: {func.__name__} completed",
                extra={
                    "execution_time": execution_time,
                    "endpoint": func.__name__,
                    "status": "success",
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

            log.error(
                f"API error in {func.__name__}: {str(e)}",
                extra={
                    "execution_time": execution_time,
                    "endpoint": func.__name__,
                    "status": "error",
                    "error_type": type(e).__name__,
                },
            )
            raise

    return wrapper


class ErrorBoundary:
    """Context manager for error boundary handling"""

    def __init__(self, operation: str, logger=None):
        self.operation = operation
        self.logger = logger or logger.bind(module=__name__)
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
                    "operation": self.operation,
                    "execution_time": execution_time,
                    "status": "error",
                    "error_type": exc_type.__name__,
                },
            )
            return False  # Re-raise exception

        self.logger.info(
            f"Operation completed: {self.operation}",
            extra={
                "operation": self.operation,
                "execution_time": execution_time,
                "status": "success",
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


def setup_performance_monitoring(log=None) -> bool:
    """Setup sys.monitoring for performance profiling (Python 3.14+)"""
    if not HAS_SYS_MONITORING:
        if log:
            log.info("sys.monitoring not available (requires Python 3.14+)")
        return False

    try:
        # Register monitoring callbacks for performance tracking
        def on_call(code, instruction_offset, callable, arg0):
            """Callback for function calls"""
            if log and log.level <= 10:  # DEBUG level
                log.debug(f"Function call: {callable.__name__ if hasattr(callable, '__name__') else str(callable)}")

        def on_return(code, instruction_offset, callable, retval):
            """Callback for function returns"""
            if log and log.level <= 10:  # DEBUG level
                log.debug(f"Function return: {callable.__name__ if hasattr(callable, '__name__') else str(callable)}")

        def on_exception(code, instruction_offset, callable, exc):
            """Callback for exceptions"""
            if log:
                log.warning(f"Exception in monitored code: {exc}")

        # Register callbacks for tool 0 (performance monitoring)
        sys.monitoring.register_callback(0, sys.monitoring.events.CALL, on_call)
        sys.monitoring.register_callback(0, sys.monitoring.events.RETURN, on_return)
        sys.monitoring.register_callback(0, sys.monitoring.events.EXCEPTION_HANDLED, on_exception)

        # Enable monitoring globally (can be restricted to specific modules)
        sys.monitoring.set_events(
            0, sys.monitoring.events.CALL | sys.monitoring.events.RETURN | sys.monitoring.events.EXCEPTION_HANDLED
        )

        if log:
            log.info("Performance monitoring enabled with sys.monitoring")
        return True

    except Exception as e:
        if log:
            log.warning(f"Failed to setup performance monitoring: {e}")
        return False


def disable_performance_monitoring(log=None) -> bool:
    """Disable sys.monitoring performance profiling"""
    if not HAS_SYS_MONITORING:
        return False

    try:
        # Disable all events for tool 0
        sys.monitoring.set_events(0, 0)

        # Unregister callbacks
        sys.monitoring.register_callback(0, sys.monitoring.events.CALL, None)
        sys.monitoring.register_callback(0, sys.monitoring.events.RETURN, None)
        sys.monitoring.register_callback(0, sys.monitoring.events.EXCEPTION_HANDLED, None)

        if log:
            log.info("Performance monitoring disabled")
        return True

    except Exception as e:
        if log:
            log.warning(f"Failed to disable performance monitoring: {e}")
        return False


# Log level mapping for compatibility
LOG_LEVELS = {
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARNING",
    "error": "ERROR",
    "critical": "CRITICAL",
}


def get_logger(module_name: str):
    """
    Get logger for specified module

    Args:
        module_name: Module name

    Returns:
        Configured module logger (loguru logger with context)
    """
    return logger.bind(module=module_name)


def get_system_health() -> dict:
    """
    Get system health information including error statistics

    Returns:
        Health information dictionary
    """
    return {
        "logging": {
            "error_summary": get_error_summary(),
        }
    }


# Set log levels for third-party libraries (using standard logging for compatibility)
logging.getLogger("asyncssh").setLevel(logging.WARNING)
logging.getLogger("kubernetes").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
