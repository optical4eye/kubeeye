#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API endpoints for report cleanup management
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from core.config.settings import settings
from services.components.report_cleanup_service import (
    get_report_cleanup_service,
    cleanup_old_reports,
    get_cleanup_stats,
    cleanup_reports_by_cluster,
)

from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/cleanup/stats")
async def get_cleanup_statistics():
    """Get cleanup statistics"""
    try:
        stats = await get_cleanup_stats()
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        return stats
    except Exception as e:
        logger.error(f"Failed to get cleanup statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/run")
async def run_cleanup(
    retention_days: Optional[int] = Query(None, description="Number of days to keep reports (overrides config)")
):
    """Run cleanup of old reports"""
    try:
        result = await cleanup_old_reports(retention_days)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Failed to run cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/cluster/{cluster_name}")
async def run_cluster_cleanup(
    cluster_name: str,
    retention_days: Optional[int] = Query(None, description="Number of days to keep reports (overrides config)"),
):
    """Run cleanup of old reports for specific cluster"""
    try:
        result = await cleanup_reports_by_cluster(cluster_name, retention_days)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Failed to run cluster cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup/config")
async def get_cleanup_config():
    """Get current cleanup configuration"""
    try:
        retention_days = settings.kubeeye_report_retention_days
        logger.info(f"New cleanup/config endpoint called. REPORT_RETENTION_DAYS={retention_days}")
        service = get_report_cleanup_service()
        source = "settings"
        logger.info(f"Returning retention_days={service.retention_days}, source={source}")
        return {
            "retention_days": service.retention_days,
            "source": source,
            "env_variable": "KUBEEYE_REPORT_RETENTION_DAYS",
            "default_value": 7,
        }
    except Exception as e:
        logger.error(f"Failed to get cleanup config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
