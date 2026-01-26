#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database transaction manager - handles async database transactions
"""

from typing import AsyncGenerator, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, AsyncTransaction

from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseTransactionManager:
    """Extended manager for async database transactions with nested support"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._transactions: list[AsyncTransaction] = []

    async def __aenter__(self):
        if not self._transactions:
            # Start root transaction
            tx = await self.session.begin()
        else:
            # Start nested transaction (savepoint)
            tx = await self._transactions[-1].begin_nested()
        self._transactions.append(tx)
        await tx.__aenter__()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._transactions:
            tx = self._transactions.pop()
            await tx.__aexit__(exc_type, exc_val, exc_tb)

    async def commit(self):
        """Manually commit the current transaction level"""
        if not self._transactions:
            raise RuntimeError("No active transaction to commit")
        tx = self._transactions[-1]
        await tx.commit()
        self._transactions.pop()

    async def rollback(self):
        """Manually rollback the current transaction level"""
        if not self._transactions:
            raise RuntimeError("No active transaction to rollback")
        tx = self._transactions[-1]
        await tx.rollback()
        self._transactions.pop()

    @property
    def is_active(self) -> bool:
        """Check if transaction is active"""
        return bool(self._transactions)

    @property
    def nesting_level(self) -> int:
        """Get current nesting level"""
        return len(self._transactions)


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
