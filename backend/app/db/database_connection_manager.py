#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database connection manager - handles async database connections with adaptive pooling
"""

import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from core.config.settings import settings
from core.logging import get_logger

# Import Base from db.models.base to use the same Base instance
from db.models.base import Base

logger = get_logger(__name__)


# Формируем URL подключения к базе данных из переменных окружения
DATABASE_URL = (
    f"postgresql://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

# Формируем асинхронный URL подключения к базе данных из переменных окружения
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


def get_database_url() -> str:
    """Get database URL for connections"""
    return ASYNC_DATABASE_URL


class DatabaseConnectionManager:
    """Manager for async database connections with adaptive pooling"""

    def __init__(self):
        self._async_engine = None
        self._async_session_factory = None
        self._pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "failed_connections": 0,
        }
        self._lock = asyncio.Lock()

    def _calculate_optimal_pool_size(self) -> int:
        """Calculate optimal pool size based on CPU cores and workload"""
        cpu_count = os.cpu_count() or 4

        # Formula: (CPU cores * 2) + 1 for I/O bound workloads
        # Adjusted for async operations
        optimal_size = min((cpu_count * 2) + 1, 20)

        logger.info(f"Calculated optimal pool size: {optimal_size} (CPU cores: {cpu_count})")
        return optimal_size

    async def _ensure_async_connection(self):
        """Ensure async database connection is initialized"""
        if self._async_engine is None or self._async_session_factory is None:
            logger.info("Initializing async database connection...")

            # Calculate optimal pool size
            pool_size = self._calculate_optimal_pool_size()

            # Создаем асинхронный engine с оптимизированным пулом
            try:
                self._async_engine = create_async_engine(
                    ASYNC_DATABASE_URL,
                    echo=settings.sql_debug,
                    pool_size=pool_size,
                    max_overflow=pool_size // 2,
                    pool_recycle=3600,  # Recycle connections after 1 hour
                    pool_pre_ping=True,  # Test connections before use
                    pool_timeout=30,
                    # Добавляем параметры для предотвращения проблем с event loop
                    connect_args={
                        "server_settings": {"application_name": "kubeeye", "jit": "off"},
                        # Добавляем параметры для управления соединениями
                        "command_timeout": 60,
                        "prepared_statement_cache_size": 0,
                    },
                )

                logger.info(f"Created connection pool with size={pool_size}, max_overflow={pool_size // 2}")

                self._async_session_factory = async_sessionmaker(
                    self._async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False,
                )

                logger.info("Async database connection initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize async database connection: {e}")
                raise

        return True

    async def get_db(self):
        """Async dependency function to get database session with connection tracking"""
        # Убеждаемся, что подключение установлено
        await self._ensure_async_connection()

        # Track connection statistics
        async with self._lock:
            self._pool_stats["total_connections"] += 1
            self._pool_stats["active_connections"] += 1

        # Используем асинхронную сессию
        session = self._async_session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            async with self._lock:
                self._pool_stats["failed_connections"] += 1
            raise
        finally:
            await session.close()
            async with self._lock:
                self._pool_stats["active_connections"] -= 1
                self._pool_stats["idle_connections"] += 1

    async def init_database(self):
        """Initialize async database tables with retry mechanism"""
        # Always wait indefinitely for database to become available
        max_retries = float("inf")
        retry_delay = 2  # seconds
        max_delay = 30  # maximum delay between retries

        attempt = 0
        while attempt < max_retries:
            try:
                # Убеждаемся, что подключение установлено
                await self._ensure_async_connection()

                # Создаем таблицы используя асинхронный engine
                async with self._async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("Async database tables created successfully")
                return

            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Failed to initialize async database tables (attempt {attempt}, waiting indefinitely): {e}. Retrying in {retry_delay}s..."
                )

                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)  # exponential backoff with cap

    async def drop_database(self):
        """Drop all database tables (for testing/cleanup)"""
        try:
            # Убеждаемся, что подключение установлено
            await self._ensure_async_connection()

            # Удаляем таблицы используя асинхронный engine
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Async database tables dropped successfully")

        except Exception as e:
            logger.error(f"Failed to drop async database tables: {e}")
            raise

    def get_engine(self):
        """Get SQLAlchemy async engine instance"""
        if self._async_engine is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._async_engine

    def get_session_local(self):
        """Get AsyncSessionLocal factory"""
        if self._async_session_factory is None:
            raise RuntimeError("Database not initialized. Call init_database() first.")
        return self._async_session_factory

    async def _execute_health_query(self) -> tuple[bool, str]:
        """Execute health check query and return result"""
        session = self._async_session_factory()
        try:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()

            if test_value == 1:
                return True, ""
            else:
                return False, f"Async database test failed: unexpected result {test_value}"
        finally:
            await session.close()

    def _create_health_success_response(self) -> dict:
        """Create successful health check response"""
        return {
            "status": "healthy",
            "message": "Async database connection is working",
            "connection_type": "async",
        }

    def _create_health_error_response(self, message: str) -> dict:
        """Create error health check response"""
        return {
            "status": "error",
            "message": message,
            "connection_type": "async",
        }

    async def health_check(self):
        """Check async database health"""
        try:
            await self._ensure_async_connection()

            success, error_message = await self._execute_health_query()

            if success:
                return self._create_health_success_response()
            else:
                return self._create_health_error_response(error_message)

        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return self._create_health_error_response(f"Async health check failed: {e}")

    async def close_database(self):
        """Close all async database connections"""
        if self._async_engine:
            try:
                # Закрываем сам engine - это автоматически закроет все сессии
                await self._async_engine.dispose()
                logger.info("Async database connections closed")
            except Exception as e:
                logger.error(f"Error closing async database connections: {e}")
            finally:
                self._async_engine = None
                self._async_session_factory = None
        else:
            logger.info("Async database engine already None, nothing to close")

    async def get_pool_stats(self) -> dict:
        """Get detailed pool statistics"""
        if not self._async_engine:
            return {}

        pool = self._async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": self._pool_stats["total_connections"],
            "active_connections": self._pool_stats["active_connections"],
            "idle_connections": self._pool_stats["idle_connections"],
            "failed_connections": self._pool_stats["failed_connections"],
        }
