#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT utilities for token generation and validation
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from core.config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


class JWTUtils:
    """JWT utilities for token management"""

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token

        Args:
            data: Payload data to encode in token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        try:
            to_encode = data.copy()

            if expires_delta:
                expire = datetime.now(timezone.utc) + expires_delta
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    hours=settings.kubeeye_jwt_access_token_expire_hours
                )

            to_encode.update({"exp": expire, "type": "access"})

            encoded_jwt = jwt.encode(
                to_encode,
                settings.kubeeye_jwt_secret_key,
                algorithm=settings.kubeeye_jwt_algorithm
            )

            logger.debug(f"Created access token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.kubeeye_jwt_secret_key,
                algorithms=[settings.kubeeye_jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Failed to decode token: {e}")
            return None

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify access token

        Args:
            token: JWT access token string

        Returns:
            Decoded token payload or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[int]:
        """
        Extract user ID from token

        Args:
            token: JWT token string

        Returns:
            User ID or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("sub")
        return None

    @staticmethod
    def get_username_from_token(token: str) -> Optional[str]:
        """
        Extract username from token

        Args:
            token: JWT token string

        Returns:
            Username or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("username")
        return None

    @staticmethod
    def get_role_from_token(token: str) -> Optional[str]:
        """
        Extract role from token

        Args:
            token: JWT token string

        Returns:
            Role or None if invalid
        """
        payload = JWTUtils.decode_token(token)
        if payload:
            return payload.get("role")
        return None
