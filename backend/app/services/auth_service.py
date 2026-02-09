#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication service for user authentication and token management
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repository import UserRepository
from db.models.user import User
from core.security.password_service import password_service
from core.security.jwt_utils import JWTUtils
from core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with username and password

        Args:
            username: Username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            user = await self.user_repo.get_by_username(username)

            if not user:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None

            if not user.can_login():
                logger.warning(f"Authentication failed: user '{username}' is locked or inactive")
                return None

            if not password_service.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for user '{username}'")
                await self.user_repo.increment_failed_attempts(user.id)
                return None

            # Update last login and reset failed attempts
            await self.user_repo.update_last_login(user.id)
            logger.info(f"User '{username}' authenticated successfully")

            return user
        except Exception as e:
            logger.error(f"Authentication error for user '{username}': {e}")
            raise

    async def create_tokens(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create access token for user

        Args:
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Dictionary with access_token
        """
        try:
            # Create access token
            access_token = JWTUtils.create_access_token(
                data={
                    "sub": str(user.id),
                    "username": user.username,
                    "role": user.role
                }
            )

            logger.info(f"Access token created for user '{user.username}'")

            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
        except Exception as e:
            logger.error(f"Failed to create access token for user '{user.username}': {e}")
            raise

    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully, False otherwise
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            if not password_service.verify_password(old_password, user.password_hash):
                logger.warning(f"Invalid old password for user {user_id}")
                return False

            # Hash new password
            new_password_hash = password_service.hash_password(new_password)

            # Update password
            await self.user_repo.update(user_id, {"password_hash": new_password_hash})

            logger.info(f"Password changed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise
