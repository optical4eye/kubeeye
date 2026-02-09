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
from db.models.user import User, UserRole
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
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
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(int(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
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


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


async def require_operator(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require operator or admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not operator or admin
    """
    if not (current_user.is_admin() or current_user.is_operator()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin privileges required"
        )

    return current_user
