#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for cluster controller
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException

from services.cluster_service import ClusterService
from core.logging import get_logger

logger = get_logger(__name__)


@pytest.fixture
def cluster_name():
    return "test-cluster"


class TestClustersController:
    """Test cases for cluster management controller"""

    @pytest.mark.asyncio
    @patch("services.cluster_service.K8sClient")
    @patch("services.cluster_service.get_cluster_cert_status")
    @patch("services.cluster_service.get_cluster")
    @patch("services.cluster_service.list_clusters")
    async def test_get_clusters_success(
        self, mock_list_clusters, mock_get_cluster, mock_cert_status, mock_k8s_client_class
    ):
        """Test successful cluster listing"""
        logger.info("Starting test_get_clusters_success")
        # Mock cluster list
        mock_list_clusters.return_value = ["cluster1", "cluster2"]
        logger.info("Mock list_clusters set")

        # Mock cluster configs
        mock_cluster1 = Mock()
        mock_cluster1.get_nodes = AsyncMock(return_value=[{"ip": "192.168.1.1", "port": 22}])
        mock_cluster1.get_prometheus_config = AsyncMock(return_value={"enabled": True})
        mock_cluster1.get_kubeconfig = AsyncMock(return_value="kubeconfig_content")

        mock_cluster2 = Mock()
        mock_cluster2.get_nodes = AsyncMock(return_value=[{"ip": "192.168.1.2", "port": 22}])
        mock_cluster2.get_prometheus_config = AsyncMock(return_value={"enabled": False})
        mock_cluster2.get_kubeconfig = AsyncMock(return_value=None)

        mock_get_cluster.side_effect = [mock_cluster1, mock_cluster2]
        logger.info("Mock get_cluster set")

        # Mock cert status
        mock_cert_status.side_effect = [{"days_remaining": 30}, None]
        logger.info("Mock cert_status set")

        # Mock K8sClient for version
        mock_k8s_client = Mock()
        mock_k8s_client.get_cluster_info = AsyncMock(return_value={"version": "v1.28.0"})
        mock_k8s_client_class.return_value = mock_k8s_client
        logger.info("Mock K8sClient set")

        logger.info("Calling get_clusters_list()")
        service = ClusterService()
        result = await service.get_clusters_list()
        logger.info(f"get_clusters_list() returned: {result}")

        assert "clusters" in result
        assert len(result["clusters"]) == 2

        cluster1 = result["clusters"][0]
        assert cluster1["name"] == "cluster1"
        assert cluster1["k8s_version"] == "v1.28.0"
        assert cluster1["cert_expiry_days"] == 30

        cluster2 = result["clusters"][1]
        assert cluster2["name"] == "cluster2"
        assert cluster2["k8s_version"] is None
        assert cluster2["cert_expiry_days"] is None
        logger.info("test_get_clusters_success completed successfully")

    @pytest.mark.asyncio
    @patch("services.cluster_service.list_clusters")
    @patch("services.cluster_service.get_cluster")
    async def test_get_clusters_error(self, mock_get_cluster, mock_list_clusters):
        """Test cluster listing error handling"""
        # Mock to return empty list
        mock_list_clusters.return_value = []
        mock_get_cluster.return_value = None

        service = ClusterService()
        result = await service.get_clusters_list()

        # Should return empty clusters list
        assert "clusters" in result
        assert len(result["clusters"]) == 0

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    @patch("services.cluster_service.SecretVariableParser")
    async def test_create_cluster_success(self, mock_parser_class, mock_get_cluster):
        """Test successful cluster creation"""
        # Mock SecretVariableParser
        mock_parser = Mock()
        mock_parser.validate_variables = AsyncMock(return_value=(True, []))
        mock_parser_class.return_value = mock_parser

        mock_cluster_config = Mock()
        mock_cluster_config.update_node = AsyncMock()
        mock_cluster_config.update_prometheus = AsyncMock()
        mock_cluster_config.update_kubeconfig = AsyncMock()
        mock_get_cluster.return_value = mock_cluster_config

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(
            name="test-cluster",
            nodes=[
                {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "name": "node1",
                    "username": "testuser",
                    "auth_type": "password",
                    "password": "${secret:test-password-secret}",
                }
            ],
            prometheus_config={"enabled": True, "url": "http://prometheus:9090"},
            kubeconfig="${secret:test-kubeconfig-secret}",
        )

        service = ClusterService()
        result = await service.create_cluster(cluster_data.model_dump())

        assert result == {"message": "Cluster test-cluster created successfully"}
        mock_cluster_config.update_node.assert_called_once_with(cluster_data.nodes[0])
        mock_cluster_config.update_kubeconfig.assert_called_once_with(cluster_data.kubeconfig)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_create_cluster_error(self, mock_get_cluster):
        """Test cluster creation error handling"""
        mock_get_cluster.side_effect = Exception("Create error")

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(name="test-cluster", nodes=[])

        service = ClusterService()
        with pytest.raises(HTTPException) as exc_info:
            await service.create_cluster(cluster_data.model_dump())

        assert exc_info.value.status_code == 500
        assert "Create error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    @patch("services.cluster_service.SecretVariableParser")
    async def test_update_cluster_success(self, mock_parser_class, mock_get_cluster):
        """Test successful cluster update"""
        # Mock SecretVariableParser
        mock_parser = Mock()
        mock_parser.validate_variables = AsyncMock(return_value=(True, []))
        mock_parser_class.return_value = mock_parser

        mock_cluster_config = Mock()
        mock_cluster_config.config = {"nodes": []}
        mock_cluster_config.update_node = AsyncMock()
        mock_cluster_config.update_prometheus = AsyncMock()
        mock_cluster_config.update_kubeconfig = AsyncMock()
        mock_get_cluster.return_value = mock_cluster_config

        from api.models import ClusterCreate

        cluster_data = ClusterCreate(
            name="test-cluster",
            nodes=[
                {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "name": "node1",
                    "username": "testuser",
                    "auth_type": "password",
                    "password": "${secret:test-password-secret}",
                }
            ],
            prometheus_config={"enabled": True, "url": "http://prometheus:9090"},
            kubeconfig="${secret:test-kubeconfig-secret}",
        )

        service = ClusterService()
        result = await service.update_cluster("test-cluster", cluster_data.model_dump())

        assert result == {"message": "Cluster test-cluster updated successfully"}
        assert mock_cluster_config.update_node.call_count == 1
        mock_cluster_config.update_kubeconfig.assert_called_once_with("${secret:test-kubeconfig-secret}")

    @pytest.mark.asyncio
    @patch("services.cluster_service.delete_cluster")
    async def test_remove_cluster_success(self, mock_delete_cluster):
        """Test successful cluster deletion"""
        service = ClusterService()
        result = await service.delete_cluster("test-cluster")

        assert result == {"message": "Cluster test-cluster deleted"}
        mock_delete_cluster.assert_called_once_with("test-cluster")

    @pytest.mark.asyncio
    @patch("services.cluster_service.delete_cluster")
    async def test_remove_cluster_error(self, mock_delete_cluster):
        """Test cluster deletion error handling"""
        mock_delete_cluster.side_effect = Exception("Delete error")

        service = ClusterService()
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_cluster("test-cluster")

        assert exc_info.value.status_code == 500
        assert "Delete error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_get_cluster_details_success(self, mock_get_cluster):
        """Test successful cluster details retrieval"""
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_nodes = AsyncMock(return_value=[{"ip": "192.168.1.1", "port": 22}])
        mock_cluster_config.get_prometheus_config = AsyncMock(return_value={"enabled": True})
        mock_cluster_config.get_kubeconfig = AsyncMock(return_value="kubeconfig_content")
        mock_get_cluster.return_value = mock_cluster_config

        service = ClusterService()
        result = await service.get_cluster_details("test-cluster")

        expected = {
            "name": "test-cluster",
            "nodes": [{"ip": "192.168.1.1", "port": 22}],
            "kubeconfig": "kubeconfig_content",
        }
        assert result == expected

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_get_cluster_details_not_found(self, mock_get_cluster):
        """Test cluster details for non-existent cluster"""
        mock_get_cluster.return_value = None

        service = ClusterService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_cluster_details("non-existent")

        assert exc_info.value.status_code == 404
        assert "Cluster not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    @patch("services.cluster_service.K8sClient")
    async def test_get_cluster_nodes_success(self, mock_k8s_client_class, mock_get_cluster):
        """Test successful cluster nodes retrieval"""
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_kubeconfig = AsyncMock(return_value="kubeconfig_content")
        mock_get_cluster.return_value = mock_cluster_config

        mock_k8s_client = Mock()
        mock_k8s_client.get_nodes = Mock(return_value={"status": "success", "nodes": ["node1", "node2"]})
        mock_k8s_client_class.return_value = mock_k8s_client

        service = ClusterService()
        result = await service.get_cluster_nodes("test-cluster")

        assert result == {"status": "success", "nodes": ["node1", "node2"]}
        mock_k8s_client_class.assert_called_once_with("kubeconfig_content")
        mock_k8s_client.get_nodes.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_get_cluster_nodes_no_kubeconfig(self, mock_get_cluster):
        """Test cluster nodes retrieval without kubeconfig"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_kubeconfig = AsyncMock(return_value=None)
        mock_get_cluster.return_value = mock_cluster_config

        service = ClusterService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_cluster_nodes("test-cluster")

        assert exc_info.value.status_code == 400
        assert "Kubeconfig not configured" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    @patch("services.cluster_service.K8sClient")
    async def test_get_cluster_nodes_k8s_error(self, mock_k8s_client_class, mock_get_cluster):
        """Test cluster nodes retrieval with K8s error"""
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_kubeconfig = AsyncMock(return_value="kubeconfig_content")
        mock_get_cluster.return_value = mock_cluster_config

        mock_k8s_client = Mock()
        mock_k8s_client.get_nodes = Mock(return_value={"status": "error", "error": "K8s connection failed"})
        mock_k8s_client_class.return_value = mock_k8s_client

        service = ClusterService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_cluster_nodes("test-cluster")

        assert exc_info.value.status_code == 500
        assert "K8s connection failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_get_nodes_for_testing_with_request(self, mock_get_cluster):
        """Test _get_nodes_for_testing with explicit nodes in request"""
        request_nodes = [{"ip": "192.168.1.1", "port": 22}]

        service = ClusterService()
        result = await service._get_nodes_for_testing("test-cluster", request_nodes)

        assert result == [{"ip": "192.168.1.1", "port": 22}]
        mock_get_cluster.assert_not_called()

    @pytest.mark.asyncio
    @patch("services.cluster_service.get_cluster")
    async def test_get_nodes_for_testing_from_cluster(self, mock_get_cluster):
        """Test _get_nodes_for_testing getting nodes from cluster config"""
        mock_cluster_config = Mock()
        mock_cluster_config.get_nodes = AsyncMock(return_value=[{"ip": "192.168.1.1", "port": 22}])
        mock_get_cluster.return_value = mock_cluster_config

        service = ClusterService()
        result = await service._get_nodes_for_testing("test-cluster", None)

        assert result == [{"ip": "192.168.1.1", "port": 22}]
        mock_get_cluster.assert_called_once_with("test-cluster")

    @patch("services.cluster_service.test_node_connection")
    def test_test_single_node_success(self, mock_test_connection):
        """Test successful single node testing"""
        mock_test_connection.return_value = (True, "Connection successful")

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        service = ClusterService()
        result = service._create_node_test_result(node, True, "Connection successful")

        expected = {"node": "192.168.1.1:22", "node_name": "node1", "success": True, "message": "Connection successful"}
        assert result == expected

    @patch("services.cluster_service.test_node_connection")
    def test_test_single_node_failure(self, mock_test_connection):
        """Test failed single node testing"""
        mock_test_connection.side_effect = Exception("Connection failed")

        node = {"ip": "192.168.1.1", "port": 22}
        service = ClusterService()
        result = service._create_node_test_result(node, False, "", "Connection failed")

        assert result["node"] == "192.168.1.1:22"
        assert result["success"] is False
        assert "Connection failed" in result["message"]
