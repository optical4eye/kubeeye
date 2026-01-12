#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for task manager component
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from infra.tasks.task_manager import TaskManager


class TestTaskManager:
    """Test cases for task manager"""

    @pytest.fixture
    def mock_scheduler(self):
        """Mock scheduler"""
        scheduler = Mock()
        scheduler.start = AsyncMock(return_value=True)
        scheduler.stop = AsyncMock(return_value=True)
        scheduler.add_job = AsyncMock(return_value=True)
        scheduler.remove_job = AsyncMock(return_value=True)
        scheduler.get_jobs = AsyncMock(return_value=[])
        scheduler.is_running = Mock(return_value=True)
        return scheduler

    @pytest.fixture
    def mock_task_executor(self):
        """Mock task executor"""
        executor = Mock()
        executor.validate_task = AsyncMock(return_value=True)
        executor.execute_task = AsyncMock(return_value={"success": True, "message": "Task executed"})
        executor.get_execution_stats = AsyncMock(return_value={"total_tasks": 10, "successful": 8})
        return executor

    @pytest.fixture
    def mock_task_repository(self):
        """Mock task repository"""
        repo = Mock()
        repo.create_task = AsyncMock(
            return_value={"task_id": "test-task", "name": "Test Task", "task_type": "cron", "cron_expr": "0 0 * * *"}
        )
        repo.update_task = AsyncMock(return_value=True)
        repo.delete_task = AsyncMock(return_value=True)
        repo.get_task = AsyncMock(
            return_value={"task_id": "test-task", "name": "Test Task", "task_type": "cron", "cron_expr": "0 0 * * *"}
        )
        repo.get_all_tasks = AsyncMock(return_value=[{"task_id": "task1"}, {"task_id": "task2"}])
        repo.get_enabled_tasks = AsyncMock(
            return_value=[{"task_id": "enabled-task", "enabled": True, "task_type": "cron", "cron_expr": "0 0 * * *"}]
        )
        repo.update_task_status = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def task_manager(self, mock_scheduler, mock_task_executor, mock_task_repository):
        """Create TaskManager instance with mocks"""
        return TaskManager(mock_scheduler, mock_task_executor, mock_task_repository)

    @pytest.mark.asyncio
    async def test_initialize_success(self, task_manager, mock_scheduler, mock_task_repository):
        """Test successful initialization"""
        success = await task_manager.initialize()

        assert success is True
        assert task_manager._initialized is True
        mock_scheduler.start.assert_called_once()
        mock_task_repository.get_enabled_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_scheduler_failure(self, task_manager, mock_scheduler):
        """Test initialization when scheduler fails to start"""
        mock_scheduler.start.return_value = False

        success = await task_manager.initialize()

        assert success is False
        assert task_manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, task_manager):
        """Test initialization when already initialized"""
        task_manager._initialized = True

        success = await task_manager.initialize()

        assert success is True
        # Should not call start again
        task_manager.scheduler.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_success(self, task_manager, mock_scheduler):
        """Test successful shutdown"""
        task_manager._initialized = True

        success = await task_manager.shutdown()

        assert success is True
        assert task_manager._initialized is False
        mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_failure(self, task_manager, mock_scheduler):
        """Test shutdown when scheduler fails"""
        mock_scheduler.stop.side_effect = Exception("Shutdown failed")

        success = await task_manager.shutdown()

        assert success is False

    @pytest.mark.asyncio
    async def test_create_task_success(self, task_manager, mock_task_executor, mock_task_repository, mock_scheduler):
        """Test successful task creation"""
        task_data = {"name": "Test Task", "task_type": "cron", "cron_expr": "0 0 * * *"}

        result = await task_manager.create_task(task_data)

        assert result is not None
        assert result["task_id"] == "test-task"
        mock_task_executor.validate_task.assert_called_once_with(task_data)
        mock_task_repository.create_task.assert_called_once_with(task_data)
        mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_validation_failure(self, task_manager, mock_task_executor):
        """Test task creation with validation failure"""
        mock_task_executor.validate_task.return_value = False

        result = await task_manager.create_task({"name": "Invalid Task"})

        assert result is None
        mock_task_executor.validate_task.assert_called_once()
        task_manager.task_repository.create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_exception(self, task_manager, mock_task_executor, mock_task_repository):
        """Test task creation with exception"""
        mock_task_repository.create_task.side_effect = Exception("DB error")

        result = await task_manager.create_task({"name": "Test Task", "task_type": "cron"})

        assert result is None

    @pytest.mark.asyncio
    async def test_update_task_success(self, task_manager, mock_task_repository, mock_scheduler):
        """Test successful task update"""
        updates = {"name": "Updated Task"}

        success = await task_manager.update_task("test-task", updates)

        assert success is True
        mock_task_repository.update_task.assert_called_once_with("test-task", updates)
        mock_task_repository.get_task.assert_called_once_with("test-task")
        mock_scheduler.remove_job.assert_called_once_with("test-task")
        mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_repository_failure(self, task_manager, mock_task_repository):
        """Test task update when repository update fails"""
        mock_task_repository.update_task.return_value = False

        success = await task_manager.update_task("test-task", {"name": "Updated"})

        assert success is False
        mock_task_repository.get_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, task_manager, mock_task_repository):
        """Test task update when task not found after update"""
        mock_task_repository.get_task.return_value = None

        success = await task_manager.update_task("test-task", {"name": "Updated"})

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_manager, mock_task_repository, mock_scheduler):
        """Test successful task deletion"""
        success = await task_manager.delete_task("test-task")

        assert success is True
        mock_scheduler.remove_job.assert_called_once_with("test-task")
        mock_task_repository.delete_task.assert_called_once_with("test-task")

    @pytest.mark.asyncio
    async def test_delete_task_scheduler_failure(self, task_manager, mock_scheduler, mock_task_repository):
        """Test task deletion when scheduler removal fails"""
        mock_scheduler.remove_job.side_effect = Exception("Scheduler error")

        success = await task_manager.delete_task("test-task")

        assert success is False
        mock_task_repository.delete_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_task_success(self, task_manager, mock_task_repository):
        """Test successful task retrieval"""
        result = await task_manager.get_task("test-task")

        assert result is not None
        assert result["task_id"] == "test-task"
        mock_task_repository.get_task.assert_called_once_with("test-task")

    @pytest.mark.asyncio
    async def test_get_task_exception(self, task_manager, mock_task_repository):
        """Test task retrieval with exception"""
        mock_task_repository.get_task.side_effect = Exception("DB error")

        result = await task_manager.get_task("test-task")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_tasks_success(self, task_manager, mock_task_repository):
        """Test successful retrieval of all tasks"""
        result = await task_manager.get_all_tasks()

        assert len(result) == 2
        mock_task_repository.get_all_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_tasks_exception(self, task_manager, mock_task_repository):
        """Test retrieval of all tasks with exception"""
        mock_task_repository.get_all_tasks.side_effect = Exception("DB error")

        result = await task_manager.get_all_tasks()

        assert result == []

    @pytest.mark.asyncio
    async def test_run_task_now_success(self, task_manager, mock_task_executor, mock_task_repository):
        """Test successful immediate task execution"""
        result = await task_manager.run_task_now("test-task")

        assert result["success"] is True
        assert result["message"] == "Task executed"
        mock_task_executor.execute_task.assert_called_once()
        mock_task_repository.update_task_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_now_task_not_found(self, task_manager, mock_task_repository):
        """Test immediate execution when task not found"""
        mock_task_repository.get_task.return_value = None

        result = await task_manager.run_task_now("non-existent")

        assert result["success"] is False
        assert "Task not found" in result["message"]

    @pytest.mark.asyncio
    async def test_run_task_now_execution_failure(self, task_manager, mock_task_executor, mock_task_repository):
        """Test immediate execution when task execution fails"""
        mock_task_executor.execute_task.return_value = {"success": False, "message": "Execution failed"}

        result = await task_manager.run_task_now("test-task")

        assert result["success"] is False
        assert result["message"] == "Execution failed"
        mock_task_repository.update_task_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_scheduler_status_success(self, task_manager, mock_scheduler):
        """Test successful scheduler status retrieval"""
        result = await task_manager.get_scheduler_status()

        assert result["running"] is True
        assert result["jobs_count"] == 0
        mock_scheduler.get_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_scheduler_status_exception(self, task_manager, mock_scheduler):
        """Test scheduler status retrieval with exception"""
        mock_scheduler.get_jobs.side_effect = Exception("Scheduler error")

        result = await task_manager.get_scheduler_status()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_execution_stats_success(self, task_manager, mock_task_executor):
        """Test successful execution stats retrieval"""
        result = await task_manager.get_execution_stats()

        assert result["total_tasks"] == 10
        assert result["successful"] == 8
        mock_task_executor.get_execution_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_execution_stats_exception(self, task_manager, mock_task_executor):
        """Test execution stats retrieval with exception"""
        mock_task_executor.get_execution_stats.side_effect = Exception("Stats error")

        result = await task_manager.get_execution_stats()

        assert "error" in result

    @pytest.mark.asyncio
    async def test_schedule_task_cron(self, task_manager, mock_scheduler):
        """Test scheduling a cron task"""
        task = {"task_id": "cron-task", "task_type": "cron", "cron_expr": "0 0 * * *", "enabled": True}

        await task_manager._schedule_task(task)

        mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_task_once(self, task_manager, mock_scheduler):
        """Test scheduling a one-time task"""
        run_datetime = datetime.now()
        task = {"task_id": "once-task", "task_type": "once", "run_datetime": run_datetime, "enabled": True}

        await task_manager._schedule_task(task)

        mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_task_hourly(self, task_manager, mock_scheduler):
        """Test scheduling an hourly task"""
        task = {"task_id": "hourly-task", "task_type": "hourly", "enabled": True}

        await task_manager._schedule_task(task)

        mock_scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_task_disabled(self, task_manager, mock_scheduler):
        """Test scheduling a disabled task"""
        task = {"task_id": "disabled-task", "task_type": "cron", "enabled": False}

        await task_manager._schedule_task(task)

        mock_scheduler.add_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_scheduled_task_success(self, task_manager, mock_task_executor, mock_task_repository):
        """Test successful execution of scheduled task"""
        task = {"task_id": "scheduled-task"}
        mock_task_executor.execute_task.return_value = {"success": True}

        await task_manager._execute_scheduled_task(task)

        mock_task_executor.execute_task.assert_called_once_with(task)
        mock_task_repository.update_task_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scheduled_task_failure_with_retry(
        self, task_manager, mock_task_executor, mock_task_repository
    ):
        """Test scheduled task execution with failure and retry"""
        task = {"task_id": "failing-task"}
        mock_task_executor.execute_task.side_effect = Exception("Task failed")

        await task_manager._execute_scheduled_task(task)

        # Should be called 3 times (max_retries)
        assert mock_task_executor.execute_task.call_count == 3
        mock_task_repository.update_task_status.assert_called_once()
