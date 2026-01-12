#!/usr/bin/env python3
from core.logging import get_logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for scheduled tasks controller with new task_manager API
"""

import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from api.scheduled_tasks import (
    get_scheduled_tasks,
    get_scheduled_task,
    create_scheduled_task,
    remove_scheduled_task,
    run_scheduled_task,
    update_scheduled_task,
)

logger = get_logger(__name__)


@pytest.fixture
def mock_task_manager():
    """Mock task manager"""
    manager = Mock()
    manager.get_all_tasks = AsyncMock()
    manager.get_task = AsyncMock()
    manager.create_task = AsyncMock()
    manager.delete_task = AsyncMock()
    manager.run_task_now = AsyncMock()
    manager.update_task = AsyncMock()
    return manager


@pytest.fixture
def sample_task():
    """Sample task data"""
    return {
        "task_id": "task_123",
        "cluster": "test-cluster",
        "name": "Test Task",
        "description": "Test description",
        "cron_expr": "0 0 * * *",
        "enabled": True,
        "rules": ["rule1", "rule2"],
        "task_type": "cron",
    }


@pytest.fixture
def sample_task_create():
    """Sample task create data"""
    from api.models import ScheduledTaskCreate

    return ScheduledTaskCreate(
        cluster="test-cluster",
        name="Test_Task",
        description="Test description",
        cron_expr="0 0 * * *",
        enabled=True,
        rules={"node": ["rule1"], "opa": ["rule2"]},
        task_type="cron",
    )


class TestScheduledTasksController:
    """Test cases for scheduled tasks controller"""

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_get_scheduled_tasks_success(self, mock_get_service, mock_task_manager, sample_task):
        """Test successful get scheduled tasks"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.get_all_tasks.return_value = [sample_task]

        with patch("api.scheduled_tasks.calculate_next_run", return_value="2024-01-01 00:00:00"):
            result = await get_scheduled_tasks()

        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["task_id"] == "task_123"
        assert result["tasks"][0]["next_run"] == "2024-01-01 00:00:00"
        mock_task_manager.get_all_tasks.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_get_scheduled_tasks_error(self, mock_get_service, mock_task_manager):
        """Test get scheduled tasks error handling"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.get_all_tasks.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_scheduled_tasks()

        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_get_scheduled_task_success(self, mock_get_service, mock_task_manager, sample_task):
        """Test successful get specific scheduled task"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.get_task.return_value = sample_task

        with patch("api.scheduled_tasks.calculate_next_run", return_value="2024-01-01 00:00:00"):
            result = await get_scheduled_task("task_123")

        assert result["task_id"] == "task_123"
        assert result["next_run"] == "2024-01-01 00:00:00"
        mock_task_manager.get_task.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_get_scheduled_task_not_found(self, mock_get_service, mock_task_manager):
        """Test get scheduled task not found"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_scheduled_task("task_123")

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_get_scheduled_task_validation_error(self, mock_get_service, mock_task_manager):
        """Test get scheduled task with invalid task_id"""
        mock_get_service.return_value = mock_task_manager

        with patch("api.scheduled_tasks.validate_task_id", side_effect=ValueError("Invalid task ID")):
            with pytest.raises(HTTPException) as exc_info:
                await get_scheduled_task("invalid-task-id")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_create_scheduled_task_success(self, mock_get_service, mock_task_manager, sample_task_create):
        """Test successful create scheduled task"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.create_task.return_value = {
            "task_id": "task_1234567890",
            "cluster": "test-cluster",
            "name": "Test Task",
        }

        result = await create_scheduled_task(sample_task_create)

        assert result["message"] == "Task created successfully"
        assert result["task_id"] == "task_1234567890"
        mock_task_manager.create_task.assert_called_once()

        # Verify task data structure
        call_args = mock_task_manager.create_task.call_args[0][0]
        assert call_args["cluster"] == "test-cluster"
        assert call_args["name"] == "Test_Task"
        assert call_args["cron_expr"] == "0 0 * * *"
        assert call_args["enabled"] is True
        assert call_args["task_type"] == "cron"

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_create_scheduled_task_failure(self, mock_get_service, mock_task_manager, sample_task_create):
        """Test create scheduled task failure"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.create_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await create_scheduled_task(sample_task_create)

        assert exc_info.value.status_code == 500
        assert "Failed to create task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_remove_scheduled_task_success(self, mock_get_service, mock_task_manager):
        """Test successful remove scheduled task"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.delete_task.return_value = True

        result = await remove_scheduled_task("task_123")

        assert result["message"] == "Task task_123 deleted"
        mock_task_manager.delete_task.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_remove_scheduled_task_not_found(self, mock_get_service, mock_task_manager):
        """Test remove scheduled task not found"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.delete_task.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await remove_scheduled_task("task_123")

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_run_scheduled_task_success(self, mock_get_service, mock_task_manager):
        """Test successful run scheduled task"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.run_task_now.return_value = {
            "success": True,
            "message": "Task executed successfully",
            "results": {"some": "data"},
        }

        result = await run_scheduled_task("task_123")

        assert result["message"] == "Task executed successfully"
        assert result["results"] == {"some": "data"}
        mock_task_manager.run_task_now.assert_called_once_with("task_123")

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_run_scheduled_task_failure(self, mock_get_service, mock_task_manager):
        """Test run scheduled task failure"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.run_task_now.return_value = {"success": False, "message": "Task execution failed"}

        with pytest.raises(HTTPException) as exc_info:
            await run_scheduled_task("task_123")

        assert exc_info.value.status_code == 500
        assert "Task execution failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_update_scheduled_task_success(self, mock_get_service, mock_task_manager, sample_task_create):
        """Test successful update scheduled task"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.update_task.return_value = True

        result = await update_scheduled_task("task_123", sample_task_create)

        assert result["message"] == "Task updated successfully"
        mock_task_manager.update_task.assert_called_once_with(
            "task_123",
            {
                "cluster": "test-cluster",
                "name": "Test_Task",
                "description": "Test description",
                "cron_expr": "0 0 * * *",
                "enabled": True,
                "rules": {"node": ["rule1"], "opa": ["rule2"]},
                "task_type": "cron",
                "run_datetime": None,
            },
        )

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_update_scheduled_task_not_found(self, mock_get_service, mock_task_manager, sample_task_create):
        """Test update scheduled task not found"""
        mock_get_service.return_value = mock_task_manager
        mock_task_manager.update_task.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await update_scheduled_task("task_123", sample_task_create)

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.scheduled_tasks.get_service")
    async def test_create_scheduled_task_once_type(self, mock_get_service, mock_task_manager):
        """Test create scheduled task with once type"""
        from api.models import ScheduledTaskCreate

        mock_get_service.return_value = mock_task_manager
        mock_task_manager.create_task.return_value = {"task_id": "task_123"}

        task_create = ScheduledTaskCreate(
            cluster="test-cluster",
            name="One_time_Task",
            description="Test one-time task",
            cron_expr="",  # Empty cron for once type
            enabled=True,
            rules={"node": ["rule1"]},
            task_type="once",
            run_datetime="2024-01-01T00:00:00Z",
        )

        result = await create_scheduled_task(task_create)

        assert result["message"] == "Task created successfully"
        call_args = mock_task_manager.create_task.call_args[0][0]
        assert call_args["task_type"] == "once"
        assert call_args["run_datetime"] == "2024-01-01T00:00:00Z"
