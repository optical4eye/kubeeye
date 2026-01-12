# Unit tests for reports get functionality
import pytest
from unittest.mock import patch

from api.reports import get_report


class TestReportsGet:
    """Test cases for get_report functionality"""

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_success(self, mock_validate_id, mock_load_result):
        """Test successful retrieval of specific report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock report - return a valid report that exists
        mock_load_result.return_value = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        result = await get_report("report-123")

        assert result["result_id"] == "validated-report-123"
        assert result["cluster_name"] == "test-cluster"
        mock_validate_id.assert_called_once_with("report-123")
        mock_load_result.assert_called_once_with("validated-report-123")

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_not_found(self, mock_validate_id, mock_load_result):
        """Test retrieval of non-existent report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock report not found
        mock_load_result.return_value = None

        with pytest.raises(Exception) as exc_info:
            await get_report("report-123")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_with_minimal_data(self, mock_validate_id, mock_load_result):
        """Test get_report with minimal valid data"""
        mock_validate_id.return_value = "validated-report-123"

        # Minimal valid report - must include inspection_results to avoid KeyError
        mock_load_result.return_value = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        result = await get_report("report-123")

        assert result["result_id"] == "validated-report-123"
        assert result["cluster_name"] == "test-cluster"

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_validation_error(self, mock_validate_id):
        """Test get_report with validation error"""
        mock_validate_id.side_effect = ValueError("Invalid ID")

        with pytest.raises(Exception) as exc_info:
            await get_report("invalid-id")

        assert "Invalid ID" in str(exc_info.value)
