#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication service for user authentication and token management
Supports both local and LDAP authentication
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from db.repositories.user_repository import UserRepository
from db.models.user import User, AuthType, UserRole
from core.security.password_service import password_service
from core.security.jwt_utils import JWTUtils
from core.config.settings import settings
from infra.security.ldap_service import ldap_service
from core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate_user(
        self, username: str, password: str, ip_address: Optional[str] = None,
        user_agent: Optional[str] = None, auth_type: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with username and password
        Supports both local and LDAP authentication

        Args:
            username: Username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            auth_type: Explicit authentication type ('local' or 'ldap')

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            user = await self.user_repo.get_by_username(username)

            # If explicit auth_type is provided, use only that method
            if auth_type == "local":
                # Local only authentication
                if user and user.is_local():
                    if not user.can_login():
                        logger.warning(f"Authentication failed: user '{username}' is locked or inactive")
                        return None
                    return await self._authenticate_local(user, password)
                logger.warning(f"Authentication failed: local user '{username}' not found")
                return None

            elif auth_type == "ldap":
                # LDAP only authentication
                if not ldap_service.is_enabled():
                    logger.warning("LDAP authentication requested but LDAP is not enabled")
                    return None

                if user:
                    if not user.can_login():
                        logger.warning(f"Authentication failed: user '{username}' is locked or inactive")
                        return None
                    if user.is_ldap():
                        return await self._authenticate_ldap(user, password)
                    # User exists but is local - reject LDAP login
                    logger.warning(f"LDAP authentication failed: user '{username}' is a local user")
                    return None
                else:
                    # New LDAP user
                    return await self._authenticate_new_ldap_user(username, password)

            # Auto-detect auth type (original behavior)
            if user:
                # Check if user can login
                if not user.can_login():
                    logger.warning(f"Authentication failed: user '{username}' is locked or inactive")
                    return None

                # Local user - authenticate with local password
                if user.is_local():
                    return await self._authenticate_local(user, password)

                # LDAP user - authenticate via LDAP
                elif user.is_ldap():
                    return await self._authenticate_ldap(user, password)

            # User not found in database - try LDAP if enabled
            if ldap_service.is_enabled():
                return await self._authenticate_new_ldap_user(username, password)

            logger.warning(f"Authentication failed: user '{username}' not found")
            return None

        except Exception as e:
            logger.error(f"Authentication error for user '{username}': {e}")
            raise

    async def _authenticate_local(self, user: User, password: str) -> Optional[User]:
        """
        Authenticate local user with password

        Args:
            user: User object
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        if not password_service.verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for local user '{user.username}'")
            await self.user_repo.increment_failed_attempts(user.id)
            return None

        # Update last login and reset failed attempts
        await self.user_repo.update_last_login(user.id)
        logger.info(f"Local user '{user.username}' authenticated successfully")

        return user

    async def _authenticate_ldap(self, user: User, password: str) -> Optional[User]:
        """
        Authenticate LDAP user via LDAP server

        Args:
            user: User object
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Authenticate via LDAP
        ldap_user = ldap_service.authenticate(user.username, password)

        if not ldap_user:
            logger.warning(f"LDAP authentication failed for user '{user.username}'")
            await self.user_repo.increment_failed_attempts(user.id)
            return None

        # Determine role from LDAP groups
        role = ldap_service.determine_role(ldap_user.groups)

        if not role:
            logger.warning(f"User '{user.username}' not in any authorized LDAP group")
            return None

        # Update user info from LDAP if needed
        update_data = {}
        if user.email != ldap_user.email:
            update_data["email"] = ldap_user.email
        if user.role != role:
            update_data["role"] = role
        if user.ldap_dn != ldap_user.dn:
            update_data["ldap_dn"] = ldap_user.dn

        if update_data:
            await self.user_repo.update(user.id, update_data)
            logger.info(f"Updated LDAP user '{user.username}' info: {list(update_data.keys())}")

        # Update last login
        await self.user_repo.update_last_login(user.id)
        logger.info(f"LDAP user '{user.username}' authenticated successfully")

        # Refresh user from database
        return await self.user_repo.get_by_id(user.id)

    async def _authenticate_new_ldap_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate and create new LDAP user

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Authenticate via LDAP
        ldap_user = ldap_service.authenticate(username, password)

        if not ldap_user:
            logger.warning(f"LDAP authentication failed for new user '{username}'")
            return None

        # Determine role from LDAP groups
        role = ldap_service.determine_role(ldap_user.groups)

        if not role:
            logger.warning(f"New user '{username}' not in any authorized LDAP group")
            return None

        # Create user in database
        try:
            user = await self.user_repo.create({
                "username": username,
                "email": ldap_user.email,
                "password_hash": None,  # No password for LDAP users
                "role": role,
                "auth_type": AuthType.LDAP,
                "ldap_dn": ldap_user.dn,
                "is_active": True
            })

            # Update last login
            await self.user_repo.update_last_login(user.id)
            logger.info(f"Created new LDAP user '{username}' with role '{role}'")

            return user
        except Exception as e:
            logger.error(f"Failed to create LDAP user '{username}': {e}")
            return None

    async def create_tokens(
        self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None
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
                data={"sub": str(user.id), "username": user.username, "role": user.role}
            )

            logger.info(f"Access token created for user '{user.username}'")

            return {"access_token": access_token, "token_type": "bearer"}
        except Exception as e:
            logger.error(f"Failed to create access token for user '{user.username}': {e}")
            raise

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password (only for local users)

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

            # Only local users can change password
            if not user.is_local():
                logger.warning(f"Cannot change password for LDAP user {user_id}")
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
