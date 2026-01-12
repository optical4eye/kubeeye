#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database monitor - handles async database connection monitoring
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from .database_connection_manager import DatabaseConnectionManager

from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseMonitor:
    """Database monitor with automatic recovery"""

    def __init__(
        self, connection_manager: "DatabaseConnectionManager", check_interval: int = 30, failure_threshold: int = 3
    ):
        self.connection_manager = connection_manager
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self._running = False
        self._failure_count = 0
        self._last_check = None
        self._last_success = None
        self._last_failure = None
        self._monitor_task = None

        # Статистика
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
            "uptime_percentage": 0.0,
        }

    async def _perform_connection_test(self) -> tuple[bool, str, dict]:
        """Perform the actual connection test query using connection pool directly"""
        async with self.connection_manager.get_engine().connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()

            if test_value == 1:
                return True, "", {}
            else:
                return False, f"Test query failed: {test_value}", {"test_value": test_value}

    def _handle_successful_check(self):
        """Handle successful connection check"""
        self.stats["successful_checks"] += 1
        self._last_success = datetime.now()
        if self._failure_count > 0:
            logger.info("Database connection restored after failures")
        self._failure_count = 0

    def _handle_failed_check(self, message: str, error: Exception = None):
        """Handle failed connection check"""
        self.stats["failed_checks"] += 1
        self._last_failure = datetime.now()
        self._failure_count += 1
        if error:
            logger.warning(f"Database connection check failed: {error}")

    def _create_success_result(self) -> dict:
        """Create success result dict"""
        return {
            "status": "success",
            "timestamp": self._last_success.isoformat(),
        }

    def _create_failure_result(self, message: str, error: str = None) -> dict:
        """Create failure result dict"""
        result = {
            "status": "error" if error else "failed",
            "timestamp": self._last_failure.isoformat(),
            "failure_count": self._failure_count,
        }
        if error:
            result["error"] = error
        if message:
            result["message"] = message
        return result

    async def _check_connection_async(self) -> dict:
        """Async connection check"""
        try:
            success, message, data = await self._perform_connection_test()

            if success:
                self._handle_successful_check()
                return self._create_success_result()
            else:
                self._handle_failed_check(message)
                return self._create_failure_result(message)

        except Exception as e:
            self._handle_failed_check("", e)
            return self._create_failure_result("", str(e))

    async def _attempt_recovery_async(self) -> bool:
        """Async connection recovery"""
        try:
            self.stats["recovery_attempts"] += 1
            logger.info(f"Attempting async database connection recovery (attempt #{self.stats['recovery_attempts']})")

            # Close existing connections
            await self.connection_manager.close_database()

            # Reinitialize
            await self.connection_manager._ensure_async_connection()

            # Test the new connection
            health = await self._check_connection_async()
            if health["status"] == "success":
                self.stats["successful_recoveries"] += 1
                self._failure_count = 0
                logger.info("Async database connection recovery successful")
                return True
            else:
                logger.error("Async database connection recovery failed")
                return False

        except Exception as e:
            logger.error(f"Async database connection recovery error: {e}")
            return False

    async def _monitor_loop(self):
        """Main async monitoring loop"""
        logger.info("Async database connection monitor started")

        while self._running:
            try:
                self.stats["total_checks"] += 1
                self._last_check = datetime.now()

                # Check connection
                check_result = await self._check_connection_async()

                # Log connection status periodically or on changes
                if check_result["status"] != "success":
                    logger.warning(f"Database connection check failed: {check_result}")
                elif self.stats["total_checks"] % 10 == 0:  # Log success every 10 checks
                    logger.debug(f"Database connection healthy (check #{self.stats['total_checks']})")

                # Attempt recovery if failure threshold reached
                if self._failure_count >= self.failure_threshold:
                    logger.warning(
                        f"Failure threshold reached ({self._failure_count}/{self.failure_threshold}), attempting recovery"
                    )
                    await self._attempt_recovery_async()

                # Update stats
                if self.stats["total_checks"] > 0:
                    self.stats["uptime_percentage"] = (
                        self.stats["successful_checks"] / self.stats["total_checks"]
                    ) * 100

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)

        logger.info("Async database connection monitor stopped")

    async def start_monitoring(self):
        """Start async monitoring"""
        if self._running:
            logger.warning("Async connection monitor is already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Async database connection monitor started")

    async def stop_monitoring(self):
        """Stop async monitoring"""
        if not self._running:
            logger.warning("Async connection monitor is not running")
            return

        logger.info("Stopping async database connection monitor...")
        self._running = False

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self._monitor_task = None
        logger.info("Async database connection monitor stopped")

    async def force_recovery(self) -> bool:
        """Force async connection recovery"""
        logger.info("Forcing async database connection recovery")
        return await self._attempt_recovery_async()

    def get_status(self) -> dict:
        """Get monitor status"""
        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "failure_threshold": self.failure_threshold,
            "failure_count": self._failure_count,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "last_success": self._last_success.isoformat() if self._last_success else None,
            "last_failure": self._last_failure.isoformat() if self._last_failure else None,
            "stats": self.stats.copy(),
        }
