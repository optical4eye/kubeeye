#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asynchronous task queue for inspection processing
"""

import asyncio
import logging

# json not used
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task data structure"""

    task_id: str
    task_type: str
    payload: Dict[str, Any]
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress_callback: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "result": self.result,
            "error": self.error,
        }


class AsyncTaskQueue:
    """Asynchronous task queue with worker pool"""

    def __init__(self, max_workers: int = 3, queue_size: int = 100):
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.max_workers = max_workers
        self.workers = []
        self.tasks = {}  # task_id -> Task
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the task queue workers"""
        if self.running:
            return

        self.running = True
        self._shutdown_event.clear()

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)

        logger.info(f"Started async task queue with {self.max_workers} workers")

    async def stop(self):
        """Stop the task queue and cancel all workers"""
        if not self.running:
            return

        self.running = False
        self._shutdown_event.set()

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        # Cancel pending tasks
        while not self.queue.empty():
            try:
                task = self.queue.get_nowait()
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self.tasks[task.task_id] = task
            except asyncio.QueueEmpty:
                break

        logger.info("Stopped async task queue")

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Submit a task to the queue"""
        task_id = f"{task_type}_{int(datetime.now().timestamp() * 1000)}"

        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            progress_callback=progress_callback,
        )

        self.tasks[task_id] = task

        try:
            await asyncio.wait_for(self.queue.put(task), timeout=5.0)
            logger.info(f"Submitted task {task_id} of type {task_type}")
            return task_id
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = "Queue is full"
            task.completed_at = datetime.now()
            raise RuntimeError("Task queue is full")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return True
        return False

    async def _worker_loop(self, worker_id: int):
        """Worker loop for processing tasks"""
        logger.info(f"Worker {worker_id} started")

        try:
            while self.running:
                try:
                    # Wait for task with timeout
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                    # Process the task
                    await self._process_task(task, worker_id)

                    # Mark task as done in queue
                    self.queue.task_done()

                except asyncio.TimeoutError:
                    # Check if we should continue running
                    if self._shutdown_event.is_set():
                        break
                    continue
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    continue

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {worker_id} failed: {e}")

        logger.info(f"Worker {worker_id} stopped")

    async def _process_task(self, task: Task, worker_id: int):
        """Process a single task"""
        try:
            logger.info(f"Worker {worker_id} processing task {task.task_id}")

            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            # Process based on task type
            if task.task_type == "inspection":
                result = await self._process_inspection_task(task)
            elif task.task_type == "cleanup":
                result = await self._process_cleanup_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

            logger.info(f"Task {task.task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")

            # Mark as failed
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()

    async def _process_inspection_task(self, task: Task) -> Dict[str, Any]:
        """Process inspection task"""
        from services.components.inspection_engine import execute_inspection_unified

        payload = task.payload

        # Call progress callback if provided
        if task.progress_callback:
            task.progress_callback("Starting inspection...")

        # Execute inspection
        success, message, results = await execute_inspection_unified(
            cluster_name=payload["cluster_name"],
            selected_rules=payload.get("selected_rules"),
            inspection_type=payload.get("inspection_type", "immediate"),
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=payload.get("use_gitops", False),
        )

        if task.progress_callback:
            task.progress_callback("Inspection completed")

        # Inspection now always succeeds (errors are recorded in results)
        return {
            "success": success,
            "message": message,
            "results": results,
        }

    async def _process_cleanup_task(self, task: Task) -> Dict[str, Any]:
        """Process cleanup task"""
        from scripts.cleanup_reports import run_cleanup

        # Call progress callback if provided
        if task.progress_callback:
            task.progress_callback("Starting cleanup...")

        # Execute cleanup
        run_cleanup()

        if task.progress_callback:
            task.progress_callback("Cleanup completed")

        return {
            "success": True,
            "message": "Cleanup completed successfully",
        }


# Global task queue instance
task_queue = AsyncTaskQueue(max_workers=3, queue_size=50)


async def get_task_queue() -> AsyncTaskQueue:
    """Get the global task queue instance"""
    return task_queue


async def submit_inspection_task(
    cluster_name: str,
    selected_rules: Optional[Dict[str, Any]] = None,
    inspection_type: str = "immediate",
    use_gitops: bool = False,
    progress_callback: Optional[Callable] = None,
) -> str:
    """Submit an inspection task to the queue"""
    payload = {
        "cluster_name": cluster_name,
        "selected_rules": selected_rules,
        "inspection_type": inspection_type,
        "use_gitops": use_gitops,
    }

    return await task_queue.submit_task("inspection", payload, progress_callback)


async def submit_cleanup_task(progress_callback: Optional[Callable] = None) -> str:
    """Submit a cleanup task to the queue"""
    return await task_queue.submit_task("cleanup", {}, progress_callback)
