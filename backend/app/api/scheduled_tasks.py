#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduled tasks routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from .models import ScheduledTaskCreate
from infra.dependency_injection.container import get_service
from core.common.schedule_utils import calculate_next_run
from core.common.metrics import count_requests, time_operation
from core.common.unified_validation import validate_task_id
from api.dependencies import get_current_user
from db.models.user import User
from services.audit_service import AuditService
from core.rbac import Permission, require_permission

router = APIRouter()


@router.get("/scheduled-tasks")
@count_requests("scheduled_tasks_list")
@time_operation("api_get_scheduled_tasks")
@require_permission(Permission.SCHEDULE_READ)
async def get_scheduled_tasks(current_user: User = Depends(get_current_user)):
    """Get scheduled tasks"""
    try:
        task_manager = await get_service("task_manager")
        tasks = await task_manager.get_all_tasks()

        # Add computed fields for compatibility
        for task in tasks:
            # Calculate next_run if not present
            if "next_run" not in task and task.get("cron_expr"):
                task["next_run"] = calculate_next_run(task["cron_expr"])

        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled-tasks/{task_id}")
@count_requests("scheduled_tasks_get")
@time_operation("api_get_scheduled_task")
@require_permission(Permission.SCHEDULE_READ)
async def get_scheduled_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get specific scheduled task"""
    try:
        # Validate task_id parameter using centralized validation
        validated_task_id = validate_task_id(task_id)

        task_manager = await get_service("task_manager")
        task = await task_manager.get_task(validated_task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Add computed fields for compatibility
        if "next_run" not in task and task.get("cron_expr"):
            task["next_run"] = calculate_next_run(task["cron_expr"])

        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks")
@count_requests("scheduled_tasks_create")
@time_operation("api_create_scheduled_task")
@require_permission(Permission.SCHEDULE_CREATE)
async def create_scheduled_task(
    task: ScheduledTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create scheduled task"""
    try:
        import time

        task_data = {
            "task_id": f"task_{int(time.time())}",
            "cluster": task.cluster,
            "name": task.name,
            "description": task.description,
            "cron_expr": task.cron_expr if task.cron_expr else "",
            "enabled": task.enabled,
            "rules": task.rules,
            "tags": task.tags,
            "task_type": task.task_type or ("cron" if task.cron_expr else "once"),
            "run_datetime": task.run_datetime if hasattr(task, "run_datetime") else None,
        }

        task_manager = await get_service("task_manager")
        created_task = await task_manager.create_task(task_data)

        if created_task:
            # Log audit with resource name
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                username=current_user.username,
                action="create",
                resource_type="task",
                resource_id=created_task["task_id"],
                resource_name=task.name,
            )

            return {"message": "Task created successfully", "task_id": created_task["task_id"]}
        else:
            raise HTTPException(status_code=500, detail="Failed to create task")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled-tasks/{task_id}")
@count_requests("scheduled_tasks_delete")
@time_operation("api_delete_scheduled_task")
@require_permission(Permission.SCHEDULE_DELETE)
async def remove_scheduled_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete scheduled task"""
    try:
        # Validate task_id parameter using centralized validation
        validated_task_id = validate_task_id(task_id)

        task_manager = await get_service("task_manager")

        # Get task name before deletion
        task = await task_manager.get_task(validated_task_id)
        task_name = task.get("name", validated_task_id) if task else validated_task_id

        if await task_manager.delete_task(validated_task_id):
            # Log audit with resource name
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                username=current_user.username,
                action="delete",
                resource_type="task",
                resource_id=validated_task_id,
                resource_name=task_name,
            )

            return {"message": f"Task {validated_task_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/run")
@count_requests("scheduled_tasks_run")
@time_operation("api_run_scheduled_task")
@require_permission(Permission.TASK_RUN)
async def run_scheduled_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run scheduled task"""
    try:
        # Validate task_id parameter using centralized validation
        validated_task_id = validate_task_id(task_id)

        task_manager = await get_service("task_manager")

        # Get task name for audit
        task = await task_manager.get_task(validated_task_id)
        task_name = task.get("name", validated_task_id) if task else validated_task_id

        result = await task_manager.run_task_now(validated_task_id)

        if result["success"]:
            # Log audit with resource name
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                username=current_user.username,
                action="run",
                resource_type="task",
                resource_id=validated_task_id,
                resource_name=task_name,
            )

            return {"message": result["message"], "results": result.get("results")}
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled-tasks/{task_id}")
@count_requests("scheduled_tasks_update")
@time_operation("api_update_scheduled_task")
@require_permission(Permission.SCHEDULE_UPDATE)
async def update_scheduled_task(
    task_id: str,
    task: ScheduledTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update scheduled task"""
    try:
        # Validate task_id parameter using centralized validation
        validated_task_id = validate_task_id(task_id)

        # Prepare update data
        update_data = {
            "cluster": task.cluster,
            "name": task.name,
            "description": task.description,
            "cron_expr": task.cron_expr if task.cron_expr else "",
            "enabled": task.enabled,
            "rules": task.rules,
            "tags": task.tags,
            "task_type": task.task_type or ("cron" if task.cron_expr else "once"),
            "run_datetime": task.run_datetime,
        }

        task_manager = await get_service("task_manager")
        if await task_manager.update_task(validated_task_id, update_data):
            # Log audit with resource name
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                username=current_user.username,
                action="update",
                resource_type="task",
                resource_id=validated_task_id,
                resource_name=task.name,
            )
            return {"message": "Task updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
