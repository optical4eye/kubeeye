# Unit tests for network check utilities

import pytest
from unittest.mock import patch, Mock
from infrastructure.network.network_check import validate_ip, validate_port, NetworkConnectivityResult


class TestNetworkValidation:
    """Test network validation functions"""

    def test_validate_ip_valid(self):
        """Test valid IP addresses"""
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.0.0.1") is True
        assert validate_ip("172.16.0.1") is True

    def test_validate_ip_invalid(self):
        """Test invalid IP addresses"""
        assert validate_ip("256.1.1.1") is False
        assert validate_ip("192.168.1") is False
        assert validate_ip("192.168.1.1.1") is False
        assert validate_ip("abc.def.ghi.jkl") is False
        assert validate_ip("") is False

    def test_validate_port_valid(self):
        """Test valid port numbers"""
        assert validate_port(80) is True
        assert validate_port(443) is True
        assert validate_port(1) is True
        assert validate_port(65535) is True

    def test_validate_port_invalid(self):
        """Test invalid port numbers"""
        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port(-1) is False
        assert validate_port("80") is False
        assert validate_port(None) is False


class TestNetworkConnectivityResult:
    """Test NetworkConnectivityResult class"""


    def test_add_check(self):
        """Test adding check results"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        check_result = {
            "status": "success",
            "response_time": 0.5,
            "node_ip": "10.0.0.1",
            "target_ip": "192.168.1.1",
            "target_port": 80
        }

        result.add_check(check_result)
        assert len(result.checks) == 1
        assert result.checks[0] == check_result

    def test_get_summary(self):
        """Test summary generation"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        # Add successful check
        result.add_check({"status": "success", "response_time": 0.5})
        # Add failed check
        result.add_check({"status": "failed", "response_time": 1.0})

        summary = result.get_summary()

        assert summary["cluster_name"] == "test-cluster"
        assert summary["target_ip"] == "192.168.1.1"
        assert summary["target_port"] == 80
        assert summary["total_checks"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 50.0

    def test_get_summary_empty(self):
        """Test summary with no checks"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        summary = result.get_summary()

        assert summary["total_checks"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["success_rate"] == 0