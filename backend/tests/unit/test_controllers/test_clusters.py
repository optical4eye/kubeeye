#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for cluster controller
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from api.clusters import (
    get_clusters,
    create_cluster,
    update_cluster,
    remove_cluster,
    get_cluster_details,
    get_cluster_nodes,
    _get_nodes_for_testing,
    _test_single_node,
)


@pytest.fixture
def cluster_name():
    return "test-cluster"


class TestClustersController:
    """Test cases for cluster management controller"""

    @pytest.mark.asyncio
    @patch("infrastructure.common.dashboard.get_dashboard_data_api")
    async def test_get_dashboard_success(self, mock_get_dashboard):
        """Test successful dashboard data retrieval"""
        mock_get_dashboard.return_value = {"data": "test"}

        from api.clusters import get_dashboard

        result = await get_dashboard()

        assert result == {"data": "test"}
        mock_get_dashboard.assert_called_once()

    @pytest.mark.asyncio
    @patch("infrastructure.common.dashboard.get_dashboard_data_api")
    async def test_get_dashboard_error(self, mock_get_dashboard):
        """Test dashboard error handling"""
        mock_get_dashboard.side_effect = Exception("Dashboard error")

        from api.clusters import get_dashboard

        with pytest.raises(HTTPException) as exc_info:
            await get_dashboard()

        assert exc_info.value.status_code == 500
        assert "Dashboard error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.list_clusters")
    @patch("api.clusters.get_cluster")
    @patch("api.clusters.get_cluster_cert_status")
    async def test_get_clusters_success(self, mock_cert_status, mock_get_cluster, mock_list_clusters):
        """Test successful cluster listing"""
        # Mock cluster list
        mock_list_clusters.return_value = ["cluster1", "cluster2"]

        # Mock cluster configs
        mock_cluster1 = Mock()
        mock_cluster1.get_nodes.return_value = [{"ip": "192.168.1.1", "port": 22}]
        mock_cluster1.get_prometheus_config.return_value = {"enabled": True}
        mock_cluster1.get_kubeconfig.return_value = "kubeconfig_content"

        mock_cluster2 = Mock()
        mock_cluster2.get_nodes.return_value = [{"ip": "192.168.1.2", "port": 22}]
        mock_cluster2.get_prometheus_config.return_value = {"enabled": False}
        mock_cluster2.get_kubeconfig.return_value = None

        mock_get_cluster.side_effect = [mock_cluster1, mock_cluster2]

        # Mock cert status
        mock_cert_status.side_effect = [{"days_remaining": 30}, None]

        result = await get_clusters()

        assert "clusters" in result
        assert len(result["clusters"]) == 2

        cluster1 = result["clusters"][0]
        assert cluster1["name"] == "cluster1"
        assert cluster1["kubeconfig"] is True
        assert cluster1["cert_expiry_days"] == 30

        cluster2 = result["clusters"][1]
        assert cluster2["name"] == "cluster2"
        assert cluster2["kubeconfig"] is False
        assert cluster2["cert_expiry_days"] is None

    @pytest.mark.asyncio
    @patch("api.clusters.list_clusters")
    async def test_get_clusters_error(self, mock_list_clusters):
        """Test cluster listing error handling"""
        mock_list_clusters.side_effect = Exception("List error")

        with pytest.raises(HTTPException) as exc_info:
            await get_clusters()

        assert exc_info.value.status_code == 500
        assert "List error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_create_cluster_success(self, mock_get_cluster):
        """Test successful cluster creation"""
        mock_cluster_config = Mock()
        mock_get_cluster.return_value = mock_cluster_config

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(
            name="test-cluster",
            nodes=[{"ip": "192.168.1.1", "port": 22, "name": "node1"}],
            prometheus_config={"enabled": True, "url": "http://prometheus:9090"},
            kubeconfig="test-kubeconfig",
        )

        result = await create_cluster(cluster_data)

        assert result == {"message": "Cluster test-cluster created successfully"}
        mock_cluster_config.update_node.assert_called_once_with(cluster_data.nodes[0])
        mock_cluster_config.update_prometheus.assert_called_once_with(cluster_data.prometheus_config)
        mock_cluster_config.update_kubeconfig.assert_called_once_with(cluster_data.kubeconfig)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_create_cluster_error(self, mock_get_cluster):
        """Test cluster creation error handling"""
        mock_get_cluster.side_effect = Exception("Create error")

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(name="test-cluster", nodes=[])

        from api.clusters import create_cluster

        with pytest.raises(HTTPException) as exc_info:
            await create_cluster(cluster_data)

        assert exc_info.value.status_code == 500
        assert "Create error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_update_cluster_success(self, mock_get_cluster):
        """Test successful cluster update"""
        mock_cluster_config = Mock()
        mock_cluster_config.config = {"nodes": []}
        mock_get_cluster.return_value = mock_cluster_config

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(
            name="test-cluster",
            nodes=[{"ip": "192.168.1.1", "port": 22, "name": "node1"}],
            prometheus_config={"enabled": True, "url": "http://prometheus:9090"},
            kubeconfig="updated-kubeconfig",
        )

        from api.clusters import update_cluster

        result = await update_cluster("test-cluster", cluster_data)

        assert result == {"message": "Cluster test-cluster updated successfully"}
        assert mock_cluster_config.update_node.call_count == 1
        mock_cluster_config.update_prometheus.assert_called_once_with(
            {"enabled": True, "url": "http://prometheus:9090"}
        )
        mock_cluster_config.update_kubeconfig.assert_called_once_with("updated-kubeconfig")

    @pytest.mark.asyncio
    @patch("api.clusters.delete_cluster")
    async def test_remove_cluster_success(self, mock_delete_cluster):
        """Test successful cluster deletion"""
        result = await remove_cluster("test-cluster")

        assert result == {"message": "Cluster test-cluster deleted"}
        mock_delete_cluster.assert_called_once_with("test-cluster")

    @pytest.mark.asyncio
    @patch("api.clusters.delete_cluster")
    async def test_remove_cluster_error(self, mock_delete_cluster):
        """Test cluster deletion error handling"""
        mock_delete_cluster.side_effect = Exception("Delete error")

        with pytest.raises(HTTPException) as exc_info:
            await remove_cluster("test-cluster")

        assert exc_info.value.status_code == 500
        assert "Delete error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_get_cluster_details_success(self, mock_get_cluster):
        """Test successful cluster details retrieval"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes.return_value = [{"ip": "192.168.1.1", "port": 22}]
        mock_cluster_config.get_prometheus_config.return_value = {"enabled": True}
        mock_cluster_config.get_kubeconfig.return_value = "kubeconfig_content"
        mock_get_cluster.return_value = mock_cluster_config

        result = await get_cluster_details("test-cluster")

        expected = {
            "name": "test-cluster",
            "nodes": [{"ip": "192.168.1.1", "port": 22}],
            "prometheus_config": {"enabled": True},
            "kubeconfig": "kubeconfig_content",
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_get_cluster_details_not_found(self, mock_get_cluster):
        """Test cluster details for non-existent cluster"""
        mock_get_cluster.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_cluster_details("non-existent")

        assert exc_info.value.status_code == 404
        assert "Cluster not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    @patch("api.clusters.K8sClient")
    async def test_get_cluster_nodes_success(self, mock_k8s_client_class, mock_get_cluster):
        """Test successful cluster nodes retrieval"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_kubeconfig.return_value = "kubeconfig_content"
        mock_get_cluster.return_value = mock_cluster_config

        mock_k8s_client = Mock()
        mock_k8s_client.get_nodes.return_value = {"status": "success", "nodes": ["node1", "node2"]}
        mock_k8s_client_class.return_value = mock_k8s_client

        result = await get_cluster_nodes("test-cluster")

        assert result == {"status": "success", "nodes": ["node1", "node2"]}
        mock_k8s_client_class.assert_called_once_with("kubeconfig_content")
        mock_k8s_client.get_nodes.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_get_cluster_nodes_no_kubeconfig(self, mock_get_cluster):
        """Test cluster nodes retrieval without kubeconfig"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster_config

        with pytest.raises(HTTPException) as exc_info:
            await get_cluster_nodes("test-cluster")

        assert exc_info.value.status_code == 400
        assert "Kubeconfig not configured" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    @patch("api.clusters.K8sClient")
    async def test_get_cluster_nodes_k8s_error(self, mock_k8s_client_class, mock_get_cluster):
        """Test cluster nodes retrieval with K8s error"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_kubeconfig.return_value = "kubeconfig_content"
        mock_get_cluster.return_value = mock_cluster_config

        mock_k8s_client = Mock()
        mock_k8s_client.get_nodes.return_value = {"status": "error", "error": "K8s connection failed"}
        mock_k8s_client_class.return_value = mock_k8s_client

        with pytest.raises(HTTPException) as exc_info:
            await get_cluster_nodes("test-cluster")

        assert exc_info.value.status_code == 500
        assert "K8s connection failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_get_nodes_for_testing_with_request(self, mock_get_cluster):
        """Test _get_nodes_for_testing with explicit nodes in request"""
        request = Mock()
        request.nodes = [{"ip": "192.168.1.1", "port": 22}]

        result = await _get_nodes_for_testing("test-cluster", request)

        assert result == [{"ip": "192.168.1.1", "port": 22}]
        mock_get_cluster.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.clusters.get_cluster")
    async def test_get_nodes_for_testing_from_cluster(self, mock_get_cluster):
        """Test _get_nodes_for_testing getting nodes from cluster config"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes.return_value = [{"ip": "192.168.1.1", "port": 22}]
        mock_get_cluster.return_value = mock_cluster_config

        result = await _get_nodes_for_testing("test-cluster", None)

        assert result == [{"ip": "192.168.1.1", "port": 22}]
        mock_get_cluster.assert_called_once_with("test-cluster")

    @patch("api.clusters.test_node_connection")
    def test_test_single_node_success(self, mock_test_connection):
        """Test successful single node testing"""
        mock_test_connection.return_value = (True, "Connection successful")

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        result = _test_single_node(node)

        expected = {"node": "192.168.1.1:22", "success": True, "message": "Connection successful"}
        assert result == expected

    @patch("api.clusters.test_node_connection")
    def test_test_single_node_failure(self, mock_test_connection):
        """Test failed single node testing"""
        mock_test_connection.side_effect = Exception("Connection failed")

        node = {"ip": "192.168.1.1", "port": 22}
        result = _test_single_node(node)

        assert result["node"] == "192.168.1.1:22"
        assert result["success"] is False
        assert "Connection failed" in result["message"]
