#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup functions for FastAPI application
"""

from core.logging import get_logger

logger = get_logger(__name__)
# Import models to ensure they are registered with SQLAlchemy Base.metadata
from db.models import (  # pylint: disable=unused-import
    Cluster,
    InspectionResult,
    ScheduledTask,
    EncryptionKey,
)


async def _init_database():
    """Initialize async database tables with retry mechanism"""
    try:
        logger.info("Starting database initialization process...")
        from db.database import init_database, health_check, start_connection_monitoring

        logger.info("Initializing async database connection...")
        # Form database URL from individual env vars for logging
        from db.database import get_database_url

        db_url = get_database_url()
        # Better URL masking for security
        if "://" in db_url:
            protocol = db_url.split("://")[0]
            rest = db_url.split("://")[1]
            if "@" in rest:
                # Mask credentials: postgresql://user:pass@host:port/db -> postgresql://***:***@host:port/db
                auth_part, host_part = rest.split("@", 1)
                if ":" in auth_part:
                    masked_auth = "***:***"
                else:
                    masked_auth = "***"
                safe_url = f"{protocol}://{masked_auth}@{host_part}"
            else:
                safe_url = db_url
        else:
            safe_url = db_url

        logger.info(f"Database URL: {safe_url}")

        # Инициализация асинхронной базы данных с механизмом повторных попыток
        await init_database()
        logger.info("Async database init_database() completed")

        # Проверка состояния базы данных
        health = await health_check()
        logger.info(f"Async database health check result: {health}")

        if health.get("status") == "healthy":
            logger.info("Async database initialized successfully on application startup")
        else:
            logger.warning(f"Async database initialized with warnings: {health.get('message', 'Unknown warning')}")

        # Запуск асинхронного мониторинга подключений
        logger.info("Starting async database connection monitoring...")
        await start_connection_monitoring()
        logger.info("Async database connection monitoring started")

        logger.info("Database initialization process completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize async database on startup: {e}", exc_info=True)
        logger.warning(
            "Continuing startup despite async database initialization failure - retry mechanism will work in background"
        )
        return


async def _start_task_manager():
    """Initialize and start the new task manager"""
    try:
        logger.info("Starting task manager initialization...")
        from infra.dependency_injection.container import get_service

        # Откладываем запуск task manager на несколько секунд, чтобы избежать конфликта event loop
        import asyncio

        logger.info("Waiting 5 seconds before starting task manager to avoid event loop conflicts...")
        await asyncio.sleep(5)

        logger.info("Getting task manager service...")
        task_manager = await get_service("task_manager")

        logger.info("Initializing task manager...")
        result = await task_manager.initialize()
        if result:
            logger.info("Task manager initialized successfully on application startup")
        else:
            logger.error("Task manager initialization returned False")
    except Exception as e:
        logger.error(f"Failed to start task manager on startup: {e}", exc_info=True)


async def _start_task_queue():
    """Initialize and start the async task queue"""
    try:
        from infra.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        await task_queue.start()
        logger.info("Async task queue initialized on application startup")
    except Exception as e:
        logger.error(f"Failed to start task queue on startup: {e}")


async def _start_cleanup_worker():
    """Start the automatic cleanup background worker using asyncio"""
    try:
        import asyncio
        from scripts.database_cleanup import run_database_cleanup

        async def cleanup_worker():
            """Run cleanup every 24 hours"""
            while True:
                try:
                    logger.info("Starting scheduled database cleanup...")
                    await run_database_cleanup()
                    logger.info("Scheduled database cleanup completed successfully")
                except Exception as e:
                    logger.error(f"Cleanup error: {e}", exc_info=True)
                # Wait 24 hours before next cleanup
                await asyncio.sleep(24 * 3600)

        # Run initial cleanup on startup
        try:
            logger.info("Running initial database cleanup on startup...")
            await run_database_cleanup()
            logger.info("Initial database cleanup completed successfully")
        except Exception as e:
            logger.error(f"Initial cleanup failed: {e}", exc_info=True)

        # Start background cleanup task
        asyncio.create_task(cleanup_worker())
        logger.info("Automatic cleanup initialized on application startup")
    except Exception as e:
        logger.error(f"Failed to start automatic cleanup: {e}", exc_info=True)


async def _start_database_monitoring():
    """Запуск асинхронного мониторинга подключений к базе данных"""
    try:
        from db.database import start_connection_monitoring

        await start_connection_monitoring()
        logger.info("Async database connection monitoring started on application startup")
    except Exception as e:
        logger.error(f"Failed to start async database monitoring on startup: {e}")


async def _init_encryption_key():
    """Initialize encryption key from database on startup"""
    try:
        logger.info("Initializing encryption key from database...")
        from infra.security.crypto_utils import initialize_encryption_key
        from db.database import get_session_local

        # Get session factory and create session
        session_factory = get_session_local()
        async with session_factory() as db:
            # Initialize encryption key from database
            await initialize_encryption_key(db)
            logger.info("Encryption key initialized successfully from database")
    except Exception as e:
        logger.error(f"Failed to initialize encryption key on startup: {e}", exc_info=True)
        # Don't fail startup if encryption key initialization fails
        # It will be initialized on first use


async def _init_websocket_subscriptions():
    """Initialize WebSocket event subscriptions"""
    try:
        logger.info("Initializing WebSocket event subscriptions...")
        from core.events.event_bus import init_websocket_subscriptions

        await init_websocket_subscriptions()
        logger.info("WebSocket event subscriptions initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket subscriptions on startup: {e}", exc_info=True)
