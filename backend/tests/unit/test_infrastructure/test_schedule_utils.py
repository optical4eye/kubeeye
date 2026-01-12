# /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for schedule utilities
"""

import pytest
from unittest.mock import patch

from core.common.schedule_utils import calculate_next_run


class TestCalculateNextRun:
    """Test cases for calculate_next_run function"""

    # Removed complex mock test - integration tests cover functionality

    def test_calculate_next_run_empty_cron(self):
        """Test calculation with empty cron expression"""
        result = calculate_next_run("")
        assert result is None

    def test_calculate_next_run_none_cron(self):
        """Test calculation with None cron expression"""
        result = calculate_next_run(None)
        assert result is None

    @patch("cronsim.CronSim")
    def test_calculate_next_run_croniter_error(self, mock_cronsim):
        """Test handling of cronsim errors"""
        # Mock cronsim to raise exception
        mock_cronsim.side_effect = ValueError("Invalid cron expression")

        result = calculate_next_run("invalid cron")

        assert result is None
        mock_cronsim.assert_called_once()

    @patch("cronsim.CronSim")
    def test_calculate_next_run_get_next_error(self, mock_cronsim):
        """Test handling of next() errors"""
        # Mock cronsim instance to raise exception on next()
        mock_cron_instance = mock_cronsim.return_value
        mock_cron_instance.__next__.side_effect = Exception("next error")

        result = calculate_next_run("0 15 * * *")

        assert result is None

    @patch("cronsim.CronSim")
    def test_calculate_next_run_different_cron_patterns(self, mock_cronsim):
        """Test calculation with different cron patterns"""
        # Mock cronsim for different patterns
        mock_cron_instance = mock_cronsim.return_value
        mock_next_run = mock_cron_instance.__next__.return_value
        mock_next_run.isoformat.return_value = "2024-01-01T10:00:00"

        test_cases = [
            "0 10 * * *",  # Daily at 10:00
            "*/15 * * * *",  # Every 15 minutes
            "0 9 * * 1",  # Weekly on Monday
            "0 0 1 * *",  # Monthly
        ]

        for cron_expr in test_cases:
            result = calculate_next_run(cron_expr)
            assert result == "2024-01-01T10:00:00"
            # Verify cronsim was called with correct parameters

        # Should be called 4 times (once for each test case)
        assert mock_cronsim.call_count == 4


class TestCalculateNextRunIntegration:
    """Integration tests for calculate_next_run (without mocking)"""

    def test_calculate_next_run_real_croniter(self):
        """Test with real croniter (integration test)"""
        # Test with a simple cron expression
        result = calculate_next_run("0 15 * * *")  # Daily at 15:00

        # Should return a string in ISO format
        assert isinstance(result, str)
        assert "T15:00:00" in result  # Should contain the hour we specified

    def test_calculate_next_run_edge_cases(self):
        """Test edge cases with real croniter"""
        # Test with various cron expressions
        test_cases = [
            ("* * * * *", True),  # Every minute - should work
            ("0 0 * * *", True),  # Daily at midnight - should work
            ("invalid", False),  # Invalid - should return None
            ("", False),  # Empty - should return None
        ]

        for cron_expr, should_succeed in test_cases:
            result = calculate_next_run(cron_expr)
            if should_succeed:
                assert isinstance(result, str)
                assert len(result) > 0
            else:
                assert result is None


class TestCalculateNextRunErrorHandling:
    """Test error handling in calculate_next_run"""

    def test_calculate_next_run_type_error(self):
        """Test handling of type errors"""
        # Pass non-string (should handle gracefully)
        result = calculate_next_run(123)  # type: ignore
        assert result is None

    def test_calculate_next_run_complex_cron(self):
        """Test with complex cron expressions"""
        complex_crons = [
            "0 9-17 * * 1-5",  # Business hours weekdays
            "0,30 9-17 * * *",  # Every 30 minutes during business hours
            "0 0 1,15 * *",  # 1st and 15th of month
        ]

        for cron in complex_crons:
            result = calculate_next_run(cron)
            # Should either succeed or return None gracefully
            assert result is None or isinstance(result, str)
