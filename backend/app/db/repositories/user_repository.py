#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User repository for user management
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.base_repository import BaseRepository
from db.models.user import User, UserRole
from core.logging import get_logger

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise

    async def get_active_users(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get all active users"""
        try:
            stmt = select(User).where(User.is_active == True).offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            raise

    async def get_users_by_role(self, role: str, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Get users by role"""
        try:
            stmt = select(User).where(User.role == role).offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get users by role {role}: {e}")
            raise

    async def username_exists(self, username: str) -> bool:
        """Check if username exists"""
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check username existence {username}: {e}")
            raise

    async def email_exists(self, email: str) -> bool:
        """Check if email exists"""
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check email existence {email}: {e}")
            raise

    async def update_last_login(self, user_id: int):
        """Update last login timestamp"""
        try:
            from datetime import datetime, timezone
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.last_login_at = datetime.now(timezone.utc)
                    user.failed_login_attempts = 0
                    user.locked_until = None
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
            raise

    async def increment_failed_attempts(self, user_id: int):
        """Increment failed login attempts"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.increment_failed_attempts()
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.lock_account(lock_duration_minutes=30)
        except Exception as e:
            logger.error(f"Failed to increment failed attempts for user {user_id}: {e}")
            raise

    async def lock_user(self, user_id: int, lock_duration_minutes: int = 30):
        """Lock user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.lock_account(lock_duration_minutes)
        except Exception as e:
            logger.error(f"Failed to lock user {user_id}: {e}")
            raise

    async def unlock_user(self, user_id: int):
        """Unlock user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.unlock_account()
        except Exception as e:
            logger.error(f"Failed to unlock user {user_id}: {e}")
            raise

    async def deactivate_user(self, user_id: int):
        """Deactivate user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.is_active = False
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            raise

    async def activate_user(self, user_id: int):
        """Activate user account"""
        try:
            async with self.transaction():
                user = await self.get_by_id(user_id)
                if user:
                    user.is_active = True
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            raise
