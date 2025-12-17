#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for enhanced logging functionality
"""

import json
import logging
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from infrastructure.logging.enhanced_logging import (
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


class TestStructuredFormatter:
    """Test cases for structured logging formatter"""

    def test_format_basic_record(self):
        """Test basic log record formatting"""
        formatter = StructuredFormatter()

        # Create mock log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_function"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test"
        assert parsed["function"] == "test_function"
        assert parsed["line"] == 10
        assert "timestamp" in parsed

    def test_format_with_exception(self):
        """Test log record formatting with exception"""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test"
        record.funcName = "test_function"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error occurred"
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test error"
        assert "traceback" in parsed["exception"]

    def test_format_with_context_variables(self):
        """Test log record formatting with context variables"""
        formatter = StructuredFormatter()

        # Set context variables
        token = request_id.set("req-123")
        token2 = user_id.set("user-456")
        token3 = cluster_name.set("cluster-789")

        try:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test with context",
                args=(),
                exc_info=None,
            )
            record.module = "test"
            record.funcName = "test_function"

            result = formatter.format(record)
            parsed = json.loads(result)

            assert parsed["request_id"] == "req-123"
            assert parsed["user_id"] == "user-456"
            assert parsed["cluster_name"] == "cluster-789"
        finally:
            request_id.reset(token)
            user_id.reset(token2)
            cluster_name.reset(token3)

    def test_format_with_extra_fields(self):
        """Test log record formatting with extra fields"""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test with extra",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_function"
        record.extra_fields = {"custom_field": "custom_value", "number": 42}

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["custom_field"] == "custom_value"
        assert parsed["number"] == 42


class TestErrorTracker:
    """Test cases for error tracking"""

    def test_add_error(self):
        """Test adding error to tracker"""
        tracker = ErrorTracker()

        error = ValueError("Test error")
        context = {"operation": "test"}

        tracker.add_error(error, context)

        assert len(tracker.errors) == 1
        error_info = tracker.errors[0]
        assert error_info["type"] == "ValueError"
        assert error_info["message"] == "Test error"
        assert error_info["context"] == context
        assert "timestamp" in error_info
        assert "traceback" in error_info

    def test_max_errors_limit(self):
        """Test max errors limit"""
        tracker = ErrorTracker()
        tracker.max_errors = 2

        # Add 3 errors
        tracker.add_error(ValueError("Error 1"))
        tracker.add_error(ValueError("Error 2"))
        tracker.add_error(ValueError("Error 3"))

        assert len(tracker.errors) == 2
        assert tracker.errors[0]["message"] == "Error 2"
        assert tracker.errors[1]["message"] == "Error 3"

    def test_get_recent_errors(self):
        """Test getting recent errors"""
        tracker = ErrorTracker()

        tracker.add_error(ValueError("Error 1"))
        tracker.add_error(ValueError("Error 2"))
        tracker.add_error(ValueError("Error 3"))

        recent = tracker.get_recent_errors(2)
        assert len(recent) == 2
        assert recent[0]["message"] == "Error 2"
        assert recent[1]["message"] == "Error 3"

    def test_get_error_stats(self):
        """Test error statistics"""
        tracker = ErrorTracker()

        tracker.add_error(ValueError("Value error 1"))
        tracker.add_error(ValueError("Value error 2"))
        tracker.add_error(RuntimeError("Runtime error"))

        stats = tracker.get_error_stats()
        assert stats["ValueError"] == 2
        assert stats["RuntimeError"] == 1


class TestSetupLogging:
    """Test cases for logging setup"""

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.Path")
    def test_setup_logging_basic(self, mock_path, mock_logging):
        """Test basic logging setup"""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20

        result = setup_logging(log_level="INFO", enable_console=True, enable_structured=True)

        assert result == mock_logger
        mock_logger.setLevel.assert_called_with(20)
        mock_logger.addHandler.assert_called()

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.Path")
    def test_setup_logging_with_file(self, mock_path, mock_logging):
        """Test logging setup with file output"""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.handlers.RotatingFileHandler = Mock()

        result = setup_logging(log_file="test.log", enable_console=False)

        # Should add file handler
        assert mock_logger.addHandler.call_count == 1

    @patch("infrastructure.logging.enhanced_logging.logging")
    def test_setup_logging_unstructured(self, mock_logging):
        """Test logging setup with unstructured format"""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_logging.getLogger.return_value = mock_logger

        setup_logging(enable_structured=False)

        # Should use basic formatter
        mock_logger.addHandler.assert_called()


class TestDecorators:
    """Test cases for logging decorators"""

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    def test_log_execution_time_success(self, mock_datetime, mock_logging):
        """Test execution time logging decorator success"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 5)
        mock_datetime.now.side_effect = [start_time, end_time]

        @log_execution_time
        def test_function():
            return "success"

        result = test_function()

        assert result == "success"
        assert mock_logger.debug.called
        assert mock_logger.info.called

        # Check the info call
        info_call = mock_logger.info.call_args
        assert "Completed execution" in info_call[0][0]
        assert "execution_time" in info_call[1]["extra"]["extra_fields"]

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    @patch("infrastructure.logging.enhanced_logging.error_tracker")
    def test_log_execution_time_error(self, mock_error_tracker, mock_datetime, mock_logging):
        """Test execution time logging decorator error"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 2)
        mock_datetime.now.side_effect = [start_time, end_time]

        @log_execution_time
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        mock_logger.error.assert_called()
        mock_error_tracker.add_error.assert_called()

    @pytest.mark.asyncio
    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    async def test_log_api_request_success(self, mock_datetime, mock_logging):
        """Test API request logging decorator success"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 1)
        mock_datetime.now.side_effect = [start_time, end_time]

        # Mock request
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/test"
        mock_request.url.query = "param=value"

        @log_api_request
        async def test_endpoint(request):
            return {"result": "ok"}

        result = await test_endpoint(mock_request)

        assert result == {"result": "ok"}
        assert mock_logger.info.call_count == 2  # Request and response logs

    @pytest.mark.asyncio
    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    @patch("infrastructure.logging.enhanced_logging.error_tracker")
    async def test_log_api_request_error(self, mock_error_tracker, mock_datetime, mock_logging):
        """Test API request logging decorator error"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 1)
        mock_datetime.now.side_effect = [start_time, end_time]

        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/test"

        @log_api_request
        async def failing_endpoint(request):
            raise HTTPException(status_code=400, detail="Bad request")

        with pytest.raises(HTTPException):
            await failing_endpoint(mock_request)

        mock_logger.error.assert_called()
        mock_error_tracker.add_error.assert_called()


class TestErrorBoundary:
    """Test cases for error boundary context manager"""

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    def test_error_boundary_success(self, mock_datetime, mock_logging):
        """Test error boundary success case"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 2)
        mock_datetime.now.side_effect = [start_time, end_time]

        with ErrorBoundary("test_operation", mock_logger) as boundary:
            # Successful operation
            pass

        mock_logger.info.assert_called()
        success_call = [call for call in mock_logger.info.call_args_list if "completed" in str(call)][0]
        assert "test_operation" in success_call[0][0]

    @patch("infrastructure.logging.enhanced_logging.logging")
    @patch("infrastructure.logging.enhanced_logging.datetime")
    @patch("infrastructure.logging.enhanced_logging.error_tracker")
    def test_error_boundary_failure(self, mock_error_tracker, mock_datetime, mock_logging):
        """Test error boundary failure case"""
        mock_logger = Mock()
        mock_logging.getLogger.return_value = mock_logger

        # Mock datetime
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 1)
        mock_datetime.now.side_effect = [start_time, end_time]

        with pytest.raises(ValueError):
            with ErrorBoundary("test_operation", mock_logger) as boundary:
                raise ValueError("Test error")

        mock_logger.error.assert_called()
        mock_error_tracker.add_error.assert_called()


class TestErrorSummary:
    """Test cases for error summary functions"""

    def test_get_error_summary(self):
        """Test error summary generation"""
        # Clear existing errors
        error_tracker.errors.clear()

        # Add some test errors
        error_tracker.add_error(ValueError("Value error"))
        error_tracker.add_error(RuntimeError("Runtime error"))
        error_tracker.add_error(ValueError("Another value error"))

        summary = get_error_summary()

        assert summary["total_errors"] == 3
        assert summary["error_stats"]["ValueError"] == 2
        assert summary["error_stats"]["RuntimeError"] == 1
        assert len(summary["recent_errors"]) <= 10


# Import sys for exception testing
import sys
from fastapi import HTTPException
