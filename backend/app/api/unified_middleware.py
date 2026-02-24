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
from core.logging import get_logger, request_id, resource_name, resource_type, resource_id, client_ip, client_user_agent

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

        # Reset resource context variables at the start of each request
        resource_name.set(None)
        resource_type.set(None)
        resource_id.set(None)

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

        # Set client IP and user-agent in context for audit decorator
        client_ip.set(ip)
        client_user_agent.set(user_agent)

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

                # Get resource info from context variables (set by endpoints)
                res_name = resource_name.get()
                res_type = resource_type.get()
                res_id = resource_id.get()

                extra_fields = {
                    "request_id": req_id,
                    "status_code": response_status,
                    "execution_time": execution_time,
                }

                # Add resource info if available
                if res_name:
                    extra_fields["resource_name"] = res_name
                if res_type:
                    extra_fields["resource_type"] = res_type
                if res_id:
                    extra_fields["resource_id"] = res_id

                logger.info(
                    f"Request completed: {method} {path} - {response_status}",
                    extra={"extra_fields": extra_fields},
                )

        try:
            await self.app(scope, receive, logging_send)
        except Exception as e:
            execution_time = time.time() - start_time

            # Get resource info from context variables (set by endpoints)
            res_name = resource_name.get()
            res_type = resource_type.get()
            res_id = resource_id.get()

            extra_fields = {
                "request_id": req_id,
                "execution_time": execution_time,
                "error": str(e),
            }

            # Add resource info if available
            if res_name:
                extra_fields["resource_name"] = res_name
            if res_type:
                extra_fields["resource_type"] = res_type
            if res_id:
                extra_fields["resource_id"] = res_id

            logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                extra={"extra_fields": extra_fields},
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

            # Note: Body validation is handled by FastAPI's Pydantic models automatically
            # We don't validate body here to avoid consuming the request body
            # which would prevent FastAPI from processing it

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

        # Skip validation for audit logs endpoint (action parameter can contain SQL keywords)
        if request.url.path.startswith("/api/auth/audit"):
            metrics.increment_counter("validation_query_success")
            return

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


# ============================================================================
# Resource Context Helpers
# ============================================================================


def set_resource_context(
    name: Optional[str] = None,
    type: Optional[str] = None,
    id: Optional[str] = None,
) -> None:
    """
    Set resource context for logging in middleware.

    This function should be called from endpoints to provide resource information
    that will be included in the middleware's request completion log.

    Args:
        name: Human-readable name of the resource (e.g., secret name, cluster name)
        type: Type of resource (e.g., "secret", "cluster", "inspection")
        id: Unique identifier of the resource

    Example:
        ```python
        @router.post("/secrets")
        async def create_secret(...):
            secret = await service.create_secret(...)
            set_resource_context(name=secret.name, type="secret", id=str(secret.id))
            return secret
        ```
    """
    if name is not None:
        resource_name.set(name)
    if type is not None:
        resource_type.set(type)
    if id is not None:
        resource_id.set(id)


def with_resource(res_type: str, resource_id_param: str = "id", resource_name_param: Optional[str] = None):
    """
    Decorator to automatically set resource context from endpoint parameters.

    Args:
        res_type: Type of resource (e.g., "secret", "cluster")
        resource_id_param: Name of the parameter containing resource ID
        resource_name_param: Name of the parameter containing resource name (optional)

    Example:
        ```python
        @router.delete("/secrets/{secret_id}")
        @with_resource("secret", resource_id_param="secret_id")
        async def delete_secret(secret_id: int, ...):
            ...
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Set resource type
            resource_type.set(res_type)

            # Get resource ID from kwargs
            res_id = kwargs.get(resource_id_param)
            if res_id is not None:
                resource_id.set(str(res_id))

            # Get resource name from kwargs if specified
            if resource_name_param:
                res_name = kwargs.get(resource_name_param)
                if res_name is not None:
                    resource_name.set(str(res_name))

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Audit Action Decorator
# ============================================================================


def audit_action(
    action: str,
    res_type: str,
    resource_id_param: Optional[str] = None,
    resource_name_param: Optional[str] = None,
    resource_name_extractor: Optional[Callable] = None,
    resource_id_extractor: Optional[Callable] = None,
    details_extractor: Optional[Callable] = None,
):
    """
    Decorator to automatically log audit actions and set resource context.

    This decorator combines:
    1. Setting resource context for middleware logging
    2. Logging audit action to database

    Args:
        action: Audit action type (e.g., AuditAction.SECRET_CREATE)
        res_type: Type of resource (e.g., "secret", "cluster")
        resource_id_param: Name of the parameter containing resource ID (optional)
        resource_name_param: Name of the parameter containing resource name (optional)
        resource_name_extractor: Function to extract resource name from result (optional)
        resource_id_extractor: Function to extract resource ID from result (optional)
        details_extractor: Function to extract details from result (optional)

    Example:
        ```python
        @router.post("/secrets")
        @audit_action(
            action=AuditAction.SECRET_CREATE,
            res_type="secret",
            resource_name_extractor=lambda result: result.name,
            resource_id_extractor=lambda result: str(result.id),
        )
        async def create_secret(...):
            secret = await service.create_secret(...)
            return secret
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from db.database import get_db
            from services.audit_service import AuditService
            from db.models.audit_log import AuditStatus

            # Find current_user in kwargs
            current_user = kwargs.get("current_user")
            if current_user is None:
                # Try to find User type in args
                from db.models.user import User

                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

            # Find db session in kwargs
            db = kwargs.get("db")

            # Get IP and User-Agent from context variables (set by middleware)
            ip_address = client_ip.get()
            user_agent = client_user_agent.get()

            # Extract resource info from parameters before execution
            res_id = kwargs.get(resource_id_param) if resource_id_param else None
            res_name = kwargs.get(resource_name_param) if resource_name_param else None

            # Set initial resource context
            if res_id is not None:
                resource_id.set(str(res_id))
            if res_name is not None:
                resource_name.set(str(res_name))
            resource_type.set(res_type)

            error_occurred = False
            error_message = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException as e:
                error_occurred = True
                error_message = e.detail
                raise
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                raise
            finally:
                # Extract resource info from result if extractors provided
                if result and not error_occurred:
                    if resource_name_extractor:
                        try:
                            extracted_name = resource_name_extractor(result)
                            if extracted_name:
                                res_name = extracted_name
                                resource_name.set(str(res_name))
                        except Exception as e:
                            logger.debug(f"Failed to extract resource name: {e}")

                    if resource_id_extractor:
                        try:
                            extracted_id = resource_id_extractor(result)
                            if extracted_id:
                                res_id = extracted_id
                                resource_id.set(str(res_id))
                        except Exception as e:
                            logger.debug(f"Failed to extract resource ID: {e}")

                # Read current context values (may have been set by set_resource_context inside function)
                context_res_name = resource_name.get()
                context_res_id = resource_id.get()

                # Use context values if available, otherwise use extracted/param values
                final_res_name = context_res_name or res_name
                final_res_id = context_res_id or res_id

                # Log audit action if we have user and db
                if current_user and db:
                    try:
                        audit_service = AuditService(db)

                        # Extract details if extractor provided
                        details = None
                        if details_extractor and result:
                            try:
                                details = details_extractor(result)
                            except Exception as e:
                                logger.debug(f"Failed to extract details: {e}")

                        await audit_service.log_action(
                            user_id=current_user.id,
                            username=current_user.username,
                            action=action,
                            resource_type=res_type,
                            resource_id=str(final_res_id) if final_res_id else None,
                            resource_name=str(final_res_name) if final_res_name else None,
                            details=details,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            status=AuditStatus.FAILURE if error_occurred else AuditStatus.SUCCESS,
                            error_message=error_message,
                        )
                    except Exception as e:
                        logger.error(f"Failed to log audit action: {e}")

        return wrapper

    return decorator


# HTTP method to action mapping (simple action names)
HTTP_METHOD_ACTION_MAP = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
    "GET": "read",
}


def audit_resource(
    res_type: str,
    resource_id_param: Optional[str] = None,
    resource_name_param: Optional[str] = None,
    resource_name_extractor: Optional[Callable] = None,
    resource_id_extractor: Optional[Callable] = None,
    details_extractor: Optional[Callable] = None,
    action_prefix: Optional[str] = None,
):
    """
    Simplified decorator that automatically determines action from HTTP method.

    This decorator automatically determines the audit action based on the HTTP method:
    - POST -> {res_type}_create
    - PUT/PATCH -> {res_type}_update
    - DELETE -> {res_type}_delete
    - GET -> {res_type}_read

    Args:
        res_type: Type of resource (e.g., "secret", "cluster")
        resource_id_param: Name of the parameter containing resource ID (optional)
        resource_name_param: Name of the parameter containing resource name (optional)
        resource_name_extractor: Function to extract resource name from result (optional)
        resource_id_extractor: Function to extract resource ID from result (optional)
        details_extractor: Function to extract details from result (optional)
        action_prefix: Custom prefix for action (default: res_type)

    Example:
        ```python
        @router.post("/secrets")
        @audit_resource(
            res_type="secret",
            resource_name_extractor=lambda result: result.name,
            resource_id_extractor=lambda result: str(result.id),
        )
        async def create_secret(...):
            # Automatically logs "secret_create" action
            secret = await service.create_secret(...)
            return secret

        @router.delete("/secrets/{secret_id}")
        @audit_resource(res_type="secret", resource_id_param="secret_id")
        async def delete_secret(secret_id: int, ...):
            # Automatically logs "secret_delete" action
            ...
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from db.database import get_db
            from services.audit_service import AuditService
            from db.models.audit_log import AuditStatus, AuditAction

            # Determine action from function name or HTTP method
            # Try to get HTTP method from request
            request = kwargs.get("request")
            http_method = None
            if request and isinstance(request, Request):
                http_method = request.method
            else:
                # Try to infer from function name
                func_name = func.__name__.lower()
                if "create" in func_name or "add" in func_name or "post" in func_name:
                    http_method = "POST"
                elif "update" in func_name or "edit" in func_name or "put" in func_name:
                    http_method = "PUT"
                elif "delete" in func_name or "remove" in func_name:
                    http_method = "DELETE"
                elif "get" in func_name or "list" in func_name or "find" in func_name:
                    http_method = "GET"

            # Build action name (simple action like "create", "update", "delete")
            action = HTTP_METHOD_ACTION_MAP.get(http_method or "", "action")

            # Find current_user in kwargs
            current_user = kwargs.get("current_user")
            if current_user is None:
                from db.models.user import User

                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

            # Find db session in kwargs
            db = kwargs.get("db")

            # Get IP and User-Agent from context variables (set by middleware)
            ip_address = client_ip.get()
            user_agent = client_user_agent.get()

            # Extract resource info from parameters before execution
            res_id = kwargs.get(resource_id_param) if resource_id_param else None
            res_name = kwargs.get(resource_name_param) if resource_name_param else None

            # Set initial resource context
            if res_id is not None:
                resource_id.set(str(res_id))
            if res_name is not None:
                resource_name.set(str(res_name))
            resource_type.set(res_type)

            error_occurred = False
            error_message = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException as e:
                error_occurred = True
                error_message = e.detail
                raise
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                raise
            finally:
                # Extract resource info from result if extractors provided
                if result and not error_occurred:
                    if resource_name_extractor:
                        try:
                            extracted_name = resource_name_extractor(result)
                            if extracted_name:
                                res_name = extracted_name
                                resource_name.set(str(res_name))
                        except Exception as e:
                            logger.debug(f"Failed to extract resource name: {e}")

                    if resource_id_extractor:
                        try:
                            extracted_id = resource_id_extractor(result)
                            if extracted_id:
                                res_id = extracted_id
                                resource_id.set(str(res_id))
                        except Exception as e:
                            logger.debug(f"Failed to extract resource ID: {e}")

                # Read current context values (may have been set by set_resource_context inside function)
                context_res_name = resource_name.get()
                context_res_id = resource_id.get()

                # Use context values if available, otherwise use extracted/param values
                final_res_name = context_res_name or res_name
                final_res_id = context_res_id or res_id

                # Log audit action if we have user and db
                if current_user and db:
                    try:
                        audit_service = AuditService(db)

                        # Extract details if extractor provided
                        details = None
                        if details_extractor and result:
                            try:
                                details = details_extractor(result)
                            except Exception as e:
                                logger.debug(f"Failed to extract details: {e}")

                        await audit_service.log_action(
                            user_id=current_user.id,
                            username=current_user.username,
                            action=action,
                            resource_type=res_type,
                            resource_id=str(final_res_id) if final_res_id else None,
                            resource_name=str(final_res_name) if final_res_name else None,
                            details=details,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            status=AuditStatus.FAILURE if error_occurred else AuditStatus.SUCCESS,
                            error_message=error_message,
                        )
                    except Exception as e:
                        logger.error(f"Failed to log audit action: {e}")

        return wrapper

    return decorator
