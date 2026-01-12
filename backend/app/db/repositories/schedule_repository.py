#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository for scheduled tasks - Async Only
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.repositories.base_repository import BaseRepository
from db.models.schedule import ScheduledTask
from core.common.exceptions import TaskNotFoundError, DatabaseError
from core.common.retry_utils import retry_on_failure
from core.logging import get_logger

logger = get_logger(__name__)


class ScheduleRepository(BaseRepository[ScheduledTask]):
    """Repository for scheduled task operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ScheduledTask)

    async def get_by_task_id(self, task_id: str) -> ScheduledTask:
        """Get task by task_id"""
        task = await self.get_by_field("task_id", task_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
        return task

    async def get_enabled_tasks(self) -> List[ScheduledTask]:
        """Get all enabled tasks"""
        return await self.get_all(enabled=True)

    async def get_tasks_by_cluster(self, cluster_name: str) -> List[ScheduledTask]:
        """Get tasks for specific cluster"""
        return await self.get_all(cluster_name=cluster_name)

    async def create_task(self, task_data: Dict[str, Any]) -> ScheduledTask:
        """Create new scheduled task"""
        return await self.create(task_data)

    @retry_on_failure(max_attempts=3, exceptions=(DatabaseError,))
    async def update_task_status(
        self,
        task_id: str,
        last_run: Optional[datetime] = None,
        last_status: Optional[str] = None,
        next_run: Optional[datetime] = None,
    ) -> bool:
        """Update task execution status"""
        try:
            update_data = {}
            if last_run is not None:
                update_data["last_run"] = last_run
            if last_status is not None:
                update_data["last_status"] = last_status
            if next_run is not None:
                update_data["next_run"] = next_run

            if update_data:
                updated = await self.get_by_field_and_update("task_id", task_id, update_data)
                return updated is not None
            return True
        except TaskNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise DatabaseError(f"Failed to update task status: {e}")

    async def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        """Enable or disable task"""
        try:
            updated = await self.get_by_field_and_update("task_id", task_id, {"enabled": enabled})
            return updated is not None
        except Exception as e:
            logger.error(f"Error enabling/disabling task: {e}")
            raise

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task by task_id"""
        try:
            update_data = {}
            for key, value in updates.items():
                if key == "cluster":
                    update_data["cluster_name"] = value
                elif key == "run_datetime" and isinstance(value, str):
                    # Parse datetime string to datetime object
                    update_data["run_datetime"] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    update_data[key] = value

            # If run_datetime is set, ensure task_type is "once"
            if "run_datetime" in update_data and update_data["run_datetime"] is not None:
                update_data["task_type"] = "once"

            if update_data:
                updated = await self.get_by_field_and_update("task_id", task_id, update_data)
                return updated is not None
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            raise

    async def delete_task(self, task_id: str) -> bool:
        """Delete task by task_id"""
        try:
            return await self.get_by_field_and_delete("task_id", task_id)
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise

    async def get_pending_one_time_tasks(self) -> List[ScheduledTask]:
        """Get one-time tasks that are due to run"""
        now = datetime.utcnow()
        try:
            stmt = select(ScheduledTask).where(
                and_(
                    ScheduledTask.task_type == "once",
                    ScheduledTask.enabled.is_(True),
                    ScheduledTask.run_datetime <= now,
                    ScheduledTask.last_run.is_(None),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting pending one-time tasks: {e}")
            raise

    def to_dict(self, task: ScheduledTask) -> Dict[str, Any]:
        """Convert task to dictionary (compatible with existing ScheduleTask)"""
        return {
            "task_id": task.task_id,
            "cluster": task.cluster_name,
            "name": task.name,
            "description": task.description,
            "cron_expr": task.cron_expr,
            "enabled": task.enabled,
            "rules": task.rules,
            "task_type": task.task_type,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_status": task.last_status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "run_datetime": task.run_datetime.isoformat() if task.run_datetime else None,
        }

    def from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dict to task data format"""
        return {
            "task_id": data.get("task_id"),
            "cluster_name": data.get("cluster"),
            "name": data.get("name"),
            "description": data.get("description"),
            "cron_expr": data.get("cron_expr"),
            "enabled": data.get("enabled", True),
            "rules": data.get("rules", {}),
            "task_type": data.get("task_type", "cron"),
            "last_run": data.get("last_run"),
            "last_status": data.get("last_status"),
            "run_datetime": data.get("run_datetime"),
        }
