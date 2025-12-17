#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for KubeEye API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from api.main import app


class TestAPIIntegration:
    """Integration tests for the complete API"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "KubeEye API" in data["message"]
        assert "version" in data
        assert "docs" in data
        assert "endpoints" in data

        # Check that all expected endpoints are listed
        endpoints = data["endpoints"]
        expected_endpoints = [
            "health",
            "clusters",
            "inspection",
            "reports",
            "rules",
            "scheduled_tasks",
            "gitops",
            "cleanup",
            "network-check",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in endpoints

    def test_api_info_endpoint(self, client):
        """Test API info endpoint"""
        response = client.get("/api/info")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "KubeEye API"
        assert "version" in data
        assert "features" in data
        assert "security" in data
        assert "supported_inspection_types" in data
        assert "documentation" in data

        # Check features list
        features = data["features"]
        assert "Multi-cluster management" in features
        assert "Automated security inspections" in features

        # Check security features
        security = data["security"]
        assert "Read-only operations only" in security

    @patch("api.main.get_system_health")
    @patch("infrastructure.tasks.task_queue.task_queue")
    def test_health_check_endpoint(self, mock_task_queue, mock_get_health, client):
        """Test health check endpoint"""
        # Mock system health
        mock_get_health.return_value = {"cpu_usage": 45.2, "memory_usage": 67.8, "disk_usage": 23.1}

        # Mock task queue
        mock_task_queue.running = True
        mock_task_queue.queue.qsize.return_value = 2
        mock_task_queue.tasks = {
            "task1": Mock(status=Mock(value="running")),
            "task2": Mock(status=Mock(value="pending")),
            "task3": Mock(status=Mock(value="completed")),
        }

        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "queue" in data

        # Check queue information
        queue_info = data["queue"]
        assert queue_info["running"] is True
        assert queue_info["queue_size"] == 2
        assert queue_info["active_workers"] == 1  # One running task
        assert queue_info["pending_tasks"] == 1

    @patch("infrastructure.tasks.task_queue.task_queue")
    def test_queue_status_endpoint(self, mock_task_queue, client):
        """Test queue status endpoint"""
        mock_task_queue.running = True
        mock_task_queue.max_workers = 5
        mock_task_queue.queue.qsize.return_value = 3
        mock_task_queue.tasks = {
            "task1": Mock(status=Mock(value="running")),
            "task2": Mock(status=Mock(value="running")),
            "task3": Mock(status=Mock(value="pending")),
        }

        response = client.get("/api/queue/status")

        assert response.status_code == 200
        data = response.json()

        assert data["running"] is True
        assert data["max_workers"] == 5
        assert data["queue_size"] == 3
        assert data["active_tasks"] == 2
        assert data["pending_tasks"] == 1
        assert data["total_tasks"] == 3

    @patch("infrastructure.tasks.task_queue.task_queue")
    def test_queue_tasks_endpoint(self, mock_task_queue, client):
        """Test queue tasks endpoint"""
        # Create mock tasks with creation times
        mock_task1 = Mock()
        mock_task1.created_at = 1000
        mock_task1.to_dict.return_value = {"id": "task1", "status": "running"}

        mock_task2 = Mock()
        mock_task2.created_at = 2000
        mock_task2.to_dict.return_value = {"id": "task2", "status": "pending"}

        mock_task_queue.tasks = {"task1": mock_task1, "task2": mock_task2}

        response = client.get("/api/queue/tasks")

        assert response.status_code == 200
        data = response.json()

        assert "tasks" in data
        assert len(data["tasks"]) == 2
        assert data["total"] == 2

        # Tasks should be sorted by creation time (newest first)
        tasks = data["tasks"]
        assert tasks[0]["id"] == "task2"  # Newer task first
        assert tasks[1]["id"] == "task1"

    @patch("infrastructure.tasks.task_queue.task_queue")
    def test_queue_tasks_endpoint_with_limit(self, mock_task_queue, client):
        """Test queue tasks endpoint with limit parameter"""
        # Create many mock tasks
        mock_tasks = {}
        for i in range(10):
            mock_task = Mock()
            mock_task.created_at = i * 100
            mock_task.to_dict.return_value = {"id": f"task{i}", "status": "pending"}
            mock_tasks[f"task{i}"] = mock_task

        mock_task_queue.tasks = mock_tasks

        response = client.get("/api/queue/tasks?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert len(data["tasks"]) == 3
        assert data["total"] == 10

    @patch("api.clusters.list_clusters")
    @patch("api.clusters.get_cluster")
    @patch("api.clusters.get_cluster_cert_status")
    def test_clusters_endpoint(self, mock_cert_status, mock_get_cluster, mock_list_clusters, client):
        """Test clusters listing endpoint"""
        # Mock cluster data
        mock_list_clusters.return_value = ["cluster1", "cluster2"]

        # Mock cluster objects
        mock_cluster1 = Mock()
        mock_cluster1.get_nodes.return_value = [{"ip": "192.168.1.1", "port": 22}]
        mock_cluster1.get_prometheus_config.return_value = {"enabled": True}
        mock_cluster1.get_kubeconfig.return_value = "config1"

        mock_cluster2 = Mock()
        mock_cluster2.get_nodes.return_value = [{"ip": "192.168.1.2", "port": 22}]
        mock_cluster2.get_prometheus_config.return_value = {"enabled": False}
        mock_cluster2.get_kubeconfig.return_value = None

        mock_get_cluster.side_effect = [mock_cluster1, mock_cluster2]
        mock_cert_status.side_effect = [{"days_remaining": 30}, None]

        response = client.get("/api/clusters")

        assert response.status_code == 200
        data = response.json()

        assert "clusters" in data
        clusters = data["clusters"]
        assert len(clusters) == 2

        # Check first cluster
        cluster1 = clusters[0]
        assert cluster1["name"] == "cluster1"
        assert cluster1["kubeconfig"] is True
        assert cluster1["cert_expiry_days"] == 30

        # Check second cluster
        cluster2 = clusters[1]
        assert cluster2["name"] == "cluster2"
        assert cluster2["kubeconfig"] is False
        assert cluster2["cert_expiry_days"] is None

    @patch("api.clusters.list_clusters")
    def test_clusters_endpoint_error(self, mock_list_clusters, client):
        """Test clusters endpoint error handling"""
        mock_list_clusters.side_effect = Exception("Database error")

        response = client.get("/api/clusters")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]

    @patch("api.clusters.get_cluster")
    def test_create_cluster_endpoint(self, mock_get_cluster, client):
        """Test cluster creation endpoint"""
        mock_cluster = Mock()
        mock_cluster.update_node = Mock()
        mock_cluster.update_prometheus = Mock()
        mock_cluster.update_kubeconfig = Mock()
        mock_get_cluster.return_value = mock_cluster

        cluster_data = {
            "name": "new-cluster",
            "nodes": [{"ip": "192.168.1.100", "port": 22, "name": "node1"}],
            "prometheus_config": {"enabled": True, "url": "http://prometheus:9090"},
            "kubeconfig": "base64-encoded-config",
        }

        response = client.post("/api/clusters", json=cluster_data)

        assert response.status_code == 200
        data = response.json()
        assert "Cluster new-cluster created successfully" in data["message"]

        # Verify cluster methods were called
        mock_cluster.update_node.assert_called_once()
        mock_cluster.update_prometheus.assert_called_once_with({"enabled": True, "url": "http://prometheus:9090"})
        mock_cluster.update_kubeconfig.assert_called_once_with("base64-encoded-config")

    @patch("api.clusters.get_cluster")
    def test_create_cluster_endpoint_error(self, mock_get_cluster, client):
        """Test cluster creation endpoint error handling"""
        mock_get_cluster.side_effect = Exception("Storage error")

        cluster_data = {"name": "test-cluster", "nodes": []}

        response = client.post("/api/clusters", json=cluster_data)

        assert response.status_code == 500
        data = response.json()
        assert "Storage error" in data["detail"]

    @patch("api.clusters.delete_cluster")
    def test_delete_cluster_endpoint(self, mock_delete_cluster, client):
        """Test cluster deletion endpoint"""
        response = client.delete("/api/clusters/test-cluster")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Cluster test-cluster deleted"

        mock_delete_cluster.assert_called_once_with("test-cluster")

    @patch("api.clusters.get_cluster")
    def test_get_cluster_details_endpoint(self, mock_get_cluster, client):
        """Test cluster details endpoint"""
        mock_cluster = Mock()
        mock_cluster.get_nodes.return_value = [{"ip": "192.168.1.1", "port": 22}]
        mock_cluster.get_prometheus_config.return_value = {"enabled": True}
        mock_cluster.get_kubeconfig.return_value = "config-data"
        mock_get_cluster.return_value = mock_cluster

        response = client.get("/api/clusters/test-cluster")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "test-cluster"
        assert data["nodes"] == [{"ip": "192.168.1.1", "port": 22}]
        assert data["prometheus_config"] == {"enabled": True}
        assert data["kubeconfig"] == "config-data"

    @patch("api.clusters.get_cluster")
    def test_get_cluster_details_not_found(self, mock_get_cluster, client):
        """Test cluster details endpoint for non-existent cluster"""
        mock_get_cluster.return_value = None

        response = client.get("/api/clusters/non-existent")

        assert response.status_code == 404
        data = response.json()
        assert "Cluster not found" in data["detail"]

    @patch("api.clusters.get_cluster")
    @patch("api.clusters.K8sClient")
    def test_get_cluster_nodes_endpoint(self, mock_k8s_client_class, mock_get_cluster, client):
        """Test cluster nodes endpoint"""
        mock_cluster = Mock()
        mock_cluster.get_kubeconfig.return_value = "kubeconfig-data"
        mock_get_cluster.return_value = mock_cluster

        mock_k8s_client = Mock()
        mock_k8s_client.get_nodes.return_value = {"status": "success", "nodes": [{"name": "node1", "status": "Ready"}]}
        mock_k8s_client_class.return_value = mock_k8s_client

        response = client.get("/api/clusters/test-cluster/nodes")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "node1"

    @patch("api.clusters.get_cluster")
    def test_get_cluster_nodes_no_kubeconfig(self, mock_get_cluster, client):
        """Test cluster nodes endpoint without kubeconfig"""
        mock_cluster = Mock()
        mock_cluster.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster

        response = client.get("/api/clusters/test-cluster/nodes")

        assert response.status_code == 400
        data = response.json()
        assert "Kubeconfig not configured" in data["detail"]

    @patch("api.clusters.get_cluster")
    @patch("api.clusters.K8sClient")
    def test_test_cluster_kubeconfig_endpoint(self, mock_k8s_client_class, mock_get_cluster, client):
        """Test cluster kubeconfig testing endpoint"""
        mock_cluster = Mock()
        mock_cluster.get_kubeconfig.return_value = "kubeconfig-data"
        mock_get_cluster.return_value = mock_cluster

        mock_k8s_client = Mock()
        mock_k8s_client.test_connection.return_value = (True, "Connection successful")
        mock_k8s_client_class.return_value = mock_k8s_client

        response = client.post("/api/clusters/test-cluster/test-kubeconfig")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Connection successful"

    @patch("api.clusters.get_cluster")
    def test_test_cluster_kubeconfig_no_config(self, mock_get_cluster, client):
        """Test cluster kubeconfig testing without configuration"""
        mock_cluster = Mock()
        mock_cluster.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster

        response = client.post("/api/clusters/test-cluster/test-kubeconfig")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not configured" in data["message"]

    def test_invalid_endpoint(self, client):
        """Test invalid endpoint returns 404"""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405"""
        response = client.post("/api/health")

        assert response.status_code == 405

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-credentials" in response.headers
