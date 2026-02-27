#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication dependencies for FastAPI
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import User
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger
from core.rbac import RBACManager, Role
from core.common.exceptions import NotFoundError

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        token = credentials.credentials

        # Verify access token
        payload = JWTUtils.verify_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

        return user
    except HTTPException:
        raise
    except NotFoundError:
        # User not found in database - token is valid but user was deleted
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        User object or None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials

        # Verify access token
        payload = JWTUtils.verify_access_token(token)
        if not payload:
            return None

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id))

        if not user or not user.is_active:
            return None

        return user
    except Exception as e:
        logger.warning(f"Get optional user error: {e}")
        return None


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role using simplified RBAC

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    try:
        # Check if user has admin role using simplified RBAC
        if current_user.role != Role.ADMIN:
            logger.warning(
                f"Admin role required: user_id={current_user.id}, "
                f"username={current_user.username}, user_role={current_user.role}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking admin role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def require_operator(current_user: User = Depends(get_current_user)) -> User:
    """
    Require operator or admin role using simplified RBAC

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not operator or admin
    """
    try:
        # Check if user has operator or admin role using simplified RBAC
        if current_user.role != Role.ADMIN and current_user.role != Role.OPERATOR:
            logger.warning(
                f"Operator or admin role required: user_id={current_user.id}, "
                f"username={current_user.username}, user_role={current_user.role}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator or admin privileges required")

        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking operator role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def require_permission(permission: str, current_user: User = Depends(get_current_user)) -> User:
    """
    Require a specific permission using simplified RBAC

    Args:
        permission: Permission string (e.g., "cluster:read")
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user doesn't have the required permission
    """
    try:
        # Check permission using simplified RBAC
        has_permission = RBACManager.check_permission(current_user.role, permission)

        if not has_permission:
            logger.warning(
                f"Permission denied: user_id={current_user.id}, "
                f"username={current_user.username}, permission={permission}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission}' required")

        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def require_role(role: str, current_user: User = Depends(get_current_user)) -> User:
    """
    Require a specific role using simplified RBAC

    Args:
        role: Role name (e.g., "admin", "operator")
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user doesn't have the required role
    """
    try:
        # Check if user has the required role using simplified RBAC
        if current_user.role != role:
            logger.warning(
                f"Role required: user_id={current_user.id}, "
                f"username={current_user.username}, required_role={role}, user_role={current_user.role}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required")

        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
