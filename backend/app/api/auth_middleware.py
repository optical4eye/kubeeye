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
from db.database import get_db
from services.audit_service import AuditService
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication and authorization

    This middleware checks for valid JWT tokens on protected routes
    """

    def __init__(self, app: ASGIApp, excluded_paths: list = None, excluded_prefixes: list = None):
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
            "/api/auth/refresh",
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
                status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Missing or invalid Authorization header"}
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

    def __init__(self, app: ASGIApp, excluded_paths: list = None, excluded_prefixes: list = None):
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
            "/api/auth/logout",
            "/api/auth/me",
            "/api/audit/logs",
            "/api/audit/stats",
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

        # Get user info from JWT token
        user_id = None
        username = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = JWTUtils.verify_access_token(token)
                if payload:
                    user_id = payload.get("sub")
                    # Convert user_id to integer for database compatibility
                    if user_id and isinstance(user_id, str):
                        try:
                            user_id = int(user_id)
                        except (ValueError, TypeError):
                            user_id = None
                    username = payload.get("username", "unknown")

                    # Set user info in request state for use by other middleware
                    request.state.user_id = user_id
                    request.state.username = username
            except Exception as e:
                logger.warning(f"Failed to extract user info from token: {e}")

        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Process request
        response = await call_next(request)

        # Log action if user is authenticated
        if user_id and username:
            try:
                # Extract action and resource info from path
                action, resource_type, resource_id, resource_name = self._extract_action_info(method, path)

                # Check if endpoint set resource_name in request.state
                if hasattr(request.state, "audit_resource_name"):
                    resource_name = request.state.audit_resource_name

                # Only log if action is in the allowed list
                if action:
                    # Create audit service instance
                    async for db in get_db():
                        audit_service = AuditService(db)

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
                            except (json.JSONDecodeError, AttributeError, TypeError):
                                error_message = f"HTTP {response.status_code}"

                        # Log action
                        await audit_service.log_action(
                            user_id=user_id,
                            username=username,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            resource_name=resource_name,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            status=status,
                            error_message=error_message,
                        )
                        break  # Exit after using one database session
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

    def _extract_action_info(self, method: str, path: str) -> tuple[str | None, str | None, str | None, str | None]:
        """
        Extract action, resource type, resource ID and resource name from request

        Args:
            method: HTTP method
            path: Request path

        Returns:
            Tuple of (action, resource_type, resource_id, resource_name)
        """
        # Parse path
        parts = path.strip("/").split("/")

        # Default values
        action = "unknown"
        resource_type = None
        resource_id = None
        resource_name = None  # Human-readable name (same as ID for most resources)

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
                    # For most resources, the ID is also the name
                    resource_name = resource_id

        # Determine action based on method and resource
        # Only log actions that are NOT explicitly logged in endpoints with resource_name
        # Secrets, clusters, users, tasks, reports are logged explicitly in endpoints
        if resource_type == "auth":
            if "login" in path:
                action = "login"
            elif "logout" in path:
                action = "logout"
        elif resource_type == "inspection":
            if "async" in path and method == "POST":
                action = "run"
            elif method == "POST":
                action = "create"
            elif method == "DELETE":
                action = "delete"
        elif resource_type == "report":
            # Only report create is logged here, report delete is logged in endpoint
            if method == "POST":
                action = "create"
        elif resource_type == "network-check" and method == "POST":
            action = "check"
        elif resource_type == "popeye" and method == "POST":
            action = "scan"
        # Note: secrets, clusters, users, tasks are logged explicitly in endpoints with resource_name

        # Return None for action if it's not in the allowed list
        if action == "unknown":
            action = None

        return action, resource_type, resource_id, resource_name
