#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection routes with async queue processing
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.components.inspection_engine import execute_inspection_unified
from infra.tasks.task_queue import submit_inspection_task, get_task_queue
from core.common.unified_validation import validate_task_id
from .models import InspectionRequest
from api.dependencies import get_current_user
from db.models.user import User
from core.rbac import Permission, require_permission


# Response models for better OpenAPI documentation
class InspectionResponse(BaseModel):
    """Response model for inspection results"""

    message: str
    results: Dict[str, Any]


class AsyncInspectionResponse(BaseModel):
    """Response model for async inspection submission"""

    task_id: str
    message: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response model for task status"""

    task_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AsyncInspectionRequest(BaseModel):
    """Request model for async inspection"""

    cluster_name: str
    selected_rules: Optional[Dict[str, Any]] = None
    selected_tags: Optional[Dict[str, Any]] = None
    inspection_type: str = "immediate"
    use_gitops: bool = False


@router.post(
    "/inspection",
    summary="Run immediate cluster inspection",
    description="""
    Execute a synchronous security inspection on specified Kubernetes cluster.

    This endpoint runs inspections immediately and returns results directly.
    For large clusters or complex inspections, consider using async endpoint.

    **Supported inspection types:**
    - Node-level security checks (SSH-based)
    - OPA policy validation
    - Popeye resource analysis

    **Response includes:**
    - Inspection results by inspector type
    - Security findings and recommendations
    - Compliance status
    """,
    response_model=InspectionResponse,
    response_description="Inspection results with security findings and compliance status",
)
@require_permission(Permission.INSPECTION_RUN)
async def run_immediate_inspection(
    request: InspectionRequest, current_user: Annotated[User, Depends(get_current_user)]
):
    """Run synchronous cluster inspection with comprehensive security analysis."""
    try:
        logger.info(f"Starting synchronous inspection for cluster: {request.cluster_name}")

        # Determine whether to use GitOps rules
        from infra.rules.rule_manager import RuleManager

        use_gitops = RuleManager.should_use_gitops()

        success, message, results = await execute_inspection_unified(
            cluster_name=request.cluster_name,
            selected_rules=request.selected_rules,
            selected_tags=request.selected_tags,
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

        # Serialize InspectionResult objects for JSON response
        results_serializable = {}
        if results:
            for inspector_name, inspection_result in results.items():
                if hasattr(inspection_result, "get_summary"):
                    results_serializable[inspector_name] = inspection_result.get_summary()
                elif hasattr(inspection_result, "to_dict"):
                    results_serializable[inspector_name] = inspection_result.to_dict()
                else:
                    # Fallback: convert to string representation
                    results_serializable[inspector_name] = str(inspection_result)

        logger.info(f"Inspection completed successfully for cluster: {request.cluster_name}")
        return {"message": message, "results": results_serializable}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during inspection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inspection error: {str(e)}")


@router.post(
    "/inspection/async",
    summary="Run asynchronous cluster inspection",
    description="""
    Submit a cluster inspection task to background queue for asynchronous processing.

    This endpoint is recommended for:
    - Large clusters with many nodes
    - Complex inspections with multiple rule types
    - Scheduled or automated workflows

    The task will be processed in background and results can be retrieved using task status endpoint.

    **Returns:**
    - Task ID for status tracking
    - Initial status (pending)
    """,
    response_model=AsyncInspectionResponse,
    response_description="Task submission confirmation with task ID",
    status_code=202,
)
@require_permission(Permission.INSPECTION_CREATE)
async def run_async_inspection(
    request: AsyncInspectionRequest, current_user: Annotated[User, Depends(get_current_user)]
):
    """Submit cluster inspection to background queue for asynchronous processing."""
    try:
        logger.info(f"Submitting async inspection task for cluster: {request.cluster_name}")

        # Determine whether to use GitOps rules if not specified
        if not request.use_gitops:
            from infra.rules.rule_manager import RuleManager

            request.use_gitops = RuleManager.should_use_gitops()

        task_id = await submit_inspection_task(
            cluster_name=request.cluster_name,
            selected_rules=request.selected_rules,
            selected_tags=request.selected_tags,
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


@router.get(
    "/inspection/task/{task_id}",
    summary="Get inspection task status",
    description="""
    Retrieve current status and progress of an asynchronous inspection task.

    **Status values:**
    - `pending`: Task is queued and waiting to start
    - `running`: Task is currently executing
    - `completed`: Task finished successfully with results
    - `failed`: Task encountered an error

    **Response includes:**
    - Current status and progress information
    - Results when task is completed
    - Error details if task failed
    - Timestamps for task lifecycle
    """,
    response_model=TaskStatusResponse,
    response_description="Current task status with progress and results if available",
)
async def get_inspection_task_status(task_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    """Get current status and progress of asynchronous inspection task."""
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


@router.delete(
    "/inspection/task/{task_id}",
    summary="Cancel inspection task",
    description="""
    Cancel a running or pending asynchronous inspection task.

    **Note:** Only pending or running tasks can be cancelled.
    Completed or failed tasks cannot be cancelled.

    **Response:** Confirmation message indicating successful cancellation.
    """,
    response_description="Task cancellation confirmation",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"description": "Task cannot be cancelled (already completed or running)"},
        404: {"description": "Task not found"},
    },
)
@require_permission(Permission.INSPECTION_DELETE)
async def cancel_inspection_task(task_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    """Cancel a running or pending asynchronous inspection task."""
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
