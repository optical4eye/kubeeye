#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for network connectivity reports
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from scripts.api import app


class TestNetworkReportsIntegration:
    """Integration tests for network connectivity reports functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_network_check_request(self):
        """Sample network check request data"""
        return {
            "cluster_name": "test-cluster",
            "selected_nodes": ["192.168.1.1", "192.168.1.2"],
            "target_ip": "8.8.8.8",
            "target_port": 53,
            "timeout": 5,
        }

    @pytest.fixture
    def mock_network_check_result(self):
        """Mock network check result data"""
        return {
            "result_id": "test-network-result-123",
            "cluster_name": "test-cluster",
            "target_ip": "8.8.8.8",
            "target_port": 53,
            "timestamp": "2023-01-01T00:00:00Z",
            "results": [
                {
                    "status": "success",
                    "response_time": 0.023,
                    "node_ip": "192.168.1.1",
                    "target_ip": "8.8.8.8",
                    "target_port": 53,
                    "error": None,
                },
                {
                    "status": "success",
                    "response_time": 0.019,
                    "node_ip": "192.168.1.2",
                    "target_ip": "8.8.8.8",
                    "target_port": 53,
                    "error": None,
                },
            ],
        }

    @patch("api.network.check_connectivity_from_nodes")
    @patch("api.network.get_cluster")
    async def test_create_network_check_success(
        self, mock_get_cluster, mock_check_connectivity, client, sample_network_check_request
    ):
        """Test successful network connectivity check creation"""
        # Mock cluster configuration
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes = AsyncMock(
            return_value=[
                {"ip": "192.168.1.1", "port": 22, "name": "node1"},
                {"ip": "192.168.1.2", "port": 22, "name": "node2"},
            ]
        )
        mock_get_cluster.return_value = mock_cluster_config

        # Mock connectivity check results
        mock_check_results = [
            {
                "status": "success",
                "response_time": 0.023,
                "node_ip": "192.168.1.1",
                "target_ip": "8.8.8.8",
                "target_port": 53,
                "error": None,
            },
            {
                "status": "success",
                "response_time": 0.019,
                "node_ip": "192.168.1.2",
                "target_ip": "8.8.8.8",
                "target_port": 53,
                "error": None,
            },
        ]
        mock_check_connectivity.return_value = mock_check_results

        # Mock result saving
        with patch("api.network.NetworkConnectivityResult") as mock_result_class:
            mock_result_instance = Mock()
            mock_result_instance.save = AsyncMock(return_value="test-result-id-123")
            mock_result_class.return_value = mock_result_instance

            response = client.post("/api/network-check", json=sample_network_check_request)

            assert response.status_code == 200
            data = response.json()

            assert "result_id" in data
            assert "results" in data
            assert len(data["results"]) == 2
            assert data["results"][0]["status"] == "success"
            assert data["results"][1]["status"] == "success"

            # Verify mocks were called
            mock_get_cluster.assert_called_once_with("test-cluster")
            mock_check_connectivity.assert_called_once()
            mock_result_instance.save.assert_called_once()

    @patch("api.network.get_cluster")
    async def test_create_network_check_cluster_not_found(self, mock_get_cluster, client, sample_network_check_request):
        """Test network check creation with non-existent cluster"""
        mock_get_cluster.return_value = None

        response = client.post("/api/network-check", json=sample_network_check_request)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("api.network.InspectionResultRepository")
    async def test_delete_network_check_result_success(self, mock_repo_class, client):
        """Test successful deletion of network check result"""
        mock_repo = Mock()
        mock_repo.delete_by_result_id = AsyncMock(return_value=True)
        mock_repo_class.return_value = mock_repo

        response = client.delete("/api/network-check/results/test-network-result-123")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        mock_repo.delete_by_result_id.assert_called_once_with("test-network-result-123")

    @patch("api.network.InspectionResultRepository")
    async def test_delete_network_check_result_not_found(self, mock_repo_class, client):
        """Test deletion of non-existent network check result"""
        mock_repo = Mock()
        mock_repo.delete_by_result_id = AsyncMock(return_value=False)
        mock_repo_class.return_value = mock_repo

        response = client.delete("/api/network-check/results/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

        mock_repo.delete_by_result_id.assert_called_once_with("non-existent-id")

    @patch("api.network.list_clusters")
    @patch("api.network.get_cluster")
    async def test_get_clusters_for_network_check(self, mock_get_cluster, mock_list_clusters, client):
        """Test getting clusters available for network checks"""
        # Mock cluster names
        mock_list_clusters.return_value = ["cluster1", "cluster2"]

        # Mock cluster configurations
        mock_cluster1 = Mock()
        mock_cluster1.get_nodes = AsyncMock(
            return_value=[
                {"ip": "192.168.1.1", "name": "node1", "port": 22},
                {"ip": "192.168.1.2", "name": "node2", "port": 22},
            ]
        )

        mock_cluster2 = Mock()
        mock_cluster2.get_nodes = AsyncMock(return_value=[{"ip": "192.168.2.1", "name": "node3", "port": 22}])

        mock_get_cluster.side_effect = [mock_cluster1, mock_cluster2]

        response = client.get("/api/network-check/clusters")

        assert response.status_code == 200
        data = response.json()

        assert "clusters" in data
        assert len(data["clusters"]) == 2

        # Check first cluster
        cluster1 = data["clusters"][0]
        assert cluster1["name"] == "cluster1"
        assert len(cluster1["nodes"]) == 2
        assert cluster1["nodes"][0]["ip"] == "192.168.1.1"

        # Check second cluster
        cluster2 = data["clusters"][1]
        assert cluster2["name"] == "cluster2"
        assert len(cluster2["nodes"]) == 1
        assert cluster2["nodes"][0]["ip"] == "192.168.2.1"

        # Verify mocks were called
        mock_list_clusters.assert_called_once()

    async def test_create_network_check_invalid_ip(self, client):
        """Test network check creation with invalid IP address"""
        request_data = {
            "cluster_name": "test-cluster",
            "selected_nodes": ["192.168.1.1"],
            "target_ip": "invalid-ip",
            "target_port": 53,
            "timeout": 5,
        }

        response = client.post("/api/network-check", json=request_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "Invalid IP address or hostname" in str(data)

    async def test_create_network_check_invalid_port(self, client):
        """Test network check creation with invalid port"""
        request_data = {
            "cluster_name": "test-cluster",
            "selected_nodes": ["192.168.1.1"],
            "target_ip": "8.8.8.8",
            "target_port": 99999,  # Invalid port
            "timeout": 5,
        }

        response = client.post("/api/network-check", json=request_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "Port must be between 1 and 65535" in str(data)

    async def test_create_network_check_invalid_timeout(self, client):
        """Test network check creation with invalid timeout"""
        request_data = {
            "cluster_name": "test-cluster",
            "selected_nodes": ["192.168.1.1"],
            "target_ip": "8.8.8.8",
            "target_port": 53,
            "timeout": 50,  # Timeout too high
        }

        response = client.post("/api/network-check", json=request_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "timeout" in str(data).lower()

    @patch("api.network.list_network_check_results")
    async def test_get_network_check_results_invalid_limit(self, mock_list_results, client):
        """Test getting network check results with invalid limit parameter"""
        response = client.get("/api/network-check/results?limit=-1")

        # Should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        assert "limit" in str(data).lower()

    async def test_get_network_check_result_invalid_id(self, client):
        """Test getting network check result with invalid ID format"""
        response = client.get("/api/network-check/results/invalid@id!")

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "task_id" in str(data).lower()

    async def test_delete_network_check_result_invalid_id(self, client):
        """Test deleting network check result with invalid ID format"""
        response = client.delete("/api/network-check/results/invalid@id!")

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "task_id" in str(data).lower()

    async def test_export_network_check_result_invalid_id(self, client):
        """Test exporting network check result with invalid ID format"""
        response = client.get("/api/network-check/results/invalid@id!/export/json")

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "task_id" in str(data).lower()

    @patch("api.network.list_clusters")
    async def test_get_clusters_for_network_check_empty(self, mock_list_clusters, client):
        """Test getting clusters when no clusters are available"""
        mock_list_clusters.return_value = []

        response = client.get("/api/network-check/clusters")

        assert response.status_code == 200
        data = response.json()

        assert "clusters" in data
        assert len(data["clusters"]) == 0

        mock_list_clusters.assert_called_once()

    @patch("api.network.get_cluster")
    async def test_create_network_check_no_nodes(self, mock_get_cluster, client, sample_network_check_request):
        """Test network check creation with cluster having no nodes"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes = AsyncMock(return_value=[])
        mock_get_cluster.return_value = mock_cluster_config

        response = client.post("/api/network-check", json=sample_network_check_request)

        assert response.status_code == 400
        data = response.json()
        assert "no nodes configured" in data["detail"].lower()

    @patch("api.network.get_cluster")
    async def test_create_network_check_no_selected_nodes(self, mock_get_cluster, client):
        """Test network check creation with no selected nodes"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes = AsyncMock(return_value=[{"ip": "192.168.1.1", "port": 22, "name": "node1"}])
        mock_get_cluster.return_value = mock_cluster_config

        request_data = {
            "cluster_name": "test-cluster",
            "selected_nodes": [],  # Empty selected nodes
            "target_ip": "8.8.8.8",
            "target_port": 53,
            "timeout": 5,
        }

        response = client.post("/api/network-check", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "no valid nodes selected" in data["detail"].lower()

    @patch("api.network.list_network_check_results")
    async def test_get_network_check_results_list(self, mock_list_results, client):
        """Test getting list of network check results"""
        mock_results = [
            {
                "result_id": "result-1",
                "cluster_name": "test-cluster",
                "target_ip": "8.8.8.8",
                "target_port": 53,
                "timestamp": "2023-01-01T00:00:00Z",
                "summary": {"successful": 2, "failed": 0},
            },
            {
                "result_id": "result-2",
                "cluster_name": "test-cluster-2",
                "target_ip": "1.1.1.1",
                "target_port": 80,
                "timestamp": "2023-01-02T00:00:00Z",
                "summary": {"successful": 1, "failed": 1},
            },
        ]
        mock_list_results.return_value = mock_results

        response = client.get("/api/network-check/results")

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["result_id"] == "result-1"
        assert data["results"][1]["result_id"] == "result-2"

        mock_list_results.assert_called_once_with(cluster_name=None, limit=50)

    @patch("api.network.list_network_check_results")
    async def test_get_network_check_results_filtered_by_cluster(self, mock_list_results, client):
        """Test getting network check results filtered by cluster"""
        mock_results = [
            {
                "result_id": "result-1",
                "cluster_name": "test-cluster",
                "target_ip": "8.8.8.8",
                "target_port": 53,
                "timestamp": "2023-01-01T00:00:00Z",
            }
        ]
        mock_list_results.return_value = mock_results

        response = client.get("/api/network-check/results?cluster_name=test-cluster&limit=10")

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        assert data["results"][0]["cluster_name"] == "test-cluster"

        mock_list_results.assert_called_once_with(cluster_name="test-cluster", limit=10)

    @patch("api.network.load_network_check_result")
    async def test_get_network_check_result_success(self, mock_load_result, client, mock_network_check_result):
        """Test getting specific network check result"""
        mock_load_result.return_value = mock_network_check_result

        response = client.get("/api/network-check/results/test-network-result-123")

        assert response.status_code == 200
        data = response.json()

        assert data["result_id"] == "test-network-result-123"
        assert data["cluster_name"] == "test-cluster"
        assert data["target_ip"] == "8.8.8.8"
        assert data["target_port"] == 53
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "success"
        assert data["results"][1]["status"] == "success"

        mock_load_result.assert_called_once_with("test-network-result-123")

    @patch("api.network.load_network_check_result")
    async def test_get_network_check_result_not_found(self, mock_load_result, client):
        """Test getting non-existent network check result"""
        mock_load_result.return_value = None

        response = client.get("/api/network-check/results/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

        mock_load_result.assert_called_once_with("non-existent-id")

    @patch("api.network.export_network_stream")
    @patch("api.network.load_network_check_result")
    async def test_export_network_check_result_json(
        self, mock_load_result, mock_export_stream, client, mock_network_check_result
    ):
        """Test exporting network check result as JSON"""
        mock_load_result.return_value = mock_network_check_result

        # Mock the async generator
        async def mock_generator():
            yield json.dumps(mock_network_check_result).encode("utf-8")

        mock_export_stream.return_value = mock_generator()

        response = client.get("/api/network-check/results/test-network-result-123/export/json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify the response content
        content = response.content.decode("utf-8")
        data = json.loads(content)
        assert data["result_id"] == "test-network-result-123"

        mock_load_result.assert_called_once_with("test-network-result-123")
        mock_export_stream.assert_called_once_with("test-network-result-123", "json")

    @patch("api.network.load_network_check_result")
    async def test_export_network_check_result_invalid_format(
        self, mock_load_result, client, mock_network_check_result
    ):
        """Test exporting network check result with invalid format"""
        mock_load_result.return_value = mock_network_check_result

        response = client.get("/api/network-check/results/test-network-result-123/export/invalid")

        assert response.status_code == 400
        data = response.json()
        assert "format must be one of" in data["detail"].lower()

    @patch("api.network.load_network_check_result")
    async def test_export_network_check_result_not_found(self, mock_load_result, client):
        """Test exporting non-existent network check result"""
        mock_load_result.return_value = None

        response = client.get("/api/network-check/results/non-existent-id/export/json")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
