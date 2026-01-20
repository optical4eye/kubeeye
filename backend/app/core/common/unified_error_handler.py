#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Error Handler - centralized error handling for KubeEye
Combines functionality from error_handler.py, error_handler_utils.py, and base_controller.py
"""

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Optional, Union, Dict, TypeVar, Awaitable
from fastapi import HTTPException

from .exceptions import KubeEyeException
from .metrics import metrics
from core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


# ============================================================================
# DECORATORS
# ============================================================================


def handle_errors(
    reraise: bool = True,
    log_level: str = "error",
    return_on_error: Any = None,
    convert_to_http: bool = False,
    http_status_code: int = 500,
    timing: bool = False,
) -> Callable:
    """
    Decorator for unified error handling.

    Args:
        reraise: Whether to re-raise the exception after logging
        log_level: Logging level ('debug', 'info', 'warning', 'error', 'critical')
        return_on_error: Value to return on error (if not reraise)
        convert_to_http: Convert KubeEyeException to HTTPException
        http_status_code: HTTP status code for HTTPException
        timing: Whether to track execution time

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        operation_name = f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if timing:
                start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                if timing:
                    duration = time.time() - start_time
                    metrics.record_timing(operation_name, duration)
                return result
            except Exception as e:
                if timing:
                    duration = time.time() - start_time
                    metrics.record_timing(f"{operation_name}_error", duration)
                return _handle_exception(
                    e, func, reraise, log_level, return_on_error, convert_to_http, http_status_code
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if timing:
                start_time = time.time()
            try:
                result = func(*args, **kwargs)
                if timing:
                    duration = time.time() - start_time
                    metrics.record_timing(operation_name, duration)
                return result
            except Exception as e:
                if timing:
                    duration = time.time() - start_time
                    metrics.record_timing(f"{operation_name}_error", duration)
                return _handle_exception(
                    e, func, reraise, log_level, return_on_error, convert_to_http, http_status_code
                )

        # Choose wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _handle_exception(
    exception: Exception,
    func: Callable,
    reraise: bool,
    log_level: str,
    return_on_error: Any,
    convert_to_http: bool,
    http_status_code: int,
) -> Any:
    """Handle exception based on decorator parameters"""
    # Get logger for the function's module using centralized logging
    func_logger = get_logger(func.__module__)

    # Log the exception
    log_method = getattr(func_logger, log_level, func_logger.error)
    log_method(f"Error in {func.__name__}: {str(exception)}", exc_info=True)

    # Increment error metrics
    error_type = type(exception).__name__
    metrics.increment_counter(f"errors_{error_type}")
    metrics.increment_counter("errors_total")

    # Convert to HTTPException if requested and it's a KubeEyeException
    if convert_to_http and isinstance(exception, KubeEyeException):
        raise HTTPException(status_code=http_status_code, detail=str(exception))

    # Re-raise if requested
    if reraise:
        raise

    # Return specified value on error
    return return_on_error


# Convenience decorators for common use cases
def handle_api_errors(status_code: int = 500, timing: bool = True) -> Callable:
    """Decorator for API endpoints - converts KubeEyeException to HTTPException"""
    return handle_errors(reraise=False, convert_to_http=True, http_status_code=status_code, timing=timing)


def handle_service_errors(return_on_error: Any = None, timing: bool = False) -> Callable:
    """Decorator for services - logs and returns on error"""
    return handle_errors(reraise=False, return_on_error=return_on_error, timing=timing)


def handle_infrastructure_errors(timing: bool = False) -> Callable:
    """Decorator for infrastructure code - logs and re-raises"""
    return handle_errors(reraise=True, timing=timing)


# ============================================================================
# ERROR RESULT CREATION
# ============================================================================


class ErrorHandler:
    """Centralized error handling utilities for creating error results"""

    @staticmethod
    def create_error_result(
        rule: Any, error_msg: str, description: Optional[str] = None, severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Create standardized error result for inspection rules

        Args:
            rule: Rule object that failed
            error_msg: Error message
            description: Optional description (defaults to error_msg)
            severity: Error severity level

        Returns:
            Standardized error result dictionary
        """
        if description is None:
            description = f"Error in rule {rule.id}: {error_msg}"

        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "status": "error",
            "severity": severity,
            "description": description,
            "details": error_msg,
            "solution": getattr(rule, "solution", "Check logs for more details"),
        }

    @staticmethod
    def create_execution_error_result(rule: Any, node: Dict[str, Any], error_msg: str) -> Optional[Dict[str, Any]]:
        """
        Create execution error result for node-specific failures

        Args:
            rule: Rule object that failed
            node: Node information dictionary
            error_msg: Execution error message

        Returns:
            Error result dictionary or None if node has SSH errors
        """
        # Don't create execution error for nodes with SSH connection errors
        # This should be handled by SSH error manager
        if node.get("connection_status", {}).get("success") is False:
            return None

        node_name = node.get("name", node.get("ip", "unknown"))
        description = f"Execution error on node {node_name}"

        result = ErrorHandler.create_error_result(rule=rule, error_msg=error_msg, description=description)

        # Add node information
        result["node"] = {"ip": node["ip"], "name": node_name}
        result["name"] = f"{rule.name} - {node_name}"

        return result

    @staticmethod
    def create_no_nodes_result(rule: Any, reason: str) -> Dict[str, Any]:
        """
        Create result when no nodes are available for rule execution

        Args:
            rule: Rule object
            reason: Reason why no nodes are available

        Returns:
            Skipped result dictionary
        """
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "status": "skipped",
            "severity": "info",
            "description": f"Rule execution skipped: {reason}",
            "details": reason,
            "solution": "Ensure nodes are available and properly configured",
        }


# ============================================================================
# OPERATION EXECUTION
# ============================================================================


class OperationExecutor:
    """Unified operation execution with standardized error handling"""

    def __init__(self, logger_instance=None):
        """
        Initialize operation executor

        Args:
            logger_instance: Optional logger instance (defaults to module logger)
        """
        self.logger = logger_instance or logger

    async def execute_operation(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_name: str,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> T:
        """
        Execute an async operation with standardized error handling and logging

        Args:
            operation: Async callable to execute
            operation_name: Name of the operation for logging
            success_message: Optional success message to log
            error_message: Optional error message prefix

        Returns:
            Result of the operation

        Raises:
            HTTPException: For errors during operation
        """
        try:
            self.logger.info(f"Starting {operation_name}")

            result = await operation()

            if success_message:
                self.logger.info(success_message)
            else:
                self.logger.info(f"{operation_name} completed successfully")

            return result

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            # Convert ValueError to HTTP 400
            error_msg = f"{error_message or operation_name} validation error: {str(e)}"
            self.logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert other exceptions to HTTP 500
            error_msg = f"{error_message or operation_name} error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)

    def execute_sync_operation(
        self,
        operation: Callable[[], T],
        operation_name: str,
        success_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> T:
        """
        Execute a synchronous operation with standardized error handling and logging

        Args:
            operation: Callable to execute
            operation_name: Name of the operation for logging
            success_message: Optional success message to log
            error_message: Optional error message prefix

        Returns:
            Result of the operation

        Raises:
            HTTPException: For errors during operation
        """
        try:
            self.logger.info(f"Starting {operation_name}")

            result = operation()

            if success_message:
                self.logger.info(success_message)
            else:
                self.logger.info(f"{operation_name} completed successfully")

            return result

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            # Convert ValueError to HTTP 400
            error_msg = f"{error_message or operation_name} validation error: {str(e)}"
            self.logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert other exceptions to HTTP 500
            error_msg = f"{error_message or operation_name} error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)

    @staticmethod
    def handle_async_operation(
        operation_name: str, operation_func, *args, error_msg: Optional[str] = None, **kwargs
    ) -> Any:
        """
        Handle async operation with standardized error handling

        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            error_msg: Custom error message
            *args, **kwargs: Arguments for the operation function

        Returns:
            Result of the operation or None on error
        """
        try:
            logger.debug(f"Starting async operation: {operation_name}")
            result = operation_func(*args, **kwargs)
            if hasattr(result, "__await__") or hasattr(result, "__aiter__"):
                if inspect.iscoroutine(result):
                    # For coroutines, we need to await them
                    # But since this is a utility function, we'll return the coroutine
                    return result
                else:
                    return result
            else:
                return result
        except Exception as e:
            error_message = error_msg or f"Error in {operation_name}: {str(e)}"
            logger.error(error_message, exc_info=True)
            return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def log_and_continue(operation_name: str, exception: Exception, log_level: str = "error") -> None:
    """
    Log exception and continue execution

    Args:
        operation_name: Name of the operation
        exception: Exception that occurred
        log_level: Logging level
    """
    log_method = getattr(logger, log_level, logger.error)
    log_method(f"Error in {operation_name}: {str(exception)}", exc_info=True)


def safe_get_attr(obj: Any, attr_path: str, default: Any = None) -> Any:
    """
    Safely get nested attribute from object

    Args:
        obj: Object to get attribute from
        attr_path: Dot-separated attribute path (e.g., "config.nodes")
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    try:
        for attr in attr_path.split("."):
            if hasattr(obj, attr):
                obj = getattr(obj, attr)
            elif isinstance(obj, dict) and attr in obj:
                obj = obj[attr]
            else:
                return default
        return obj
    except Exception:
        return default


# ============================================================================
# RESPONSE CREATION
# ============================================================================


def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standardized success response

    Args:
        message: Success message
        data: Optional additional data

    Returns:
        Response dictionary
    """
    response = {"message": message}
    if data:
        response.update(data)
    return response


def create_error_response(error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standardized error response

    Args:
        error_type: Type of error
        message: Error message
        details: Optional error details

    Returns:
        Response dictionary
    """
    response = {"error": error_type, "message": message}
    if details:
        response.update(details)
    return response


# ============================================================================
# PARAMETER VALIDATION
# ============================================================================


def validate_and_sanitize_param(
    param_value: Any, param_name: str, validator: Optional[Callable[[Any], Any]] = None, required: bool = True
) -> Any:
    """
    Validate and sanitize a parameter

    Args:
        param_value: Parameter value to validate
        param_name: Name of the parameter for error messages
        validator: Optional validation function
        required: Whether the parameter is required

    Returns:
        Validated and sanitized parameter value

    Raises:
        HTTPException: If validation fails
    """
    if required and (param_value is None or param_value == ""):
        raise HTTPException(status_code=400, detail=f"Missing required parameter: {param_name}")

    if param_value is not None and validator:
        try:
            return validator(param_value)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid {param_name}: {str(e)}")

    return param_value
