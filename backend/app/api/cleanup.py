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

        # Validate and sanitize config values
        enabled = config.get("enabled", False)
        if not isinstance(enabled, bool):
            enabled = False

        max_age_days = config.get("max_age_days", 30)
        if not isinstance(max_age_days, int) or max_age_days < 1 or max_age_days > 365:
            max_age_days = 30

        cleanup_interval_hours = config.get("cleanup_interval_hours", 24)
        if (
            not isinstance(cleanup_interval_hours, int) or cleanup_interval_hours < 1 or cleanup_interval_hours > 168
        ):  # 168 hours = 1 week
            cleanup_interval_hours = 24

        return {
            "enabled": enabled,
            "max_age_days": max_age_days,
            "cleanup_interval_hours": cleanup_interval_hours,
            "last_cleanup": config.get("last_cleanup"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup-config")
async def get_cleanup_config():
    """Get auto cleanup config for reports"""
    try:
        config = load_cleanup_config()

        # Sanitize config to remove any potentially sensitive information
        if isinstance(config, dict):
            sanitized_config = {}
            for key, value in config.items():
                if key == "last_cleanup":
                    # Keep timestamp as is
                    sanitized_config[key] = value
                elif key in ["enabled", "max_age_days", "cleanup_interval_hours"]:
                    # Validate numeric/boolean values
                    if key == "enabled":
                        sanitized_config[key] = bool(value) if isinstance(value, bool) else False
                    elif key in ["max_age_days", "cleanup_interval_hours"]:
                        if isinstance(value, int) and 1 <= value <= (365 if key == "max_age_days" else 168):
                            sanitized_config[key] = value
                        else:
                            sanitized_config[key] = 30 if key == "max_age_days" else 24
                else:
                    # Skip unknown keys for security
                    continue
            return sanitized_config
        else:
            return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
