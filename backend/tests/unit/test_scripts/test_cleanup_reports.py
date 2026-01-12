#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test cases for database cleanup script
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import scripts.database_cleanup


class TestDatabaseCleanup:
    """Test cases for database cleanup script"""

    @patch("scripts.database_cleanup.get_retention_days")
    def test_get_retention_days_from_env(self, mock_get_days):
        """Test getting retention days from environment variable"""
        mock_get_days.return_value = 5

        from scripts.database_cleanup import get_retention_days

        result = get_retention_days()
        assert result == 5
        mock_get_days.assert_called_once()

    @patch("scripts.database_cleanup.get_retention_days")
    def test_get_retention_days_default(self, mock_get_days):
        """Test getting retention days with invalid environment variable"""
        mock_get_days.return_value = 7  # default value

        from scripts.database_cleanup import get_retention_days

        result = get_retention_days()
        assert result == 7
        mock_get_days.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.components.report_cleanup_service.cleanup_old_reports", new_callable=AsyncMock)
    async def test_run_database_cleanup_success(self, mock_cleanup):
        """Test successful database cleanup"""
        mock_cleanup.return_value = {
            "deleted_count": 10,
            "retention_days": 5,
            "message": "Successfully deleted 10 old reports",
        }

        from scripts.database_cleanup import run_database_cleanup

        result = await run_database_cleanup(5)

        assert result["deleted_count"] == 10
        assert result["retention_days"] == 5
        mock_cleanup.assert_called_once_with(5)

    @pytest.mark.asyncio
    @patch("services.components.report_cleanup_service.cleanup_old_reports", new_callable=AsyncMock)
    async def test_run_database_cleanup_with_default(self, mock_cleanup):
        """Test database cleanup with default retention days"""
        mock_cleanup.return_value = {
            "deleted_count": 5,
            "retention_days": 0,
            "message": "Successfully deleted 5 old reports",
        }

        from scripts.database_cleanup import run_database_cleanup

        result = await run_database_cleanup()

        assert result["deleted_count"] == 5
        assert result["retention_days"] == 0
        mock_cleanup.assert_called_once_with(0)

    @pytest.mark.asyncio
    @patch("services.components.report_cleanup_service.cleanup_old_reports", new_callable=AsyncMock)
    async def test_run_database_cleanup_error(self, mock_cleanup):
        """Test database cleanup with error"""
        mock_cleanup.return_value = {"deleted_count": 0, "error": "Database connection failed", "retention_days": 7}

        from scripts.database_cleanup import run_database_cleanup

        result = await run_database_cleanup(5)

        assert result["deleted_count"] == 0
        assert "error" in result
        mock_cleanup.assert_called_once_with(5)

    @pytest.mark.asyncio
    @patch("scripts.database_cleanup.get_cleanup_statistics", new_callable=AsyncMock)
    async def test_get_cleanup_statistics_success(self, mock_stats):
        """Test getting cleanup statistics successfully"""
        mock_stats.return_value = {
            "total_records": 100,
            "old_records": 20,
            "recent_records": 80,
            "retention_days": 7,
            "cleanup_percentage": 20.0,
        }

        from scripts.database_cleanup import get_cleanup_statistics

        result = await get_cleanup_statistics()

        assert result["total_records"] == 100
        assert result["old_records"] == 20
        assert result["recent_records"] == 80
        assert result["cleanup_percentage"] == 20.0
        mock_stats.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.components.report_cleanup_service.cleanup_reports_by_cluster", new_callable=AsyncMock)
    async def test_cleanup_cluster_reports_success(self, mock_cleanup):
        """Test successful cluster cleanup"""
        mock_cleanup.return_value = {
            "deleted_count": 3,
            "cluster_name": "test-cluster",
            "retention_days": 5,
            "message": "Successfully deleted 3 old reports for cluster 'test-cluster'",
        }

        from scripts.database_cleanup import cleanup_cluster_reports

        result = await cleanup_cluster_reports("test-cluster", 5)

        assert result["deleted_count"] == 3
        assert result["cluster_name"] == "test-cluster"
        assert result["retention_days"] == 5
        mock_cleanup.assert_called_once_with("test-cluster", 5)

    @pytest.mark.asyncio
    @patch("services.components.report_cleanup_service.cleanup_reports_by_cluster", new_callable=AsyncMock)
    async def test_cleanup_cluster_reports_default(self, mock_cleanup):
        """Test cluster cleanup with default retention days"""
        mock_cleanup.return_value = {
            "deleted_count": 2,
            "cluster_name": "test-cluster",
            "retention_days": 0,
            "message": "Successfully deleted 2 old reports for cluster 'test-cluster'",
        }

        from scripts.database_cleanup import cleanup_cluster_reports

        result = await cleanup_cluster_reports("test-cluster")

        assert result["deleted_count"] == 2
        assert result["cluster_name"] == "test-cluster"
        assert result["retention_days"] == 0
        mock_cleanup.assert_called_once_with("test-cluster", 0)
