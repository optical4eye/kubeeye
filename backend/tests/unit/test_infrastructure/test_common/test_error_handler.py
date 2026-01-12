#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for error_handler
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi import HTTPException

from core.common.unified_error_handler import (
    handle_errors,
    handle_api_errors,
    handle_service_errors,
    handle_infrastructure_errors,
)
from core.common.exceptions import KubeEyeException


class TestHandleErrors:
    """Test cases for handle_errors decorator"""

    def test_handle_errors_sync_success(self):
        """Test handle_errors with sync function success"""

        @handle_errors()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_handle_errors_sync_exception_reraise(self):
        """Test handle_errors with sync function exception and reraise"""

        @handle_errors(reraise=True)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()

    def test_handle_errors_sync_exception_return_on_error(self):
        """Test handle_errors with sync function exception and return_on_error"""

        @handle_errors(reraise=False, return_on_error="default")
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == "default"

    def test_handle_errors_sync_exception_log_level(self):
        """Test handle_errors with custom log level"""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            @handle_errors(reraise=False, log_level="warning", return_on_error=None)
            def test_func():
                raise ValueError("Test error")

            test_func()

            mock_logger.warning.assert_called_once()
            args = mock_logger.warning.call_args[0]
            assert "Error in test_func: Test error" in args[0]

    @pytest.mark.asyncio
    async def test_handle_errors_async_success(self):
        """Test handle_errors with async function success"""

        @handle_errors()
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_errors_async_exception_reraise(self):
        """Test handle_errors with async function exception and reraise"""

        @handle_errors(reraise=True)
        async def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await test_func()

    @pytest.mark.asyncio
    async def test_handle_errors_async_exception_return_on_error(self):
        """Test handle_errors with async function exception and return_on_error"""

        @handle_errors(reraise=False, return_on_error="default")
        async def test_func():
            raise ValueError("Test error")

        result = await test_func()
        assert result == "default"

    @pytest.mark.asyncio
    async def test_handle_errors_async_convert_to_http(self):
        """Test handle_errors with convert_to_http for KubeEyeException"""

        @handle_errors(reraise=False, convert_to_http=True, http_status_code=400)
        async def test_func():
            raise KubeEyeException("Test error")

        with pytest.raises(HTTPException) as exc_info:
            await test_func()

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Test error"

    @pytest.mark.asyncio
    async def test_handle_errors_async_convert_to_http_non_kubeeye_exception(self):
        """Test handle_errors with convert_to_http for non-KubeEyeException"""

        @handle_errors(reraise=False, convert_to_http=True, http_status_code=400, return_on_error="default")
        async def test_func():
            raise ValueError("Test error")

        result = await test_func()
        assert result == "default"


class TestConvenienceDecorators:
    """Test cases for convenience decorators"""

    @pytest.mark.asyncio
    async def test_handle_api_errors_success(self):
        """Test handle_api_errors success"""

        @handle_api_errors(status_code=404)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_api_errors_exception(self):
        """Test handle_api_errors with exception"""

        @handle_api_errors(status_code=404)
        async def test_func():
            raise KubeEyeException("Not found")

        with pytest.raises(HTTPException) as exc_info:
            await test_func()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_handle_service_errors_success(self):
        """Test handle_service_errors success"""

        @handle_service_errors(return_on_error="error")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_service_errors_exception(self):
        """Test handle_service_errors with exception"""

        @handle_service_errors(return_on_error="error")
        async def test_func():
            raise ValueError("Service error")

        result = await test_func()
        assert result == "error"

    @pytest.mark.asyncio
    async def test_handle_infrastructure_errors_success(self):
        """Test handle_infrastructure_errors success"""

        @handle_infrastructure_errors()
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_infrastructure_errors_exception(self):
        """Test handle_infrastructure_errors with exception"""

        @handle_infrastructure_errors()
        async def test_func():
            raise ValueError("Infrastructure error")

        with pytest.raises(ValueError, match="Infrastructure error"):
            await test_func()
