#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaces for task scheduling system
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


class IScheduler(ABC):
    """Interface for task schedulers"""

    @abstractmethod
    async def start(self) -> bool:
        """Start the scheduler"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the scheduler"""
        pass

    @abstractmethod
    async def add_job(self, job_id: str, func: Callable, trigger: str, **trigger_args) -> bool:
        """Add a scheduled job"""
        pass

    @abstractmethod
    async def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        pass

    @abstractmethod
    async def get_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        pass


class ITaskExecutor(ABC):
    """Interface for task execution"""

    @abstractmethod
    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a scheduled task"""
        pass

    @abstractmethod
    async def validate_task(self, task_data: Dict[str, Any]) -> bool:
        """Validate task data before execution"""
        pass

    @abstractmethod
    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        pass


class ITaskRepository(ABC):
    """Interface for task persistence"""

    @abstractmethod
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new task"""
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        pass

    @abstractmethod
    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        pass

    @abstractmethod
    async def get_enabled_tasks(self) -> List[Dict[str, Any]]:
        """Get enabled tasks"""
        pass

    @abstractmethod
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update task"""
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        pass

    @abstractmethod
    async def update_task_status(
        self,
        task_id: str,
        last_run: Optional[datetime] = None,
        last_status: Optional[str] = None,
        next_run: Optional[datetime] = None,
    ) -> bool:
        """Update task execution status"""
        pass
