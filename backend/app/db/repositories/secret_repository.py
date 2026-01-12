#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository for secrets and encryption keys database operations
"""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from db.models.secrets import Secret, EncryptionKey
from db.repositories.base_repository import BaseRepository
from core.logging import get_logger

logger = get_logger(__name__)


class EncryptionKeyRepository(BaseRepository):
    """Repository for encryption key CRUD operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EncryptionKey)

    async def get_active_key(self) -> Optional[EncryptionKey]:
        """Get the currently active encryption key"""
        stmt = select(EncryptionKey).where(EncryptionKey.is_active)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, key_name: str) -> Optional[EncryptionKey]:
        """Get encryption key by name"""
        stmt = select(EncryptionKey).where(EncryptionKey.key_name == key_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_key(self, key_name: str, encryption_key: str, is_active: bool = True) -> EncryptionKey:
        """
        Create a new encryption key

        Args:
            key_name: Unique name for the key
            encryption_key: Encryption key data
            is_active: Whether this key is active

        Returns:
            Created EncryptionKey object
        """
        # Deactivate other keys if this one is active
        if is_active:
            stmt = update(EncryptionKey).where(EncryptionKey.is_active).values(is_active=False)
            await self.session.execute(stmt)

        # Create new key
        encryption_key_obj = EncryptionKey(key_name=key_name, encryption_key=encryption_key, is_active=is_active)

        self.session.add(encryption_key_obj)
        await self.session.commit()
        await self.session.refresh(encryption_key_obj)

        logger.info(f"Created encryption key: {key_name}")
        return encryption_key_obj

    async def deactivate_key(self, key_id: int) -> bool:
        """
        Deactivate an encryption key

        Args:
            key_id: ID of the key to deactivate

        Returns:
            True if deactivated successfully
        """
        try:
            encryption_key = await self.get_by_id(key_id)
            if encryption_key:
                encryption_key.is_active = False
                await self.session.commit()
                logger.info(f"Deactivated encryption key: {encryption_key.key_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating encryption key {key_id}: {e}")
            await self.session.rollback()
            return False

    async def list_keys(self, active_only: bool = False) -> List[EncryptionKey]:
        """
        List encryption keys

        Args:
            active_only: If True, only return active keys

        Returns:
            List of EncryptionKey objects
        """
        stmt = select(EncryptionKey)
        if active_only:
            stmt = stmt.where(EncryptionKey.is_active)
        stmt = stmt.order_by(EncryptionKey.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SecretRepository(BaseRepository):
    """Repository for secret CRUD operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Secret)

    async def get_by_name(self, name: str) -> Optional[Secret]:
        """Get secret by name"""
        stmt = select(Secret).where(Secret.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_type(self, secret_type: str, active_only: bool = True) -> List[Secret]:
        """Get secrets by type"""
        stmt = select(Secret).where(Secret.secret_type == secret_type)
        if active_only:
            stmt = stmt.where(Secret.is_active)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_filtered(
        self,
        secret_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Secret], int]:
        """Get secrets with filters"""
        stmt = select(Secret)

        # Apply filters
        if secret_type:
            stmt = stmt.where(Secret.secret_type == secret_type)

        if is_active is not None:
            stmt = stmt.where(Secret.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(or_(Secret.name.ilike(search_pattern), Secret.description.ilike(search_pattern)))

        # Get total count
        count_stmt = select(Secret.id).where(stmt.whereclause)
        if stmt.whereclause:
            count_stmt = select(Secret.id).where(stmt.whereclause)
        else:
            count_stmt = select(Secret.id)

        count_result = await self.session.execute(count_stmt)
        total = len(count_result.all())

        # Apply pagination
        stmt = stmt.order_by(Secret.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        secrets = result.scalars().all()

        return secrets, total

    async def update_last_used(self, secret_id: int) -> bool:
        """Update last_used_at timestamp"""
        try:
            from datetime import datetime

            # Use direct update to avoid caching issues
            stmt = update(Secret).where(Secret.id == secret_id).values(last_used_at=datetime.utcnow())
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating last_used_at for secret {secret_id}: {e}")
            await self.session.rollback()
            return False

    async def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if secret name exists (excluding specific ID for updates)"""
        stmt = select(Secret).where(Secret.name == name)
        if exclude_id:
            stmt = stmt.where(Secret.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def soft_delete(self, secret_id: int) -> bool:
        """Soft delete secret by setting is_active to False"""
        try:
            secret = await self.get_by_id(secret_id)
            if secret:
                secret.is_active = False
                await self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error soft deleting secret {secret_id}: {e}")
            await self.session.rollback()
            return False
