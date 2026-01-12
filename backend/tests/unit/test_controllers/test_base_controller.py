#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for BaseController
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from api.controllers.base_controller import BaseController


class TestBaseController:
    """Test cases for BaseController"""

    @pytest.fixture
    def controller(self):
        """Create a BaseController instance for testing"""
        return BaseController()

    @pytest.mark.asyncio
    async def test_execute_operation_success(self, controller):
        """Test successful async operation execution"""

        async def mock_operation():
            return "success"

        result = await controller.execute_operation(mock_operation, "test_operation", "Custom success message")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_operation_http_exception(self, controller):
        """Test that HTTPException is re-raised"""

        async def mock_operation():
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc_info:
            await controller.execute_operation(mock_operation, "test_operation")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_execute_operation_value_error(self, controller):
        """Test ValueError conversion to HTTP 400"""

        async def mock_operation():
            raise ValueError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            await controller.execute_operation(mock_operation, "test_operation")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid input"

    @pytest.mark.asyncio
    async def test_execute_operation_generic_error(self, controller):
        """Test generic exception conversion to HTTP 500"""

        async def mock_operation():
            raise Exception("Something went wrong")

        with pytest.raises(HTTPException) as exc_info:
            await controller.execute_operation(mock_operation, "test_operation")

        assert exc_info.value.status_code == 500
        assert "test_operation error: Something went wrong" in exc_info.value.detail

    def test_execute_sync_operation_success(self, controller):
        """Test successful sync operation execution"""

        def mock_operation():
            return "success"

        result = controller.execute_sync_operation(mock_operation, "test_operation", "Custom success message")

        assert result == "success"

    def test_execute_sync_operation_value_error(self, controller):
        """Test ValueError conversion in sync operation"""

        def mock_operation():
            raise ValueError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            controller.execute_sync_operation(mock_operation, "test_operation")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid input"

    def test_validate_and_sanitize_param_required_missing(self, controller):
        """Test validation of missing required parameter"""
        with pytest.raises(HTTPException) as exc_info:
            controller.validate_and_sanitize_param(None, "test_param", required=True)

        assert exc_info.value.status_code == 400
        assert "Missing required parameter: test_param" in exc_info.value.detail

    def test_validate_and_sanitize_param_with_validator(self, controller):
        """Test parameter validation with validator function"""

        def validator(value):
            if value < 0:
                raise ValueError("Must be positive")
            return value

        # Valid value
        result = controller.validate_and_sanitize_param(5, "test_param", validator=validator)
        assert result == 5

        # Invalid value
        with pytest.raises(HTTPException) as exc_info:
            controller.validate_and_sanitize_param(-1, "test_param", validator=validator)

        assert exc_info.value.status_code == 400
        assert "Invalid test_param: Must be positive" in exc_info.value.detail

    def test_create_success_response(self, controller):
        """Test success response creation"""
        response = controller.create_success_response("Operation successful", {"data": "value"})
        expected = {"message": "Operation successful", "data": "value"}
        assert response == expected

    def test_create_success_response_no_data(self, controller):
        """Test success response creation without additional data"""
        response = controller.create_success_response("Operation successful")
        expected = {"message": "Operation successful"}
        assert response == expected

    def test_create_error_response(self, controller):
        """Test error response creation"""
        response = controller.create_error_response("validation_error", "Invalid input", {"field": "name"})
        expected = {"error": "validation_error", "message": "Invalid input", "field": "name"}
        assert response == expected

    def test_create_error_response_no_details(self, controller):
        """Test error response creation without details"""
        response = controller.create_error_response("server_error", "Internal error")
        expected = {"error": "server_error", "message": "Internal error"}
        assert response == expected
