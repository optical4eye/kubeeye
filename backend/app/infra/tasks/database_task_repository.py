#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database task repository implementing ITaskRepository interface
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .interfaces import ITaskRepository
from core.logging import get_logger
from db.database_context import with_db_session

logger = get_logger(__name__)


class DatabaseTaskRepository(ITaskRepository):
    """Database implementation of task repository"""

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new task"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            # Convert API format to DB format
            db_task_data = self.from_dict(task_data)
            created_task = await repo.create_task(db_task_data)
            task_dict = repo.to_dict(created_task)
            logger.info(f"Task created: {task_dict.get('task_id')}")
            return task_dict

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            task_db = await repo.get_by_task_id(task_id)
            if task_db:
                return repo.to_dict(task_db)
            return None

    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            tasks_db = await repo.get_all()
            return [repo.to_dict(task) for task in tasks_db]

    def to_dict(self, task) -> Dict[str, Any]:
        """Convert task to dictionary (for compatibility)"""
        from db.repositories.schedule_repository import ScheduleRepository

        repo = ScheduleRepository(None)  # We don't need db for this
        return repo.to_dict(task)

    def from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dict to task data format"""
        return {
            "task_id": data.get("task_id"),
            "cluster_name": data.get("cluster"),  # API uses "cluster", DB uses "cluster_name"
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

    async def get_enabled_tasks(self) -> List[Dict[str, Any]]:
        """Get enabled tasks"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            tasks_db = await repo.get_enabled_tasks()
            return [repo.to_dict(task) for task in tasks_db]

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            success = await repo.update_task(task_id, updates)
            if success:
                logger.info(f"Task updated: {task_id}")
            return success

    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            success = await repo.delete_task(task_id)
            if success:
                logger.info(f"Task deleted: {task_id}")
            return success

    async def update_task_status(
        self,
        task_id: str,
        last_run: Optional[datetime] = None,
        last_status: Optional[str] = None,
        next_run: Optional[datetime] = None,
    ) -> bool:
        """Update task execution status"""
        from db.repositories.schedule_repository import ScheduleRepository

        async with with_db_session() as db:
            repo = ScheduleRepository(db)
            success = await repo.update_task_status(task_id, last_run, last_status, next_run)
            if success:
                logger.debug(f"Task status updated: {task_id}")
            return success
