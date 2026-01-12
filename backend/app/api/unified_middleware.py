#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified middleware for FastAPI application - combines request logging and validation
"""

import time
import functools
import json
import re
from typing import Optional, Callable, Tuple, Type

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pydantic import BaseModel, ValidationError

from core.common.unified_validation import (
    sanitize_string,
    validate_ip_address,
    validate_status_filter,
    validate_format_param,
    validate_limit_param,
    validate_timeout_param,
    validate_port_param,
    validate_pagination_params,
    validate_datetime_param,
    contains_injection_patterns,
    validate_cluster_name,
    validate_task_id,
)
from core.common.metrics import metrics
from core.logging import get_logger, request_id

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """Middleware class for logging HTTP requests"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        import uuid

        req_id = str(uuid.uuid4())[:8]
        request_id.set(req_id)

        start_time = time.time()

        # Extract request info from scope
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        query = scope.get("query_string", b"").decode()
        headers = dict(scope.get("headers", []))

        # Get user agent and client info
        user_agent = headers.get(b"user-agent", b"").decode()
        client = scope.get("client")
        ip = client[0] if client else "unknown"

        logger.info(
            f"Request started: {method} {path}",
            extra={
                "extra_fields": {
                    "request_id": req_id,
                    "method": method,
                    "path": path,
                    "query": query,
                    "user_agent": user_agent,
                    "ip": ip,
                }
            },
        )

        # Create a wrapper for send to capture response
        original_send = send
        response_status = None

        async def logging_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]

                # Add request ID to response headers
                headers = list(message.get("headers", []))
                headers.append([b"X-Request-ID", req_id.encode()])
                message["headers"] = headers

            await original_send(message)

            # Log after response is sent
            if message["type"] == "http.response.body" and response_status is not None:
                execution_time = time.time() - start_time
                logger.info(
                    f"Request completed: {method} {path} - {response_status}",
                    extra={
                        "extra_fields": {
                            "request_id": req_id,
                            "status_code": response_status,
                            "execution_time": execution_time,
                        }
                    },
                )

        try:
            await self.app(scope, receive, logging_send)
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                extra={
                    "extra_fields": {
                        "request_id": req_id,
                        "execution_time": execution_time,
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            raise


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing input data"""

    def __init__(
        self,
        app,
        max_query_length: int = 1000,
        pydantic_model: Optional[Type[BaseModel]] = None,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.max_query_length = max_query_length
        self.pydantic_model = pydantic_model
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        metrics.increment_counter("middleware_requests")
        try:
            # Validate and sanitize query parameters
            await self._validate_query_params(request)

            # For POST/PUT requests, validate and sanitize body (except for excluded paths)
            if request.method in ["POST", "PUT", "PATCH"]:
                # Skip body validation for excluded paths (e.g., /api/secrets)
                if not any(request.url.path.startswith(path) for path in self.exclude_paths):
                    await self._validate_body(request)

                    # Validate against Pydantic model if provided
                    if self.pydantic_model:
                        await self._validate_pydantic_body(request)

            response = await call_next(request)
            metrics.increment_counter("middleware_success")
            return response
        except Exception as e:
            metrics.increment_counter("middleware_errors")
            raise

    async def _validate_query_params(self, request: Request) -> None:
        """Validate and sanitize query parameters"""
        metrics.increment_counter("validation_query_attempts")
        query_params = dict(request.query_params)

        for key, value in query_params.items():
            # Check for potentially dangerous patterns
            if self._contains_injection_patterns(value):
                metrics.increment_counter("validation_query_errors")
                logger.warning(f"Potentially dangerous query parameter detected: {key}={value}")
                raise HTTPException(status_code=400, detail=f"Invalid query parameter: {key}")

            # Sanitize the value
            sanitized_value = sanitize_string(value, self.max_query_length)
            if sanitized_value != value:
                logger.info(f"Sanitized query parameter: {key}")
        metrics.increment_counter("validation_query_success")

    async def _validate_body(self, request: Request) -> None:
        """Validate and sanitize request body"""
        metrics.increment_counter("validation_body_attempts")
        try:
            # Get the raw body
            body = await request.body()

            # Check for potentially dangerous patterns in raw body
            body_str = body.decode("utf-8", errors="ignore")
            if self._contains_injection_patterns(body_str):
                metrics.increment_counter("validation_body_errors")
                logger.warning("Potentially dangerous content detected in request body")
                raise HTTPException(status_code=400, detail="Invalid request body content")

            metrics.increment_counter("validation_body_success")
        except HTTPException:
            raise
        except Exception as e:
            # If we can't read the body, let the specific endpoint handle it
            logger.debug(f"Could not validate request body: {str(e)}")

    async def _validate_pydantic_body(self, request: Request) -> None:
        """Validate request body against Pydantic model"""
        try:
            # Get the body as JSON
            body_bytes = await request.body()
            body_data = json.loads(body_bytes.decode("utf-8"))

            # Validate against the model
            validated_model = validate_pydantic_model(self.pydantic_model, body_data)

            # Store validated model in request state for use in endpoints
            request.state.validated_body = validated_model

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        except Exception as e:
            # Re-raise validation errors
            raise

    def _contains_injection_patterns(self, value: str) -> bool:
        """Check for common injection patterns"""
        return contains_injection_patterns(value)


def validate_pydantic_model(model_class: Type[BaseModel], data: dict) -> BaseModel:
    """Validate data against a Pydantic model"""
    try:
        metrics.increment_counter("validation_pydantic_attempts")
        validated_model = model_class(**data)
        metrics.increment_counter("validation_pydantic_success")
        return validated_model
    except ValidationError as e:
        metrics.increment_counter("validation_pydantic_errors")
        logger.warning(f"Pydantic validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")
    except Exception as e:
        metrics.increment_counter("validation_pydantic_errors")
        logger.error(f"Unexpected error during Pydantic validation: {e}")
        raise HTTPException(status_code=500, detail="Internal validation error")


def validate_path_param(param_name: str, param_value: str, pattern: Optional[str] = None) -> str:
    """Validate and sanitize path parameters"""
    if not param_value:
        raise HTTPException(status_code=400, detail=f"Missing required path parameter: {param_name}")

    # Basic sanitization
    sanitized = sanitize_string(param_value, 100)

    # Check pattern if provided
    if pattern and not re.match(pattern, sanitized):
        raise HTTPException(status_code=400, detail=f"Invalid format for path parameter {param_name}")

    return sanitized


def validate_limit_param_middleware(limit: int) -> int:
    """Validate limit parameter with reasonable bounds"""
    try:
        return validate_limit_param(limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_task_id_middleware(task_id: str) -> str:
    """Validate task ID format"""
    try:
        return validate_task_id(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_cluster_name_middleware(cluster_name: str) -> str:
    """Validate cluster name format"""
    try:
        return validate_cluster_name(cluster_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_status_filter_middleware(status_filter: Optional[str]) -> Optional[str]:
    """Validate status filter parameter"""
    try:
        return validate_status_filter(status_filter)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_format_param_middleware(format_param: str) -> str:
    """Validate format parameter for export endpoints"""
    try:
        return validate_format_param(format_param)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_timeout_param_middleware(timeout: int) -> int:
    """Validate timeout parameter"""
    try:
        return validate_timeout_param(timeout)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_port_param_middleware(port: int) -> int:
    """Validate port parameter"""
    try:
        return validate_port_param(port)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_ip_address_middleware(ip: str) -> str:
    """Validate IP address or hostname"""
    if not ip:
        raise HTTPException(status_code=400, detail="IP address or hostname is required")

    if not validate_ip_address(ip, allow_hostname=True):
        raise HTTPException(status_code=400, detail="Invalid IP address or hostname")

    return ip


def validate_pagination_params_middleware(offset: int = 0, limit: int = 100) -> Tuple[int, int]:
    """Validate pagination parameters"""
    try:
        return validate_pagination_params(offset, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_datetime_param_middleware(datetime_str: str) -> str:
    """Validate datetime parameter format"""
    try:
        return validate_datetime_param(datetime_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Validation decorators for API endpoints
def validate_cluster_name_decorator(func: Callable) -> Callable:
    """Decorator to validate cluster_name parameter"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "cluster_name" in kwargs:
            kwargs["cluster_name"] = validate_cluster_name_middleware(kwargs["cluster_name"])
        return await func(*args, **kwargs)

    return wrapper


def validate_task_id_decorator(func: Callable) -> Callable:
    """Decorator to validate task_id parameter"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "task_id" in kwargs:
            kwargs["task_id"] = validate_task_id_middleware(kwargs["task_id"])
        if "report_id" in kwargs:  # Also validate report_id as task_id
            kwargs["report_id"] = validate_task_id_middleware(kwargs["report_id"])
        return await func(*args, **kwargs)

    return wrapper


def validate_limit_decorator(func: Callable) -> Callable:
    """Decorator to validate limit parameter"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "limit" in kwargs:
            kwargs["limit"] = validate_limit_param_middleware(kwargs["limit"])
        return await func(*args, **kwargs)

    return wrapper


def validate_status_filter_decorator(func: Callable) -> Callable:
    """Decorator to validate status_filter parameter"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "status_filter" in kwargs:
            kwargs["status_filter"] = validate_status_filter_middleware(kwargs["status_filter"])
        return await func(*args, **kwargs)

    return wrapper


def validate_format_decorator(func: Callable) -> Callable:
    """Decorator to validate format parameter"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "format" in kwargs:
            kwargs["format"] = validate_format_param_middleware(kwargs["format"])
        return await func(*args, **kwargs)

    return wrapper


def validate_pagination_decorator(func: Callable) -> Callable:
    """Decorator to validate pagination parameters"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if "offset" in kwargs or "limit" in kwargs:
            offset = kwargs.get("offset", 0)
            limit = kwargs.get("limit", 100)
            validated_offset, validated_limit = validate_pagination_params_middleware(offset, limit)
            kwargs["offset"] = validated_offset
            kwargs["limit"] = validated_limit
        return await func(*args, **kwargs)

    return wrapper


def validate_request_body(model_class: Type[BaseModel]):
    """Decorator to validate request body against a Pydantic model"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None and kwargs.get("request"):
                request = kwargs["request"]

            if request:
                try:
                    body_bytes = await request.body()
                    body_data = json.loads(body_bytes.decode("utf-8"))
                    validated_model = validate_pydantic_model(model_class, body_data)
                    # Add to kwargs or request.state
                    kwargs["validated_body"] = validated_model
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON in request body")
                except Exception as e:
                    raise

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def api_error_handler(func: Callable) -> Callable:
    """Decorator to handle API errors uniformly"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            # Convert ValueError to HTTP 400
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Convert other exceptions to HTTP 500
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return wrapper
