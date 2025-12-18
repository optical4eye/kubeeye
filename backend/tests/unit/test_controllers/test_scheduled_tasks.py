#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for scheduled tasks API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException

from api.scheduled_tasks import (
    get_scheduled_tasks,
    create_scheduled_task,
    remove_scheduled_task,
    run_scheduled_task,
    update_scheduled_task,
)
from api.models import ScheduledTaskCreate


class TestScheduledTasksAPI:
    """Test cases for scheduled tasks API endpoints"""

    @patch("api.scheduled_tasks.load_schedules")
    @pytest.mark.asyncio
    async def test_get_scheduled_tasks_success(self, mock_load_schedules):
        """Test successful retrieval of scheduled tasks"""
        # Mock tasks
        mock_task1 = Mock()
        mock_task1.task_id = "task1"
        mock_task1.name = "Task 1"
        mock_task1.cron_expr = "0 0 * * *"
        mock_next_run = Mock()
        mock_next_run.isoformat.return_value = "2023-01-01T12:00:00Z"
        mock_task1.get_next_run = Mock(return_value=mock_next_run)

        mock_task2 = Mock()
        mock_task2.task_id = "task2"
        mock_task2.name = "Task 2"
        mock_task2.cron_expr = ""
        mock_task2.get_next_run = Mock(return_value=None)

        mock_load_schedules.return_value = [mock_task1, mock_task2]

        result = await get_scheduled_tasks()

        assert "tasks" in result
        assert len(result["tasks"]) == 2

        task1 = result["tasks"][0]
        assert task1["task_id"] == "task1"
        assert task1["name"] == "Task 1"
        assert task1["next_run"] == "2023-01-01T12:00:00Z"
        assert task1["task_type"] == "cron"

        task2 = result["tasks"][1]
        assert task2["task_id"] == "task2"
        assert task2["name"] == "Task 2"
        assert task2["next_run"] is None
        assert task2["task_type"] == "once"

    @patch("api.scheduled_tasks.load_schedules")
    @pytest.mark.asyncio
    async def test_get_scheduled_tasks_exception(self, mock_load_schedules):
        """Test scheduled tasks retrieval when exception occurs"""
        mock_load_schedules.side_effect = Exception("Load error")

        with pytest.raises(HTTPException) as exc_info:
            await get_scheduled_tasks()

        assert exc_info.value.status_code == 500
        assert "Load error" in str(exc_info.value.detail)

    @patch("api.scheduled_tasks.add_schedule")
    @patch("api.scheduled_tasks.ScheduleTask")
    @patch("time.time")
    @pytest.mark.asyncio
    async def test_create_scheduled_task_success(self, mock_time, mock_schedule_task_class, mock_add_schedule):
        """Test successful creation of scheduled task"""
        # Mock time
        mock_time.return_value = 1672531200  # 2023-01-01 00:00:00 UTC

        # Mock task creation
        mock_schedule_task_class.return_value = Mock()

        # Mock schedule addition
        mock_add_schedule.return_value = True

        # Create request
        task = ScheduledTaskCreate(
            name="Test_Task",
            cluster="test-cluster",
            description="Test description",
            cron_expr="0 0 * * *",
            enabled=True,
            rules={"node": ["rule1"]},
            task_type="cron",
        )

        result = await create_scheduled_task(task)

        assert result["message"] == "Task created successfully"
        assert "task_id" in result
        assert result["task_id"].startswith("task_")
        mock_schedule_task_class.assert_called_once()
        mock_add_schedule.assert_called_once()

    @patch("api.scheduled_tasks.add_schedule")
    @patch("api.scheduled_tasks.ScheduleTask")
    @patch("time.time")
    @pytest.mark.asyncio
    async def test_create_scheduled_task_failure(self, mock_time, mock_schedule_task_class, mock_add_schedule):
        """Test scheduled task creation when add_schedule fails"""
        # Mock time
        mock_time.return_value = 1672531200

        # Mock task creation
        mock_schedule_task_class.return_value = Mock()

        # Mock schedule addition failure
        mock_add_schedule.return_value = False

        # Create request
        task = ScheduledTaskCreate(
            name="Test_Task",
            cluster="test-cluster",
            description="Test description",
            cron_expr="0 0 * * *",
            enabled=True,
            rules={"node": ["rule1"]},
            task_type="cron",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_scheduled_task(task)

        assert exc_info.value.status_code == 500
        assert "Failed to create task" in str(exc_info.value.detail)

    @patch("api.scheduled_tasks.add_schedule")
    @patch("api.scheduled_tasks.ScheduleTask")
    @patch("time.time")
    @pytest.mark.asyncio
    async def test_create_scheduled_task_once_type(self, mock_time, mock_schedule_task_class, mock_add_schedule):
        """Test creation of one-time scheduled task"""
        # Mock time
        mock_time.return_value = 1672531200

        # Mock task creation
        mock_schedule_task_class.return_value = Mock()

        # Mock schedule addition
        mock_add_schedule.return_value = True

        # Create request for once type (should have empty cron_expr)
        task = ScheduledTaskCreate(
            name="One_time_Task",
            cluster="test-cluster",
            description="Test description",
            cron_expr="",  # Empty for once type
            enabled=True,
            rules={"node": ["rule1"]},
            task_type="once",
        )

        result = await create_scheduled_task(task)

        assert result["message"] == "Task created successfully"
        # Verify ScheduleTask was created with empty cron_expr
        call_args = mock_schedule_task_class.call_args[1]
        assert call_args["cron_expr"] == ""

    @patch("api.scheduled_tasks.delete_schedule")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_remove_scheduled_task_success(self, mock_validate_id, mock_delete_schedule):
        """Test successful deletion of scheduled task"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock deletion
        mock_delete_schedule.return_value = True

        result = await remove_scheduled_task("task-123")

        assert result["message"] == "Task validated-task-123 deleted"
        mock_validate_id.assert_called_once_with("task-123")
        mock_delete_schedule.assert_called_once_with("validated-task-123")

    @patch("api.scheduled_tasks.delete_schedule")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_remove_scheduled_task_not_found(self, mock_validate_id, mock_delete_schedule):
        """Test deletion of non-existent scheduled task"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock deletion failure
        mock_delete_schedule.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await remove_scheduled_task("task-123")

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @patch("api.scheduled_tasks.update_task_status")
    @patch("api.scheduled_tasks.run_inspection")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_run_scheduled_task_success(self, mock_validate_id, mock_run_inspection, mock_update_status):
        """Test successful execution of scheduled task"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock inspection execution
        mock_run_inspection.return_value = (True, "Inspection completed", {"results": "data"})

        result = await run_scheduled_task("task-123")

        assert result["message"] == "Inspection completed"
        assert result["results"] == {"results": "data"}
        mock_validate_id.assert_called_once_with("task-123")
        mock_run_inspection.assert_called_once_with("validated-task-123", return_results=True)
        mock_update_status.assert_called_once_with("validated-task-123", last_status="success")

    @patch("api.scheduled_tasks.update_task_status")
    @patch("api.scheduled_tasks.run_inspection")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_run_scheduled_task_success_again(self, mock_validate_id, mock_run_inspection, mock_update_status):
        """Test successful execution of scheduled task again"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock inspection execution success
        mock_run_inspection.return_value = (True, "Inspection completed", {"results": "data"})

        result = await run_scheduled_task("task-123")

        assert result["message"] == "Inspection completed"
        assert result["results"] == {"results": "data"}
        mock_validate_id.assert_called_once_with("task-123")
        mock_run_inspection.assert_called_once_with("validated-task-123", return_results=True)
        mock_update_status.assert_called_once_with("validated-task-123", last_status="success")

    @patch("api.scheduled_tasks.update_task_status")
    @patch("api.scheduled_tasks.run_inspection")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_run_scheduled_task_success_third(self, mock_validate_id, mock_run_inspection, mock_update_status):
        """Test successful execution of scheduled task third time"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock inspection execution success
        mock_run_inspection.return_value = (True, "Inspection completed", {"results": "data"})

        result = await run_scheduled_task("task-123")

        assert result["message"] == "Inspection completed"
        assert result["results"] == {"results": "data"}
        mock_validate_id.assert_called_once_with("task-123")
        mock_run_inspection.assert_called_once_with("validated-task-123", return_results=True)
        mock_update_status.assert_called_once_with("validated-task-123", last_status="success")

    @patch("api.scheduled_tasks.schedule_tasks")
    @patch("api.scheduled_tasks.add_schedule")
    @patch("api.scheduled_tasks.delete_schedule")
    @patch("api.scheduled_tasks.load_schedules")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_update_scheduled_task_success(
        self,
        mock_validate_id,
        mock_load_schedules,
        mock_delete_schedule,
        mock_add_schedule,
        mock_schedule_tasks,
    ):
        """Test successful update of scheduled task"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock existing task
        mock_existing_task = Mock()
        mock_existing_task.task_id = "validated-task-123"
        # Mock load_schedules to return a list of tasks
        mock_load_schedules.return_value = [mock_existing_task]

        # Mock deletion and addition
        mock_delete_schedule.return_value = True
        mock_add_schedule.return_value = True

        # Create update request
        task = ScheduledTaskCreate(
            name="Updated_Task",
            cluster="test-cluster",
            description="Updated description",
            cron_expr="0 12 * * *",
            enabled=True,
            rules={"node": ["rule1"]},
            task_type="cron",
        )

        result = await update_scheduled_task("task-123", task)

        assert result["message"] == "Task updated successfully"
        mock_validate_id.assert_called_once_with("task-123")
        mock_delete_schedule.assert_called_once_with("validated-task-123")
        mock_add_schedule.assert_called_once()
        # Check that schedule_tasks was called at least once
        mock_schedule_tasks.assert_called_once()

    @patch("api.scheduled_tasks.load_schedules")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_update_scheduled_task_not_found(self, mock_validate_id, mock_load_schedules):
        """Test update of non-existent scheduled task"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock empty task list
        mock_load_schedules.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            await update_scheduled_task(
                "task-123",
                ScheduledTaskCreate(
                    name="Test_Task",
                    description="Test Description",
                    cluster="test-cluster",
                    cron_expr="0 9 * * 1",
                    rules={"node": ["rule1", "rule2"]},
                ),
            )

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @patch("api.scheduled_tasks.add_schedule")
    @patch("api.scheduled_tasks.delete_schedule")
    @patch("api.scheduled_tasks.load_schedules")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_update_scheduled_task_add_failure(
        self, mock_validate_id, mock_load_schedules, mock_delete_schedule, mock_add_schedule
    ):
        """Test update of scheduled task when add_schedule fails"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock existing task
        mock_existing_task = Mock()
        mock_existing_task.task_id = "validated-task-123"
        mock_load_schedules.return_value = [mock_existing_task]

        # Mock deletion success but addition failure
        mock_delete_schedule.return_value = True
        mock_add_schedule.return_value = False

        with patch("infrastructure.tasks.schedule_manager.ScheduleTask", return_value=Mock()):
            with pytest.raises(HTTPException) as exc_info:
                await update_scheduled_task(
                    "task-123",
                    ScheduledTaskCreate(
                        name="Test_Task",
                        description="Test Description",
                        cluster="test-cluster",
                        cron_expr="0 9 * * 1",
                        rules={"node": ["rule1", "rule2"]},
                    ),
                )

            assert exc_info.value.status_code == 500
            assert "Failed to update task" in str(exc_info.value.detail)
