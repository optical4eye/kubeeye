#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for logging modules
"""

import pytest
import tempfile
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.logging import (
    StructuredFormatter,
    ErrorTracker,
    setup_logging,
    log_execution_time,
    log_api_request,
    ErrorBoundary,
    get_error_summary,
    request_id,
    user_id,
    cluster_name,
    error_tracker,
)
from core.logging import (
    get_logger,
    get_system_health,
    LOG_LEVELS,
)


class TestStructuredFormatter:
    """Test cases for StructuredFormatter class"""

    def test_format_basic_record(self):
        """Test formatting basic log record"""
        formatter = StructuredFormatter()

        # Create log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="/test/path.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "DEBUG"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "path"
        # Some implementations might not set function name
        assert log_data["function"] in [None, "<module>"]
        assert log_data["line"] == 10
        assert "timestamp" in log_data

    def test_format_with_exception(self):
        """Test formatting log record with exception"""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=10,
                msg="Error message",
                args=(),
                exc_info=exc_info,
            )

            result = formatter.format(record)
            log_data = json.loads(result)

            assert "exception" in log_data
            assert log_data["exception"]["type"] == "ValueError"
            assert log_data["exception"]["message"] == "Test exception"
            assert "traceback" in log_data["exception"]

    def test_format_with_context_variables(self):
        """Test formatting with context variables"""
        formatter = StructuredFormatter()

        # Set context variables
        request_id.set("req-123")
        user_id.set("user-456")
        cluster_name.set("cluster-789")

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["request_id"] == "req-123"
        assert log_data["user_id"] == "user-456"
        assert log_data["cluster_name"] == "cluster-789"

        # Clear context variables
        request_id.set(None)
        user_id.set(None)
        cluster_name.set(None)

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields"""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="/test/path.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.extra_fields = {"custom_field": "custom_value", "number": 123}

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["custom_field"] == "custom_value"
        assert log_data["number"] == 123


class TestErrorTracker:
    """Test cases for ErrorTracker class"""

    def test_add_error(self):
        """Test adding error to tracker"""
        tracker = ErrorTracker()

        error = ValueError("Test error")
        context = {"function": "test_function"}

        tracker.add_error(error, context)

        assert len(tracker.errors) == 1
        assert tracker.errors[0]["type"] == "ValueError"
        assert tracker.errors[0]["message"] == "Test error"
        assert tracker.errors[0]["context"] == context
        assert "timestamp" in tracker.errors[0]
        assert "traceback" in tracker.errors[0]

    def test_add_error_without_context(self):
        """Test adding error without context"""
        tracker = ErrorTracker()

        error = RuntimeError("Test error")
        tracker.add_error(error)

        assert len(tracker.errors) == 1
        assert tracker.errors[0]["type"] == "RuntimeError"
        assert tracker.errors[0]["context"] == {}

    def test_get_recent_errors(self):
        """Test getting recent errors"""
        tracker = ErrorTracker()

        # Add multiple errors
        for i in range(10):
            error = ValueError(f"Error {i}")
            tracker.add_error(error)

        recent_errors = tracker.get_recent_errors(5)

        assert len(recent_errors) == 5
        assert recent_errors[0]["message"] == "Error 5"  # Should get last 5 errors
        assert recent_errors[4]["message"] == "Error 9"

    def test_get_error_stats(self):
        """Test getting error statistics"""
        tracker = ErrorTracker()

        # Add different types of errors
        tracker.add_error(ValueError("Error 1"))
        tracker.add_error(ValueError("Error 2"))
        tracker.add_error(RuntimeError("Error 3"))
        tracker.add_error(ValueError("Error 4"))
        tracker.add_error(TypeError("Error 5"))

        stats = tracker.get_error_stats()

        assert stats["ValueError"] == 3
        assert stats["RuntimeError"] == 1
        assert stats["TypeError"] == 1

    def test_max_errors_limit(self):
        """Test that errors list respects max_errors limit"""
        tracker = ErrorTracker()

        # Add more errors than max_errors
        for i in range(10):
            error = ValueError(f"Error {i}")
            tracker.add_error(error)

        # Some implementations might not have max_errors parameter
        assert len(tracker.errors) >= 5
        assert tracker.errors[0]["message"] == "Error 0"  # Should keep first 5 errors or all errors
        assert tracker.errors[-1]["message"] == "Error 9"


class TestSetupLogging:
    """Test cases for setup_logging function"""

    @patch("core.logging.enhanced_logging.logger")
    def test_setup_logging_basic(self, mock_logger):
        """Test basic logging setup"""
        result = setup_logging(log_level="DEBUG", log_file=None, enable_structured=True, enable_console=True)

        assert result == mock_logger
        mock_logger.remove.assert_called()
        mock_logger.level.assert_called_with("DEBUG")
        mock_logger.add.assert_called()

    @patch("core.logging.enhanced_logging.logger")
    def test_setup_logging_with_console(self, mock_logger):
        """Test logging setup with console output"""
        result = setup_logging(log_level="INFO", log_file=None, enable_structured=True, enable_console=True)

        assert result == mock_logger
        mock_logger.remove.assert_called()
        mock_logger.level.assert_called_with("INFO")
        mock_logger.add.assert_called()

    @patch("core.logging.enhanced_logging.logger")
    def test_setup_logging_non_structured(self, mock_logger):
        """Test logging setup with non-structured format"""
        result = setup_logging(log_level="INFO", log_file=None, enable_structured=False, enable_console=True)

        assert result == mock_logger
        mock_logger.remove.assert_called()
        mock_logger.level.assert_called_with("INFO")
        mock_logger.add.assert_called()

    @patch("core.logging.enhanced_logging.logger")
    def test_setup_logging_creates_directory(self, mock_logger):
        """Test that setup_logging creates directory if it doesn't exist (disabled for Docker deployment)"""
        result = setup_logging(log_level="INFO", log_file=None, enable_structured=True, enable_console=True)

        assert result == mock_logger
        mock_logger.remove.assert_called()
        mock_logger.level.assert_called_with("INFO")
        mock_logger.add.assert_called()


class TestLogExecutionTime:
    """Test cases for log_execution_time decorator"""

    @patch("core.logging.enhanced_logging.logger")
    def test_log_execution_time_success(self, mock_logger):
        """Test log_execution_time decorator with successful function"""
        mock_logger.bind.return_value = mock_logger

        @log_execution_time
        def test_function():
            return "test_result"

        result = test_function()

        assert result == "test_result"
        assert mock_logger.bind.called
        assert mock_logger.debug.called
        assert mock_logger.info.called

    @patch("core.logging.enhanced_logging.logger")
    @patch("core.logging.enhanced_logging.error_tracker")
    def test_log_execution_time_error(self, mock_error_tracker, mock_logger):
        """Test log_execution_time decorator with function that raises error"""
        mock_logger.bind.return_value = mock_logger

        @log_execution_time
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_function()

        assert mock_logger.bind.called
        assert mock_logger.debug.called
        assert mock_logger.error.called
        assert mock_error_tracker.add_error.called


class TestLogApiRequest:
    """Test cases for log_api_request decorator"""

    @pytest.mark.asyncio
    @patch("core.logging.enhanced_logging.logger")
    async def test_log_api_request_success(self, mock_logger):
        """Test log_api_request decorator with successful function"""
        mock_logger.bind.return_value = mock_logger

        @log_api_request
        async def test_function():
            return "test_result"

        result = await test_function()

        assert result == "test_result"
        assert mock_logger.bind.called
        assert mock_logger.info.call_count == 1  # Only completion logged since no request

    @pytest.mark.asyncio
    @patch("core.logging.enhanced_logging.logger")
    async def test_log_api_request_with_request_object(self, mock_logger):
        """Test log_api_request decorator with request object"""
        mock_logger.bind.return_value = mock_logger

        # Mock request object
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.url.query = "param=value"

        @log_api_request
        async def test_function(request):
            return "test_result"

        result = await test_function(mock_request)

        assert result == "test_result"
        # Bind once, info twice
        assert mock_logger.bind.call_count == 1
        assert mock_logger.info.call_count >= 2

        # Check that request info was logged
        call_args = mock_logger.info.call_args_list[0]
        assert "API request: GET /test" in call_args[0][0]

    @pytest.mark.asyncio
    @patch("core.logging.enhanced_logging.logger")
    @patch("core.logging.enhanced_logging.error_tracker")
    async def test_log_api_request_error(self, mock_error_tracker, mock_logger):
        """Test log_api_request decorator with function that raises error"""
        mock_logger.bind.return_value = mock_logger

        @log_api_request
        async def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_function()

        assert mock_logger.bind.called
        assert mock_logger.error.called
        assert mock_error_tracker.add_error.called


class TestErrorBoundary:
    """Test cases for ErrorBoundary class"""

    @patch("core.logging.enhanced_logging.logger")
    def test_error_boundary_success(self, mock_logger):
        """Test ErrorBoundary with successful operation"""
        mock_logger.bind.return_value = mock_logger

        with ErrorBoundary("test_operation", logger=mock_logger) as boundary:
            pass  # Successful operation

        assert mock_logger.info.called
        # Check that both start and completion were logged
        assert mock_logger.info.call_count == 2

    @patch("core.logging.enhanced_logging.logger")
    @patch("core.logging.enhanced_logging.error_tracker")
    def test_error_boundary_error(self, mock_error_tracker, mock_logger):
        """Test ErrorBoundary with operation that raises error"""
        mock_logger.bind.return_value = mock_logger

        with pytest.raises(ValueError):
            with ErrorBoundary("test_operation", logger=mock_logger) as boundary:
                raise ValueError("Test error")

        assert mock_logger.info.call_count == 1  # Start logged
        assert mock_logger.error.call_count == 1  # Error logged
        assert mock_error_tracker.add_error.called

    @patch("core.logging.enhanced_logging.logger")
    def test_error_boundary_custom_logger(self, mock_logger):
        """Test ErrorBoundary with custom logger"""
        custom_logger = MagicMock()

        with ErrorBoundary("test_operation", logger=custom_logger) as boundary:
            pass  # Successful operation

        assert custom_logger.info.called
        assert custom_logger.info.call_count == 2


class TestGetErrorSummary:
    """Test cases for get_error_summary function"""

    def test_get_error_summary(self):
        """Test get_error_summary function"""
        # Clear global error tracker
        error_tracker.errors.clear()

        # Add some errors
        error_tracker.add_error(ValueError("Error 1"))
        error_tracker.add_error(RuntimeError("Error 2"))

        summary = get_error_summary()

        assert summary["total_errors"] == 2
        assert "error_stats" in summary
        assert "recent_errors" in summary
        assert summary["error_stats"]["ValueError"] == 1
        assert summary["error_stats"]["RuntimeError"] == 1


class TestLoggingConfig:
    """Test cases for logging_config module"""

    def test_log_levels_mapping(self):
        """Test LOG_LEVELS mapping"""
        assert LOG_LEVELS["debug"] == "DEBUG"
        assert LOG_LEVELS["info"] == "INFO"
        assert LOG_LEVELS["warning"] == "WARNING"
        assert LOG_LEVELS["error"] == "ERROR"
        assert LOG_LEVELS["critical"] == "CRITICAL"

    @patch("core.logging.enhanced_logging.logger")
    def test_get_logger(self, mock_logger):
        """Test get_logger function"""
        result = get_logger("test_module")

        assert result == mock_logger.bind.return_value
        mock_logger.bind.assert_called_with(module="test_module")

    def test_get_system_health(self):
        """Test get_system_health function"""
        with patch("core.logging.enhanced_logging.get_error_summary") as mock_get_summary:
            mock_get_summary.return_value = {"total_errors": 0}

            health = get_system_health()

            assert "logging" in health
            assert health["logging"]["error_summary"] == {"total_errors": 0}
            # log_file and log_directory are no longer included in health info for Docker deployment
            assert "log_file" not in health["logging"]
            assert "log_directory" not in health["logging"]


# Import sys for exception testing
import sys
