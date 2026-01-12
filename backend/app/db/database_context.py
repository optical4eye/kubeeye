#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database context manager for safe database operations
"""

from contextlib import asynccontextmanager
from db.database import get_db
from core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def with_db_session():
    """Контекстный менеджер для работы с БД

    Предоставляет безопасный способ работы с сессией БД,
    автоматически обрабатывая ошибки и логируя их.

    Yields:
        AsyncSession: Сессия базы данных

    Raises:
        Exception: Любое исключение при работе с БД
    """
    async for db in get_db():
        try:
            yield db
        except Exception as e:
            logger.error(f"Database error: {e}", exc_info=True)
            raise
