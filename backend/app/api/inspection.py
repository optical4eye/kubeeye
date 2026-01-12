#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection routes with async queue processing
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.components.inspection_engine import execute_inspection_unified
from infra.tasks.task_queue import submit_inspection_task, get_task_queue
from core.common.unified_validation import validate_task_id
from .models import InspectionRequest

from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AsyncInspectionRequest(BaseModel):
    """Request model for async inspection"""

    cluster_name: str
    selected_rules: Optional[Dict[str, Any]] = None
    inspection_type: str = "immediate"
    use_gitops: bool = False


@router.post("/inspection")
async def run_immediate_inspection(request: InspectionRequest, background_tasks: BackgroundTasks):
    """Run inspection synchronously"""
    try:
        logger.info(f"Starting synchronous inspection for cluster: {request.cluster_name}")

        # Determine whether to use GitOps rules
        from infra.rules.rule_manager import RuleManager

        use_gitops = RuleManager.should_use_gitops()

        success, message, results = await execute_inspection_unified(
            cluster_name=request.cluster_name,
            selected_rules=request.selected_rules,
            inspection_type=request.inspection_type,
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=use_gitops,
        )

        # Inspection now always succeeds (errors are recorded in results)
        # Only raise exception for critical infrastructure errors
        if not success and "No inspection types were configured" in message:
            logger.error(f"Inspection failed for cluster {request.cluster_name}: {message}")
            raise HTTPException(status_code=400, detail=message)

        logger.info(f"Inspection completed successfully for cluster: {request.cluster_name}")
        return {"message": message, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during inspection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inspection error: {str(e)}")


@router.post("/inspection/async")
async def run_async_inspection(request: AsyncInspectionRequest):
    """Run inspection asynchronously using task queue"""
    try:
        logger.info(f"Submitting async inspection task for cluster: {request.cluster_name}")

        # Determine whether to use GitOps rules if not specified
        if not request.use_gitops:
            from infra.rules.rule_manager import RuleManager

            request.use_gitops = RuleManager.should_use_gitops()

        task_id = await submit_inspection_task(
            cluster_name=request.cluster_name,
            selected_rules=request.selected_rules,
            inspection_type=request.inspection_type,
            use_gitops=request.use_gitops,
        )

        logger.info(f"Async inspection task submitted: {task_id}")
        return {
            "task_id": task_id,
            "message": "Inspection task submitted successfully",
            "status": "pending",
        }
    except Exception as e:
        logger.error(f"Failed to submit async inspection task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@router.get("/inspection/task/{task_id}")
async def get_inspection_task_status(task_id: str):
    """Get status of async inspection task"""
    try:
        # Validate task_id using centralized validation
        validated_task_id = validate_task_id(task_id)

        logger.info(f"Getting status for task: {validated_task_id}")

        task_queue = await get_task_queue()
        task_status = await task_queue.get_task_status(validated_task_id)

        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")

        return task_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete("/inspection/task/{task_id}")
async def cancel_inspection_task(task_id: str):
    """Cancel async inspection task"""
    try:
        # Validate task_id using centralized validation
        validated_task_id = validate_task_id(task_id)

        logger.info(f"Cancelling task: {validated_task_id}")

        task_queue = await get_task_queue()
        cancelled = await task_queue.cancel_task(validated_task_id)

        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail="Task cannot be cancelled (may be running or completed)",
            )

        logger.info(f"Task cancelled successfully: {validated_task_id}")
        return {"message": "Task cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")
