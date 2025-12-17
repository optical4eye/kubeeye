#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Middleware for input validation and sanitization
"""

import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re

from .models import sanitize_string

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing input data"""

    def __init__(self, app, max_query_length: int = 1000):
        super().__init__(app)
        self.max_query_length = max_query_length

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate and sanitize query parameters
        await self._validate_query_params(request)

        # For POST/PUT requests, validate and sanitize body
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_body(request)

        response = await call_next(request)
        return response

    async def _validate_query_params(self, request: Request) -> None:
        """Validate and sanitize query parameters"""
        query_params = dict(request.query_params)

        for key, value in query_params.items():
            # Check for potentially dangerous patterns
            if self._contains_injection_patterns(value):
                logger.warning(f"Potentially dangerous query parameter detected: {key}={value}")
                raise HTTPException(status_code=400, detail=f"Invalid query parameter: {key}")

            # Sanitize the value
            sanitized_value = sanitize_string(value, self.max_query_length)
            if sanitized_value != value:
                logger.info(f"Sanitized query parameter: {key}")

    async def _validate_body(self, request: Request) -> None:
        """Validate and sanitize request body"""
        try:
            # Get the raw body
            body = await request.body()

            # Check for potentially dangerous patterns in raw body
            body_str = body.decode("utf-8", errors="ignore")
            if self._contains_injection_patterns(body_str):
                logger.warning("Potentially dangerous content detected in request body")
                raise HTTPException(status_code=400, detail="Invalid request body content")

        except Exception as e:
            # If we can't read the body, let the specific endpoint handle it
            logger.debug(f"Could not validate request body: {str(e)}")

    def _contains_injection_patterns(self, value: str) -> bool:
        """Check for common injection patterns"""
        if not isinstance(value, str):
            return False

        # SQL Injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|\#|\/\*|\*\/)",
            r"(\bOR\b.*\b1\s*=\s*1\b|\bAND\b.*\b1\s*=\s*1\b)",
        ]

        # XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",  # onclick=, onload=, etc.
        ]

        # Command injection patterns
        cmd_patterns = [
            r"[;&|`$()]",
            r"\b(curl|wget|nc|netcat|ssh|ftp|telnet)\b",
        ]

        # Check all patterns
        all_patterns = sql_patterns + xss_patterns + cmd_patterns

        for pattern in all_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return True

        return False


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


def validate_limit_param(limit: int) -> int:
    """Validate limit parameter with reasonable bounds"""
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be at least 1")

    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")

    return limit


def validate_task_id(task_id: str) -> str:
    """Validate task ID format"""
    if not task_id:
        raise HTTPException(status_code=400, detail="Task ID is required")

    # Allow alphanumeric characters, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", task_id):
        raise HTTPException(
            status_code=400, detail="Task ID can only contain alphanumeric characters, hyphens, and underscores"
        )

    if len(task_id) > 100:
        raise HTTPException(status_code=400, detail="Task ID cannot exceed 100 characters")

    return sanitize_string(task_id, 100)


def validate_cluster_name(cluster_name: str) -> str:
    """Validate cluster name format"""
    if not cluster_name:
        raise HTTPException(status_code=400, detail="Cluster name is required")

    # Allow alphanumeric characters, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", cluster_name):
        raise HTTPException(
            status_code=400, detail="Cluster name can only contain alphanumeric characters, hyphens, and underscores"
        )

    if len(cluster_name) > 100:
        raise HTTPException(status_code=400, detail="Cluster name cannot exceed 100 characters")

    return sanitize_string(cluster_name, 100)


def validate_status_filter(status_filter: Optional[str]) -> Optional[str]:
    """Validate status filter parameter"""
    if status_filter is None:
        return None

    valid_statuses = ["pending", "running", "completed", "failed"]
    if status_filter not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status filter must be one of: {', '.join(valid_statuses)}")

    return status_filter


def validate_format_param(format_param: str) -> str:
    """Validate format parameter for export endpoints"""
    if not format_param:
        raise HTTPException(status_code=400, detail="Format parameter is required")

    valid_formats = ["json", "csv", "excel", "pdf"]
    if format_param not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Format must be one of: {', '.join(valid_formats)}")

    return format_param


def validate_timeout_param(timeout: int) -> int:
    """Validate timeout parameter"""
    if timeout < 1:
        raise HTTPException(status_code=400, detail="Timeout must be at least 1 second")

    if timeout > 300:  # 5 minutes max
        raise HTTPException(status_code=400, detail="Timeout cannot exceed 300 seconds")

    return timeout


def validate_port_param(port: int) -> int:
    """Validate port parameter"""
    if port < 1 or port > 65535:
        raise HTTPException(status_code=400, detail="Port must be between 1 and 65535")

    return port


def validate_ip_address(ip: str) -> str:
    """Validate IP address or hostname"""
    import socket

    if not ip:
        raise HTTPException(status_code=400, detail="IP address or hostname is required")

    try:
        socket.gethostbyname(ip)
        return ip
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Invalid IP address or hostname")


def sanitize_json_response(data: dict) -> dict:
    """Sanitize JSON response data to prevent injection"""
    if not isinstance(data, dict):
        return data if isinstance(data, dict) else {}

    def sanitize_value(value):
        if isinstance(value, str):
            # Remove potential script tags and dangerous patterns
            sanitized = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
            return sanitize_string(sanitized, 10000)  # Larger limit for response data
        elif isinstance(value, dict):
            return {k: sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [sanitize_value(item) for item in value]
        else:
            return value

    return sanitize_value(data)


def validate_pagination_params(offset: int = 0, limit: int = 100) -> tuple[int, int]:
    """Validate pagination parameters"""
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset cannot be negative")

    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be at least 1")

    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")

    return offset, limit


def validate_datetime_param(datetime_str: str) -> str:
    """Validate datetime parameter format"""
    if not datetime_str:
        raise HTTPException(status_code=400, detail="Datetime parameter is required")

    from datetime import datetime

    try:
        # Try to parse ISO format datetime
        datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return datetime_str
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
