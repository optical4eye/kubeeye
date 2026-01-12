#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
New task manager using APScheduler and new architecture
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.logging import get_logger
from .interfaces import IScheduler, ITaskExecutor, ITaskRepository

logger = get_logger(__name__)


class TaskManager:
    """New task manager using dependency injection and interfaces"""

    def __init__(self, scheduler: IScheduler, task_executor: ITaskExecutor, task_repository: ITaskRepository):
        self.scheduler = scheduler
        self.task_executor = task_executor
        self.task_repository = task_repository
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the task manager"""
        try:
            if self._initialized:
                return True

            # Start the scheduler
            success = await self.scheduler.start()
            if not success:
                logger.error("Failed to start scheduler")
                return False

            # Load and schedule existing tasks
            await self._load_and_schedule_tasks()

            self._initialized = True
            logger.info("TaskManager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize TaskManager: {e}", exc_info=True)
            return False

    async def shutdown(self) -> bool:
        """Shutdown the task manager"""
        try:
            success = await self.scheduler.stop()
            self._initialized = False
            logger.info("TaskManager shutdown successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to shutdown TaskManager: {e}")
            return False

    async def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new scheduled task"""
        try:
            # Validate task data
            if not await self.task_executor.validate_task(task_data):
                logger.error("Task validation failed")
                return None

            # Create task in repository
            created_task = await self.task_repository.create_task(task_data)

            # Schedule the task
            await self._schedule_task(created_task)

            logger.info(f"Task created and scheduled: {created_task.get('task_id')}")
            return created_task

        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            return None

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing task"""
        try:
            # Update in repository
            success = await self.task_repository.update_task(task_id, updates)
            if not success:
                return False

            # Get updated task
            updated_task = await self.task_repository.get_task(task_id)
            if not updated_task:
                return False

            # Reschedule the task
            await self._reschedule_task(updated_task)

            logger.info(f"Task updated and rescheduled: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
            return False

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        try:
            # Remove from scheduler
            await self.scheduler.remove_job(task_id)

            # Delete from repository
            success = await self.task_repository.delete_task(task_id)

            if success:
                logger.info(f"Task deleted: {task_id}")
            return success

        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        try:
            return await self.task_repository.get_task(task_id)
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        try:
            return await self.task_repository.get_all_tasks()
        except Exception as e:
            logger.error(f"Failed to get all tasks: {e}")
            return []

    async def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """Run a task immediately"""
        try:
            task = await self.get_task(task_id)
            if not task:
                return {"success": False, "message": "Task not found", "task_id": task_id}

            # Execute the task
            result = await self.task_executor.execute_task(task)

            # Update task status
            await self.task_repository.update_task_status(
                task_id, last_run=datetime.now(), last_status="success" if result["success"] else "failed"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to run task {task_id}: {e}", exc_info=True)
            return {"success": False, "message": str(e), "task_id": task_id}

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        try:
            jobs = await self.scheduler.get_jobs()
            return {"running": self.scheduler.is_running(), "jobs_count": len(jobs), "jobs": jobs}
        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            return {"error": str(e)}

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        try:
            return await self.task_executor.get_execution_stats()
        except Exception as e:
            logger.error(f"Failed to get execution stats: {e}")
            return {"error": str(e)}

    async def _load_and_schedule_tasks(self) -> None:
        """Load existing tasks and schedule them"""
        try:
            tasks = await self.task_repository.get_enabled_tasks()
            logger.info(f"Loading {len(tasks)} enabled tasks")

            for task in tasks:
                await self._schedule_task(task)

            logger.info("All tasks loaded and scheduled")

        except Exception as e:
            logger.error(f"Failed to load and schedule tasks: {e}", exc_info=True)

    async def _schedule_task(self, task: Dict[str, Any]) -> None:
        """Schedule a single task"""
        try:
            task_id = task["task_id"]
            task_type = task.get("task_type", "cron")
            enabled = task.get("enabled", True)

            if not enabled:
                logger.debug(f"Skipping disabled task: {task_id}")
                return

            # Create execution function
            async def execute_task():
                await self._execute_scheduled_task(task)

            if task_type == "cron":
                cron_expr = task.get("cron_expr", "")
                if cron_expr:
                    success = await self.scheduler.add_job(
                        job_id=task_id, func=execute_task, trigger="cron", cron_expr=cron_expr
                    )
                    if success:
                        logger.info(f"Scheduled cron task: {task_id} ({cron_expr})")
                    else:
                        logger.error(f"Failed to schedule cron task: {task_id}")
                else:
                    logger.error(f"No cron expression for task: {task_id}")

            elif task_type == "once":
                run_datetime = task.get("run_datetime")
                if run_datetime:
                    success = await self.scheduler.add_job(
                        job_id=task_id, func=execute_task, trigger="date", run_date=run_datetime
                    )
                    if success:
                        logger.info(f"Scheduled one-time task: {task_id} at {run_datetime}")
                    else:
                        logger.error(f"Failed to schedule one-time task: {task_id}")
                else:
                    logger.error(f"No run_datetime for one-time task: {task_id}")

            elif task_type in ["hourly", "daily", "weekly", "monthly"]:
                # Map task types to interval triggers
                interval_map = {
                    "hourly": {"hours": 1},
                    "daily": {"days": 1},
                    "weekly": {"weeks": 1},
                    "monthly": {"days": 30},  # Approximation
                }

                interval_args = interval_map.get(task_type, {})
                if interval_args:
                    success = await self.scheduler.add_job(
                        job_id=task_id, func=execute_task, trigger="interval", **interval_args
                    )
                    if success:
                        logger.info(f"Scheduled {task_type} task: {task_id}")
                    else:
                        logger.error(f"Failed to schedule {task_type} task: {task_id}")
                else:
                    logger.error(f"Unknown task type: {task_type} for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to schedule task {task.get('task_id')}: {e}", exc_info=True)

    async def _reschedule_task(self, task: Dict[str, Any]) -> None:
        """Reschedule an updated task"""
        try:
            task_id = task["task_id"]

            # Remove existing job
            await self.scheduler.remove_job(task_id)

            # Schedule again if enabled
            if task.get("enabled", True):
                await self._schedule_task(task)
            else:
                logger.info(f"Task disabled, removed from scheduler: {task_id}")

        except Exception as e:
            logger.error(f"Failed to reschedule task {task.get('task_id')}: {e}", exc_info=True)

    async def _execute_scheduled_task(self, task: Dict[str, Any]) -> None:
        """Execute a scheduled task with retry mechanism and timeout"""
        task_id = task.get("task_id", "unknown")
        max_retries = 3
        base_delay = 1.0  # seconds
        task_timeout = 300  # 5 minutes timeout for task execution

        for attempt in range(max_retries):
            try:
                logger.info(f"Executing scheduled task: {task_id} (attempt {attempt + 1}/{max_retries})")

                # Execute the task with timeout
                try:
                    async with asyncio.timeout(task_timeout):
                        result = await self.task_executor.execute_task(task)
                except TimeoutError:
                    logger.error(f"Scheduled task {task_id} timed out after {task_timeout} seconds")
                    result = {"success": False, "message": f"Task timed out after {task_timeout} seconds"}

                # Update task status
                status = "success" if result["success"] else "failed"
                await self.task_repository.update_task_status(task_id, last_run=datetime.now(), last_status=status)

                if result["success"]:
                    logger.info(f"Scheduled task completed successfully: {task_id}")
                else:
                    logger.warning(
                        f"Scheduled task completed with errors: {task_id} - {result.get('message', 'Unknown error')}"
                    )

                return  # Success, exit retry loop

            except Exception as e:
                logger.error(
                    f"Failed to execute scheduled task {task_id} (attempt {attempt + 1}/{max_retries}): {e}",
                    exc_info=True,
                )

                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2**attempt)
                    logger.info(f"Retrying task {task_id} in {delay} seconds...")

                    await asyncio.sleep(delay)
                else:
                    # Last attempt failed
                    try:
                        await self.task_repository.update_task_status(
                            task_id, last_run=datetime.now(), last_status="failed"
                        )
                        logger.error(f"Scheduled task failed permanently: {task_id} after {max_retries} attempts")
                    except Exception as status_error:
                        logger.error(f"Failed to update task status for {task_id}: {status_error}")
