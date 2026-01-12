#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streaming response utilities for secure downloads without disk storage
"""

from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Callable

from core.logging import get_logger

logger = get_logger(__name__)


class StreamingExportResponse:
    """
    Response that streams export content without saving to disk.
    Most secure option - no temporary files created.
    """

    def __init__(
        self,
        content_generator: Callable[[], AsyncGenerator[bytes, None]],
        filename: str,
        media_type: str = "application/octet-stream",
    ):
        """
        Initialize streaming export response

        Args:
            content_generator: Async generator function that yields bytes
            filename: Name for the downloaded file
            media_type: MIME type for the response
        """
        self.content_generator = content_generator
        self.filename = filename
        self.media_type = media_type

    def to_response(self) -> StreamingResponse:
        """Convert to FastAPI StreamingResponse"""
        return StreamingResponse(
            self.content_generator(),
            media_type=self.media_type,
            headers={"Content-Disposition": f"attachment; filename={self.filename}", "Cache-Control": "no-cache"},
        )
