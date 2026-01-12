# Integration tests for scheduled tasks functionality

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from scripts.api import app


class TestScheduledTasksIntegration:
    """Integration tests for scheduled tasks API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_get_scheduled_tasks_success(self, mock_get_service, client):
        """Test successful retrieval of scheduled tasks"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_all_tasks.return_value = [
            {
                "task_id": "task1",
                "name": "Test Task 1",
                "cluster": "test-cluster",
                "cron_expr": "0 0 * * *",
                "enabled": True,
                "task_type": "cron",
            },
            {
                "task_id": "task2",
                "name": "Test Task 2",
                "cluster": "prod-cluster",
                "cron_expr": "0 */6 * * *",
                "enabled": False,
                "task_type": "cron",
            },
        ]
        mock_get_service.return_value = mock_task_manager

        response = client.get("/api/scheduled-tasks")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "task1"
        assert data["tasks"][1]["task_id"] == "task2"

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_get_scheduled_tasks_empty(self, mock_get_service, client):
        """Test retrieval of empty scheduled tasks list"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_all_tasks.return_value = []
        mock_get_service.return_value = mock_task_manager

        response = client.get("/api/scheduled-tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_get_scheduled_tasks_error(self, mock_get_service, client):
        """Test scheduled tasks retrieval with error"""
        mock_get_service.side_effect = Exception("Database error")

        response = client.get("/api/scheduled-tasks")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_get_scheduled_task_success(self, mock_get_service, client):
        """Test successful retrieval of specific scheduled task"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_task.return_value = {
            "task_id": "task1",
            "name": "Test Task",
            "cluster": "test-cluster",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "task_type": "cron",
        }
        mock_get_service.return_value = mock_task_manager

        response = client.get("/api/scheduled-tasks/task1")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task1"
        assert data["name"] == "Test Task"
        assert data["cluster"] == "test-cluster"

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_get_scheduled_task_not_found(self, mock_get_service, client):
        """Test retrieval of non-existent scheduled task"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_task.return_value = None
        mock_get_service.return_value = mock_task_manager

        response = client.get("/api/scheduled-tasks/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data["detail"]

    def test_get_scheduled_task_invalid_id(self, client):
        """Test retrieval with invalid task ID"""
        response = client.get("/api/scheduled-tasks/invalid@id")

        assert response.status_code == 500  # Validation error converted to 500

    @patch("api.unified_middleware.ValidationMiddleware._validate_body")
    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_create_scheduled_task_success(self, mock_get_service, mock_validate, client):
        """Test successful creation of scheduled task"""
        mock_validate.return_value = None
        mock_task_manager = AsyncMock()
        mock_task_manager.create_task.return_value = {
            "task_id": "task_1234567890",
            "name": "New Task",
            "cluster": "test-cluster",
        }
        mock_get_service.return_value = mock_task_manager

        task_data = {
            "cluster": "test-cluster",
            "name": "New_Task",
            "description": "A simple task",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["node_disk_usage"]},
            "task_type": "cron",
        }

        response = client.post("/api/scheduled-tasks", json=task_data)

        assert response.status_code == 200
        data = response.json()
        assert "Task created successfully" in data["message"]
        assert "task_id" in data

    @patch("api.unified_middleware.ValidationMiddleware._validate_body")
    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_create_scheduled_task_failure(self, mock_get_service, mock_validate, client):
        """Test scheduled task creation failure"""
        mock_validate.return_value = None
        mock_task_manager = AsyncMock()
        mock_task_manager.create_task.return_value = None
        mock_get_service.return_value = mock_task_manager

        task_data = {
            "cluster": "test-cluster",
            "name": "Failed_Task",
            "description": "A failed task",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["node_disk_usage"]},
        }

        response = client.post("/api/scheduled-tasks", json=task_data)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to create task" in data["detail"]

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_delete_scheduled_task_success(self, mock_get_service, client):
        """Test successful deletion of scheduled task"""
        mock_task_manager = AsyncMock()
        mock_task_manager.delete_task.return_value = True
        mock_get_service.return_value = mock_task_manager

        response = client.delete("/api/scheduled-tasks/task1")

        assert response.status_code == 200
        data = response.json()
        assert "Task task1 deleted" in data["message"]

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_delete_scheduled_task_not_found(self, mock_get_service, client):
        """Test deletion of non-existent scheduled task"""
        mock_task_manager = AsyncMock()
        mock_task_manager.delete_task.return_value = False
        mock_get_service.return_value = mock_task_manager

        response = client.delete("/api/scheduled-tasks/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data["detail"]

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_run_scheduled_task_success(self, mock_get_service, client):
        """Test successful execution of scheduled task"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_task.return_value = {"task_id": "task1"}
        mock_task_manager.run_task_now.return_value = {
            "success": True,
            "message": "Task executed successfully",
            "results": {"status": "completed"},
        }
        mock_get_service.return_value = mock_task_manager

        response = client.post("/api/scheduled-tasks/task1/run")

        assert response.status_code == 200
        data = response.json()
        assert "Task executed successfully" in data["message"]
        assert data["results"]["status"] == "completed"

    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_run_scheduled_task_failure(self, mock_get_service, client):
        """Test scheduled task execution failure"""
        mock_task_manager = AsyncMock()
        mock_task_manager.get_task.return_value = {"task_id": "task1"}
        mock_task_manager.run_task_now.return_value = {"success": False, "message": "Task execution failed"}
        mock_get_service.return_value = mock_task_manager

        response = client.post("/api/scheduled-tasks/task1/run")

        assert response.status_code == 500
        data = response.json()
        assert "Task execution failed" in data["detail"]

    @patch("api.unified_middleware.ValidationMiddleware._validate_body")
    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_update_scheduled_task_success(self, mock_get_service, mock_validate, client):
        """Test successful update of scheduled task"""
        mock_validate.return_value = None
        mock_task_manager = AsyncMock()
        mock_task_manager.update_task.return_value = True
        mock_get_service.return_value = mock_task_manager

        update_data = {
            "cluster": "updated-cluster",
            "name": "Updated_Task",
            "description": "An updated task",
            "cron_expr": "0 */2 * * *",
            "enabled": False,
            "rules": {"node": ["node_memory_usage"]},
            "task_type": "cron",
        }

        response = client.put("/api/scheduled-tasks/task1", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert "Task updated successfully" in data["message"]

    @patch("api.unified_middleware.ValidationMiddleware._validate_body")
    @patch("api.scheduled_tasks.get_service", new_callable=AsyncMock)
    def test_update_scheduled_task_not_found(self, mock_get_service, mock_validate, client):
        """Test update of non-existent scheduled task"""
        mock_validate.return_value = None
        mock_task_manager = AsyncMock()
        mock_task_manager.update_task.return_value = False
        mock_get_service.return_value = mock_task_manager

        update_data = {
            "cluster": "test-cluster",
            "name": "Updated_Task",
            "description": "An updated task",
            "cron_expr": "0 0 * * *",
            "enabled": True,
            "rules": {"node": ["node_disk_usage"]},
        }

        response = client.put("/api/scheduled-tasks/non-existent", json=update_data)

        assert response.status_code == 404
        data = response.json()
        assert "Task not found" in data["detail"]
