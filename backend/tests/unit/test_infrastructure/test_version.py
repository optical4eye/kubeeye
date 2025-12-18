#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for version information module
"""

import pytest
from infrastructure.common.version import (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    VERSION_TAG,
    VERSION,
    APP_NAME,
    APP_DESCRIPTION,
    APP_AUTHOR,
    APP_URL,
    RELEASE_DATE,
    get_version,
    VERSION_INFO,
    get_version_info,
    get_version_string,
)


class TestVersionConstants:
    """Test cases for version constants"""

    def test_version_constants(self):
        """Test that version constants are properly defined"""
        assert isinstance(VERSION_MAJOR, int)
        assert isinstance(VERSION_MINOR, int)
        assert isinstance(VERSION_PATCH, int)
        assert isinstance(VERSION_TAG, str)

        assert VERSION_MAJOR >= 0
        assert VERSION_MINOR >= 0
        assert VERSION_PATCH >= 0

    def test_app_constants(self):
        """Test that app constants are properly defined"""
        assert isinstance(APP_NAME, str)
        assert isinstance(APP_DESCRIPTION, str)
        assert isinstance(APP_AUTHOR, str)
        assert isinstance(APP_URL, str)
        assert isinstance(RELEASE_DATE, str)

        assert APP_NAME == "kubeeye"
        assert APP_DESCRIPTION == "Kubernetes cluster inspection tool"
        assert APP_AUTHOR == "pixiake"
        assert APP_URL == "https://github.com/kubesphere/kubeeye"

    def test_version_format(self):
        """Test that VERSION is properly formatted"""
        assert isinstance(VERSION, str)

        # Check version format: major.minor.patch or major.minor.patch-tag
        if VERSION_TAG:
            expected = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}-{VERSION_TAG}"
        else:
            expected = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

        assert VERSION == expected


class TestVersionFunctions:
    """Test cases for version functions"""

    def test_get_version(self):
        """Test get_version function"""
        version = get_version()
        assert version == VERSION
        assert isinstance(version, str)

    def test_get_version_info(self):
        """Test get_version_info function"""
        version_info = get_version_info()

        assert isinstance(version_info, dict)
        assert version_info == VERSION_INFO

        # Check required keys
        required_keys = ["name", "version", "description", "author", "url", "release_date"]
        for key in required_keys:
            assert key in version_info
            assert isinstance(version_info[key], str)

        # Check values
        assert version_info["name"] == APP_NAME
        assert version_info["version"] == VERSION
        assert version_info["description"] == APP_DESCRIPTION
        assert version_info["author"] == APP_AUTHOR
        assert version_info["url"] == APP_URL
        assert version_info["release_date"] == RELEASE_DATE

    def test_get_version_string(self):
        """Test get_version_string function"""
        version_string = get_version_string()
        expected = f"{APP_NAME} v{VERSION}"

        assert version_string == expected
        assert isinstance(version_string, str)

    def test_version_info_immutability(self):
        """Test that VERSION_INFO is not modified by function calls"""
        original_info = VERSION_INFO.copy()

        # Call functions multiple times
        get_version_info()
        get_version_info()

        # Ensure VERSION_INFO hasn't changed
        assert VERSION_INFO == original_info


class TestVersionScenarios:
    """Test cases for different version scenarios"""

    def test_version_with_tag(self):
        """Test version format with tag"""
        # This tests the current implementation with tag
        assert "-" in VERSION  # Should contain dash when tag is present
        assert VERSION_TAG in VERSION

    def test_version_components_consistency(self):
        """Test that version components are consistent"""
        # Extract components from VERSION string
        if VERSION_TAG:
            version_part = VERSION.split("-")[0]
            tag_part = VERSION.split("-")[1]
        else:
            version_part = VERSION
            tag_part = None

        # Check version part
        expected_version_part = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
        assert version_part == expected_version_part

        # Check tag part if present
        if tag_part:
            assert tag_part == VERSION_TAG

    def test_release_date_format(self):
        """Test that release date is in expected format"""
        # Should be in YYYY-MM-DD format
        assert len(RELEASE_DATE) == 10
        assert RELEASE_DATE[4] == "-"
        assert RELEASE_DATE[7] == "-"

        # Check that it's a valid date format
        year, month, day = RELEASE_DATE.split("-")
        assert len(year) == 4
        assert len(month) == 2
        assert len(day) == 2

        # Check that all parts are numeric
        assert year.isdigit()
        assert month.isdigit()
        assert day.isdigit()

        # Check reasonable ranges
        assert 2000 <= int(year) <= 2100
        assert 1 <= int(month) <= 12
        assert 1 <= int(day) <= 31
