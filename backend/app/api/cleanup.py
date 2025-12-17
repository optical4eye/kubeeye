#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup management routes
"""

from fastapi import APIRouter, HTTPException
from scripts.cleanup_reports import load_cleanup_config

router = APIRouter()


@router.get("/cleanup")
async def get_cleanup_status():
    """Get cleanup status"""
    try:
        config = load_cleanup_config()
        return {
            "enabled": config.get("enabled", False),
            "max_age_days": config.get("max_age_days", 30),
            "cleanup_interval_hours": config.get("cleanup_interval_hours", 24),
            "last_cleanup": config.get("last_cleanup"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup-config")
async def get_cleanup_config():
    """Get auto cleanup config for reports"""
    try:
        config = load_cleanup_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
