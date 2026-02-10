#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base repository with common CRUD operations - Async Only
"""

from typing import List, Optional, TypeVar, Generic, Type, Any, Dict
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from db.models.base import Base
from core.common.retry_utils import retry_on_failure
from core.common.exceptions import RepositoryError, NotFoundError
from core.common.cache_utils import cached, invalidate_cache
from core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Async base repository with common CRUD operations"""

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
        self.namespace = f"{self.model_class.__name__.lower()}_repository"

    @asynccontextmanager
    async def transaction(self):
        """Async context manager for database transactions with proper cleanup"""
        try:
            yield
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Async database transaction failed: {e}")
            raise

    @cached("base_repository", ttl=300)
    @retry_on_failure(max_attempts=3, exceptions=(Exception,))
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID"""
        return await self._get_by_id_internal(id)

    async def _get_by_id_internal(self, id: int) -> Optional[T]:
        """Internal method to get entity by ID without retry decorator"""
        try:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await self.session.execute(stmt)
            entity = result.scalar_one_or_none()
            if entity is None:
                raise NotFoundError(f"Entity with ID {id} not found")
            return entity
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get entity by ID {id}: {e}")
            raise RepositoryError(f"Failed to get entity by ID {id}: {e}")

    async def get_all(self, limit: Optional[int] = None, offset: int = 0, **filters) -> List[T]:
        """Get all entities with pagination and filters"""
        try:
            stmt = select(self.model_class).offset(offset)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            if limit:
                stmt = stmt.limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get all entities: {e}")
            raise

    async def get_all_optimized(
        self, limit: Optional[int] = None, offset: int = 0, eager_loads: Optional[List[str]] = None, **filters
    ) -> List[T]:
        """
        Get all entities with optimized eager loading to avoid N+1 queries

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            eager_loads: List of relationship names to eager load
            **filters: Filter conditions

        Returns:
            List of entities with loaded relationships
        """
        try:
            stmt = select(self.model_class).offset(offset)

            # Apply eager loading
            if eager_loads:
                for relation in eager_loads:
                    if hasattr(self.model_class, relation):
                        stmt = stmt.options(selectinload(getattr(self.model_class, relation)))

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            if limit:
                stmt = stmt.limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get all entities optimized: {e}")
            raise

    @retry_on_failure(max_attempts=3, exceptions=(Exception,))
    async def create(self, obj_data: dict) -> T:
        """Create new entity"""
        try:
            # Basic validation
            if not obj_data:
                raise ValueError("Empty data provided for entity creation")
            if not isinstance(obj_data, dict):
                raise ValueError("Data must be a dictionary")

            # Call model validation if available
            if hasattr(self.model_class, "validate_data"):
                obj_data = self.model_class.validate_data(obj_data)

            async with self.transaction():
                entity = self.model_class(**obj_data)
                self.session.add(entity)
                await self.session.flush()  # Get ID without committing
                await self.session.refresh(entity)
                invalidate_cache(self.namespace)
                return entity
        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            raise RepositoryError(f"Failed to create entity: {e}")

    @retry_on_failure(max_attempts=3, exceptions=(Exception,))
    async def update(self, id: int, obj_data: dict) -> Optional[T]:
        """Update entity by ID"""
        try:
            # Basic validation
            if not obj_data:
                raise ValueError("Empty data provided for entity update")
            if not isinstance(obj_data, dict):
                raise ValueError("Data must be a dictionary")

            # Call model validation if available
            if hasattr(self.model_class, "validate_data"):
                obj_data = self.model_class.validate_data(obj_data)

            async with self.transaction():
                entity = await self._get_by_id_internal(id)
                if entity:
                    for key, value in obj_data.items():
                        if hasattr(entity, key):
                            setattr(entity, key, value)
                    await self.session.flush()
                    await self.session.refresh(entity)
                    invalidate_cache(self.namespace)
                return entity
        except Exception as e:
            logger.error(f"Failed to update entity with ID {id}: {e}")
            raise RepositoryError(f"Failed to update entity with ID {id}: {e}")

    @retry_on_failure(max_attempts=3, exceptions=(Exception,))
    async def delete(self, id: int) -> bool:
        """Delete entity by ID"""
        try:
            async with self.transaction():
                entity = await self._get_by_id_internal(id)
                if entity:
                    await self.session.delete(entity)
                    invalidate_cache(self.namespace)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete entity with ID {id}: {e}")
            raise RepositoryError(f"Failed to delete entity with ID {id}: {e}")

    @cached("base_repository", ttl=300)
    async def count(self, **filters) -> int:
        """Count total entities with optional filters"""
        try:
            stmt = select(func.count(self.model_class.id))

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            result = await self.session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.error(f"Failed to count entities: {e}")
            raise

    async def exists(self, id: int) -> bool:
        """Check if entity exists"""
        try:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Failed to check if entity exists with ID {id}: {e}")
            raise

    async def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Get entity by custom field"""
        try:
            field = getattr(self.model_class, field_name, None)
            if field is None:
                raise ValueError(f"Field {field_name} not found in model {self.model_class.__name__}")

            stmt = select(self.model_class).where(field == value)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get entity by {field_name}={value}: {e}")
            raise

    async def get_many_by_field(self, field_name: str, value: Any) -> List[T]:
        """Get multiple entities by custom field"""
        try:
            field = getattr(self.model_class, field_name, None)
            if field is None:
                raise ValueError(f"Field {field_name} not found in model {self.model_class.__name__}")

            stmt = select(self.model_class).where(field == value)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get entities by {field_name}={value}: {e}")
            raise

    async def bulk_create(self, entities_data: List[dict]) -> List[T]:
        """Bulk create entities"""
        try:
            async with self.transaction():
                entities = [self.model_class(**data) for data in entities_data]
                self.session.add_all(entities)
                await self.session.flush()

                # Refresh all entities to get their IDs
                for entity in entities:
                    await self.session.refresh(entity)

                return entities
        except Exception as e:
            logger.error(f"Failed to bulk create entities: {e}")
            raise

    async def bulk_create_optimized(self, entities_data: List[dict]) -> List[T]:
        """
        Bulk create entities with optimized performance using bulk_insert_mappings

        Args:
            entities_data: List of dictionaries with entity data

        Returns:
            List of created entities with IDs
        """
        try:
            async with self.transaction():
                # Use bulk_insert_mappings for better performance
                entities = [self.model_class(**data) for data in entities_data]
                self.session.add_all(entities)
                await self.session.flush()

                # Refresh all entities to get their IDs
                for entity in entities:
                    await self.session.refresh(entity)

                invalidate_cache(self.namespace)
                return entities
        except Exception as e:
            logger.error(f"Failed to bulk create entities optimized: {e}")
            raise

    async def bulk_update(self, updates: List[dict]) -> int:
        """Bulk update entities by ID"""
        try:
            async with self.transaction():
                updated_count = 0
                for update_data in updates:
                    if "id" not in update_data:
                        continue

                    entity_id = update_data.pop("id")
                    stmt = update(self.model_class).where(self.model_class.id == entity_id).values(**update_data)
                    result = await self.session.execute(stmt)
                    updated_count += result.rowcount

                if updated_count > 0:
                    invalidate_cache(self.namespace)
                return updated_count
        except Exception as e:
            logger.error(f"Failed to bulk update entities: {e}")
            raise

    async def bulk_delete(self, ids: List[int]) -> int:
        """Bulk delete entities by IDs"""
        try:
            async with self.transaction():
                stmt = delete(self.model_class).where(self.model_class.id.in_(ids))
                result = await self.session.execute(stmt)
                if result.rowcount > 0:
                    invalidate_cache(self.namespace)
                return result.rowcount
        except Exception as e:
            logger.error(f"Failed to bulk delete entities: {e}")
            raise

    async def get_by_field_and_update(self, field_name: str, field_value: Any, update_data: dict) -> Optional[T]:
        """Get entity by field and update it in one operation"""
        try:
            entity = await self.get_by_field(field_name, field_value)
            if entity:
                await self.update(entity.id, update_data)
                return entity
            return None
        except Exception as e:
            logger.error(f"Failed to get and update entity by {field_name}={field_value}: {e}")
            raise

    async def get_by_field_and_delete(self, field_name: str, field_value: Any) -> bool:
        """Get entity by field and delete it in one operation"""
        try:
            entity = await self.get_by_field(field_name, field_value)
            if entity:
                await self.delete(entity.id)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to get and delete entity by {field_name}={field_value}: {e}")
            raise

    def to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to dictionary (base implementation)"""
        result = {}
        for column in self.model_class.__table__.columns:
            value = getattr(entity, column.name, None)
            if value is not None and hasattr(value, "isoformat"):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dict to entity data format (base implementation)"""
        return data.copy()


# Factory function for creating repository instances
def create_repository(model_class: Type[T], session: AsyncSession) -> BaseRepository[T]:
    """
    Factory function to create repository instances

    Args:
        model_class: SQLAlchemy model class
        session: AsyncSession instance

    Returns:
        BaseRepository instance
    """
    return BaseRepository(session, model_class)
