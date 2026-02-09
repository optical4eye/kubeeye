#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication API endpoints
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.repositories.user_repository import UserRepository
from db.models.user import User, UserRole
from services.auth_service import AuthService
from services.audit_service import AuditService
from core.security.password_service import password_service
from api.models import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    UserResponse,
    UserCreateRequest,
    UserUpdateRequest
)
from api.dependencies import get_current_user, require_admin
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user with username and password

    Returns access token
    """
    try:
        auth_service = AuthService(db)

        # Get client info
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        # Authenticate user
        user = await auth_service.authenticate_user(
            username=request.username,
            password=request.password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Create tokens
        tokens = await auth_service.create_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Add user info to response
        tokens["user"] = UserResponse.model_validate(user)

        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user (clears access token from client)
    """
    try:
        # Access token will be cleared by client
        logger.info("User logged out successfully")
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user password

    Requires authentication
    """
    try:
        auth_service = AuthService(db)
        success = await auth_service.change_password(
            user_id=current_user.id,
            old_password=request.old_password,
            new_password=request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid old password"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information

    Requires authentication
    """
    return UserResponse.model_validate(current_user)

# Admin-only endpoints
@router.get("/users", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)
        users = await user_repo.get_all(limit=limit, offset=skip)
        return [UserResponse.model_validate(user) for user in users]
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if username exists
        if await user_repo.username_exists(request.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        # Check if email exists
        if await user_repo.email_exists(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

        # Hash password
        password_hash = password_service.hash_password(request.password)

        # Create user
        user = await user_repo.create({
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "role": request.role,
            "is_active": request.is_active
        })

        logger.info(f"User created by admin: {request.username}")

        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prepare update data
        update_data = {}
        if request.email is not None:
            # Check if email exists for another user
            existing_user = await user_repo.get_by_email(request.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            update_data["email"] = request.email

        if request.role is not None:
            update_data["role"] = request.role

        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        # Update user
        updated_user = await user_repo.update(user_id, update_data)

        logger.info(f"User {user_id} updated by admin")

        return UserResponse.model_validate(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user

    Requires admin role
    """
    try:
        user_repo = UserRepository(db)

        # Check if user exists
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent deleting self
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself"
            )

        # Delete user
        await user_repo.delete(user_id)

        logger.info(f"User {user_id} deleted by admin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Audit endpoints (admin only)
@router.get("/audit/logs", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_logs(
    offset: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs with filtering and pagination

    Requires admin role
    """
    try:
        audit_service = AuditService(db)

        logs, total = await audit_service.get_audit_logs(
            limit=limit,
            offset=offset,
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            status=status,
            date_from=date_from,
            date_to=date_to
        )

        return {
            "logs": logs,
            "total": total,
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Get audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit/logs/{log_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit log by ID

    Requires admin role
    """
    try:
        audit_service = AuditService(db)

        log = await audit_service.get_audit_log_by_id(log_id)

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log not found"
            )

        return log
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get audit log error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit/stats", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit statistics

    Requires admin role
    """
    try:
        audit_service = AuditService(db)

        stats = await audit_service.get_audit_stats(date_from, date_to)

        return stats
    except Exception as e:
        logger.error(f"Get audit stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/audit/config", response_model=dict, status_code=status.HTTP_200_OK)
async def get_audit_cleanup_config(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs cleanup configuration

    Requires admin role
    """
    try:
        from core.config.settings import settings

        retention_days = settings.kubeeye_audit_retention_days
        logger.info(f"Returning audit cleanup config: retention_days={retention_days}")

        return {
            "retention_days": retention_days,
            "source": "settings"
        }
    except Exception as e:
        logger.error(f"Failed to get audit cleanup config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/audit/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_audit_logs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up old audit logs based on retention policy

    Requires admin role
    """
    try:
        audit_service = AuditService(db)

        deleted_count = await audit_service.cleanup_old_logs()

        return {
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} old audit logs"
        }
    except Exception as e:
        logger.error(f"Cleanup audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
