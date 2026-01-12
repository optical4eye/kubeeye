#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced encryption utilities for secret management
"""

import base64
import time
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db.models.secrets import EncryptionKey
from db.repositories.secret_repository import EncryptionKeyRepository
from core.logging import get_logger
from db.database import get_engine
from asyncio import get_event_loop

logger = get_logger(__name__)

# Global cache for encryption key
_encryption_key_cache: Optional[bytes] = None


def initialize_encryption_key_sync() -> bytes:
    """
    Initialize encryption key from database or generate new one (synchronous)
    This function should be called from async context using run_sync

    Returns:
        Encryption key as bytes
    """
    global _encryption_key_cache

    if _encryption_key_cache is not None:
        return _encryption_key_cache

    # Generate new encryption key if not cached
    _encryption_key_cache = Fernet.generate_key()
    logger.info("New encryption key generated (will be saved to database)")
    return _encryption_key_cache


async def run_sync_in_async_context(func, *args, **kwargs):
    """
    Run a synchronous function in async context

    Args:
        func: Synchronous function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the function
    """
    loop = get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def initialize_encryption_key(session: AsyncSession) -> bytes:
    """
    Initialize encryption key from database or generate new one

    Args:
        session: Async database session

    Returns:
        Encryption key as bytes
    """
    global _encryption_key_cache

    if _encryption_key_cache is not None:
        return _encryption_key_cache

    key_repository = EncryptionKeyRepository(session)

    # Try to get active key from database
    encryption_key_record = await key_repository.get_active_key()

    if encryption_key_record:
        # Load key from database
        try:
            _encryption_key_cache = encryption_key_record.encryption_key.encode("utf-8")
            logger.info("Encryption key loaded from database")
            return _encryption_key_cache
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
            raise ValueError(f"Failed to load encryption key: {e}")
    else:
        # Generate new encryption key
        _encryption_key_cache = Fernet.generate_key()

        # Save to database
        try:
            await key_repository.create_key(key_name="default", encryption_key=_encryption_key_cache.decode("utf-8"))
            logger.info("New encryption key generated and saved to database")
            return _encryption_key_cache
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")
            raise ValueError(f"Failed to save encryption key: {e}")


class EncryptionService:
    """Service for encrypting and decrypting secrets"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.key_repository = EncryptionKeyRepository(session)

    async def _get_encryption_key(self) -> bytes:
        """
        Get encryption key from cache or initialize it

        Returns:
            Encryption key as bytes

        Raises:
            ValueError: If key cannot be loaded or created
        """
        # Use cached key if available
        if _encryption_key_cache is not None:
            return _encryption_key_cache

        # Initialize key using async function with database session
        await initialize_encryption_key(self.session)
        return _encryption_key_cache

    async def encrypt(self, data: str) -> str:
        """
        Encrypt data with encryption key

        Args:
            data: Plain text data to encrypt

        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return ""

        try:
            # Ensure key is initialized
            await self._get_encryption_key()

            fernet = Fernet(_encryption_key_cache)
            encrypted = fernet.encrypt(data.encode("utf-8"))
            return base64.urlsafe_b64encode(encrypted).decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")

    async def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data with encryption key

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""

        try:
            # Ensure key is initialized
            await self._get_encryption_key()

            fernet = Fernet(_encryption_key_cache)

            # Decode base64
            try:
                encrypted = base64.urlsafe_b64decode(encrypted_data)
            except Exception as e:
                logger.error(f"Base64 decoding error: {e}")
                raise ValueError("Invalid encrypted data format")

            # Decrypt
            try:
                decrypted = fernet.decrypt(encrypted).decode("utf-8")
                logger.debug("Decryption successful")
                return decrypted
            except Exception as e:
                logger.error(f"Fernet decryption error: {e}")
                raise ValueError("Failed to decrypt data")

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    async def validate_key(self) -> bool:
        """
        Validate that encryption key is valid

        Returns:
            True if encryption key is valid
        """
        try:
            await self._get_encryption_key()
            return True
        except Exception as e:
            logger.error(f"Encryption key validation failed: {e}")
            return False

    async def rotate_key(self) -> bytes:
        """
        Rotate encryption key

        Returns:
            New encryption key

        Raises:
            ValueError: If key rotation fails
        """
        global _encryption_key_cache

        try:
            # Generate new key
            new_key = Fernet.generate_key()

            # Save new key to database
            await self.key_repository.create_key(
                key_name=f"rotated_{int(time.time())}", encryption_key=new_key.decode("utf-8")
            )

            # Deactivate old key
            old_key_record = await self.key_repository.get_active_key()
            if old_key_record:
                await self.key_repository.deactivate_key(old_key_record.id)

            # Update global cache
            _encryption_key_cache = new_key

            logger.info("Encryption key rotated successfully")
            return new_key

        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise ValueError(f"Failed to rotate encryption key: {e}")


# Global encryption service factory
def get_encryption_service(session: AsyncSession) -> EncryptionService:
    """Get encryption service instance for given database session"""
    return EncryptionService(session)
