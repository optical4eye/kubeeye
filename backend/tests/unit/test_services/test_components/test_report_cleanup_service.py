#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for report cleanup service component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta
from services.components.report_cleanup_service import (
    ReportCleanupService,
    get_report_cleanup_service,
    cleanup_old_reports,
    get_cleanup_stats,
    cleanup_reports_by_cluster,
)


class TestReportCleanupService:
    """Test cases for report cleanup service"""

    @pytest.fixture
    def cleanup_service(self):
        """Create ReportCleanupService instance"""
        return ReportCleanupService()

    @patch("services.components.report_cleanup_service.settings")
    def test_init_with_env_var(self, mock_settings):
        """Test initialization with environment variable"""
        mock_settings.kubeeye_report_retention_days = 14
        service = ReportCleanupService()
        assert service.retention_days == 14

    @patch("services.components.report_cleanup_service.settings")
    def test_init_default(self, mock_settings):
        """Test initialization with default value"""
        mock_settings.kubeeye_report_retention_days = 7
        service = ReportCleanupService()
        assert service.retention_days == 7

    @patch("services.components.report_cleanup_service.settings")
    def test_init_invalid_env_var(self, mock_settings):
        """Test initialization with invalid environment variable"""
        mock_settings.kubeeye_report_retention_days = "invalid"
        service = ReportCleanupService()
        assert service.retention_days == 0  # max(0, int("invalid")) -> 0

    @patch("services.components.report_cleanup_service.settings")
    def test_init_negative_env_var(self, mock_settings):
        """Test initialization with negative environment variable"""
        mock_settings.kubeeye_report_retention_days = -5
        service = ReportCleanupService()
        assert service.retention_days == 0

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_cleanup_old_reports_no_records(self, mock_get_db, cleanup_service):
        """Test cleanup when no old records exist"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        # Mock count query
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await cleanup_service.cleanup_old_reports(retention_days=7)

        assert result["deleted_count"] == 0
        assert "No old reports found" in result["message"]
        assert result["retention_days"] == 7

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_cleanup_old_reports_success(self, mock_get_db, cleanup_service):
        """Test successful cleanup of old reports"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        # Mock count query
        count_result = Mock()
        count_result.scalar.return_value = 5
        # Mock delete query
        delete_result = Mock()
        delete_result.rowcount = 5

        mock_db.execute.side_effect = [count_result, delete_result]

        result = await cleanup_service.cleanup_old_reports(retention_days=10)

        assert result["deleted_count"] == 5
        assert "Successfully deleted 5 old reports" in result["message"]
        assert result["retention_days"] == 10

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_cleanup_old_reports_negative_retention(self, mock_get_db, cleanup_service):
        """Test cleanup with negative retention days"""
        result = await cleanup_service.cleanup_old_reports(retention_days=-1)

        assert result["deleted_count"] == 0
        assert "Invalid retention days" in result["error"]
        mock_get_db.assert_not_called()

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_cleanup_old_reports_db_error(self, mock_get_db, cleanup_service):
        """Test cleanup when database error occurs"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        mock_db.execute.side_effect = Exception("Database connection failed")

        result = await cleanup_service.cleanup_old_reports()

        assert result["deleted_count"] == 0
        assert "Failed to cleanup old reports" in result["error"]

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_get_cleanup_stats_success(self, mock_get_db, cleanup_service):
        """Test successful retrieval of cleanup statistics"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        # Mock total count
        total_result = Mock()
        total_result.scalar.return_value = 100
        # Mock old count
        old_result = Mock()
        old_result.scalar.return_value = 20

        mock_db.execute.side_effect = [total_result, old_result]

        result = await cleanup_service.get_cleanup_stats()

        assert result["total_records"] == 100
        assert result["old_records"] == 20
        assert result["recent_records"] == 80
        assert result["retention_days"] == cleanup_service.retention_days
        assert result["cleanup_percentage"] == 20.0

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_get_cleanup_stats_db_error(self, mock_get_db, cleanup_service):
        """Test cleanup stats when database error occurs"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        mock_db.execute.side_effect = Exception("Database error")

        result = await cleanup_service.get_cleanup_stats()

        assert "error" in result
        assert "Failed to get cleanup stats" in result["error"]

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_delete_reports_by_cluster_no_records(self, mock_get_db, cleanup_service):
        """Test cluster cleanup when no old records exist"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        # Mock count query
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await cleanup_service.delete_reports_by_cluster("test-cluster", retention_days=5)

        assert result["deleted_count"] == 0
        assert result["cluster_name"] == "test-cluster"
        assert "No old reports found" in result["message"]

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_delete_reports_by_cluster_success(self, mock_get_db, cleanup_service):
        """Test successful cluster cleanup"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        # Mock count query
        count_result = Mock()
        count_result.scalar.return_value = 3
        # Mock delete query
        delete_result = Mock()
        delete_result.rowcount = 3

        mock_db.execute.side_effect = [count_result, delete_result]

        result = await cleanup_service.delete_reports_by_cluster("prod-cluster")

        assert result["deleted_count"] == 3
        assert result["cluster_name"] == "prod-cluster"
        assert "Successfully deleted 3 old reports" in result["message"]

    @patch("db.database_context.get_db")
    @pytest.mark.asyncio
    async def test_delete_reports_by_cluster_db_error(self, mock_get_db, cleanup_service):
        """Test cluster cleanup when database error occurs"""
        mock_db = AsyncMock()

        # Mock async generator
        async def mock_async_gen():
            yield mock_db

        mock_get_db.return_value = mock_async_gen()

        mock_db.execute.side_effect = Exception("Cluster cleanup failed")

        result = await cleanup_service.delete_reports_by_cluster("test-cluster")

        assert result["deleted_count"] == 0
        assert result["cluster_name"] == "test-cluster"
        assert "Failed to cleanup reports for cluster" in result["error"]

    def test_get_report_cleanup_service_singleton(self):
        """Test singleton pattern for cleanup service"""
        service1 = get_report_cleanup_service()
        service2 = get_report_cleanup_service()

        assert service1 is service2
        assert isinstance(service1, ReportCleanupService)

    @patch("services.components.report_cleanup_service.get_report_cleanup_service")
    @pytest.mark.asyncio
    async def test_cleanup_old_reports_function(self, mock_get_service):
        """Test cleanup_old_reports convenience function"""
        mock_service = Mock()
        mock_service.cleanup_old_reports = AsyncMock(return_value={"deleted_count": 10})
        mock_get_service.return_value = mock_service

        result = await cleanup_old_reports(retention_days=15)

        assert result["deleted_count"] == 10
        mock_service.cleanup_old_reports.assert_called_once_with(15)

    @patch("services.components.report_cleanup_service.get_report_cleanup_service")
    @pytest.mark.asyncio
    async def test_get_cleanup_stats_function(self, mock_get_service):
        """Test get_cleanup_stats convenience function"""
        mock_service = Mock()
        mock_service.get_cleanup_stats = AsyncMock(return_value={"total_records": 50})
        mock_get_service.return_value = mock_service

        result = await get_cleanup_stats()

        assert result["total_records"] == 50
        mock_service.get_cleanup_stats.assert_called_once()

    @patch("services.components.report_cleanup_service.get_report_cleanup_service")
    @pytest.mark.asyncio
    async def test_cleanup_reports_by_cluster_function(self, mock_get_service):
        """Test cleanup_reports_by_cluster convenience function"""
        mock_service = Mock()
        mock_service.delete_reports_by_cluster = AsyncMock(return_value={"deleted_count": 5})
        mock_get_service.return_value = mock_service

        result = await cleanup_reports_by_cluster("test-cluster", retention_days=10)

        assert result["deleted_count"] == 5
        mock_service.delete_reports_by_cluster.assert_called_once_with("test-cluster", 10)
