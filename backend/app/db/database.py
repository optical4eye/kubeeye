#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database connection and session management - Async Only
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .database_connection_manager import DatabaseConnectionManager, Base, get_database_url
from .database_monitor import DatabaseMonitor
from .database_transaction_manager import DatabaseTransactionManager

from core.logging import get_logger

logger = get_logger(__name__)


# Класс для управления базой данных
class DatabaseManager:
    """Manager for async database connections and sessions"""

    def __init__(self):
        self.connection_manager = DatabaseConnectionManager()
        self.monitor = DatabaseMonitor(self.connection_manager)

    async def get_db(self):
        """Async dependency function to get database session"""
        async for session in self.connection_manager.get_db():
            yield session

    async def init_database(self):
        """Initialize async database tables with retry mechanism"""
        await self.connection_manager.init_database()

    async def drop_database(self):
        """Drop all database tables (for testing/cleanup)"""
        await self.connection_manager.drop_database()

    def get_engine(self):
        """Get SQLAlchemy async engine instance"""
        return self.connection_manager.get_engine()

    def get_session_local(self):
        """Get AsyncSessionLocal factory"""
        return self.connection_manager.get_session_local()

    async def health_check(self):
        """Check async database health"""
        return await self.connection_manager.health_check()

    async def get_pool_stats(self):
        """Get detailed pool statistics"""
        return await self.connection_manager.get_pool_stats()

    async def close_database(self):
        """Close all async database connections"""
        await self.connection_manager.close_database()

    def get_monitor(self):
        """Get database monitor"""
        return self.monitor


# Глобальный экземпляр менеджера базы данных
_db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function to get database session.
    Use in FastAPI endpoints with `Depends(get_db)`

    Yields:
        Async database session
    """
    async for session in _db_manager.get_db():
        yield session


async def init_database():
    """
    Initialize async database tables with retry mechanism
    """
    await _db_manager.init_database()


async def drop_database():
    """
    Drop all database tables (for testing/cleanup)
    """
    await _db_manager.drop_database()


def get_engine():
    """
    Get SQLAlchemy async engine instance
    """
    return _db_manager.get_engine()


def get_session_local():
    """
    Get AsyncSessionLocal factory
    """
    return _db_manager.get_session_local()


async def health_check():
    """
    Check async database health
    """
    return await _db_manager.health_check()


async def get_pool_stats():
    """
    Get detailed pool statistics
    """
    return await _db_manager.get_pool_stats()


async def close_database():
    """
    Close all async database connections
    """
    await _db_manager.close_database()


# Backward compatibility aliases
AsyncConnectionMonitor = DatabaseMonitor
AsyncTransactionManager = DatabaseTransactionManager


def get_async_monitor() -> DatabaseMonitor:
    """Get async monitor instance from database manager"""
    return _db_manager.get_monitor()


# Функции для обратной совместимости
async def start_connection_monitoring():
    """Start async connection monitoring"""
    monitor = _db_manager.get_monitor()
    await monitor.start_monitoring()


async def stop_connection_monitoring():
    """Stop async connection monitoring"""
    monitor = _db_manager.get_monitor()
    await monitor.stop_monitoring()


async def get_connection_health() -> dict:
    """Get async connection health"""
    monitor = _db_manager.get_monitor()
    check_result = await monitor._check_connection_async()

    # Add pool info if available
    pool_info = {}
    engine = _db_manager.get_engine()
    if engine and hasattr(engine.pool, "size"):
        pool_info = {
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
        }

    return {
        "status": check_result["status"],
        "message": check_result.get("message", ""),
        "timestamp": check_result["timestamp"],
        "connection_type": "async",
        "pool_info": pool_info,
        "monitor_stats": monitor.get_status(),
    }


async def force_connection_recovery() -> bool:
    """Force async connection recovery"""
    monitor = _db_manager.get_monitor()
    return await monitor.force_recovery()


# Экспортируем основные компоненты
__all__ = [
    "Base",
    "DatabaseManager",
    "_db_manager",
    "get_db",
    "init_database",
    "drop_database",
    "get_engine",
    "get_session_local",
    "health_check",
    "get_pool_stats",
    "close_database",
    "DatabaseConnectionManager",
    "DatabaseMonitor",
    "DatabaseTransactionManager",
    "AsyncTransactionManager",
    "AsyncConnectionMonitor",
    "get_async_monitor",
    "start_connection_monitoring",
    "stop_connection_monitoring",
    "get_connection_health",
    "force_connection_recovery",
    "get_database_url",
]
