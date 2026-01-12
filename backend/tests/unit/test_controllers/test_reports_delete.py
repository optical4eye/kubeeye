# Unit tests for reports delete functionality
import pytest
from unittest.mock import patch, AsyncMock

from api.reports import delete_report


class TestReportsDelete:
    """Test cases for delete_report functionality"""

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_success(self, mock_validate_id, mock_get_db, mock_delete):
        """Test successful deletion of report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock db session
        mock_db = AsyncMock()

        # Mock get_db as an async generator that yields the mock db
        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock delete
        mock_delete.return_value = True

        result = await delete_report("report-123")

        assert result["message"] == "Report validated-report-123 deleted"
        mock_validate_id.assert_called_once_with("report-123")
        mock_delete.assert_called_once_with("validated-report-123")

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_not_found(self, mock_validate_id, mock_get_db, mock_delete):
        """Test deletion of non-existent report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock db session
        mock_db = AsyncMock()

        # Mock get_db as an async generator that yields the mock db
        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock delete not found
        mock_delete.return_value = False

        with pytest.raises(Exception) as exc_info:
            await delete_report("report-123")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_with_db_error(self, mock_validate_id, mock_get_db, mock_delete):
        """Test delete_report with database error"""
        mock_validate_id.return_value = "validated-report-123"

        mock_db = AsyncMock()

        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock database error
        mock_delete.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            await delete_report("report-123")

        assert exc_info.value.status_code == 500
        assert "Database connection failed" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_validation_error(self, mock_validate_id):
        """Test delete_report with validation error"""
        mock_validate_id.side_effect = ValueError("Invalid ID")

        with pytest.raises(Exception) as exc_info:
            await delete_report("invalid-id")

        assert "Invalid ID" in str(exc_info.value)
