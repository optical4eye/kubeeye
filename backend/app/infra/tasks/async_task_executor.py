#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Async task executor implementing ITaskExecutor interface
"""

import time
from typing import Dict, Any
from datetime import datetime

from .interfaces import ITaskExecutor
from core.logging import get_logger

logger = get_logger(__name__)


class AsyncTaskExecutor(ITaskExecutor):
    """Async implementation of task executor"""

    def __init__(self):
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "last_execution_time": None,
        }
        self._execution_times = []

    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a scheduled task with internal retry mechanism"""
        start_time = time.time()
        task_id = task_data.get("task_id", "unknown")
        max_retries = 2  # Internal retries for transient failures
        base_delay = 0.5

        # Update execution stats
        self.execution_stats["total_executions"] += 1

        for attempt in range(max_retries):
            try:
                logger.info(f"Starting execution of task {task_id} (attempt {attempt + 1}/{max_retries})")

                # Import and execute inspection
                from services.components.inspection_engine import execute_inspection_unified

                cluster_name = task_data.get("cluster", "")
                rules = task_data.get("rules", {})
                tags = task_data.get("tags", {})

                success, message, results = await execute_inspection_unified(
                    cluster_name=cluster_name,
                    selected_rules=rules,
                    selected_tags=tags,
                    inspection_type="scheduled",
                    show_progress=False,
                    show_ui_feedback=False,
                    use_gitops=True,
                )

                execution_time = time.time() - start_time
                self._execution_times.append(execution_time)

                # Update stats
                if success:
                    self.execution_stats["successful_executions"] += 1
                else:
                    self.execution_stats["failed_executions"] += 1

                self.execution_stats["last_execution_time"] = datetime.now().isoformat()
                self.execution_stats["average_execution_time"] = sum(self._execution_times) / len(self._execution_times)

                logger.info(f"Task {task_id} completed in {execution_time:.2f}s, success: {success}")

                return {
                    "success": success,
                    "message": message,
                    "results": results,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "attempts": attempt + 1,
                }

            except Exception as e:
                execution_time = time.time() - start_time

                # Check if this is a retryable error
                is_retryable = self._is_retryable_error(e)

                if attempt < max_retries - 1 and is_retryable:
                    delay = base_delay * (2**attempt)
                    logger.warning(f"Task {task_id} failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    import asyncio

                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final failure
                    self.execution_stats["failed_executions"] += 1
                    self._execution_times.append(execution_time)

                    logger.error(f"Task {task_id} failed permanently after {execution_time:.2f}s: {e}", exc_info=True)

                    return {
                        "success": False,
                        "message": str(e),
                        "results": None,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "attempts": attempt + 1,
                        "retryable": is_retryable,
                    }

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable"""
        error_str = str(error).lower()

        # Network-related errors are usually retryable
        retryable_patterns = ["connection", "timeout", "network", "unreachable", "temporary", "busy", "locked"]

        return any(pattern in error_str for pattern in retryable_patterns)

    async def validate_task(self, task_data: Dict[str, Any]) -> bool:
        """Validate task data before execution"""
        try:
            required_fields = ["task_id", "cluster"]
            for field in required_fields:
                if field not in task_data:
                    logger.error(f"Missing required field: {field}")
                    return False

            # Validate cluster exists (basic check)
            cluster = task_data.get("cluster")
            if not cluster or not isinstance(cluster, str):
                logger.error("Invalid cluster specification")
                return False

            # Validate rules structure
            rules = task_data.get("rules", {})
            if not isinstance(rules, dict):
                logger.error("Invalid rules structure")
                return False

            return True

        except Exception as e:
            logger.error(f"Task validation error: {e}")
            return False

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.execution_stats.copy()
