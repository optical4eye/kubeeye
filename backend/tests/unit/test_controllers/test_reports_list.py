# Unit tests for reports list functionality
import pytest
from unittest.mock import patch

from api.reports import get_reports


class TestReportsList:
    """Test cases for get_reports functionality"""

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_success(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test successful retrieval of reports"""
        # Mock validation
        mock_validate_limit.return_value = 100

        # Mock results with pagination metadata
        mock_list_results.return_value = {
            "results": [
                {"result_id": "report1", "cluster_name": "cluster1", "timestamp": "2023-01-01T00:00:00"},
                {"result_id": "report2", "cluster_name": "cluster2", "timestamp": "2023-01-02T00:00:00"},
            ],
            "total": 2,
            "limit": 100,
            "offset": 0,
        }

        result = await get_reports(limit=100)

        assert "reports" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert len(result["reports"]) == 2
        assert result["total"] == 2
        mock_validate_limit.assert_called_once_with(100)
        mock_clear_cache.assert_called_once()
        mock_list_results.assert_called_once_with(limit=100, offset=0, order_by="timestamp DESC")

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_exception(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test retrieval of reports with exception"""
        # Mock validation
        mock_validate_limit.return_value = 100

        # Mock exception
        mock_list_results.side_effect = Exception("List error")

        with pytest.raises(Exception) as exc_info:
            await get_reports(limit=100)

        assert "List error" in str(exc_info.value)
        mock_validate_limit.assert_called_once_with(100)
        mock_clear_cache.assert_called_once()
        mock_list_results.assert_called_once_with(limit=100, offset=0, order_by="timestamp DESC")

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_with_different_limits(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test get_reports with different limit values"""
        # Test with limit 0
        mock_validate_limit.return_value = 0
        mock_list_results.return_value = {
            "results": [],
            "total": 0,
            "limit": 0,
            "offset": 0,
        }

        result = await get_reports(limit=0)
        assert "reports" in result
        mock_list_results.assert_called_with(limit=0, offset=0, order_by="timestamp DESC")

        # Test with large limit
        mock_validate_limit.return_value = 1000
        mock_list_results.return_value = {
            "results": [{"result_id": "report1"}],
            "total": 1,
            "limit": 1000,
            "offset": 0,
        }

        result = await get_reports(limit=1000)
        assert len(result["reports"]) == 1
        assert result["total"] == 1

    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_validation_error(self, mock_validate_limit):
        """Test get_reports with validation error"""
        mock_validate_limit.side_effect = ValueError("Limit must be at least 1")

        with pytest.raises(Exception) as exc_info:
            await get_reports(limit=-1)

        assert "Limit must be at least 1" in str(exc_info.value)
