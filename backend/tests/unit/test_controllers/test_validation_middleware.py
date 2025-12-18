#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for validation middleware
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.validation_middleware import (
    ValidationMiddleware,
    validate_path_param,
    validate_limit_param,
    validate_task_id,
    validate_cluster_name,
    validate_status_filter,
    validate_format_param,
    validate_timeout_param,
    validate_port_param,
    validate_ip_address,
    sanitize_json_response,
    validate_pagination_params,
    validate_datetime_param,
)


class TestValidationMiddleware:
    """Test cases for ValidationMiddleware class"""

    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI app"""
        return Mock()

    @pytest.fixture
    def middleware(self, mock_app):
        """Create ValidationMiddleware instance"""
        return ValidationMiddleware(mock_app, max_query_length=100)

    @pytest.fixture
    def mock_request(self):
        """Create mock Request object"""
        request = Mock(spec=Request)
        request.method = "GET"
        request.query_params = {}
        request.body = AsyncMock(return_value=b"{}")
        return request

    @pytest.mark.asyncio
    async def test_dispatch_get_request(self, middleware, mock_request):
        """Test dispatch with GET request"""
        mock_request.method = "GET"
        mock_request.query_params = {"param1": "value1", "param2": "value2"}

        mock_call_next = AsyncMock(return_value=Mock(spec=Response))

        with patch.object(middleware, "_validate_query_params", new_callable=AsyncMock) as mock_validate_query:
            await middleware.dispatch(mock_request, mock_call_next)

            mock_validate_query.assert_called_once_with(mock_request)
            mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_post_request(self, middleware, mock_request):
        """Test dispatch with POST request"""
        mock_request.method = "POST"
        mock_request.query_params = {}
        mock_request.body.return_value = b'{"key": "value"}'

        mock_call_next = AsyncMock(return_value=Mock(spec=Response))

        with patch.object(
            middleware, "_validate_query_params", new_callable=AsyncMock
        ) as mock_validate_query, patch.object(
            middleware, "_validate_body", new_callable=AsyncMock
        ) as mock_validate_body:

            await middleware.dispatch(mock_request, mock_call_next)

            mock_validate_query.assert_called_once_with(mock_request)
            mock_validate_body.assert_called_once_with(mock_request)
            mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_validate_query_params_safe(self, middleware, mock_request):
        """Test _validate_query_params with safe parameters"""
        mock_request.query_params = {"name": "test", "limit": "10"}

        # Should not raise any exception
        await middleware._validate_query_params(mock_request)

    @pytest.mark.asyncio
    async def test_validate_query_params_sql_injection(self, middleware, mock_request):
        """Test _validate_query_params with SQL injection patterns"""
        mock_request.query_params = {"id": "1; DROP TABLE users; --"}

        with pytest.raises(HTTPException) as exc_info:
            await middleware._validate_query_params(mock_request)

        assert exc_info.value.status_code == 400
        assert "Invalid query parameter: id" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_query_params_xss(self, middleware, mock_request):
        """Test _validate_query_params with XSS patterns"""
        mock_request.query_params = {"comment": "<script>alert('xss')</script>"}

        with pytest.raises(HTTPException) as exc_info:
            await middleware._validate_query_params(mock_request)

        assert exc_info.value.status_code == 400
        assert "Invalid query parameter: comment" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_query_params_command_injection(self, middleware, mock_request):
        """Test _validate_query_params with command injection patterns"""
        mock_request.query_params = {"cmd": "ls; rm -rf /"}

        with pytest.raises(HTTPException) as exc_info:
            await middleware._validate_query_params(mock_request)

        assert exc_info.value.status_code == 400
        assert "Invalid query parameter: cmd" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_body_safe(self, middleware, mock_request):
        """Test _validate_body with safe content"""
        mock_request.body.return_value = b'{"name": "test", "value": 123}'

        # Should not raise any exception
        await middleware._validate_body(mock_request)

    @pytest.mark.asyncio
    async def test_validate_body_with_injection(self, middleware, mock_request):
        """Test _validate_body with injection patterns"""
        mock_request.body.return_value = b'{"query": "SELECT * FROM users WHERE 1=1"}'

        # This test logs a warning but doesn't raise an exception in the actual implementation
        # The middleware only logs the warning and continues processing
        await middleware._validate_body(mock_request)

        # The test passes if no exception is raised, as the actual implementation
        # only logs the warning but doesn't raise an HTTPException

    @pytest.mark.asyncio
    async def test_validate_body_decode_error(self, middleware, mock_request):
        """Test _validate_body with decode error"""
        mock_request.body.return_value = b"\xff\xfe"  # Invalid UTF-8

        # Should not raise exception, just log debug message
        await middleware._validate_body(mock_request)

    def test_contains_injection_patterns_sql(self, middleware):
        """Test _contains_injection_patterns with SQL injection"""
        assert middleware._contains_injection_patterns("SELECT * FROM users")
        assert middleware._contains_injection_patterns("1 OR 1=1")
        assert middleware._contains_injection_patterns("DROP TABLE users")
        assert middleware._contains_injection_patterns("-- comment")
        assert middleware._contains_injection_patterns("/* comment */")

    def test_contains_injection_patterns_xss(self, middleware):
        """Test _contains_injection_patterns with XSS"""
        assert middleware._contains_injection_patterns("<script>alert('xss')</script>")
        assert middleware._contains_injection_patterns("javascript:alert('xss')")
        assert middleware._contains_injection_patterns("onclick=alert('xss')")

    def test_contains_injection_patterns_command(self, middleware):
        """Test _contains_injection_patterns with command injection"""
        assert middleware._contains_injection_patterns("ls; rm -rf /")
        assert middleware._contains_injection_patterns("curl http://evil.com")
        assert middleware._contains_injection_patterns("nc -l 8080")
        assert middleware._contains_injection_patterns("$(whoami)")

    def test_contains_injection_patterns_safe(self, middleware):
        """Test _contains_injection_patterns with safe content"""
        assert not middleware._contains_injection_patterns("normal text")
        assert not middleware._contains_injection_patterns("user@example.com")
        assert not middleware._contains_injection_patterns("123-456-7890")

    def test_contains_injection_patterns_non_string(self, middleware):
        """Test _contains_injection_patterns with non-string input"""
        assert not middleware._contains_injection_patterns(123)
        assert not middleware._contains_injection_patterns(None)
        assert not middleware._contains_injection_patterns([])


class TestValidationFunctions:
    """Test cases for validation functions"""

    def test_validate_path_param_success(self):
        """Test validate_path_param with valid input"""
        result = validate_path_param("id", "123")
        assert result == "123"

    def test_validate_path_param_empty(self):
        """Test validate_path_param with empty value"""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_param("id", "")

        assert exc_info.value.status_code == 400
        assert "Missing required path parameter: id" in str(exc_info.value.detail)

    def test_validate_path_param_with_pattern(self):
        """Test validate_path_param with pattern validation"""
        result = validate_path_param("id", "123", r"^\d+$")
        assert result == "123"

    def test_validate_path_param_invalid_pattern(self):
        """Test validate_path_param with invalid pattern"""
        with pytest.raises(HTTPException) as exc_info:
            validate_path_param("id", "abc", r"^\d+$")

        assert exc_info.value.status_code == 400
        assert "Invalid format for path parameter id" in str(exc_info.value.detail)

    def test_validate_limit_param_valid(self):
        """Test validate_limit_param with valid values"""
        assert validate_limit_param(1) == 1
        assert validate_limit_param(100) == 100
        assert validate_limit_param(1000) == 1000

    def test_validate_limit_param_too_small(self):
        """Test validate_limit_param with value too small"""
        with pytest.raises(HTTPException) as exc_info:
            validate_limit_param(0)

        assert exc_info.value.status_code == 400
        assert "Limit must be at least 1" in str(exc_info.value.detail)

    def test_validate_limit_param_too_large(self):
        """Test validate_limit_param with value too large"""
        with pytest.raises(HTTPException) as exc_info:
            validate_limit_param(1001)

        assert exc_info.value.status_code == 400
        assert "Limit cannot exceed 1000" in str(exc_info.value.detail)

    def test_validate_task_id_valid(self):
        """Test validate_task_id with valid IDs"""
        assert validate_task_id("task-123") == "task-123"
        assert validate_task_id("task_456") == "task_456"
        assert validate_task_id("TASK789") == "TASK789"

    def test_validate_task_id_empty(self):
        """Test validate_task_id with empty ID"""
        with pytest.raises(HTTPException) as exc_info:
            validate_task_id("")

        assert exc_info.value.status_code == 400
        assert "Task ID is required" in str(exc_info.value.detail)

    def test_validate_task_id_invalid_chars(self):
        """Test validate_task_id with invalid characters"""
        with pytest.raises(HTTPException) as exc_info:
            validate_task_id("task@123")

        assert exc_info.value.status_code == 400
        assert "Task ID can only contain alphanumeric characters" in str(exc_info.value.detail)

    def test_validate_task_id_too_long(self):
        """Test validate_task_id with ID too long"""
        with pytest.raises(HTTPException) as exc_info:
            validate_task_id("a" * 101)

        assert exc_info.value.status_code == 400
        assert "Task ID cannot exceed 100 characters" in str(exc_info.value.detail)

    def test_validate_cluster_name_valid(self):
        """Test validate_cluster_name with valid names"""
        assert validate_cluster_name("cluster-1") == "cluster-1"
        assert validate_cluster_name("cluster_test") == "cluster_test"
        assert validate_cluster_name("CLUSTER123") == "CLUSTER123"

    def test_validate_cluster_name_empty(self):
        """Test validate_cluster_name with empty name"""
        with pytest.raises(HTTPException) as exc_info:
            validate_cluster_name("")

        assert exc_info.value.status_code == 400
        assert "Cluster name is required" in str(exc_info.value.detail)

    def test_validate_cluster_name_invalid_chars(self):
        """Test validate_cluster_name with invalid characters"""
        with pytest.raises(HTTPException) as exc_info:
            validate_cluster_name("cluster@123")

        assert exc_info.value.status_code == 400
        assert "Cluster name can only contain alphanumeric characters" in str(exc_info.value.detail)

    def test_validate_cluster_name_too_long(self):
        """Test validate_cluster_name with name too long"""
        with pytest.raises(HTTPException) as exc_info:
            validate_cluster_name("a" * 101)

        assert exc_info.value.status_code == 400
        assert "Cluster name cannot exceed 100 characters" in str(exc_info.value.detail)

    def test_validate_status_filter_valid(self):
        """Test validate_status_filter with valid values"""
        assert validate_status_filter("pending") == "pending"
        assert validate_status_filter("running") == "running"
        assert validate_status_filter("completed") == "completed"
        assert validate_status_filter("failed") == "failed"

    def test_validate_status_filter_none(self):
        """Test validate_status_filter with None"""
        assert validate_status_filter(None) is None

    def test_validate_status_filter_invalid(self):
        """Test validate_status_filter with invalid value"""
        with pytest.raises(HTTPException) as exc_info:
            validate_status_filter("invalid")

        assert exc_info.value.status_code == 400
        assert "Status filter must be one of" in str(exc_info.value.detail)

    def test_validate_format_param_valid(self):
        """Test validate_format_param with valid formats"""
        assert validate_format_param("json") == "json"
        assert validate_format_param("csv") == "csv"
        assert validate_format_param("excel") == "excel"
        assert validate_format_param("pdf") == "pdf"

    def test_validate_format_param_empty(self):
        """Test validate_format_param with empty format"""
        with pytest.raises(HTTPException) as exc_info:
            validate_format_param("")

        assert exc_info.value.status_code == 400
        assert "Format parameter is required" in str(exc_info.value.detail)

    def test_validate_format_param_invalid(self):
        """Test validate_format_param with invalid format"""
        with pytest.raises(HTTPException) as exc_info:
            validate_format_param("xml")

        assert exc_info.value.status_code == 400
        assert "Format must be one of" in str(exc_info.value.detail)

    def test_validate_timeout_param_valid(self):
        """Test validate_timeout_param with valid values"""
        assert validate_timeout_param(1) == 1
        assert validate_timeout_param(60) == 60
        assert validate_timeout_param(300) == 300

    def test_validate_timeout_param_too_small(self):
        """Test validate_timeout_param with value too small"""
        with pytest.raises(HTTPException) as exc_info:
            validate_timeout_param(0)

        assert exc_info.value.status_code == 400
        assert "Timeout must be at least 1 second" in str(exc_info.value.detail)

    def test_validate_timeout_param_too_large(self):
        """Test validate_timeout_param with value too large"""
        with pytest.raises(HTTPException) as exc_info:
            validate_timeout_param(301)

        assert exc_info.value.status_code == 400
        assert "Timeout cannot exceed 300 seconds" in str(exc_info.value.detail)

    def test_validate_port_param_valid(self):
        """Test validate_port_param with valid ports"""
        assert validate_port_param(1) == 1
        assert validate_port_param(80) == 80
        assert validate_port_param(443) == 443
        assert validate_port_param(65535) == 65535

    def test_validate_port_param_too_small(self):
        """Test validate_port_param with port too small"""
        with pytest.raises(HTTPException) as exc_info:
            validate_port_param(0)

        assert exc_info.value.status_code == 400
        assert "Port must be between 1 and 65535" in str(exc_info.value.detail)

    def test_validate_port_param_too_large(self):
        """Test validate_port_param with port too large"""
        with pytest.raises(HTTPException) as exc_info:
            validate_port_param(65536)

        assert exc_info.value.status_code == 400
        assert "Port must be between 1 and 65535" in str(exc_info.value.detail)

    @patch("socket.gethostbyname")
    def test_validate_ip_address_valid_ip(self, mock_gethostbyname):
        """Test validate_ip_address with valid IP"""
        mock_gethostbyname.return_value = "192.168.1.1"

        result = validate_ip_address("192.168.1.1")
        assert result == "192.168.1.1"
        mock_gethostbyname.assert_called_once_with("192.168.1.1")

    @patch("socket.gethostbyname")
    def test_validate_ip_address_valid_hostname(self, mock_gethostbyname):
        """Test validate_ip_address with valid hostname"""
        mock_gethostbyname.return_value = "93.184.216.34"

        result = validate_ip_address("example.com")
        assert result == "example.com"
        mock_gethostbyname.assert_called_once_with("example.com")

    def test_validate_ip_address_empty(self):
        """Test validate_ip_address with empty value"""
        with pytest.raises(HTTPException) as exc_info:
            validate_ip_address("")

        assert exc_info.value.status_code == 400
        assert "IP address or hostname is required" in str(exc_info.value.detail)

    @patch("socket.gethostbyname")
    def test_validate_ip_address_invalid(self, mock_gethostbyname):
        """Test validate_ip_address with invalid IP/hostname"""
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")

        with pytest.raises(HTTPException) as exc_info:
            validate_ip_address("invalid.hostname")

        assert exc_info.value.status_code == 400
        assert "Invalid IP address or hostname" in str(exc_info.value.detail)

    def test_sanitize_json_response_dict(self):
        """Test sanitize_json_response with dictionary"""
        data = {
            "name": "John",
            "comment": "<script>alert('xss')</script>",
            "url": "javascript:alert('xss')",
            "nested": {"value": "test"},
        }

        result = sanitize_json_response(data)

        assert result["name"] == "John"
        assert "<script>" not in result["comment"]
        assert "javascript:" not in result["url"]
        assert result["nested"]["value"] == "test"

    def test_sanitize_json_response_list(self):
        """Test sanitize_json_response with list"""
        data = ["item1", "<script>alert('xss')</script>", {"key": "value"}]

        result = sanitize_json_response(data)

        # For non-dict input, should return empty dict
        assert result == {}

    def test_sanitize_json_response_non_dict(self):
        """Test sanitize_json_response with non-dict input"""
        result = sanitize_json_response("string")
        assert result == {}

    def test_validate_pagination_params_valid(self):
        """Test validate_pagination_params with valid values"""
        result = validate_pagination_params(0, 100)
        assert result == (0, 100)

        result = validate_pagination_params(10, 50)
        assert result == (10, 50)

    def test_validate_pagination_params_negative_offset(self):
        """Test validate_pagination_params with negative offset"""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(-1, 100)

        assert exc_info.value.status_code == 400
        assert "Offset cannot be negative" in str(exc_info.value.detail)

    def test_validate_pagination_params_invalid_limit(self):
        """Test validate_pagination_params with invalid limit"""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(0, 0)

        assert exc_info.value.status_code == 400
        assert "Limit must be at least 1" in str(exc_info.value.detail)

    def test_validate_pagination_params_limit_too_large(self):
        """Test validate_pagination_params with limit too large"""
        with pytest.raises(HTTPException) as exc_info:
            validate_pagination_params(0, 1001)

        assert exc_info.value.status_code == 400
        assert "Limit cannot exceed 1000" in str(exc_info.value.detail)

    def test_validate_datetime_param_valid(self):
        """Test validate_datetime_param with valid datetime"""
        result = validate_datetime_param("2023-01-01T12:00:00")
        assert result == "2023-01-01T12:00:00"

        result = validate_datetime_param("2023-01-01T12:00:00Z")
        assert result == "2023-01-01T12:00:00Z"

    def test_validate_datetime_param_empty(self):
        """Test validate_datetime_param with empty value"""
        with pytest.raises(HTTPException) as exc_info:
            validate_datetime_param("")

        assert exc_info.value.status_code == 400
        assert "Datetime parameter is required" in str(exc_info.value.detail)

    def test_validate_datetime_param_invalid(self):
        """Test validate_datetime_param with invalid format"""
        with pytest.raises(HTTPException) as exc_info:
            validate_datetime_param("not-a-datetime")

        assert exc_info.value.status_code == 400
        assert "Invalid datetime format" in str(exc_info.value.detail)
