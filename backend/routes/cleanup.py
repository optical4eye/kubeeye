#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup management routes
"""

from fastapi import APIRouter, HTTPException
from cleanup_reports import load_cleanup_config

router = APIRouter()


@router.get("/cleanup-config")
async def get_cleanup_config():
    """Get auto cleanup config for reports"""
    try:
        config = load_cleanup_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
