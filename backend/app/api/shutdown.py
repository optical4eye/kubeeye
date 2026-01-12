#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shutdown functions for FastAPI application
"""

from core.logging import get_logger

logger = get_logger(__name__)


async def _shutdown_task_queue():
    """Stop the async task queue on shutdown"""
    try:
        from infra.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        await task_queue.stop()
        logger.info("Async task queue stopped on application shutdown")
    except Exception as e:
        logger.error(f"Failed to stop task queue on shutdown: {e}")


async def _close_ssh_pool():
    """Close SSH connection pool on shutdown"""
    try:
        from infra.dependency_injection.container import get_service

        ssh_service = await get_service("ssh_service")
        await ssh_service.close_all_connections()
        logger.info("SSH connection pool closed on application shutdown")
    except Exception as e:
        logger.error(f"Failed to close SSH connection pool on shutdown: {e}")


async def _cleanup_services():
    """Cleanup all DI services on shutdown"""
    try:
        from infra.dependency_injection.container import cleanup_services

        await cleanup_services()
        logger.info("DI services cleaned up on application shutdown")
    except Exception as e:
        logger.error(f"Failed to cleanup DI services on shutdown: {e}")


async def _stop_database_monitoring():
    """РћСЃС‚Р°РЅРѕРІРєР° Р°СЃРёРЅС…СЂРѕРЅРЅРѕРіРѕ РјРѕРЅРёС‚РѕСЂРёРЅРіР° РїРѕРґРєР»СЋС‡РµРЅРёР№ Рє Р±Р°Р·Рµ РґР°РЅРЅС‹С…"""
    try:
        from db.database import stop_connection_monitoring

        await stop_connection_monitoring()
        logger.info("Async database connection monitoring stopped on application shutdown")
    except Exception as e:
        logger.error(f"Failed to stop async database monitoring on shutdown: {e}")


async def _close_database_connections():
    """Р—Р°РєСЂС‹С‚РёРµ РІСЃРµС… Р°СЃРёРЅС…СЂРѕРЅРЅС‹С… РїРѕРґРєР»СЋС‡РµРЅРёР№ Рє Р±Р°Р·Рµ РґР°РЅРЅС‹С… РїСЂРё Р·Р°РІРµСЂС€РµРЅРёРё РїСЂРёР»РѕР¶РµРЅРёСЏ"""
    try:
        from db.database import close_database

        await close_database()
        logger.info("Async database connections closed on application shutdown")
    except Exception as e:
        logger.error(f"Failed to close async database connections on shutdown: {e}")
