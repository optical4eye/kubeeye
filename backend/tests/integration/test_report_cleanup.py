# Integration tests for report cleanup functionality

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from scripts.api import app


class TestReportCleanupIntegration:
    """Integration tests for report cleanup API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @patch("api.report_cleanup.get_cleanup_stats", new_callable=AsyncMock)
    def test_get_cleanup_statistics_success(self, mock_get_stats, client):
        """Test successful retrieval of cleanup statistics"""
        mock_get_stats.return_value = {
            "total_records": 100,
            "old_records": 20,
            "recent_records": 80,
            "retention_days": 7,
            "cleanup_percentage": 20.0,
        }

        response = client.get("/api/cleanup/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 100
        assert data["old_records"] == 20
        assert data["recent_records"] == 80
        assert data["retention_days"] == 7
        assert data["cleanup_percentage"] == 20.0

    @patch("api.report_cleanup.get_cleanup_stats", new_callable=AsyncMock)
    def test_get_cleanup_statistics_error(self, mock_get_stats, client):
        """Test cleanup statistics with error"""
        mock_get_stats.return_value = {"error": "Database connection failed"}

        response = client.get("/api/cleanup/stats")

        assert response.status_code == 500
        data = response.json()
        assert "Database connection failed" in data["detail"]

    @patch("api.report_cleanup.cleanup_old_reports", new_callable=AsyncMock)
    def test_run_cleanup_success(self, mock_cleanup, client):
        """Test successful cleanup run"""
        mock_cleanup.return_value = {
            "deleted_count": 15,
            "retention_days": 7,
            "message": "Successfully deleted 15 old reports",
        }

        response = client.post("/api/cleanup/run")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 15
        assert data["retention_days"] == 7
        assert "Successfully deleted 15 old reports" in data["message"]

    @patch("api.report_cleanup.cleanup_old_reports", new_callable=AsyncMock)
    def test_run_cleanup_with_custom_retention(self, mock_cleanup, client):
        """Test cleanup run with custom retention days"""
        mock_cleanup.return_value = {
            "deleted_count": 25,
            "retention_days": 3,
            "message": "Successfully deleted 25 old reports",
        }

        response = client.post("/api/cleanup/run?retention_days=3")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 25
        assert data["retention_days"] == 3

    @patch("api.report_cleanup.cleanup_old_reports", new_callable=AsyncMock)
    def test_run_cleanup_error(self, mock_cleanup, client):
        """Test cleanup run with error"""
        mock_cleanup.return_value = {"error": "Cleanup failed"}

        response = client.post("/api/cleanup/run")

        assert response.status_code == 500
        data = response.json()
        assert "Cleanup failed" in data["detail"]

    @patch("api.report_cleanup.cleanup_reports_by_cluster", new_callable=AsyncMock)
    def test_run_cluster_cleanup_success(self, mock_cleanup, client):
        """Test successful cluster-specific cleanup"""
        mock_cleanup.return_value = {
            "deleted_count": 5,
            "cluster_name": "test-cluster",
            "retention_days": 7,
            "message": "Successfully deleted 5 old reports for cluster 'test-cluster'",
        }

        response = client.post("/api/cleanup/cluster/test-cluster")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 5
        assert data["cluster_name"] == "test-cluster"
        assert data["retention_days"] == 7

    @patch("api.report_cleanup.cleanup_reports_by_cluster", new_callable=AsyncMock)
    def test_run_cluster_cleanup_with_custom_retention(self, mock_cleanup, client):
        """Test cluster cleanup with custom retention days"""
        mock_cleanup.return_value = {
            "deleted_count": 8,
            "cluster_name": "prod-cluster",
            "retention_days": 14,
            "message": "Successfully deleted 8 old reports for cluster 'prod-cluster'",
        }

        response = client.post("/api/cleanup/cluster/prod-cluster?retention_days=14")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 8
        assert data["cluster_name"] == "prod-cluster"
        assert data["retention_days"] == 14

    @patch("api.report_cleanup.cleanup_reports_by_cluster", new_callable=AsyncMock)
    def test_run_cluster_cleanup_error(self, mock_cleanup, client):
        """Test cluster cleanup with error"""
        mock_cleanup.return_value = {"error": "Cluster not found"}

        response = client.post("/api/cleanup/cluster/non-existent")

        assert response.status_code == 500
        data = response.json()
        assert "Cluster not found" in data["detail"]

    @patch("api.report_cleanup.settings")
    @patch("api.report_cleanup.get_report_cleanup_service")
    def test_get_cleanup_config_from_env(self, mock_get_service, mock_settings, client):
        """Test getting cleanup config from environment variable"""
        mock_settings.kubeeye_report_retention_days = 10
        mock_service = AsyncMock()
        mock_service.retention_days = 10
        mock_get_service.return_value = mock_service

        response = client.get("/api/cleanup/config")

        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 10
        assert data["source"] == "settings"
        assert data["env_variable"] == "KUBEEYE_REPORT_RETENTION_DAYS"
        assert data["default_value"] == 7

    @patch("api.report_cleanup.settings")
    @patch("api.report_cleanup.get_report_cleanup_service")
    def test_get_cleanup_config_default(self, mock_get_service, mock_settings, client):
        """Test getting cleanup config with default value"""
        mock_settings.kubeeye_report_retention_days = 7
        mock_service = AsyncMock()
        mock_service.retention_days = 7
        mock_get_service.return_value = mock_service

        response = client.get("/api/cleanup/config")

        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 7
        assert data["source"] == "settings"
        assert data["default_value"] == 7

    @patch("api.report_cleanup.get_report_cleanup_service")
    def test_get_cleanup_config_error(self, mock_get_service, client):
        """Test cleanup config with error"""
        mock_get_service.side_effect = Exception("Service initialization failed")

        response = client.get("/api/cleanup/config")

        assert response.status_code == 500
        data = response.json()
        assert "Service initialization failed" in data["detail"]
