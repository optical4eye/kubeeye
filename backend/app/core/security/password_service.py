#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Password service for password hashing and verification
"""

from pwdlib import PasswordHash
from core.logging import get_logger

logger = get_logger(__name__)


class PasswordService:
    """Service for password hashing and verification"""

    def __init__(self):
        # Use recommended hasher (Argon2 when pwdlib[argon2] is installed)
        self.hasher = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        """
        Hash password using Argon2

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        try:
            hashed = self.hasher.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            is_valid = self.hasher.verify(plain_password, hashed_password)
            if is_valid:
                logger.debug("Password verified successfully")
            else:
                logger.warning("Password verification failed")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            raise


# Global password service instance
password_service = PasswordService()
