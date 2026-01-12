#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic API routes for KubeEye
"""

# Local imports
from core.logging import log_api_request
from fastapi import APIRouter
from .version import VERSION

router = APIRouter()


# Root endpoint
@router.get("/")
@log_api_request
async def root():
    """Root endpoint with API information"""
    return {
        "message": "KubeEye API",
        "version": VERSION,
        "description": "Kubernetes cluster inspection tool with security focus",
        "docs": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "endpoints": {
            "health": "/api/health",
            "health_db": "/api/health/db",
            "health_db_monitor": "/api/health/db/monitor",
            "health_db_recover": "/api/health/db/recover",
            "clusters": "/api/clusters",
            "inspection": "/api/inspection",
            "reports": "/api/reports",
            "rules": "/api/rules",
            "scheduled_tasks": "/api/scheduled-tasks",
            "gitops": "/api/gitops",
            "cleanup": "/api/cleanup",
            "network-check": "/api/network-check",
            "secrets": "/api/secrets",
        },
    }


# API information endpoint
@router.get("/api/info")
@log_api_request
async def api_info():
    """Get detailed API information"""
    return {
        "name": "KubeEye API",
        "version": VERSION,
        "description": "Comprehensive Kubernetes cluster inspection and security analysis tool",
        "features": [
            "Multi-cluster management",
            "Automated security inspections",
            "Rule-based compliance checking",
            "Scheduled assessments",
            "Multiple report formats (JSON, Excel, PDF)",
            "GitOps integration for rule management",
            "Real-time monitoring and alerting",
        ],
        "security": [
            "Read-only operations only",
            "Command security validation",
            "Encrypted sensitive data storage",
            "Secret management system",
            "Audit logging",
            "SSH connection security checks",
        ],
        "supported_inspection_types": ["node", "opa"],
        "documentation": {
            "swagger_ui": "/docs",
            "interactive_api_docs": "/redoc",
            "openapi_specification": "/openapi.json",
        },
    }
