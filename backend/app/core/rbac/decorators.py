#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decorators for RBAC system

This module provides decorators for protecting endpoints
with permission checks using simplified RBAC system.
"""

from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException, status, Depends

from db.models.user import User
from .rbac_manager import RBACManager, Permission
from core.logging import get_logger

logger = get_logger(__name__)


def require_permission(permission: str):
    """
    Decorator to require a specific permission

    Args:
        permission: Permission string (e.g., "cluster:read")

    Example:
        @router.get("/clusters")
        @require_permission(Permission.CLUSTER_READ)
        async def get_clusters(current_user: User = Depends(get_current_user)):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            # Check permission using simplified RBAC
            has_permission = RBACManager.check_permission(current_user.role, permission)

            if not has_permission:
                logger.warning(
                    f"Permission denied: user_id={current_user.id}, "
                    f"username={current_user.username}, role={current_user.role}, permission={permission}"
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission}' required")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: str):
    """
    Decorator to require at least one of the specified permissions

    Args:
        *permissions: List of permission strings

    Example:
        @router.post("/clusters")
        @require_any_permission(Permission.CLUSTER_CREATE, Permission.CLUSTER_UPDATE)
        async def create_or_update_cluster(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            # Check if user has any of the required permissions
            has_any_permission = RBACManager.check_any_permission(current_user.role, *permissions)

            if not has_any_permission:
                logger.warning(
                    f"Permission denied: user_id={current_user.id}, "
                    f"username={current_user.username}, role={current_user.role}, required_permissions={permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of the following permissions required: {', '.join(permissions)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permissions: str):
    """
    Decorator to require all of the specified permissions

    Args:
        *permissions: List of permission strings

    Example:
        @router.delete("/clusters/{cluster_id}")
        @require_all_permissions(Permission.CLUSTER_READ, Permission.CLUSTER_DELETE)
        async def delete_cluster(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            # Check if user has all required permissions
            has_all_permissions = RBACManager.check_all_permissions(current_user.role, *permissions)

            if not has_all_permissions:
                logger.warning(
                    f"Permission denied: user_id={current_user.id}, "
                    f"username={current_user.username}, role={current_user.role}, required_permissions={permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permissions: {', '.join(permissions)}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """
    Decorator to require a specific role

    Args:
        role: Role name (e.g., "admin", "operator")

    Example:
        @router.post("/users")
        @require_role(Role.ADMIN)
        async def create_user(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

            # Check if user has the required role
            if current_user.role != role:
                logger.warning(
                    f"Role required: user_id={current_user.id}, "
                    f"username={current_user.username}, required_role={role}, user_role={current_user.role}"
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
