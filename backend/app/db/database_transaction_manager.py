#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database transaction manager - handles async database transactions
"""

from typing import AsyncGenerator, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseTransactionManager:
    """Extended manager for async database transactions"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._nested_level = 0
        self._savepoints = []

    async def __aenter__(self):
        if self._nested_level == 0:
            # Start transaction
            await self.session.begin()
        else:
            # Create savepoint for nested transaction
            savepoint_name = f"sp_{self._nested_level}"
            await self.session.execute(text(f"SAVEPOINT {savepoint_name}"))
            self._savepoints.append(savepoint_name)
        self._nested_level += 1
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._nested_level -= 1

        if exc_type:
            if self._nested_level == 0:
                # Rollback main transaction
                await self.session.rollback()
                logger.error(f"Transaction failed: {exc_val}")
            else:
                # Rollback to savepoint for nested transaction
                savepoint_name = self._savepoints.pop()
                await self.session.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                logger.warning(f"Nested transaction failed, rolled back to savepoint: {exc_val}")
        else:
            if self._nested_level == 0:
                # Commit main transaction
                await self.session.commit()
            # For nested transactions, don't commit yet - let outer transaction handle it

    async def commit(self):
        """Manually commit the transaction"""
        if self._nested_level == 1:
            await self.session.commit()
        else:
            raise RuntimeError("Cannot manually commit nested transaction")

    async def rollback(self):
        """Manually rollback the transaction"""
        if self._nested_level == 1:
            await self.session.rollback()
        else:
            raise RuntimeError("Cannot manually rollback nested transaction")

    @property
    def is_active(self) -> bool:
        """Check if transaction is active"""
        return self._nested_level > 0

    @property
    def nesting_level(self) -> int:
        """Get current nesting level"""
        return self._nested_level


# Backward compatibility alias
AsyncTransactionManager = DatabaseTransactionManager


@asynccontextmanager
async def transaction_context(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions with automatic rollback on error
    """
    async with DatabaseTransactionManager(session) as tx_session:
        yield tx_session


async def execute_in_transaction(session: AsyncSession, func, *args, **kwargs) -> Any:
    """
    Execute a function within a transaction context
    """
    async with DatabaseTransactionManager(session) as tx_session:
        return await func(tx_session, *args, **kwargs)
