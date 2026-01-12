# Base test class for controller tests
import pytest
from unittest.mock import Mock, patch


class BaseControllerTest:
    """Base class for controller tests with common fixtures and utilities"""

    @pytest.fixture(autouse=True)
    def setup_method(self, mocker):
        """Setup common mocks for all controller tests"""
        # Mock database session
        self.mock_db_session = mocker.patch("db.database.get_db_session")

        # Mock logger
        self.mock_logger = mocker.patch("core.logging.enhanced_logging.logger")

        # Mock validation functions
        self.mock_validate_task_id = mocker.patch("core.common.validation.validate_task_id")
        self.mock_validate_limit_param = mocker.patch("core.common.validation.validate_limit_param")

        # Set default return values
        self.mock_validate_task_id.return_value = "validated-test-id"
        self.mock_validate_limit_param.return_value = 100

    def mock_load_result(self, return_value=None):
        """Helper to mock load_result function"""
        return patch("infra.results.inspection_result.load_result", return_value=return_value)

    def mock_list_results(self, return_value=None):
        """Helper to mock list_results function"""
        return patch("infra.results.inspection_result.list_results", return_value=return_value)

    def mock_clear_cache(self):
        """Helper to mock clear_metadata_cache function"""
        return patch("infra.results.inspection_result.clear_metadata_cache")
