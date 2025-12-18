#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for common utilities
"""

import pytest
from infrastructure.common.common import create_status_badge


class TestCreateStatusBadge:
    """Test cases for create_status_badge function"""

    def test_create_status_badge_success(self):
        """Test create_status_badge with success status"""
        result = create_status_badge("success")

        assert "Success" in result
        assert "#E7F9ED" in result  # Light green background
        assert "#1E8E3E" in result  # Dark green text
        assert "padding: 4px 8px" in result
        assert "border-radius: 4px" in result

    def test_create_status_badge_warning(self):
        """Test create_status_badge with warning status"""
        result = create_status_badge("warning")

        assert "Warning" in result
        assert "#FEF7E0" in result  # Light yellow background
        assert "#E67700" in result  # Orange text

    def test_create_status_badge_error(self):
        """Test create_status_badge with error status"""
        result = create_status_badge("error")

        assert "Error" in result
        assert "#FFE5E5" in result  # Light red background
        assert "#D93025" in result  # Red text

    def test_create_status_badge_info(self):
        """Test create_status_badge with info status"""
        result = create_status_badge("info")

        assert "Info" in result
        assert "#E8F0FE" in result  # Light blue background
        assert "#1A73E8" in result  # Blue text

    def test_create_status_badge_custom_text(self):
        """Test create_status_badge with custom text"""
        result = create_status_badge("success", "All Good")

        assert "All Good" in result
        assert "Success" not in result
        assert "#E7F9ED" in result  # Light green background

    def test_create_status_badge_unknown_status(self):
        """Test create_status_badge with unknown status (should default to info)"""
        result = create_status_badge("unknown")

        assert "Unknown" in result
        assert "#E8F0FE" in result  # Light blue background (info default)
        assert "#1A73E8" in result  # Blue text (info default)

    def test_create_status_badge_case_insensitive(self):
        """Test create_status_badge with different case"""
        result = create_status_badge("SUCCESS")

        assert "Success" in result
        assert "#E7F9ED" in result  # Light green background
        assert "#1E8E3E" in result  # Dark green text

    def test_create_status_badge_empty_text(self):
        """Test create_status_badge with empty text"""
        result = create_status_badge("success", "")

        assert "" in result
        assert "#E7F9ED" in result  # Light green background
