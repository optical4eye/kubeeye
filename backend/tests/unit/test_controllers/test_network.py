#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for network API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from fastapi import HTTPException
from pathlib import Path

from api.network import (
    check_network_connectivity,
    get_clusters_for_network_check,
    get_network_check_results,
    get_network_check_result,
    delete_network_check_result,
    export_network_check_result,
    NetworkCheckRequest,
    NetworkCheckResult,
    NetworkCheckResponse,
    NetworkConnectivityResult,
)
import api.network


class TestNetworkAPI:
    """Test cases for network API endpoints"""

    @patch("api.network.check_connectivity_from_nodes")
    @patch("api.network.NetworkConnectivityResult")
    @patch("api.network.get_cluster")
    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(
        self, mock_get_cluster, mock_network_result_class, mock_check_connectivity
    ):
        """Test successful network connectivity check"""
        # Mock cluster configuration
        mock_cluster = Mock()
        mock_cluster.get_nodes.return_value = [
            {"ip": "192.168.1.10", "name": "node1"},
            {"ip": "192.168.1.11", "name": "node2"},
        ]
        mock_get_cluster.return_value = mock_cluster

        # Mock connectivity check results
        mock_check_connectivity.return_value = [
            {"status": "success", "response_time": 0.05, "node_ip": "192.168.1.10"},
            {"status": "success", "response_time": 0.03, "node_ip": "192.168.1.11"},
        ]

        # Mock network result object
        mock_result_obj = Mock()
        mock_result_obj.result_id = "result-123"
        mock_result_obj.save.return_value = "/path/to/result.json"
        mock_network_result_class.return_value = mock_result_obj

        # Create request
        request = NetworkCheckRequest(
            cluster_name="test-cluster",
            selected_nodes=["192.168.1.10", "192.168.1.11"],
            target_ip="192.168.1.100",
            target_port=80,
            timeout=5,
        )

        result = await check_network_connectivity(request)

        assert result["result_id"] == "result-123"
        assert len(result["results"]) == 2
        assert result["results"][0]["status"] == "success"
        assert result["results"][1]["status"] == "success"
        mock_get_cluster.assert_called_once_with("test-cluster")
        mock_check_connectivity.assert_called_once()

    @patch("api.network.get_cluster")
    @pytest.mark.asyncio
    async def test_check_network_connectivity_cluster_not_found(self, mock_get_cluster):
        """Test network connectivity check with non-existent cluster"""
        mock_get_cluster.return_value = None

        # Create request
        request = NetworkCheckRequest(
            cluster_name="non-existent-cluster",
            selected_nodes=["192.168.1.10"],
            target_ip="192.168.1.100",
            target_port=80,
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_network_connectivity(request)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @patch("api.network.get_cluster")
    @pytest.mark.asyncio
    async def test_check_network_connectivity_no_nodes(self, mock_get_cluster):
        """Test network connectivity check with cluster having no nodes"""
        mock_cluster = Mock()
        mock_cluster.get_nodes.return_value = []
        mock_get_cluster.return_value = mock_cluster

        # Create request
        request = NetworkCheckRequest(
            cluster_name="empty-cluster", selected_nodes=["192.168.1.10"], target_ip="192.168.1.100", target_port=80
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_network_connectivity(request)

        assert exc_info.value.status_code == 400
        assert "No nodes configured" in str(exc_info.value.detail)

    @patch("infrastructure.cluster.cluster_config.list_clusters")
    @patch("api.network.get_cluster")
    @pytest.mark.asyncio
    async def test_get_clusters_for_network_check_success(self, mock_get_cluster, mock_list_clusters):
        """Test successful retrieval of clusters for network check"""
        # Mock list_clusters
        mock_list_clusters.return_value = ["cluster1", "cluster2"]

        # Mock get_cluster
        mock_cluster = Mock()
        mock_cluster.get_nodes.return_value = [
            {"ip": "192.168.1.10", "name": "node1"},
            {"ip": "192.168.1.11", "name": "node2"},
        ]
        mock_get_cluster.return_value = mock_cluster

        result = await get_clusters_for_network_check()

        assert "clusters" in result
        assert len(result["clusters"]) == 2
        assert result["clusters"][0]["name"] == "cluster1"
        assert len(result["clusters"][0]["nodes"]) == 2
        mock_list_clusters.assert_called_once()
        assert mock_get_cluster.call_count == 2

    @patch("infrastructure.cluster.cluster_config.list_clusters")
    @pytest.mark.asyncio
    async def test_get_clusters_for_network_check_exception(self, mock_list_clusters):
        """Test retrieval of clusters with exception"""
        mock_list_clusters.side_effect = Exception("Cluster list error")

        with pytest.raises(HTTPException) as exc_info:
            await get_clusters_for_network_check()

        assert exc_info.value.status_code == 500
        assert "Failed to get clusters" in str(exc_info.value.detail)

    @patch("api.network.list_network_check_results")
    @patch("api.validation_middleware.validate_limit_param")
    @patch("api.validation_middleware.validate_cluster_name")
    @pytest.mark.asyncio
    async def test_get_network_check_results_success(
        self, mock_validate_cluster, mock_validate_limit, mock_list_results
    ):
        """Test successful retrieval of network check results"""
        # Mock validation
        mock_validate_limit.return_value = 50
        mock_validate_cluster.return_value = "test-cluster"

        # Mock results
        mock_list_results.return_value = [
            {"result_id": "result1", "cluster_name": "test-cluster"},
            {"result_id": "result2", "cluster_name": "test-cluster"},
        ]

        result = await get_network_check_results(cluster_name="test-cluster", limit=50)

        assert "results" in result
        assert len(result["results"]) == 2
        mock_validate_limit.assert_called_once_with(50)
        mock_validate_cluster.assert_called_once_with("test-cluster")
        mock_list_results.assert_called_once_with(cluster_name="test-cluster", limit=50)

    @patch("api.network.list_network_check_results")
    @patch("api.validation_middleware.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_network_check_results_no_cluster_filter(self, mock_validate_limit, mock_list_results):
        """Test retrieval of network check results without cluster filter"""
        # Mock validation
        mock_validate_limit.return_value = 50

        # Mock results
        mock_list_results.return_value = [
            {"result_id": "result1", "cluster_name": "cluster1"},
            {"result_id": "result2", "cluster_name": "cluster2"},
        ]

        result = await get_network_check_results(cluster_name=None, limit=50)

        assert "results" in result
        assert len(result["results"]) == 2
        mock_validate_limit.assert_called_once_with(50)
        mock_list_results.assert_called_once_with(cluster_name=None, limit=50)

    @patch("api.network.load_network_check_result")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_network_check_result_success(self, mock_validate_id, mock_load_result):
        """Test successful retrieval of specific network check result"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock result
        mock_load_result.return_value = {
            "result_id": "validated-result-123",
            "cluster_name": "test-cluster",
            "target_ip": "192.168.1.100",
            "target_port": 80,
            "checks": [
                {"node_ip": "192.168.1.10", "status": "success"},
                {"node_ip": "192.168.1.11", "status": "failed"},
            ],
        }

        result = await get_network_check_result("result-123")

        assert result["result_id"] == "validated-result-123"
        assert result["cluster_name"] == "test-cluster"
        assert len(result["checks"]) == 2
        mock_validate_id.assert_called_once_with("result-123")
        mock_load_result.assert_called_once_with("validated-result-123")

    @patch("api.network.load_network_check_result")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_network_check_result_not_found(self, mock_validate_id, mock_load_result):
        """Test retrieval of non-existent network check result"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock result not found
        mock_load_result.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_network_check_result("result-123")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @patch("os.remove")
    @patch("pathlib.Path.rglob")
    @patch("os.environ.get")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_network_check_result_success(self, mock_validate_id, mock_env_get, mock_rglob, mock_remove):
        """Test successful deletion of network check result"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock environment
        mock_env_get.return_value = "/app/data"

        # Mock file finding
        mock_file_path = Mock()
        mock_file_path.__str__ = Mock(return_value="/app/data/exports/2023-01-01/network_reports/result-123.json")
        mock_rglob.return_value = [mock_file_path]

        # Mock file reading and validation
        with patch("builtins.open", mock_open(read_data='{"result_id": "validated-result-123"}')):
            with patch(
                "api.network.load_network_check_result",
                return_value={"result_id": "validated-result-123"},
            ):
                result = await delete_network_check_result("result-123")

        assert result["message"] == "Network check result validated-result-123 deleted"
        mock_validate_id.assert_called_once_with("result-123")
        mock_remove.assert_called_once()

    @patch("os.environ.get")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_network_check_result_not_found(self, mock_validate_id, mock_env_get):
        """Test deletion of non-existent network check result"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock environment
        mock_env_get.return_value = "/app/data"

        # Mock no files found
        with patch("pathlib.Path.rglob", return_value=[]):
            with pytest.raises(HTTPException) as exc_info:
                await delete_network_check_result("result-123")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @patch("api.network.FileResponse")
    @patch("api.network.export_network_report")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_network_check_result_success(self, mock_validate_id, mock_export, mock_file_response):
        """Test successful export of network check result"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock export
        mock_export.return_value = (True, "/path/to/exported_file.csv")

        # Mock FileResponse
        mock_file_response_instance = Mock()
        mock_file_response.return_value = mock_file_response_instance

        result = await export_network_check_result("result-123", "csv")

        mock_validate_id.assert_called_once_with("result-123")
        mock_export.assert_called_once_with("validated-result-123", "csv")
        assert result == mock_file_response_instance

    @patch("api.network.export_network_report")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_network_check_result_invalid_format(self, mock_validate_id, mock_export):
        """Test export with invalid format"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        with pytest.raises(HTTPException) as exc_info:
            await export_network_check_result("result-123", "invalid")

        assert exc_info.value.status_code == 400
        assert "Format must be one of" in str(exc_info.value.detail)

    @patch("api.network.load_network_check_result")
    @patch("api.network.export_network_report")
    @patch("api.validation_middleware.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_network_check_result_export_failure(self, mock_validate_id, mock_export, mock_load):
        """Test export with failure"""
        # Mock validation
        mock_validate_id.return_value = "validated-result-123"

        # Mock load result
        mock_load.return_value = {"result_id": "validated-result-123"}

        # Mock export failure
        mock_export.return_value = (False, "Export failed")

        with pytest.raises(HTTPException) as exc_info:
            await export_network_check_result("result-123", "json")

        assert exc_info.value.status_code == 500
        assert "Export failed" in str(exc_info.value.detail)


# Helper function for mocking file operations
def mock_open(read_data=""):
    """Mock open function for file operations"""
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=read_data)
