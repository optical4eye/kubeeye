#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI application and shared dependencies
"""

import logging
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
import uvicorn
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Import enhanced logging
from utils.enhanced_logging import log_api_request, ErrorBoundary, request_id
from utils.logging_config import get_system_health

# Import existing modules
from utils.cluster_config import list_clusters, get_cluster, delete_cluster
from utils.inspection_result import list_results, load_result, export_report
from utils.rule_loader import load_rules
from utils.rule_manager import RuleManager
from utils.schedule_manager import (
    load_schedules,
    add_schedule,
    delete_schedule,
    run_inspection,
    update_task_status,
)
from components.inspection_engine import execute_inspection_unified
from utils.version import VERSION
from cleanup_reports import load_cleanup_config

# Setup logger
logger = logging.getLogger(__name__)

# Ensure data directories exist
DATA_DIR = Path(__file__).parent.parent / "data"
CLUSTERS_DIR = DATA_DIR / "clusters"
RESULTS_DIR = DATA_DIR / "results"
CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="KubeEye API",
    description="Kubernetes cluster inspection tool API",
    version=VERSION,
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


# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify concrete origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ClusterCreate(BaseModel):
    name: str
    nodes: List[Dict[str, Any]]
    prometheus_config: Optional[Dict[str, Any]] = None
    kubeconfig: Optional[str] = None


class InspectionRequest(BaseModel):
    cluster_name: str
    selected_rules: Dict[str, List[str]]
    inspection_type: str = "immediate"


class ScheduledTaskCreate(BaseModel):
    name: str
    description: str = Field(..., min_length=1)
    cluster: str
    cron_expr: str
    rules: Dict[str, Any]
    enabled: bool = True
    task_type: Optional[str] = None
    run_datetime: Optional[str] = None


class TestNodesRequest(BaseModel):
    nodes: List[Dict[str, Any]]


class TestKubeconfigRequest(BaseModel):
    kubeconfig: str


# Startup event to initialize scheduler and task queue
@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and task queue on startup"""
    try:
        from utils.schedule_manager import start_scheduler

        start_scheduler()
        print("Scheduler initialized on application startup")
    except Exception as e:
        print(f"Failed to start scheduler on startup: {e}")

    # Start task queue
    try:
        from utils.task_queue import task_queue

        await task_queue.start()
        print("Async task queue initialized on application startup")
    except Exception as e:
        print(f"Failed to start task queue on startup: {e}")

    # Start automatic cleanup thread
    try:
        import threading
        import time
        from cleanup_reports import run_cleanup

        def cleanup_worker():
            """Run cleanup every 24 hours"""
            while True:
                try:
                    run_cleanup()
                except Exception as e:
                    print(f"Cleanup error: {e}")
                time.sleep(24 * 3600)  # 24 hours

        # Run cleanup immediately on startup
        run_cleanup()

        # Start background cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        print("Automatic cleanup initialized on application startup")
    except Exception as e:
        print(f"Failed to start automatic cleanup: {e}")


# Shutdown event to cleanup resources
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    try:
        from utils.task_queue import task_queue

        await task_queue.stop()
        print("Async task queue stopped on application shutdown")
    except Exception as e:
        print(f"Failed to stop task queue on shutdown: {e}")


# Root endpoint
@app.get("/")
@log_api_request
async def root():
    """Root endpoint"""
    return {"message": "KubeEye API", "version": VERSION}


# Health check endpoint
@app.get("/api/health")
@log_api_request
async def health_check():
    """System health check endpoint"""
    try:
        health_info = get_system_health()

        # Check task queue status
        from utils.task_queue import task_queue

        queue_status = {
            "running": task_queue.running,
            "queue_size": task_queue.queue.qsize(),
            "active_workers": len(
                [t for t in task_queue.tasks.values() if t.status.value == "running"]
            ),
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
async def get_queue_status():
    """Get task queue status"""
    try:
        from utils.task_queue import task_queue

        return {
            "running": task_queue.running,
            "max_workers": task_queue.max_workers,
            "queue_size": task_queue.queue.qsize(),
            "active_tasks": len(
                [t for t in task_queue.tasks.values() if t.status.value == "running"]
            ),
            "pending_tasks": len(
                [t for t in task_queue.tasks.values() if t.status.value == "pending"]
            ),
            "total_tasks": len(task_queue.tasks),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get queue status: {str(e)}"
        )


@app.get("/api/queue/tasks")
async def get_queue_tasks(limit: int = 50):
    """Get recent tasks from queue"""
    try:
        from utils.task_queue import task_queue

        # Get tasks sorted by creation time (newest first)
        tasks = list(task_queue.tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return {
            "tasks": [task.to_dict() for task in tasks[:limit]],
            "total": len(tasks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


# Import and include all route modules
from . import clusters, inspection, reports, scheduled_tasks, rules, gitops, cleanup

app.include_router(clusters.router, prefix="/api", tags=["clusters"])
app.include_router(inspection.router, prefix="/api", tags=["inspection"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(scheduled_tasks.router, prefix="/api", tags=["scheduled-tasks"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(gitops.router, prefix="/api", tags=["gitops"])
app.include_router(cleanup.router, prefix="/api", tags=["cleanup"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
