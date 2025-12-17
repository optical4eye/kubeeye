#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI application and shared dependencies
"""

# Standard library imports
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

# Third-party imports
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Local imports
from infrastructure.common.version import VERSION
from infrastructure.logging.enhanced_logging import (
    log_api_request,
    request_id,
)
from infrastructure.logging.logging_config import get_system_health

# Import route modules
from . import (
    clusters,
    inspection,
    reports,
    scheduled_tasks,
    rules,
    gitops,
    cleanup,
    network,
)

# Constants
DATA_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
CLUSTERS_DIR = DATA_DIR / "clusters"
RESULTS_DIR = DATA_DIR / "results"
LOGS_DIR = DATA_DIR / "logs"
SCHEDULES_DIR = DATA_DIR / "schedules"
GIT_RULES_DIR = DATA_DIR / "git_rules"

# Setup logger
logger = logging.getLogger(__name__)


def handle_api_exceptions(default_status_code: int = 500, default_message: str = "Internal server error"):
    """
    Decorator for handling API exceptions consistently

    Args:
        default_status_code: Default HTTP status code for exceptions
        default_message: Default error message
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise HTTPException(status_code=default_status_code, detail=default_message)

        return wrapper

    return decorator


# Ensure data directories exist
CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)
GIT_RULES_DIR.mkdir(parents=True, exist_ok=True)


def _start_scheduler():
    """Initialize and start the scheduler"""
    try:
        from infrastructure.tasks.schedule_manager import start_scheduler

        start_scheduler()
        logger.info("Scheduler initialized on application startup")
    except Exception as e:
        logger.error(f"Failed to start scheduler on startup: {e}")


async def _start_task_queue():
    """Initialize and start the async task queue"""
    try:
        from infrastructure.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        await task_queue.start()
        logger.info("Async task queue initialized on application startup")
    except Exception as e:
        logger.error(f"Failed to start task queue on startup: {e}")


def _start_cleanup_worker():
    """Start the automatic cleanup background worker"""
    try:
        import threading
        import time
        from scripts.cleanup_reports import run_cleanup

        def cleanup_worker():
            """Run cleanup every 24 hours"""
            while True:
                try:
                    run_cleanup()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
                time.sleep(24 * 3600)  # 24 hours

        # Run cleanup immediately on startup
        run_cleanup()

        # Start background cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Automatic cleanup initialized on application startup")
    except Exception as e:
        logger.error(f"Failed to start automatic cleanup: {e}")


async def _shutdown_task_queue():
    """Stop the async task queue on shutdown"""
    try:
        from infrastructure.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        await task_queue.stop()
        logger.info("Async task queue stopped on application shutdown")
    except Exception as e:
        logger.error(f"Failed to stop task queue on shutdown: {e}")


async def _close_ssh_pool():
    """Close SSH connection pool on shutdown"""
    try:
        from infrastructure.dependency_injection.container import get_service

        ssh_pool = await get_service("ssh_pool")
        await ssh_pool.close_all()
        logger.info("SSH connection pool closed on application shutdown")
    except Exception as e:
        logger.error(f"Failed to close SSH connection pool on shutdown: {e}")


async def _cleanup_services():
    """Cleanup all DI services on shutdown"""
    try:
        from infrastructure.dependency_injection.container import cleanup_services

        await cleanup_services()
        logger.info("DI services cleaned up on application shutdown")
    except Exception as e:
        logger.error(f"Failed to cleanup DI services on shutdown: {e}")


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events"""
    # Startup
    _start_scheduler()
    await _start_task_queue()
    _start_cleanup_worker()

    yield

    # Shutdown
    await _shutdown_task_queue()
    await _close_ssh_pool()
    await _cleanup_services()


app = FastAPI(
    title="KubeEye API",
    description="""
    # KubeEye - Kubernetes Cluster Inspection Tool API

    A comprehensive API for inspecting Kubernetes clusters with a focus on security and compliance.

    ## Features

    * **Cluster Management**: Add, configure, and manage multiple Kubernetes clusters
    * **Security Inspections**: Run automated security checks on nodes, pods, and configurations
    * **Rule-based Analysis**: Use customizable rules for compliance checking
    * **Scheduled Inspections**: Automate regular cluster assessments
    * **Report Generation**: Export inspection results in multiple formats (JSON, Excel, PDF)
    * **GitOps Integration**: Manage inspection rules through Git repositories

    ## Security

    All operations are read-only and follow strict security guidelines to ensure cluster safety.

    ## Authentication

    Currently uses basic authentication. For production deployments, consider implementing proper authentication mechanisms.
    """,
    version=VERSION,
    contact={
        "name": "KubeEye Team",
        "url": "https://github.com/optical4eye/kubeeye",
    },
    license_info={
        "name": "MIT License",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware for logging HTTP requests"""
    import uuid

    # Generate request ID
    req_id = str(uuid.uuid4())[:8]
    request_id.set(req_id)

    start_time = time.time()

    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "extra_fields": {
                "request_id": req_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "user_agent": request.headers.get("user-agent", ""),
                "ip": request.client.host if request.client else "unknown",
            }
        },
    )

    try:
        response = await call_next(request)
        execution_time = time.time() - start_time

        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "extra_fields": {
                    "request_id": req_id,
                    "status_code": response.status_code,
                    "execution_time": execution_time,
                }
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = req_id
        return response

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)}",
            extra={
                "extra_fields": {
                    "request_id": req_id,
                    "execution_time": execution_time,
                    "error": str(e),
                }
            },
            exc_info=True,
        )
        raise


# Add validation middleware
from .validation_middleware import ValidationMiddleware

app.add_middleware(ValidationMiddleware, max_query_length=1000)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify concrete origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
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
            "clusters": "/api/clusters",
            "inspection": "/api/inspection",
            "reports": "/api/reports",
            "rules": "/api/rules",
            "scheduled_tasks": "/api/scheduled-tasks",
            "gitops": "/api/gitops",
            "cleanup": "/api/cleanup",
            "network-check": "/api/network-check",
        },
    }


# API information endpoint
@app.get("/api/info")
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
            "Audit logging",
            "SSH connection security checks",
        ],
        "supported_inspection_types": ["node", "prometheus", "opa"],
        "documentation": {
            "swagger_ui": "/docs",
            "interactive_api_docs": "/redoc",
            "openapi_specification": "/openapi.json",
        },
    }


# Health check endpoint
@app.get("/api/health")
@log_api_request
async def health_check():
    """System health check endpoint"""
    try:
        health_info = get_system_health()

        # Check task queue status
        from infrastructure.dependency_injection.container import get_service

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


# Task queue management endpoints
@app.get("/api/queue/status")
@log_api_request
async def get_queue_status():
    """Get task queue status"""
    try:
        from infrastructure.dependency_injection.container import get_service

        task_queue = await get_service("task_queue")
        return {
            "running": task_queue.running,
            "max_workers": task_queue.max_workers,
            "queue_size": task_queue.queue.qsize(),
            "active_tasks": len([t for t in task_queue.tasks.values() if t.status.value == "running"]),
            "pending_tasks": len([t for t in task_queue.tasks.values() if t.status.value == "pending"]),
            "total_tasks": len(task_queue.tasks),
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@app.get("/api/queue/tasks")
@log_api_request
async def get_queue_tasks(
    limit: int = Query(default=50, ge=1, le=1000, description="Maximum number of tasks to return (1-1000)"),
    status_filter: Optional[str] = Query(
        default=None, description="Filter tasks by status (pending, running, completed, failed)"
    ),
):
    """Get recent tasks from queue"""
    try:
        from infrastructure.dependency_injection.container import get_service

        # Validate parameters using our validation functions
        from .validation_middleware import validate_limit_param, validate_status_filter

        validated_limit = validate_limit_param(limit)
        validated_status_filter = validate_status_filter(status_filter)

        task_queue = await get_service("task_queue")
        # Get tasks sorted by creation time (newest first)
        tasks = list(task_queue.tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply status filter if provided
        if validated_status_filter:
            tasks = [t for t in tasks if t.status.value == validated_status_filter]

        return {
            "tasks": [task.to_dict() for task in tasks[:validated_limit]],
            "total": len(tasks),
            "filtered": validated_status_filter is not None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tasks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


# Import and include all route modules

app.include_router(clusters.router, prefix="/api", tags=["clusters"])
app.include_router(inspection.router, prefix="/api", tags=["inspection"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(scheduled_tasks.router, prefix="/api", tags=["scheduled-tasks"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(gitops.router, prefix="/api", tags=["gitops"])
app.include_router(cleanup.router, prefix="/api", tags=["cleanup"])
app.include_router(network.router, prefix="/api", tags=["network"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
