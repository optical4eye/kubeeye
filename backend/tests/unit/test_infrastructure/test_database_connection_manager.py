#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for DatabaseConnectionManager
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import text

from db.database_connection_manager import (
    DatabaseConnectionManager,
    AsyncDatabaseContextManager,
    get_database_url,
    ASYNC_DATABASE_URL,
    DATABASE_URL,
    Base,
)


class TestDatabaseConnectionManager:
    """Test cases for DatabaseConnectionManager"""

    @pytest.fixture
    def db_manager(self):
        """Create DatabaseConnectionManager instance"""
        return DatabaseConnectionManager()

    def test_init(self, db_manager):
        """Test DatabaseConnectionManager initialization"""
        assert db_manager._async_engine is None
        assert db_manager._async_session_factory is None
        assert db_manager._pool_stats == {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "failed_connections": 0,
        }

    def test_calculate_optimal_pool_size(self, db_manager):
        """Test _calculate_optimal_pool_size"""
        pool_size = db_manager._calculate_optimal_pool_size()
        assert pool_size > 0
        assert pool_size <= 20  # Maximum limit

    @patch("db.database_connection_manager.os.cpu_count")
    def test_calculate_optimal_pool_size_with_cpu_count(self, mock_cpu_count, db_manager):
        """Test _calculate_optimal_pool_size with specific CPU count"""
        mock_cpu_count.return_value = 4
        pool_size = db_manager._calculate_optimal_pool_size()
        # Formula: (CPU cores * 2) + 1 = (4 * 2) + 1 = 9
        assert pool_size == 9

    @patch("db.database_connection_manager.os.cpu_count")
    def test_calculate_optimal_pool_size_max_limit(self, mock_cpu_count, db_manager):
        """Test _calculate_optimal_pool_size respects maximum limit"""
        mock_cpu_count.return_value = 20
        pool_size = db_manager._calculate_optimal_pool_size()
        # Should be capped at 20
        assert pool_size == 20

    @patch("db.database_connection_manager.create_async_engine")
    @patch("db.database_connection_manager.async_sessionmaker")
    @pytest.mark.asyncio
    async def test_ensure_async_connection(self, mock_sessionmaker, mock_create_engine, db_manager):
        """Test _ensure_async_connection"""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_session = Mock()
        mock_sessionmaker.return_value = mock_session

        result = await db_manager._ensure_async_connection()

        assert result is True
        assert db_manager._async_engine == mock_engine
        assert db_manager._async_session_factory == mock_session
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()

    @patch("db.database_connection_manager.create_async_engine")
    @patch("db.database_connection_manager.async_sessionmaker")
    @pytest.mark.asyncio
    async def test_ensure_async_connection_already_initialized(self, mock_sessionmaker, mock_create_engine, db_manager):
        """Test _ensure_async_connection when already initialized"""
        db_manager._async_engine = Mock()
        db_manager._async_session_factory = Mock()

        result = await db_manager._ensure_async_connection()

        assert result is True
        mock_create_engine.assert_not_called()
        mock_sessionmaker.assert_not_called()

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_get_db(self, mock_ensure_connection, db_manager):
        """Test get_db dependency function"""
        mock_session = Mock()
        db_manager._async_session_factory = Mock(return_value=mock_session)

        async for session in db_manager.get_db():
            assert session == mock_session
            break

        mock_ensure_connection.assert_called_once()

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_init_database(self, mock_ensure_connection, db_manager):
        """Test init_database"""
        mock_conn = AsyncMock()
        db_manager._async_engine = Mock()
        db_manager._async_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        db_manager._async_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        await db_manager.init_database()

        mock_ensure_connection.assert_called_once()
        # Check that run_sync was called with Base.metadata.create_all
        mock_conn.run_sync.assert_called_once()

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_drop_database(self, mock_ensure_connection, db_manager):
        """Test drop_database"""
        mock_conn = AsyncMock()
        db_manager._async_engine = Mock()
        db_manager._async_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        db_manager._async_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        await db_manager.drop_database()

        mock_ensure_connection.assert_called_once()
        # Check that run_sync was called with Base.metadata.drop_all
        mock_conn.run_sync.assert_called_once()

    def test_get_engine_not_initialized(self, db_manager):
        """Test get_engine when not initialized"""
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db_manager.get_engine()

    def test_get_session_local_not_initialized(self, db_manager):
        """Test get_session_local when not initialized"""
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db_manager.get_session_local()

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_execute_health_query_success(self, mock_ensure_connection, db_manager):
        """Test _execute_health_query success"""
        db_manager._async_session_factory = Mock()
        mock_session = AsyncMock()
        db_manager._async_session_factory.return_value = mock_session

        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        success, message = await db_manager._execute_health_query()

        assert success is True
        assert message == ""
        # Check that execute was called with some text object
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert "SELECT 1 as test" in str(call_args)

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_execute_health_query_failure(self, mock_ensure_connection, db_manager):
        """Test _execute_health_query failure"""
        db_manager._async_session_factory = Mock()
        mock_session = AsyncMock()
        db_manager._async_session_factory.return_value = mock_session

        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        success, message = await db_manager._execute_health_query()

        assert success is False
        assert "unexpected result 0" in message

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_ensure_connection, db_manager):
        """Test health_check success"""
        with patch.object(db_manager, "_execute_health_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = (True, "")

            result = await db_manager.health_check()

            assert result["status"] == "healthy"
            assert result["connection_type"] == "async"

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_ensure_connection, db_manager):
        """Test health_check failure"""
        with patch.object(db_manager, "_execute_health_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = (False, "Test failed")

            result = await db_manager.health_check()

            assert result["status"] == "error"
            assert "Test failed" in result["message"]

    @pytest.mark.asyncio
    async def test_close_database(self, db_manager):
        """Test close_database"""
        mock_engine = AsyncMock()
        db_manager._async_engine = mock_engine
        db_manager._async_session_factory = Mock()

        await db_manager.close_database()

        mock_engine.dispose.assert_called_once()
        assert db_manager._async_engine is None
        assert db_manager._async_session_factory is None

    @pytest.mark.asyncio
    async def test_close_database_none_engine(self, db_manager):
        """Test close_database with None engine"""
        db_manager._async_engine = None

        await db_manager.close_database()

        # Should not raise any exception

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_get_pool_stats(self, mock_ensure_connection, db_manager):
        """Test get_pool_stats"""
        mock_engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_engine.pool = mock_pool
        db_manager._async_engine = mock_engine

        # Set some stats
        db_manager._pool_stats = {
            "total_connections": 100,
            "active_connections": 3,
            "idle_connections": 5,
            "failed_connections": 2,
        }

        stats = await db_manager.get_pool_stats()

        assert stats["pool_size"] == 10
        assert stats["checked_in"] == 5
        assert stats["checked_out"] == 3
        assert stats["overflow"] == 2
        assert stats["total_connections"] == 100
        assert stats["active_connections"] == 3
        assert stats["idle_connections"] == 5
        assert stats["failed_connections"] == 2

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_get_pool_stats_no_engine(self, mock_ensure_connection, db_manager):
        """Test get_pool_stats when engine is None"""
        db_manager._async_engine = None

        stats = await db_manager.get_pool_stats()

        assert stats == {}

    @patch.object(DatabaseConnectionManager, "_ensure_async_connection")
    @pytest.mark.asyncio
    async def test_get_db_tracks_stats(self, mock_ensure_connection, db_manager):
        """Test get_db tracks connection statistics"""
        mock_session = AsyncMock()
        db_manager._async_session_factory = Mock(return_value=mock_session)

        initial_total = db_manager._pool_stats["total_connections"]
        initial_active = db_manager._pool_stats["active_connections"]

        # Use the connection
        async for session in db_manager.get_db():
            assert session == mock_session
            # Check that stats were incremented
            assert db_manager._pool_stats["total_connections"] == initial_total + 1
            assert db_manager._pool_stats["active_connections"] == initial_active + 1
            # Don't break here - let the context manager complete properly

        # After session close, active should decrease and idle should increase
        # The stats are updated in the finally block after the session is closed
        assert db_manager._pool_stats["active_connections"] == initial_active
        assert db_manager._pool_stats["idle_connections"] == 1


class TestAsyncDatabaseContextManager:
    """Test cases for AsyncDatabaseContextManager"""

    @pytest.fixture
    def manager(self):
        """Create mock DatabaseConnectionManager"""
        return Mock()

    @pytest.fixture
    def context_manager(self, manager):
        """Create AsyncDatabaseContextManager instance"""
        return AsyncDatabaseContextManager(manager)

    @pytest.mark.asyncio
    async def test_aenter_success(self, context_manager, manager):
        """Test __aenter__ success"""
        mock_session = Mock()
        manager._ensure_async_connection = AsyncMock()
        manager._async_session_factory = Mock(return_value=mock_session)

        session = await context_manager.__aenter__()

        assert session == mock_session
        manager._ensure_async_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_success(self, context_manager):
        """Test __aexit__ success"""
        mock_session = AsyncMock()
        context_manager.session = mock_session

        await context_manager.__aexit__(None, None, None)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_with_exception(self, context_manager):
        """Test __aexit__ with exception"""
        mock_session = AsyncMock()
        context_manager.session = mock_session

        await context_manager.__aexit__(Exception, Exception("test"), None)

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_no_session(self, context_manager):
        """Test __aexit__ with no session"""
        context_manager.session = None

        await context_manager.__aexit__(None, None, None)

        # Should not raise any exception


class TestGlobalFunctions:
    """Test cases for global functions"""

    @patch(
        "db.database_connection_manager.ASYNC_DATABASE_URL",
        "postgresql+asyncpg://testuser:testpass@test-host:5433/testdb",
    )
    def test_get_database_url(self):
        """Test get_database_url"""
        url = get_database_url()
        assert url == "postgresql+asyncpg://testuser:testpass@test-host:5433/testdb"

    def test_async_database_url(self):
        """Test ASYNC_DATABASE_URL construction"""
        # Test that ASYNC_DATABASE_URL is constructed from DATABASE_URL
        expected = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        assert ASYNC_DATABASE_URL == expected
