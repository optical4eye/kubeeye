#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication middleware for API protection
"""

from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from core.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication and authorization

    This middleware checks for valid JWT tokens on protected routes
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: list = None,
        excluded_prefixes: list = None
    ):
        """
        Initialize auth middleware

        Args:
            app: ASGI application
            excluded_paths: List of exact paths to exclude from auth
            excluded_prefixes: List of path prefixes to exclude from auth
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/"]
        self.excluded_prefixes = excluded_prefixes or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth",
            "/api/auth/refresh"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and check authentication

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        path = request.url.path

        # Skip authentication for excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header for path: {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"}
            )

        # Token validation will be done by route dependencies
        # This middleware just ensures the header is present
        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication

        Args:
            path: Request path

        Returns:
            True if excluded, False otherwise
        """
        # Check exact paths
        if path in self.excluded_paths:
            return True

        # Check path prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging

    This middleware logs all user actions to the audit log
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: list = None,
        excluded_prefixes: list = None
    ):
        """
        Initialize audit middleware

        Args:
            app: ASGI application
            excluded_paths: List of exact paths to exclude from audit
            excluded_prefixes: List of path prefixes to exclude from audit
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or []
        self.excluded_prefixes = excluded_prefixes or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/auth/login",
            "/api/auth/me",
            "/api/audit/logs",
            "/api/audit/stats"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log to audit

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        path = request.url.path
        method = request.method

        # Skip audit for excluded paths
        if self._is_excluded_path(path):
            return await call_next(request)

        # Get user info from request state (set by auth dependencies)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)

        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Process request
        response = await call_next(request)

        # Log action if user is authenticated
        if user_id and username:
            try:
                # Extract action and resource info from path
                action, resource_type, resource_id = self._extract_action_info(method, path)

                # Get audit service from request state
                audit_service = getattr(request.state, "audit_service", None)

                if audit_service:
                    # Determine status based on response status code
                    status = "success" if response.status_code < 400 else "failure"
                    error_message = None

                    if status == "failure":
                        # Try to get error message from response
                        try:
                            if hasattr(response, "body"):
                                import json
                                body = json.loads(response.body)
                                error_message = body.get("detail", "Unknown error")
                        except:
                            error_message = f"HTTP {response.status_code}"

                    # Log action
                    await audit_service.log_action(
                        user_id=user_id,
                        username=username,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status=status,
                        error_message=error_message
                    )
            except Exception as e:
                # Don't break the request if audit logging fails
                logger.error(f"Failed to log audit action: {e}")

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from audit

        Args:
            path: Request path

        Returns:
            True if excluded, False otherwise
        """
        # Check exact paths
        if path in self.excluded_paths:
            return True

        # Check path prefixes
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _extract_action_info(self, method: str, path: str) -> tuple[str, str, str]:
        """
        Extract action, resource type and resource ID from request

        Args:
            method: HTTP method
            path: Request path

        Returns:
            Tuple of (action, resource_type, resource_id)
        """
        # Parse path
        parts = path.strip("/").split("/")

        # Default values
        action = "unknown"
        resource_type = None
        resource_id = None

        # Map HTTP methods to actions
        method_to_action = {
            "GET": "view",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }

        # Extract resource type and ID
        if len(parts) >= 2:
            # Remove 'api' prefix if present
            if parts[0] == "api":
                parts = parts[1:]

            if len(parts) >= 1:
                resource_type = parts[0].rstrip("s")  # Remove plural 's'

                # Extract resource ID if present
                if len(parts) >= 2:
                    resource_id = parts[1]

        # Determine action based on method and resource
        if method in method_to_action:
            base_action = method_to_action[method]

            # Special cases
            if resource_type == "auth":
                if "login" in path:
                    action = "login"
                elif "logout" in path:
                    action = "logout"
                elif "change-password" in path:
                    action = "password_change"
                else:
                    action = base_action
            elif resource_type == "inspection":
                if "async" in path:
                    action = "inspection_run"
                else:
                    action = f"inspection_{base_action}"
            elif resource_type == "report":
                if "export" in path:
                    action = "report_export"
                else:
                    action = f"report_{base_action}"
            elif resource_type == "secret":
                action = f"secret_{base_action}"
            elif resource_type == "cluster":
                action = f"cluster_{base_action}"
            elif resource_type == "user":
                action = f"user_{base_action}"
            elif resource_type == "task":
                if "run" in path:
                    action = "task_run"
                else:
                    action = f"task_{base_action}"
            elif resource_type == "gitop":
                action = "gitops_sync"
            elif resource_type == "network-check":
                action = "network_check"
            elif resource_type == "popeye":
                action = "popeye_scan"
            elif resource_type == "cleanup":
                action = "cleanup_run"
            elif resource_type == "queue":
                action = "queue_clear"
            else:
                action = f"{resource_type}_{base_action}" if resource_type else base_action

        return action, resource_type, resource_id
