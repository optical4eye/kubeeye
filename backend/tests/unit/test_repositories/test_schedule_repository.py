# /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ScheduleRepository
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.schedule_repository import ScheduleRepository
from db.models.schedule import ScheduledTask
from core.common.exceptions import TaskNotFoundError, DatabaseError


class TestScheduleRepository:
    """Test cases for ScheduleRepository"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def repo(self, mock_session):
        """ScheduleRepository instance"""
        return ScheduleRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_pending_one_time_tasks_fixed_bug(self, repo, mock_session):
        """Test that get_pending_one_time_tasks uses correct SQLAlchemy syntax"""
        # Mock the current time
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Mock the query execution
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch("db.repositories.schedule_repository.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = now

            # Call the method
            result = await repo.get_pending_one_time_tasks()

            # Verify the query was constructed correctly
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args[0][0]

            # The query should be a select statement, not a raw dict filter
            # We can't easily inspect the exact SQL, but we can verify it doesn't crash
            # and that it returns the expected result
            assert result == []

    @pytest.mark.asyncio
    async def test_get_by_task_id_success(self, repo, mock_session):
        """Test successful task retrieval by ID"""
        mock_task = Mock(spec=ScheduledTask)
        mock_task.task_id = "test-task-123"

        with patch.object(repo, "get_by_field", new_callable=AsyncMock) as mock_get_by_field:
            mock_get_by_field.return_value = mock_task

            result = await repo.get_by_task_id("test-task-123")

            assert result == mock_task
            mock_get_by_field.assert_called_once_with("task_id", "test-task-123")

    @pytest.mark.asyncio
    async def test_get_by_task_id_not_found(self, repo, mock_session):
        """Test task retrieval when task doesn't exist"""
        with patch.object(repo, "get_by_field", new_callable=AsyncMock) as mock_get_by_field:
            mock_get_by_field.return_value = None

            with pytest.raises(TaskNotFoundError, match="Task with ID test-task-123 not found"):
                await repo.get_by_task_id("test-task-123")

    @pytest.mark.asyncio
    async def test_update_task_status_with_retry(self, repo, mock_session):
        """Test task status update with retry decorator"""
        mock_task = Mock(spec=ScheduledTask)

        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = mock_task

            result = await repo.update_task_status(
                "test-task-123", last_run=datetime.now(timezone.utc), last_status="success"
            )

            assert result is True
            mock_get_by_field_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_status_task_not_found(self, repo, mock_session):
        """Test task status update when task doesn't exist"""
        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            # When get_by_field_and_update returns None, update_task_status returns False
            mock_get_by_field_and_update.return_value = None

            result = await repo.update_task_status("nonexistent-task", last_run=datetime.now(timezone.utc))

            assert result is False

    @pytest.mark.asyncio
    async def test_create_task_success(self, repo, mock_session):
        """Test successful task creation"""
        task_data = {"task_id": "new-task", "name": "New Task", "cluster_name": "test-cluster"}

        mock_created_task = Mock(spec=ScheduledTask)
        mock_created_task.task_id = "new-task"

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_created_task

            result = await repo.create_task(task_data)

            assert result == mock_created_task
            mock_create.assert_called_once_with(task_data)

    @pytest.mark.asyncio
    async def test_get_enabled_tasks(self, repo, mock_session):
        """Test retrieval of enabled tasks"""
        mock_tasks = [Mock(spec=ScheduledTask), Mock(spec=ScheduledTask)]

        with patch.object(repo, "get_all", new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = mock_tasks

            result = await repo.get_enabled_tasks()

            assert result == mock_tasks
            mock_get_all.assert_called_once_with(enabled=True)

    @pytest.mark.asyncio
    async def test_get_tasks_by_cluster(self, repo, mock_session):
        """Test retrieval of tasks by cluster"""
        cluster_name = "test-cluster"
        mock_tasks = [Mock(spec=ScheduledTask)]

        with patch.object(repo, "get_all", new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = mock_tasks

            result = await repo.get_tasks_by_cluster(cluster_name)

            assert result == mock_tasks
            mock_get_all.assert_called_once_with(cluster_name=cluster_name)

    @pytest.mark.asyncio
    async def test_delete_task_success(self, repo, mock_session):
        """Test successful task deletion"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = True

            result = await repo.delete_task("test-task")

            assert result is True
            mock_get_by_field_and_delete.assert_called_once_with("task_id", "test-task")

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, repo, mock_session):
        """Test task deletion when task doesn't exist"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = False

            result = await repo.delete_task("nonexistent-task")

            assert result is False

    def test_to_dict_conversion(self, repo):
        """Test conversion of task to dictionary"""
        mock_task = Mock(spec=ScheduledTask)
        mock_task.task_id = "test-task"
        mock_task.cluster_name = "test-cluster"
        mock_task.name = "Test Task"
        mock_task.description = "Test description"
        mock_task.cron_expr = "0 0 * * *"
        mock_task.enabled = True
        mock_task.rules = {"node": ["rule1"]}
        mock_task.task_type = "cron"
        mock_task.last_run = None
        mock_task.last_status = None
        mock_task.created_at = None
        mock_task.run_datetime = None

        result = repo.to_dict(mock_task)

        expected = {
            "task_id": "test-task",
            "cluster": "test-cluster",
            "name": "Test Task",
            "description": "Test description",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["rule1"]},
            "task_type": "cron",
            "last_run": None,
            "last_status": None,
            "created_at": None,
            "run_datetime": None,
        }

        assert result == expected

    def test_from_dict_conversion(self, repo):
        """Test conversion from dictionary to task data"""
        data = {
            "task_id": "test-task",
            "cluster": "test-cluster",
            "name": "Test Task",
            "description": "Test description",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["rule1"]},
            "task_type": "cron",
            "last_run": None,
            "last_status": None,
            "run_datetime": None,
        }

        result = repo.from_dict(data)

        expected = {
            "task_id": "test-task",
            "cluster_name": "test-cluster",
            "name": "Test Task",
            "description": "Test description",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["rule1"]},
            "task_type": "cron",
            "last_run": None,
            "last_status": None,
            "run_datetime": None,
        }

        assert result == expected
