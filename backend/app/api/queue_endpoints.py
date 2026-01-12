#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task queue management endpoints for KubeEye API
"""

# Third-party imports
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# Local imports
from core.logging import log_api_request, get_logger

router = APIRouter()

logger = get_logger(__name__)


# Task queue management endpoints
@router.get("/api/queue/status")
@log_api_request
async def get_queue_status():
    """Get task queue status"""
    try:
        from infra.dependency_injection.container import get_service

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


@router.get("/api/queue/tasks")
@log_api_request
async def get_queue_tasks(
    limit: int = Query(default=50, ge=1, le=1000, description="Maximum number of tasks to return (1-1000)"),
    status_filter: Optional[str] = Query(
        default=None, description="Filter tasks by status (pending, running, completed, failed)"
    ),
):
    """Get recent tasks from queue"""
    try:
        from infra.dependency_injection.container import get_service

        # Validate parameters using centralized validation functions
        from core.common.unified_validation import validate_limit_param, validate_status_filter

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
