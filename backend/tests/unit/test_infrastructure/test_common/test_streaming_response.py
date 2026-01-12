#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for streaming_response module
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.responses import StreamingResponse

from core.common.streaming_response import StreamingExportResponse


class TestStreamingExportResponse:
    """Test cases for StreamingExportResponse"""

    @pytest.fixture
    def content_generator(self):
        """Mock content generator function"""

        async def generator():
            yield b"test data"
            yield b"more data"

        return Mock(return_value=generator())

    @pytest.fixture
    def streaming_response(self, content_generator):
        """Create StreamingExportResponse instance"""
        return StreamingExportResponse(
            content_generator=content_generator, filename="test.json", media_type="application/json"
        )

    def test_init(self, content_generator):
        """Test initialization"""
        response = StreamingExportResponse(
            content_generator=content_generator, filename="test.json", media_type="application/json"
        )

        assert response.content_generator == content_generator
        assert response.filename == "test.json"
        assert response.media_type == "application/json"

    def test_init_default_media_type(self, content_generator):
        """Test initialization with default media type"""
        response = StreamingExportResponse(content_generator=content_generator, filename="test.bin")

        assert response.media_type == "application/octet-stream"

    def test_to_response(self, streaming_response, content_generator):
        """Test conversion to FastAPI StreamingResponse"""
        response = streaming_response.to_response()

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "application/json"
        assert response.headers["Content-Disposition"] == "attachment; filename=test.json"
        assert response.headers["Cache-Control"] == "no-cache"

        # Verify content_generator was called
        content_generator.assert_called_once()

    def test_to_response_with_different_filename(self, content_generator):
        """Test to_response with different filename"""
        response = StreamingExportResponse(
            content_generator=content_generator, filename="report.pdf", media_type="application/pdf"
        )

        fastapi_response = response.to_response()

        assert fastapi_response.media_type == "application/pdf"
        assert fastapi_response.headers["Content-Disposition"] == "attachment; filename=report.pdf"
