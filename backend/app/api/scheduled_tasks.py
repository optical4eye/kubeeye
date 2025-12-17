#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduled tasks routes
"""

from fastapi import APIRouter, HTTPException
from .models import ScheduledTaskCreate

router = APIRouter()


@router.get("/scheduled-tasks")
async def get_scheduled_tasks():
    """Get scheduled tasks"""
    try:
        from infrastructure.tasks.schedule_manager import load_schedules

        tasks = load_schedules()
        # Convert objects to dictionaries and add additional fields
        task_list = []
        for task in tasks:
            task_dict = task.__dict__.copy()
            # Add computed fields
            next_run = task.get_next_run()
            task_dict["next_run"] = next_run.isoformat() if next_run else None
            task_dict["task_type"] = "cron" if task.cron_expr else "once"
            task_list.append(task_dict)
        return {"tasks": task_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks")
async def create_scheduled_task(task: ScheduledTaskCreate):
    """Create scheduled task"""
    try:
        from infrastructure.tasks.schedule_manager import ScheduleTask, add_schedule
        import time

        task_id = f"task_{int(time.time())}"
        schedule_task = ScheduleTask(
            task_id=task_id,
            cluster=task.cluster,
            name=task.name,
            description=task.description,
            cron_expr=task.cron_expr if task.cron_expr else "",
            enabled=task.enabled,
            rules=task.rules,
            task_type=task.task_type or ("cron" if task.cron_expr else "once"),
            run_datetime=task.run_datetime if hasattr(task, "run_datetime") else None,
        )

        if add_schedule(schedule_task):
            return {"message": "Task created successfully", "task_id": task_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create task")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled-tasks/{task_id}")
async def remove_scheduled_task(task_id: str):
    """Delete scheduled task"""
    try:
        # Validate task_id parameter
        from .validation_middleware import validate_task_id

        validated_task_id = validate_task_id(task_id)

        from infrastructure.tasks.schedule_manager import delete_schedule

        if delete_schedule(validated_task_id):
            return {"message": f"Task {validated_task_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/run")
async def run_scheduled_task(task_id: str):
    """Run scheduled task"""
    try:
        # Validate task_id parameter
        from .validation_middleware import validate_task_id

        validated_task_id = validate_task_id(task_id)

        from infrastructure.tasks.schedule_manager import (
            run_inspection,
            update_task_status,
        )

        success, message, results = run_inspection(validated_task_id, return_results=True)
        if success:
            update_task_status(validated_task_id, last_status="success")
            return {"message": message, "results": results}
        else:
            update_task_status(validated_task_id, last_status="failed")
            raise HTTPException(status_code=500, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        update_task_status(validated_task_id, last_status="failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: str, task: ScheduledTaskCreate):
    """Update scheduled task"""
    try:
        # Validate task_id parameter
        from .validation_middleware import validate_task_id

        validated_task_id = validate_task_id(task_id)

        from infrastructure.tasks.schedule_manager import (
            load_schedules,
            delete_schedule,
            ScheduleTask,
            add_schedule,
        )

        # Find existing task
        tasks = load_schedules()
        existing_task = next((t for t in tasks if t.task_id == validated_task_id), None)
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Delete old task
        delete_schedule(validated_task_id)

        # Create updated task
        updated_task = ScheduleTask(
            task_id=validated_task_id,
            cluster=task.cluster,
            name=task.name,
            description=task.description,
            cron_expr=task.cron_expr if task.cron_expr else "",
            enabled=task.enabled,
            rules=task.rules,
            task_type=task.task_type or ("cron" if task.cron_expr else "once"),
            run_datetime=task.run_datetime,
        )

        if add_schedule(updated_task):
            # Reschedule tasks to include the updated one
            from infrastructure.tasks.schedule_manager import schedule_tasks

            schedule_tasks()
            return {"message": "Task updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update task")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
