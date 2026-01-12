#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health check endpoints for KubeEye API
"""

# Standard library imports
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, HTTPException

# Local imports
from core.logging import log_api_request, get_system_health, get_logger

# Version definition (moved from main.py)
VERSION = "3.3.0"

router = APIRouter()

# Setup logger
logger = get_logger(__name__)


# Health check endpoint
@router.get("/api/health")
@log_api_request
async def health_check():
    """System health check endpoint"""
    try:
        health_info = get_system_health()

        # Check database health
        from db.database import health_check as db_health_check

        db_health = await db_health_check()
        if db_health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Database is not healthy")

        # Check task queue status
        from infra.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        queue_status = {
            "running": task_queue.running,
            "queue_size": task_queue.queue.qsize(),
            "active_workers": len([t for t in task_queue.tasks.values() if t.status.value == "running"]),
            "pending_tasks": len([t for t in task_queue.tasks.values() if t.status.value == "pending"]),
        }

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": VERSION,
            "queue": queue_status,
            **health_info,
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Database health check endpoint
@router.get("/api/health/db")
@log_api_request
async def health_db():
    """Проверка состояния подключения к БД с детальной информацией."""
    try:
        from db.database import health_check

        # Используем новую функцию проверки состояния
        health_info = await health_check()

        # Добавляем дополнительную информацию
        health_info["timestamp"] = datetime.now().isoformat()
        health_info["service"] = "kubeeye-backend"

        return health_info

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "service": "kubeeye-backend",
        }


# Database monitoring endpoint
@router.get("/api/health/db/monitor")
@log_api_request
async def health_db_monitor():
    """Получение детальной информации о состоянии подключения к БД и мониторинга."""
    try:
        from db.database import get_connection_health

        # Получаем полную информацию о состоянии подключения и мониторинга
        health_info = await get_connection_health()

        return {
            "database": {
                "status": health_info["status"],
                "message": health_info.get("message", ""),
                "connection_type": health_info.get("connection_type", "unknown"),
                "pool_info": health_info.get("pool_info", {}),
            },
            "monitor": health_info.get("monitor_stats", {}),
            "timestamp": datetime.now().isoformat(),
            "service": "kubeeye-backend",
        }

    except Exception as e:
        logger.error(f"Database monitor health check failed: {str(e)}", exc_info=True)
        return {
            "database": {"status": "error", "message": str(e)},
            "monitor": {"status": "error", "message": str(e)},
            "timestamp": datetime.now().isoformat(),
            "service": "kubeeye-backend",
        }


# Force database recovery endpoint
@router.post("/api/health/db/recover")
@log_api_request
async def force_db_recovery():
    """Принудительное восстановление подключения к базе данных."""
    try:
        from db.database import force_connection_recovery

        recovery_result = await force_connection_recovery()

        return {
            "status": "success" if recovery_result else "failed",
            "message": "Database recovery successful" if recovery_result else "Database recovery failed",
            "timestamp": datetime.now().isoformat(),
            "service": "kubeeye-backend",
        }

    except Exception as e:
        logger.error(f"Force database recovery failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "service": "kubeeye-backend",
        }
