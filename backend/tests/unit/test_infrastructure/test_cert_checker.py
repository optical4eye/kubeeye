#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for certificate checker
"""

import base64
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timezone, timedelta

from infra.security.cert_checker import (
    get_cluster_cert_status,
    _extract_client_cert_info,
    _extract_cluster_ca_info,
    _parse_certificate,
    _calculate_cert_status,
    check_certificate_file,
    get_certificate_details,
)


class TestCertChecker:
    """Test cases for certificate checking functionality"""

    def test_get_cluster_cert_status_empty_content(self):
        """Test certificate status check with empty kubeconfig"""
        result = get_cluster_cert_status("test-cluster", "")

        assert result["status"] == "unknown"
        assert result["days_remaining"] is None
        assert "empty" in result["error"]

    def test_get_cluster_cert_status_invalid_yaml(self):
        """Test certificate status check with invalid YAML"""
        result = get_cluster_cert_status("test-cluster", "invalid: yaml: content: [")

        assert result["status"] == "unknown"
        assert result["days_remaining"] is None
        assert "error occurred" in result["error"]

    @patch("infra.security.cert_checker._extract_client_cert_info")
    @patch("infra.security.cert_checker._extract_cluster_ca_info")
    @patch("infra.security.cert_checker._calculate_cert_status")
    def test_get_cluster_cert_status_with_client_cert(self, mock_calc_status, mock_extract_ca, mock_extract_client):
        """Test certificate status check with client certificate"""
        mock_extract_client.return_value = {"cert": "data"}
        mock_calc_status.return_value = {"status": "valid", "days_remaining": 30}

        kubeconfig = """
        users:
        - name: test-user
          user:
            client-certificate-data: test-cert-data
        """

        result = get_cluster_cert_status("test-cluster", kubeconfig)

        assert result["status"] == "valid"
        assert result["days_remaining"] == 30
        mock_extract_client.assert_called_once()
        mock_extract_ca.assert_not_called()

    @patch("infra.security.cert_checker._extract_client_cert_info")
    @patch("infra.security.cert_checker._extract_cluster_ca_info")
    @patch("infra.security.cert_checker._calculate_cert_status")
    def test_get_cluster_cert_status_with_ca_cert(self, mock_calc_status, mock_extract_ca, mock_extract_client):
        """Test certificate status check with CA certificate fallback"""
        mock_extract_client.return_value = None
        mock_extract_ca.return_value = {"cert": "data"}
        mock_calc_status.return_value = {"status": "warning", "days_remaining": 15}

        kubeconfig = """
        clusters:
        - name: test-cluster
          cluster:
            certificate-authority-data: test-ca-data
        """

        result = get_cluster_cert_status("test-cluster", kubeconfig)

        assert result["status"] == "warning"
        assert result["days_remaining"] == 15
        mock_extract_client.assert_called_once()
        mock_extract_ca.assert_called_once()

    @patch("infra.security.cert_checker._extract_client_cert_info")
    @patch("infra.security.cert_checker._extract_cluster_ca_info")
    def test_get_cluster_cert_status_no_cert_found(self, mock_extract_ca, mock_extract_client):
        """Test certificate status check when no certificates found"""
        mock_extract_client.return_value = None
        mock_extract_ca.return_value = None

        kubeconfig = """
        users:
        - name: test-user
        clusters:
        - name: test-cluster
        """

        result = get_cluster_cert_status("test-cluster", kubeconfig)

        assert result["status"] == "unknown"
        assert result["days_remaining"] is None
        assert "no valid certificate" in result["error"]

    @patch("infra.security.cert_checker.base64.b64decode")
    @patch("infra.security.cert_checker._parse_certificate")
    def test_extract_client_cert_info_with_data(self, mock_parse, mock_b64decode):
        """Test client certificate extraction with certificate data"""
        mock_b64decode.return_value = b"cert_bytes"
        mock_parse.return_value = {"cert": "info"}

        kubeconfig = {"users": [{"user": {"client-certificate-data": "dGVzdC1jZXJ0"}}]}  # base64 "test-cert"

        result = _extract_client_cert_info(kubeconfig)

        assert result == {"cert": "info"}
        mock_b64decode.assert_called_once_with("dGVzdC1jZXJ0")
        mock_parse.assert_called_once_with(b"cert_bytes")

    @patch("infra.security.cert_checker.Path")
    @patch("builtins.open", new_callable=mock_open, read_data=b"cert_content")
    @patch("infra.security.cert_checker._parse_certificate")
    def test_extract_client_cert_info_with_file(self, mock_parse, mock_file, mock_path):
        """Test client certificate extraction with certificate file"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        mock_parse.return_value = {"cert": "info"}

        kubeconfig = {"users": [{"user": {"client-certificate": "/path/to/cert.pem"}}]}

        result = _extract_client_cert_info(kubeconfig)

        assert result == {"cert": "info"}
        mock_file.assert_called_once_with("/path/to/cert.pem", "rb")
        mock_parse.assert_called_once_with(b"cert_content")

    @patch("infra.security.cert_checker.Path")
    def test_extract_client_cert_info_file_not_exists(self, mock_path):
        """Test client certificate extraction when file doesn't exist"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        kubeconfig = {"users": [{"user": {"client-certificate": "/nonexistent/cert.pem"}}]}

        result = _extract_client_cert_info(kubeconfig)

        assert result is None

    @patch("infra.security.cert_checker.base64.b64decode")
    @patch("infra.security.cert_checker._parse_certificate")
    def test_extract_cluster_ca_info_with_data(self, mock_parse, mock_b64decode):
        """Test cluster CA certificate extraction with CA data"""
        mock_b64decode.return_value = b"ca_bytes"
        mock_parse.return_value = {"ca": "info"}

        kubeconfig = {"clusters": [{"cluster": {"certificate-authority-data": "dGVzdC1jYQ=="}}]}  # base64 "test-ca"

        result = _extract_cluster_ca_info(kubeconfig)

        assert result == {"ca": "info"}
        mock_b64decode.assert_called_once_with("dGVzdC1jYQ==")
        mock_parse.assert_called_once_with(b"ca_bytes")

    @patch("infra.security.cert_checker.x509.load_pem_x509_certificate")
    def test_parse_certificate_success(self, mock_load_cert):
        """Test successful certificate parsing"""
        mock_cert = Mock()
        mock_cert.issuer.rfc4514_string.return_value = "CN=Issuer"
        mock_cert.subject.rfc4514_string.return_value = "CN=Subject"
        mock_cert.not_valid_before_utc = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_cert.not_valid_after_utc = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_cert.serial_number = 12345

        mock_load_cert.return_value = mock_cert

        cert_bytes = (
            b"-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA\n-----END CERTIFICATE-----"
        )

        result = _parse_certificate(cert_bytes)

        assert result["issuer"] == "CN=Issuer"
        assert result["subject"] == "CN=Subject"
        assert result["not_before"] == datetime(2023, 1, 1, tzinfo=timezone.utc)
        assert result["not_after"] == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert result["serial_number"] == "12345"

    @patch("infra.security.cert_checker.x509.load_pem_x509_certificate")
    def test_parse_certificate_failure(self, mock_load_cert):
        """Test certificate parsing failure"""
        mock_load_cert.side_effect = Exception("Invalid certificate")

        result = _parse_certificate(b"invalid_cert")

        assert result is None

    @patch("infra.security.cert_checker.datetime")
    def test_calculate_cert_status_valid(self, mock_datetime):
        """Test certificate status calculation - valid certificate"""
        mock_datetime.now.return_value = datetime(2023, 6, 15, tzinfo=timezone.utc)
        mock_datetime.timezone.utc = timezone.utc

        cert_info = {
            "issuer": "CN=Issuer",
            "subject": "CN=Subject",
            "not_before": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "not_after": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "serial_number": "12345",
        }

        result = _calculate_cert_status(cert_info)

        assert result["status"] == "valid"
        assert result["days_remaining"] == 200  # Approximately 200 days from 2023-06-15 to 2024-01-01
        assert "cert_info" in result
        assert result["cert_info"]["issuer"] == "CN=Issuer"

    @patch("infra.security.cert_checker.datetime")
    def test_calculate_cert_status_warning(self, mock_datetime):
        """Test certificate status calculation - warning (expires soon)"""
        mock_datetime.now.return_value = datetime(2023, 12, 20, tzinfo=timezone.utc)
        mock_datetime.timezone.utc = timezone.utc

        cert_info = {
            "issuer": "CN=Issuer",
            "subject": "CN=Subject",
            "not_before": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "not_after": datetime(2023, 12, 25, tzinfo=timezone.utc),  # Expires in 5 days
            "serial_number": "12345",
        }

        result = _calculate_cert_status(cert_info)

        assert result["status"] == "critical"  # 5 days triggers critical, not warning
        assert result["days_remaining"] == 5

    @patch("infra.security.cert_checker.datetime")
    def test_calculate_cert_status_critical(self, mock_datetime):
        """Test certificate status calculation - critical (expires very soon)"""
        mock_datetime.now.return_value = datetime(2023, 12, 26, tzinfo=timezone.utc)
        mock_datetime.timezone.utc = timezone.utc

        cert_info = {
            "issuer": "CN=Issuer",
            "subject": "CN=Subject",
            "not_before": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "not_after": datetime(2023, 12, 28, tzinfo=timezone.utc),  # Expires in 2 days
            "serial_number": "12345",
        }

        result = _calculate_cert_status(cert_info)

        assert result["status"] == "critical"
        assert result["days_remaining"] == 2

    @patch("infra.security.cert_checker.datetime")
    def test_calculate_cert_status_expired(self, mock_datetime):
        """Test certificate status calculation - expired certificate"""
        mock_datetime.now.return_value = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_datetime.timezone.utc = timezone.utc

        cert_info = {
            "issuer": "CN=Issuer",
            "subject": "CN=Subject",
            "not_before": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "not_after": datetime(2024, 1, 1, tzinfo=timezone.utc),  # Already expired
            "serial_number": "12345",
        }

        result = _calculate_cert_status(cert_info)

        assert result["status"] == "expired"
        assert result["days_remaining"] == -14  # 14 days past expiry

    @patch("infra.security.cert_checker.Path")
    @patch("builtins.open", new_callable=mock_open, read_data=b"cert_content")
    @patch("infra.security.cert_checker._parse_certificate")
    @patch("infra.security.cert_checker._calculate_cert_status")
    def test_check_certificate_file_success(self, mock_calc_status, mock_parse, mock_file, mock_path):
        """Test successful certificate file checking"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_parse.return_value = {"cert": "info"}
        mock_calc_status.return_value = {"status": "valid", "days_remaining": 100}

        result = check_certificate_file("/path/to/cert.pem")

        assert result["status"] == "valid"
        assert result["days_remaining"] == 100
        mock_file.assert_called_once_with("/path/to/cert.pem", "rb")

    @patch("infra.security.cert_checker.Path")
    def test_check_certificate_file_not_exists(self, mock_path):
        """Test certificate file checking when file doesn't exist"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        result = check_certificate_file("/nonexistent/cert.pem")

        assert result["status"] == "unknown"
        assert result["days_remaining"] is None
        assert "does not exist" in result["error"]

    @patch("infra.security.cert_checker.Path")
    @patch("builtins.open", new_callable=mock_open, read_data=b"cert_content")
    @patch("infra.security.cert_checker._parse_certificate")
    def test_check_certificate_file_parse_failure(self, mock_parse, mock_file, mock_path):
        """Test certificate file checking when parsing fails"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_parse.return_value = None

        result = check_certificate_file("/path/to/cert.pem")

        assert result["status"] == "unknown"
        assert result["days_remaining"] is None
        assert "unable to parse" in result["error"]

    @patch("infra.security.cert_checker._calculate_cert_status")
    @patch("infra.security.cert_checker._parse_certificate")
    @patch("infra.security.cert_checker.base64.b64decode")
    def test_get_certificate_details_success(self, mock_b64decode, mock_parse, mock_calc_status):
        """Test successful detailed certificate information retrieval"""
        mock_b64decode.return_value = b"cert_bytes"
        mock_parse.return_value = {
            "issuer": "CN=Issuer",
            "subject": "CN=Subject",
            "not_before": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "not_after": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "serial_number": "12345",
        }
        mock_calc_status.return_value = {
            "status": "valid",
            "days_remaining": 200,
            "cert_info": {
                "issuer": "CN=Issuer",
                "subject": "CN=Subject",
                "not_before": "2023-01-01 00:00:00 UTC",
                "not_after": "2024-01-01 00:00:00 UTC",
                "serial_number": "12345",
            },
        }

        kubeconfig = """
        users:
        - name: test-user
          user:
            client-certificate-data: dGVzdC1jZXJ0
        clusters:
        - name: test-cluster
          cluster:
            certificate-authority-data: dGVzdC1jYQ==
        """

        result = get_certificate_details(kubeconfig)

        assert "client_certificates" in result
        assert "cluster_ca_certificates" in result
        assert "summary" in result
        assert result["summary"]["total_certs"] == 2
        assert len(result["client_certificates"]) == 1
        assert len(result["cluster_ca_certificates"]) == 1

    def test_get_certificate_details_invalid_yaml(self):
        """Test detailed certificate information with invalid YAML"""
        result = get_certificate_details("invalid: yaml: content: [")

        assert "error" in result
        assert "failed to get detailed certificate information" in result["error"]
