# /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for metrics utilities
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from core.common.metrics import (
    MetricsCollector,
    time_operation,
    count_requests,
    metrics,
    log_performance_stats,
)


class TestMetricsCollector:
    """Test cases for MetricsCollector"""

    def test_increment_counter(self):
        """Test counter increment"""
        collector = MetricsCollector()
        collector.increment_counter("test_counter")
        collector.increment_counter("test_counter", 5)

        assert collector.get_counter("test_counter") == 6
        assert collector.get_counter("nonexistent") == 0

    def test_record_timing(self):
        """Test timing recording"""
        collector = MetricsCollector()
        collector.record_timing("test_operation", 1.5)
        collector.record_timing("test_operation", 2.0)
        collector.record_timing("test_operation", 2.5)

        avg = collector.get_average_timing("test_operation")
        assert avg == pytest.approx(2.0, rel=1e-2)

    def test_get_stats(self):
        """Test statistics retrieval"""
        collector = MetricsCollector()
        collector.increment_counter("requests", 10)
        collector.record_timing("operation", 1.0)
        collector.record_timing("operation", 2.0)

        stats = collector.get_stats()
        assert stats["requests"] == 10
        assert stats["operation_avg"] == 1.5
        assert stats["operation_min"] == 1.0
        assert stats["operation_max"] == 2.0

    def test_reset(self):
        """Test metrics reset"""
        collector = MetricsCollector()
        collector.increment_counter("test", 5)
        collector.record_timing("op", 1.0)

        collector.reset()
        assert collector.get_counter("test") == 0
        assert collector.get_average_timing("op") is None


class TestDecorators:
    """Test cases for metrics decorators"""

    @pytest.mark.asyncio
    async def test_time_operation_decorator(self):
        """Test time_operation decorator"""

        @time_operation("test_async_op")
        async def async_function():
            await asyncio.sleep(0.01)
            return "result"

        result = await async_function()
        assert result == "result"

        # Check that timing was recorded
        assert metrics.get_average_timing("test_async_op") is not None

    def test_time_operation_sync_decorator(self):
        """Test time_operation decorator for sync functions"""

        @time_operation("test_sync_op")
        def sync_function():
            time.sleep(0.01)
            return "result"

        result = sync_function()
        assert result == "result"

        # Check that timing was recorded
        assert metrics.get_average_timing("test_sync_op") is not None

    @pytest.mark.asyncio
    async def test_count_requests_decorator(self):
        """Test count_requests decorator"""

        @count_requests("test_endpoint")
        async def api_function():
            return {"status": "ok"}

        result = await api_function()
        assert result == {"status": "ok"}

        # Check that counter was incremented
        assert metrics.get_counter("requests_test_endpoint") == 1

    @pytest.mark.asyncio
    async def test_decorator_error_handling(self):
        """Test that decorators handle errors properly"""

        @time_operation("error_op")
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_function()

        # Check that error timing was recorded
        assert metrics.get_average_timing("error_op_error") is not None


class TestGlobalMetrics:
    """Test cases for global metrics instance"""

    def test_global_metrics_instance(self):
        """Test that global metrics instance works"""
        # Reset global metrics
        metrics.reset()

        metrics.increment_counter("global_test", 3)
        metrics.record_timing("global_op", 0.5)

        assert metrics.get_counter("global_test") == 3
        assert metrics.get_average_timing("global_op") == 0.5

    @patch("core.common.metrics.logger")
    def test_log_performance_stats(self, mock_logger):
        """Test performance stats logging"""
        metrics.reset()
        metrics.increment_counter("test_counter", 5)
        metrics.record_timing("test_timing", 1.0)

        log_performance_stats()

        # Check that logger.info was called
        mock_logger.info.assert_called()


class TestCacheBehavior:
    """Test cases for cache-like behavior in metrics"""

    def test_timing_cache_limit(self):
        """Test that timing cache maintains only last N measurements"""
        collector = MetricsCollector()

        # Add more than cache limit (100)
        for i in range(105):
            collector.record_timing("test", float(i))

        # Should only keep last 100
        stats = collector.get_stats()
        assert stats["test_count"] == 100
        # Average should be based on last 100 values (50.5 to 104.5)
        expected_avg = sum(range(5, 105)) / 100  # 50.5 to 104.5
        assert stats["test_avg"] == pytest.approx(expected_avg, rel=1e-2)
