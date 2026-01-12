#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for DatabaseMonitor
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from db.database_monitor import DatabaseMonitor


class TestDatabaseMonitor:
    """Test cases for DatabaseMonitor"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock DatabaseConnectionManager"""
        manager = Mock()
        manager.get_engine = Mock()
        return manager

    @pytest.fixture
    def monitor(self, mock_connection_manager):
        """Create DatabaseMonitor instance"""
        return DatabaseMonitor(mock_connection_manager, check_interval=1, failure_threshold=2)

    def test_init(self, monitor, mock_connection_manager):
        """Test DatabaseMonitor initialization"""
        assert monitor.connection_manager == mock_connection_manager
        assert monitor.check_interval == 1
        assert monitor.failure_threshold == 2
        assert monitor._running is False
        assert monitor._failure_count == 0
        assert monitor._last_check is None
        assert monitor._last_success is None
        assert monitor._last_failure is None
        assert monitor._monitor_task is None
        assert "total_checks" in monitor.stats
        assert "successful_checks" in monitor.stats
        assert "failed_checks" in monitor.stats
        assert "recovery_attempts" in monitor.stats
        assert "successful_recoveries" in monitor.stats
        assert "uptime_percentage" in monitor.stats

    @pytest.mark.asyncio
    async def test_perform_connection_test_success(self, monitor):
        """Test _perform_connection_test success"""
        mock_conn = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result

        monitor.connection_manager.get_engine.return_value.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        monitor.connection_manager.get_engine.return_value.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        success, message, data = await monitor._perform_connection_test()

        assert success is True
        assert message == ""
        assert data == {}

    @pytest.mark.asyncio
    async def test_perform_connection_test_failure(self, monitor):
        """Test _perform_connection_test failure"""
        mock_conn = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_conn.execute.return_value = mock_result

        monitor.connection_manager.get_engine.return_value.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        monitor.connection_manager.get_engine.return_value.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        success, message, data = await monitor._perform_connection_test()

        assert success is False
        assert "Test query failed" in message
        assert data["test_value"] == 0

    def test_handle_successful_check(self, monitor):
        """Test _handle_successful_check"""
        monitor._failure_count = 2
        monitor.stats["successful_checks"] = 5

        monitor._handle_successful_check()

        assert monitor.stats["successful_checks"] == 6
        assert isinstance(monitor._last_success, datetime)
        assert monitor._failure_count == 0

    def test_handle_failed_check(self, monitor):
        """Test _handle_failed_check"""
        monitor._failure_count = 1
        monitor.stats["failed_checks"] = 3

        monitor._handle_failed_check("Test error")

        assert monitor.stats["failed_checks"] == 4
        assert isinstance(monitor._last_failure, datetime)
        assert monitor._failure_count == 2

    def test_create_success_result(self, monitor):
        """Test _create_success_result"""
        monitor._last_success = datetime(2023, 1, 1, 12, 0, 0)

        result = monitor._create_success_result()

        assert result["status"] == "success"
        assert result["timestamp"] == "2023-01-01T12:00:00"

    def test_create_failure_result(self, monitor):
        """Test _create_failure_result"""
        monitor._last_failure = datetime(2023, 1, 1, 12, 0, 0)
        monitor._failure_count = 3

        result = monitor._create_failure_result("Test error", "Detailed error")

        assert result["status"] == "error"
        assert result["timestamp"] == "2023-01-01T12:00:00"
        assert result["failure_count"] == 3
        assert result["error"] == "Detailed error"
        assert result["message"] == "Test error"

    @patch.object(DatabaseMonitor, "_perform_connection_test")
    @pytest.mark.asyncio
    async def test_check_connection_async_success(self, mock_perform_test, monitor):
        """Test _check_connection_async success"""
        mock_perform_test.return_value = (True, "", {})

        result = await monitor._check_connection_async()

        assert result["status"] == "success"
        assert monitor._failure_count == 0

    @patch.object(DatabaseMonitor, "_perform_connection_test")
    @pytest.mark.asyncio
    async def test_check_connection_async_failure(self, mock_perform_test, monitor):
        """Test _check_connection_async failure"""
        mock_perform_test.return_value = (False, "Test failed", {"test_value": 0})

        result = await monitor._check_connection_async()

        assert result["status"] == "failed"  # No error parameter passed, so status is "failed"
        assert result["message"] == "Test failed"
        assert monitor._failure_count == 1

    @patch.object(DatabaseMonitor, "_check_connection_async")
    @pytest.mark.asyncio
    async def test_attempt_recovery_async_success(self, mock_check_connection, monitor):
        """Test _attempt_recovery_async success"""
        monitor.connection_manager.close_database = AsyncMock()
        monitor.connection_manager._ensure_async_connection = AsyncMock()
        mock_check_connection.return_value = {"status": "success"}

        success = await monitor._attempt_recovery_async()

        assert success is True
        assert monitor.stats["recovery_attempts"] == 1
        assert monitor.stats["successful_recoveries"] == 1
        assert monitor._failure_count == 0

    @patch.object(DatabaseMonitor, "_check_connection_async")
    @pytest.mark.asyncio
    async def test_attempt_recovery_async_failure(self, mock_check_connection, monitor):
        """Test _attempt_recovery_async failure"""
        monitor.connection_manager.close_database = AsyncMock()
        monitor.connection_manager._ensure_async_connection = AsyncMock()
        mock_check_connection.return_value = {"status": "error"}

        success = await monitor._attempt_recovery_async()

        assert success is False
        assert monitor.stats["recovery_attempts"] == 1
        assert monitor.stats["successful_recoveries"] == 0

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """Test start_monitoring"""
        with patch.object(monitor, "_monitor_loop", new_callable=AsyncMock) as mock_loop:
            mock_task = AsyncMock()
            mock_task.done.return_value = False
            with patch("asyncio.create_task", return_value=mock_task) as mock_create_task:

                await monitor.start_monitoring()

                assert monitor._running is True
                assert monitor._monitor_task == mock_task
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, monitor):
        """Test start_monitoring when already running"""
        monitor._running = True

        await monitor.start_monitoring()

        # Should not create new task
        assert monitor._running is True

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """Test stop_monitoring"""

        # Create a real async task that can be cancelled and awaited
        async def dummy_task():
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass

        mock_task = asyncio.create_task(dummy_task())

        monitor._running = True
        monitor._monitor_task = mock_task

        await monitor.stop_monitoring()

        assert monitor._running is False
        assert monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, monitor):
        """Test stop_monitoring when not running"""
        monitor._running = False

        await monitor.stop_monitoring()

        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_force_recovery(self, monitor):
        """Test force_recovery"""
        with patch.object(monitor, "_attempt_recovery_async", new_callable=AsyncMock) as mock_attempt:
            mock_attempt.return_value = True

            result = await monitor.force_recovery()

            assert result is True
            mock_attempt.assert_called_once()

    def test_get_status(self, monitor):
        """Test get_status"""
        monitor._running = True
        monitor._failure_count = 2
        monitor._last_check = datetime(2023, 1, 1, 12, 0, 0)
        monitor._last_success = datetime(2023, 1, 1, 11, 0, 0)
        monitor._last_failure = datetime(2023, 1, 1, 10, 0, 0)
        monitor.stats["total_checks"] = 10
        monitor.stats["successful_checks"] = 8
        monitor.stats["uptime_percentage"] = 80.0  # Set directly since calculation happens in monitor loop

        status = monitor.get_status()

        assert status["running"] is True
        assert status["check_interval"] == 1
        assert status["failure_threshold"] == 2
        assert status["failure_count"] == 2
        assert status["last_check"] == "2023-01-01T12:00:00"
        assert status["last_success"] == "2023-01-01T11:00:00"
        assert status["last_failure"] == "2023-01-01T10:00:00"
        assert status["stats"]["total_checks"] == 10
        assert status["stats"]["successful_checks"] == 8
        assert status["stats"]["uptime_percentage"] == 80.0
