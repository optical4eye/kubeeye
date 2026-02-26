#!/usr/bin/env python3
"""
Authentication service - OAuth only (LDAP removed)
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repository import UserRepository
from db.models.user import User, AuthType, UserRole
from core.security.password_service import password_service
from core.security.jwt_utils import JWTUtils
from core.config.settings import settings
from infra.security.oauth_service import oauth_service, OAuthUser
from core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations - OAuth only"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate_local_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate local user (admin only, for emergency access)
        """
        user = await self.user_repo.get_by_username(username)

        if not user or not user.is_local():
            return None

        if not user.can_login():
            logger.warning(f"Local user '{username}' is locked or inactive")
            return None

        if not password_service.verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for local user '{username}'")
            await self.user_repo.increment_failed_attempts(user.id)
            return None

        await self.user_repo.update_last_login(user.id)
        logger.info(f"Local user '{username}' authenticated")
        return user

    async def authenticate_oauth_user(self, oauth_user: OAuthUser) -> Optional[User]:
        """
        Authenticate or create user from OAuth data
        """
        # Determine role from groups
        role = oauth_service.determine_role(oauth_user.groups)

        if not role:
            logger.warning(f"User '{oauth_user.username}' not in authorized groups: {oauth_user.groups}")
            return None

        # Get user by username or email
        user = await self.user_repo.get_by_username(oauth_user.username)

        if not user:
            # Check if user exists with same email (could be local user or OAuth with different username)
            user = await self.user_repo.get_by_email(oauth_user.email)
            if user:
                logger.info(f"Found existing user by email '{oauth_user.email}', linking OAuth credentials")

        if user:
            # Update existing user
            if not user.can_login():
                logger.warning(f"OAuth user '{oauth_user.username}' is locked")
                return None

            update_data = {}
            if user.username != oauth_user.username:
                update_data["username"] = oauth_user.username
            if user.email != oauth_user.email:
                update_data["email"] = oauth_user.email
            if user.role != role:
                update_data["role"] = role
            if user.oauth_subject != oauth_user.subject:
                update_data["oauth_subject"] = oauth_user.subject
            # Convert local user to OAuth if needed
            if user.auth_type != AuthType.OAUTH:
                update_data["auth_type"] = AuthType.OAUTH
                update_data["password_hash"] = None

            if update_data:
                await self.user_repo.update(user.id, update_data)
                logger.info(f"Updated OAuth user '{oauth_user.username}': {list(update_data.keys())}")

            await self.user_repo.update_last_login(user.id)
            logger.info(f"OAuth user '{oauth_user.username}' authenticated")
        else:
            # Create new user
            user = await self.user_repo.create(
                {
                    "username": oauth_user.username,
                    "email": oauth_user.email,
                    "password_hash": None,
                    "role": role,
                    "auth_type": AuthType.OAUTH,
                    "oauth_subject": oauth_user.subject,
                    "is_active": True,
                }
            )
            await self.user_repo.update_last_login(user.id)
            logger.info(f"Created new OAuth user '{oauth_user.username}' with role '{role}'")

        return user

    async def create_tokens(
        self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Dict[str, str]:
        """Create access token for user"""
        access_token = JWTUtils.create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role}
        )

        logger.info(f"Access token created for user '{user.username}'")
        return {"access_token": access_token, "token_type": "bearer"}

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password (only for local users)
        """
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            # Only local users can change password
            if not user.is_local():
                logger.warning(f"Cannot change password for OAuth user {user_id}")
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
