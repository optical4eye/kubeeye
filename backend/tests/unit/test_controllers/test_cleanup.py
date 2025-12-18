#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for cleanup API controller
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException

from api.cleanup import get_cleanup_status, get_cleanup_config


class TestCleanupAPI:
    """Test cases for cleanup API endpoints"""

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_valid_config(self, mock_load_config):
        """Test getting cleanup status with valid configuration"""
        mock_load_config.return_value = {
            "enabled": True,
            "max_age_days": 30,
            "cleanup_interval_hours": 24,
            "last_cleanup": "2023-01-01T12:00:00Z",
        }

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is True
        assert result["max_age_days"] == 30
        assert result["cleanup_interval_hours"] == 24
        assert result["last_cleanup"] == "2023-01-01T12:00:00Z"

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_invalid_enabled_type(self, mock_load_config):
        """Test getting cleanup status with invalid enabled type"""
        mock_load_config.return_value = {
            "enabled": "true",  # String instead of boolean
            "max_age_days": 30,
            "cleanup_interval_hours": 24,
        }

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is False  # Should be converted to False
        assert result["max_age_days"] == 30
        assert result["cleanup_interval_hours"] == 24

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_invalid_max_age_days(self, mock_load_config):
        """Test getting cleanup status with invalid max_age_days"""
        mock_load_config.return_value = {
            "enabled": True,
            "max_age_days": 400,  # Over maximum
            "cleanup_interval_hours": 24,
        }

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is True
        assert result["max_age_days"] == 30  # Should default to 30
        assert result["cleanup_interval_hours"] == 24

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_invalid_cleanup_interval(self, mock_load_config):
        """Test getting cleanup status with invalid cleanup_interval_hours"""
        mock_load_config.return_value = {
            "enabled": True,
            "max_age_days": 30,
            "cleanup_interval_hours": 200,  # Over maximum (168)
        }

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is True
        assert result["max_age_days"] == 30
        assert result["cleanup_interval_hours"] == 24  # Should default to 24

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_min_values(self, mock_load_config):
        """Test getting cleanup status with minimum valid values"""
        mock_load_config.return_value = {"enabled": True, "max_age_days": 1, "cleanup_interval_hours": 1}

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is True
        assert result["max_age_days"] == 1
        assert result["cleanup_interval_hours"] == 1

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_missing_fields(self, mock_load_config):
        """Test getting cleanup status with missing fields"""
        mock_load_config.return_value = {}

        result = asyncio.run(get_cleanup_status())

        assert result["enabled"] is False  # Default
        assert result["max_age_days"] == 30  # Default
        assert result["cleanup_interval_hours"] == 24  # Default
        assert result["last_cleanup"] is None

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_status_exception(self, mock_load_config):
        """Test getting cleanup status when exception occurs"""
        mock_load_config.side_effect = Exception("Config error")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_cleanup_status())

        assert exc_info.value.status_code == 500
        assert "Config error" in str(exc_info.value.detail)

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_valid(self, mock_load_config):
        """Test getting cleanup config with valid configuration"""
        mock_load_config.return_value = {
            "enabled": True,
            "max_age_days": 30,
            "cleanup_interval_hours": 24,
            "last_cleanup": "2023-01-01T12:00:00Z",
            "unknown_field": "should_be_ignored",
        }

        result = asyncio.run(get_cleanup_config())

        assert result["enabled"] is True
        assert result["max_age_days"] == 30
        assert result["cleanup_interval_hours"] == 24
        assert result["last_cleanup"] == "2023-01-01T12:00:00Z"
        assert "unknown_field" not in result  # Should be filtered out

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_invalid_types(self, mock_load_config):
        """Test getting cleanup config with invalid types"""
        mock_load_config.return_value = {
            "enabled": "not_boolean",
            "max_age_days": "not_number",
            "cleanup_interval_hours": "not_number",
        }

        result = asyncio.run(get_cleanup_config())

        assert result["enabled"] is False  # Invalid boolean defaults to False
        assert result["max_age_days"] == 30  # Invalid number defaults to 30
        assert result["cleanup_interval_hours"] == 24  # Invalid number defaults to 24

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_out_of_range_values(self, mock_load_config):
        """Test getting cleanup config with out of range values"""
        mock_load_config.return_value = {
            "enabled": True,
            "max_age_days": 500,  # Over max 365
            "cleanup_interval_hours": 200,  # Over max 168
        }

        result = asyncio.run(get_cleanup_config())

        assert result["enabled"] is True
        assert result["max_age_days"] == 30  # Out of range defaults to 30
        assert result["cleanup_interval_hours"] == 24  # Out of range defaults to 24

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_non_dict_response(self, mock_load_config):
        """Test getting cleanup config when load returns non-dict"""
        mock_load_config.return_value = "not_a_dict"

        result = asyncio.run(get_cleanup_config())

        assert result == {}  # Should return empty dict for non-dict response

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_exception(self, mock_load_config):
        """Test getting cleanup config when exception occurs"""
        mock_load_config.side_effect = Exception("Config load error")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_cleanup_config())

        assert exc_info.value.status_code == 500
        assert "Config load error" in str(exc_info.value.detail)

    @patch("api.cleanup.load_cleanup_config")
    def test_get_cleanup_config_edge_case_values(self, mock_load_config):
        """Test getting cleanup config with edge case values"""
        mock_load_config.return_value = {
            "enabled": False,
            "max_age_days": 365,  # Maximum valid value
            "cleanup_interval_hours": 168,  # Maximum valid value (1 week)
            "last_cleanup": "",
        }

        result = asyncio.run(get_cleanup_config())

        assert result["enabled"] is False
        assert result["max_age_days"] == 365
        assert result["cleanup_interval_hours"] == 168
        assert result["last_cleanup"] == ""
