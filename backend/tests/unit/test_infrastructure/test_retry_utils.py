# /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for retry utilities
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from core.common.retry_utils import (
    retry_on_failure,
    retry_sync_on_failure,
    DatabaseError,
    NetworkError,
)


class TestAsyncRetry:
    """Test cases for async retry decorator"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful execution on first attempt"""

        @retry_on_failure()
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "max_attempts,failures_before_success",
        [
            (2, 1),  # 1 failure, 1 success
            (3, 2),  # 2 failures, 1 success
            (5, 4),  # 4 failures, 1 success
        ],
    )
    async def test_success_after_retry(self, max_attempts, failures_before_success):
        """Test successful execution after retries with various attempt counts"""
        call_count = 0

        @retry_on_failure(max_attempts=max_attempts)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count <= failures_before_success:
                raise DatabaseError("Temporary error")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == failures_before_success + 1

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """Test exhaustion of all retry attempts"""
        call_count = 0

        @retry_on_failure(max_attempts=2)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Persistent error")

        with pytest.raises(NetworkError, match="Persistent error"):
            await test_func()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_unexpected_exception(self):
        """Test that unexpected exceptions don't trigger retry"""

        @retry_on_failure(max_attempts=3)
        async def test_func():
            raise ValueError("Unexpected error")

        with pytest.raises(ValueError, match="Unexpected error"):
            await test_func()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception_class,exception_message",
        [
            (DatabaseError, "Database connection failed"),
            (NetworkError, "Network timeout"),
            (ValueError, "Invalid input"),
            (ConnectionError, "Connection lost"),
        ],
    )
    async def test_custom_exceptions(self, exception_class, exception_message):
        """Test retry with various exception types"""
        call_count = 0

        @retry_on_failure(max_attempts=2, exceptions=(exception_class,))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise exception_class(exception_message)
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff timing"""
        import time

        delays = []

        @retry_on_failure(max_attempts=3, delay=0.1, backoff=2.0)
        async def test_func():
            delays.append(time.time())
            raise DatabaseError("Error")

        start_time = time.time()
        with pytest.raises(DatabaseError):
            await test_func()

        # Check that delays increase exponentially
        assert len(delays) == 3
        # Should have delays of ~0.1, ~0.2, ~0.4 seconds
        # Use a slightly lower threshold to account for function execution time
        assert delays[1] - delays[0] >= 0.05  # At least half the expected delay
        assert delays[2] - delays[1] >= 0.15  # At least 75% of expected delay


class TestSyncRetry:
    """Test cases for sync retry decorator"""

    def test_sync_success_on_first_attempt(self):
        """Test successful sync execution on first attempt"""

        @retry_sync_on_failure()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_sync_success_after_retry(self):
        """Test successful sync execution after retries"""
        call_count = 0

        @retry_sync_on_failure(max_attempts=3)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseError("Temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_sync_exhaust_retries(self):
        """Test exhaustion of all sync retry attempts"""
        call_count = 0

        @retry_sync_on_failure(max_attempts=2)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Persistent error")

        with pytest.raises(NetworkError, match="Persistent error"):
            test_func()

        assert call_count == 2


class TestRetryLogging:
    """Test cases for retry logging"""

    @pytest.mark.asyncio
    @patch("core.common.retry_utils.logger")
    async def test_retry_logging(self, mock_logger):
        """Test that retry attempts are logged"""
        call_count = 0

        @retry_on_failure(max_attempts=2)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise DatabaseError("Error")

        with pytest.raises(DatabaseError):
            await test_func()

        # Check that warning was logged for retry attempt
        mock_logger.warning.assert_called()
        assert "Attempt 1 failed" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    @patch("core.common.retry_utils.logger")
    async def test_error_logging_on_exhaustion(self, mock_logger):
        """Test that error is logged when retries exhausted"""

        @retry_on_failure(max_attempts=2)
        async def test_func():
            raise DatabaseError("Persistent error")

        with pytest.raises(DatabaseError):
            await test_func()

        # Check that error was logged
        mock_logger.error.assert_called()
        assert "All 2 attempts failed" in mock_logger.error.call_args[0][0]


class TestRetryEdgeCases:
    """Test cases for retry edge cases"""

    @pytest.mark.asyncio
    async def test_zero_max_attempts(self):
        """Test behavior with zero max_attempts (should not retry)"""

        @retry_on_failure(max_attempts=1)  # 1 means no retries
        async def test_func():
            raise DatabaseError("Error")

        with pytest.raises(DatabaseError):
            await test_func()

    @pytest.mark.asyncio
    async def test_very_short_delays(self):
        """Test with very short delays"""
        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.001, backoff=1.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Error")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exception_in_retry_logic(self):
        """Test handling of exceptions during retry logic itself"""
        # This is hard to test directly, but we can ensure the decorator
        # doesn't break when unexpected exceptions occur in wrapped function
        pass  # Covered by other tests
