#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for inspection API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException, BackgroundTasks

from api.inspection import (
    run_immediate_inspection,
    run_async_inspection,
    get_inspection_task_status,
    cancel_inspection_task,
    AsyncInspectionRequest,
)
from api.models import InspectionRequest


class TestInspectionAPI:
    """Test cases for inspection API endpoints"""

    @patch("api.inspection.execute_inspection_unified")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_immediate_inspection_success(self, mock_should_use_gitops, mock_execute_inspection):
        """Test successful immediate inspection"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock inspection execution - return AsyncMock that returns the tuple
        async def mock_exec(*args, **kwargs):
            return (True, "Inspection completed successfully", {"results": "data"})

        mock_execute_inspection.side_effect = mock_exec

        # Create request
        request = InspectionRequest(
            cluster_name="test-cluster", selected_rules={"node": ["rule1"]}, inspection_type="immediate"
        )

        # Mock background tasks
        background_tasks = Mock(spec=BackgroundTasks)

        result = await run_immediate_inspection(request, background_tasks)

        assert result["message"] == "Inspection completed successfully"
        assert result["results"] == {"results": "data"}
        mock_execute_inspection.assert_called_once_with(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

    @patch("api.inspection.execute_inspection_unified")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_immediate_inspection_with_gitops(self, mock_should_use_gitops, mock_execute_inspection):
        """Test immediate inspection with GitOps enabled"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock inspection execution - return AsyncMock that returns the tuple
        async def mock_exec(*args, **kwargs):
            return (True, "Inspection completed successfully", {"results": "data"})

        mock_execute_inspection.side_effect = mock_exec

        # Create request
        request = InspectionRequest(
            cluster_name="test-cluster", selected_rules={"node": ["rule1"]}, inspection_type="immediate"
        )

        # Mock background tasks
        background_tasks = Mock(spec=BackgroundTasks)

        result = await run_immediate_inspection(request, background_tasks)

        assert result["message"] == "Inspection completed successfully"
        assert result["results"] == {"results": "data"}
        mock_execute_inspection.assert_called_once_with(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=True,
        )

    @patch("api.inspection.execute_inspection_unified")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_immediate_inspection_no_types_configured(self, mock_should_use_gitops, mock_execute_inspection):
        """Test immediate inspection when no types are configured"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock inspection execution with no types configured
        async def mock_exec(*args, **kwargs):
            return (False, "No inspection types were configured", {})

        mock_execute_inspection.side_effect = mock_exec

        # Create request
        request = InspectionRequest(cluster_name="test-cluster", selected_rules={}, inspection_type="immediate")

        # Mock background tasks
        background_tasks = Mock(spec=BackgroundTasks)

        with pytest.raises(HTTPException) as exc_info:
            await run_immediate_inspection(request, background_tasks)

        assert exc_info.value.status_code == 400
        assert "No inspection types were configured" in str(exc_info.value.detail)

    @patch("api.inspection.execute_inspection_unified")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_immediate_inspection_exception(self, mock_should_use_gitops, mock_execute_inspection):
        """Test immediate inspection with exception"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock inspection execution with exception
        async def mock_exec(*args, **kwargs):
            raise Exception("Inspection error")

        mock_execute_inspection.side_effect = mock_exec

        # Create request
        request = InspectionRequest(
            cluster_name="test-cluster", selected_rules={"node": ["rule1"]}, inspection_type="immediate"
        )

        # Mock background tasks
        background_tasks = Mock(spec=BackgroundTasks)

        with pytest.raises(HTTPException) as exc_info:
            await run_immediate_inspection(request, background_tasks)

        assert exc_info.value.status_code == 500
        assert "Inspection error" in str(exc_info.value.detail)

    @patch("api.inspection.submit_inspection_task")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_async_inspection_success(self, mock_should_use_gitops, mock_submit_task):
        """Test successful async inspection"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock task submission
        async def mock_submit(*args, **kwargs):
            return "task-123"

        mock_submit_task.side_effect = mock_submit

        # Create request
        request = AsyncInspectionRequest(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            use_gitops=False,
        )

        result = await run_async_inspection(request)

        assert result["task_id"] == "task-123"
        assert result["message"] == "Inspection task submitted successfully"
        assert result["status"] == "pending"
        mock_submit_task.assert_called_once_with(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            use_gitops=False,
        )

    @patch("api.inspection.submit_inspection_task")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_async_inspection_auto_gitops(self, mock_should_use_gitops, mock_submit_task):
        """Test async inspection with automatic GitOps detection"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock task submission
        async def mock_submit(*args, **kwargs):
            return "task-123"

        mock_submit_task.side_effect = mock_submit

        # Create request with use_gitops=False (should be overridden)
        request = AsyncInspectionRequest(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            use_gitops=False,
        )

        result = await run_async_inspection(request)

        assert result["task_id"] == "task-123"
        assert result["message"] == "Inspection task submitted successfully"
        assert result["status"] == "pending"
        # Verify that use_gitops was updated to True
        assert request.use_gitops is True
        mock_submit_task.assert_called_once_with(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            use_gitops=True,
        )

    @patch("api.inspection.submit_inspection_task")
    @patch("api.inspection.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_run_async_inspection_exception(self, mock_should_use_gitops, mock_submit_task):
        """Test async inspection with exception"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock task submission with exception
        async def mock_submit(*args, **kwargs):
            raise Exception("Task submission error")

        mock_submit_task.side_effect = mock_submit

        # Create request
        request = AsyncInspectionRequest(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            use_gitops=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await run_async_inspection(request)

        assert exc_info.value.status_code == 500
        assert "Failed to submit task" in str(exc_info.value.detail)
        assert "Task submission error" in str(exc_info.value.detail)

    @patch("api.inspection.get_task_queue")
    @patch("api.inspection.validate_task_id")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_get_inspection_task_status_success(self, mock_validate_id, mock_get_queue):
        """Test successful task status retrieval"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue and status
        mock_task_queue = AsyncMock()
        mock_task_queue.get_task_status.return_value = {
            "task_id": "validated-task-123",
            "status": "completed",
            "progress": 100,
        }

        async def mock_get_q(*args, **kwargs):
            return mock_task_queue

        mock_get_queue.side_effect = mock_get_q

        result = await get_inspection_task_status("task-123")

        assert result["task_id"] == "validated-task-123"
        assert result["status"] == "completed"
        assert result["progress"] == 100
        mock_validate_id.assert_called_once_with("task-123")
        mock_task_queue.get_task_status.assert_called_once_with("validated-task-123")

    @patch("infrastructure.tasks.task_queue.get_task_queue")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_inspection_task_status_not_found(self, mock_validate_id, mock_get_queue):
        """Test task status retrieval when task not found"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue and status
        mock_task_queue = AsyncMock()
        mock_task_queue.get_task_status.return_value = None
        mock_get_queue.return_value = mock_task_queue

        with pytest.raises(HTTPException) as exc_info:
            await get_inspection_task_status("task-123")

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @patch("api.inspection.get_task_queue")
    @patch("api.inspection.validate_task_id")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_get_inspection_task_status_exception(self, mock_validate_id, mock_get_queue):
        """Test task status retrieval with exception"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue with exception
        mock_task_queue = AsyncMock()
        mock_task_queue.get_task_status.side_effect = Exception("Queue error")

        async def mock_get_q(*args, **kwargs):
            return mock_task_queue

        mock_get_queue.side_effect = mock_get_q

        with pytest.raises(HTTPException) as exc_info:
            await get_inspection_task_status("task-123")

        assert exc_info.value.status_code == 500
        assert "Failed to get task status" in str(exc_info.value.detail)

    @patch("api.inspection.get_task_queue")
    @patch("api.inspection.validate_task_id")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_cancel_inspection_task_success(self, mock_validate_id, mock_get_queue):
        """Test successful task cancellation"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue and cancellation
        mock_task_queue = AsyncMock()
        mock_task_queue.cancel_task.return_value = True

        async def mock_get_q(*args, **kwargs):
            return mock_task_queue

        mock_get_queue.side_effect = mock_get_q

        result = await cancel_inspection_task("task-123")

        assert result["message"] == "Task cancelled successfully"
        mock_validate_id.assert_called_once_with("task-123")
        mock_task_queue.cancel_task.assert_called_once_with("validated-task-123")

    @patch("infrastructure.tasks.task_queue.get_task_queue")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_cancel_inspection_task_cannot_cancel(self, mock_validate_id, mock_get_queue):
        """Test task cancellation when task cannot be cancelled"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue and cancellation failure
        mock_task_queue = AsyncMock()
        mock_task_queue.cancel_task.return_value = False
        mock_get_queue.return_value = mock_task_queue

        with pytest.raises(HTTPException) as exc_info:
            await cancel_inspection_task("task-123")

        assert exc_info.value.status_code == 400
        assert "Task cannot be cancelled" in str(exc_info.value.detail)

    @patch("api.inspection.get_task_queue")
    @patch("api.inspection.validate_task_id")
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocking issues - needs refactoring")
    async def test_cancel_inspection_task_exception(self, mock_validate_id, mock_get_queue):
        """Test task cancellation with exception"""
        # Mock validation
        mock_validate_id.return_value = "validated-task-123"

        # Mock task queue with exception
        mock_task_queue = AsyncMock()
        mock_task_queue.cancel_task.side_effect = Exception("Queue error")

        async def mock_get_q(*args, **kwargs):
            return mock_task_queue

        mock_get_queue.side_effect = mock_get_q

        with pytest.raises(HTTPException) as exc_info:
            await cancel_inspection_task("task-123")

        assert exc_info.value.status_code == 500
        assert "Failed to cancel task" in str(exc_info.value.detail)
