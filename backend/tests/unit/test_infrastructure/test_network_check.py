#!/usr/bin/env python3
from core.logging import get_logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for network module
"""

import pytest
import tempfile
import json
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from datetime import datetime

from infra.network.network_check import (
    check_connection,
    check_connectivity_from_nodes,
    NetworkConnectivityResult,
    load_network_check_result,
    list_network_check_results,
)
from core.common.unified_validation import validate_ipv4_address, validate_port

logger = get_logger(__name__)


class TestCheckConnection:
    """Test cases for check_connection function"""

    @pytest.mark.asyncio
    @patch("infra.network.network_check.AsyncNodeConnection")
    async def test_check_connection_success(self, mock_async_node_connection):
        """Test check_connection with successful connection"""
        # Mock node
        node = {"ip": "192.168.1.100", "name": "test-node"}

        # Mock AsyncNodeConnection
        mock_conn = AsyncMock()
        mock_conn.connect.return_value = (True, "")
        mock_conn.close = MagicMock()
        mock_async_node_connection.return_value = mock_conn

        # Mock SSH execution
        with patch("infra.security.ssh_execution_manager.SSHExecutionManager") as mock_ssh_manager:
            mock_ssh_instance = AsyncMock()
            mock_ssh_instance.execute_command_async.return_value = ("SUCCESS", "")
            mock_ssh_manager.return_value = mock_ssh_instance

            result = await check_connection(node, "192.168.1.1", 80, timeout=5)

            assert result["status"] == "success"
            assert result["node_ip"] == "192.168.1.100"
            assert result["target_ip"] == "192.168.1.1"
            assert result["target_port"] == 80
            assert result["response_time"] >= 0
            assert "error" not in result

    @pytest.mark.asyncio
    @patch("infra.network.network_check.AsyncNodeConnection")
    async def test_check_connection_failed(self, mock_async_node_connection):
        """Test check_connection with failed connection"""
        # Mock node
        node = {"ip": "192.168.1.100", "name": "test-node"}

        # Mock AsyncNodeConnection
        mock_conn = AsyncMock()
        mock_conn.connect.return_value = (True, "")
        mock_conn.close = MagicMock()
        mock_async_node_connection.return_value = mock_conn

        # Mock SSH execution
        with patch("infra.security.ssh_execution_manager.SSHExecutionManager") as mock_ssh_manager:
            mock_ssh_instance = AsyncMock()
            mock_ssh_instance.execute_command_async.return_value = ("FAILED", "Connection failed")
            mock_ssh_manager.return_value = mock_ssh_instance

            result = await check_connection(node, "192.168.1.1", 80, timeout=5)

            assert result["status"] == "failed"
            assert result["node_ip"] == "192.168.1.100"
            assert result["target_ip"] == "192.168.1.1"
            assert result["target_port"] == 80
            assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
    @patch("infra.network.network_check.AsyncNodeConnection")
    async def test_check_connection_node_not_connected(self, mock_async_node_connection):
        """Test check_connection when node is not connected"""
        # Mock node
        node = {"ip": "192.168.1.100", "name": "test-node"}

        # Mock AsyncNodeConnection
        mock_conn = AsyncMock()
        mock_conn.connect.return_value = (False, "Cannot connect")
        mock_conn.close = MagicMock()
        mock_async_node_connection.return_value = mock_conn

        result = await check_connection(node, "192.168.1.1", 80, timeout=5)

        assert result["status"] == "failed"
        assert "Cannot connect to node for checking" in result["error"]
        assert result["response_time"] == 0

    @pytest.mark.asyncio
    @patch("infra.network.network_check.AsyncNodeConnection")
    async def test_check_connection_exception(self, mock_async_node_connection):
        """Test check_connection with exception"""
        # Mock node
        node = {"ip": "192.168.1.100", "name": "test-node"}

        # Mock AsyncNodeConnection to raise exception
        mock_async_node_connection.side_effect = Exception("Connection error")

        result = await check_connection(node, "192.168.1.1", 80, timeout=5)

        assert result["status"] == "failed"
        assert "Check execution error" in result["error"]
        assert result["response_time"] == 0

    @pytest.mark.asyncio
    async def test_check_connection_node_without_name(self):
        """Test check_connection with node without name"""
        # Mock node without name
        node = {"ip": "192.168.1.100"}

        with patch("infra.network.network_check.AsyncNodeConnection") as mock_async_node_connection:
            mock_conn = AsyncMock()
            mock_conn.connect.return_value = (False, "Cannot connect")
            mock_conn.close = MagicMock()
            mock_async_node_connection.return_value = mock_conn

            result = await check_connection(node, "192.168.1.1", 80, timeout=5)

            assert result["node_ip"] == "192.168.1.100"


class TestCheckConnectivityFromNodes:
    """Test cases for check_connectivity_from_nodes function"""

    @pytest.mark.asyncio
    @patch("infra.network.network_check.check_connection")
    async def test_check_connectivity_from_nodes_success(self, mock_check_connection):
        """Test check_connectivity_from_nodes with successful connections"""
        # Mock nodes
        nodes = [{"ip": "192.168.1.100", "name": "node1"}, {"ip": "192.168.1.101", "name": "node2"}]

        # Mock check_connection to return success
        mock_check_connection.side_effect = [
            {
                "status": "success",
                "node_ip": "192.168.1.100",
                "target_ip": "192.168.1.1",
                "target_port": 80,
                "response_time": 0.5,
            },
            {
                "status": "success",
                "node_ip": "192.168.1.101",
                "target_ip": "192.168.1.1",
                "target_port": 80,
                "response_time": 0.3,
            },
        ]

        results = await check_connectivity_from_nodes(nodes, "192.168.1.1", 80, timeout=5)

        assert len(results) == 2
        assert all(result["status"] == "success" for result in results)
        # Since asyncio.gather doesn't guarantee order, check node_ips without assuming order
        node_ips = [result["node_ip"] for result in results]
        assert "192.168.1.100" in node_ips
        assert "192.168.1.101" in node_ips

    @pytest.mark.asyncio
    @patch("infra.network.network_check.check_connection")
    async def test_check_connectivity_from_nodes_mixed_results(self, mock_check_connection):
        """Test check_connectivity_from_nodes with mixed results"""
        # Mock nodes
        nodes = [{"ip": "192.168.1.100", "name": "node1"}, {"ip": "192.168.1.101", "name": "node2"}]

        # Mock check_connection to return mixed results
        mock_check_connection.side_effect = [
            {
                "status": "success",
                "node_ip": "192.168.1.100",
                "target_ip": "192.168.1.1",
                "target_port": 80,
                "response_time": 0.5,
            },
            {
                "status": "failed",
                "node_ip": "192.168.1.101",
                "target_ip": "192.168.1.1",
                "target_port": 80,
                "error": "Connection failed",
                "response_time": 1.0,
            },
        ]

        results = await check_connectivity_from_nodes(nodes, "192.168.1.1", 80, timeout=5)

        assert len(results) == 2
        statuses = [r["status"] for r in results]
        assert "success" in statuses
        assert "failed" in statuses

    @pytest.mark.asyncio
    @patch("infra.network.network_check.check_connection")
    async def test_check_connectivity_from_nodes_exception(self, mock_check_connection):
        """Test check_connectivity_from_nodes with exception"""
        # Mock nodes
        nodes = [{"ip": "192.168.1.100", "name": "node1"}, {"ip": "192.168.1.101", "name": "node2"}]

        # Mock check_connection to raise exception for second node
        mock_check_connection.side_effect = [
            {
                "status": "success",
                "node_ip": "192.168.1.100",
                "target_ip": "192.168.1.1",
                "target_port": 80,
                "response_time": 0.5,
            },
            Exception("Check error"),
        ]

        results = await check_connectivity_from_nodes(nodes, "192.168.1.1", 80, timeout=5)

        assert len(results) == 2
        # Since asyncio.gather doesn't guarantee order, check that we have one success and one failed
        statuses = [r["status"] for r in results]
        assert "success" in statuses
        assert "failed" in statuses
        assert statuses.count("success") == 1
        assert statuses.count("failed") == 1
        # Find the failed result and check error
        failed_result = next(r for r in results if r["status"] == "failed")
        assert "Check execution error" in failed_result["error"]

    @pytest.mark.asyncio
    async def test_check_connectivity_from_nodes_empty_list(self):
        """Test check_connectivity_from_nodes with empty nodes list"""
        # This test should handle the case where asyncio.gather gets empty list
        results = await check_connectivity_from_nodes([], "192.168.1.1", 80, timeout=5)
        assert len(results) == 0


class TestValidationFunctions:
    """Test cases for validation functions"""

    def test_validate_ipv4_address_valid(self):
        """Test validate_ipv4_address with valid IP addresses"""
        valid_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "127.0.0.1", "255.255.255.255", "0.0.0.0"]

        for ip in valid_ips:
            assert validate_ipv4_address(ip) is True, f"IP should be valid: {ip}"

    def test_validate_ipv4_address_invalid(self):
        """Test validate_ipv4_address with invalid IP addresses"""
        invalid_ips = [
            "256.1.1.1",  # Octet > 255
            "192.168.1",  # Too few octets
            "192.168.1.1.1",  # Too many octets
            "192.168.1.a",  # Non-numeric
            "192.168.-1.1",  # Negative number
            "",  # Empty string
            "not.an.ip.address",
        ]

        for ip in invalid_ips:
            assert validate_ipv4_address(ip) is False, f"IP should be invalid: {ip}"

    def test_validate_port_valid(self):
        """Test validate_port with valid ports"""
        valid_ports = [1, 80, 443, 8080, 65535]

        for port in valid_ports:
            assert validate_port(port) is True, f"Port should be valid: {port}"

    def test_validate_port_invalid(self):
        """Test validate_port with invalid ports"""
        invalid_ports = [0, -1, 65536, 100000, None]

        for port in invalid_ports:
            assert validate_port(port) is False, f"Port should be invalid: {port}"

        # Test with string (should fail)
        assert validate_port("80") is False, "Port should be invalid for string"
        # Test with float (should fail)
        assert validate_port(80.5) is False, "Port should be invalid for float"


class TestNetworkConnectivityResult:
    """Test cases for NetworkConnectivityResult class"""

    def test_init(self):
        """Test NetworkConnectivityResult initialization"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        assert result.cluster_name == "test-cluster"
        assert result.target_ip == "192.168.1.1"
        assert result.target_port == 80
        assert isinstance(result.timestamp, datetime)
        assert result.checks == []
        assert result.result_id.startswith("network_test-cluster_")
        assert len(result.result_id) > len("network_test-cluster_")

    def test_add_check(self):
        """Test add_check method"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        check_result = {
            "status": "success",
            "node_ip": "192.168.1.100",
            "target_ip": "192.168.1.1",
            "target_port": 80,
            "response_time": 0.5,
        }

        result.add_check(check_result)

        assert len(result.checks) == 1
        assert result.checks[0] == check_result

    def test_get_checks(self):
        """Test get_checks method"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        check_result1 = {"status": "success", "node_ip": "192.168.1.100"}
        check_result2 = {"status": "failed", "node_ip": "192.168.1.101"}

        result.add_check(check_result1)
        result.add_check(check_result2)

        checks = result.get_checks()

        assert len(checks) == 2
        assert checks[0] == check_result1
        assert checks[1] == check_result2

    def test_get_summary(self):
        """Test get_summary method"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        # Add some check results
        result.add_check({"status": "success", "node_ip": "192.168.1.100"})
        result.add_check({"status": "failed", "node_ip": "192.168.1.101"})
        result.add_check({"status": "success", "node_ip": "192.168.1.102"})

        summary = result.get_summary()

        assert summary["cluster_name"] == "test-cluster"
        assert summary["target_ip"] == "192.168.1.1"
        assert summary["target_port"] == 80
        assert summary["total_checks"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 66.7

    def test_get_summary_empty(self):
        """Test get_summary with no checks"""
        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        summary = result.get_summary()

        assert summary["total_checks"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["success_rate"] == 0

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_save(self, mock_get_db, mock_repo_class):
        """Test save method"""
        logger.info("Starting test_save")
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            logger.info("Mock get_db generator called")
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.create = AsyncMock()

        # Mock db methods
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()  # Added missing mock
        logger.info("Mocks set up for test_save")

        result = NetworkConnectivityResult("test-cluster", "192.168.1.1", 80)

        # Add check result
        result.add_check({"status": "success", "node_ip": "192.168.1.100"})

        # Save result
        logger.info("Calling result.save()")
        result_id = await result.save()
        logger.info(f"result.save() returned: {result_id}")

        # Verify database was called
        mock_repo.create.assert_called_once()
        args = mock_repo.create.call_args[0][0]
        assert args["result_id"] == result.result_id
        assert args["cluster_name"] == "test-cluster"
        assert args["inspection_type"] == "network"
        assert "result_data" in args
        assert args["result_data"]["cluster_name"] == "test-cluster"
        assert args["result_data"]["target_ip"] == "192.168.1.1"
        assert args["result_data"]["target_port"] == 80
        assert len(args["result_data"]["checks"]) == 1
        assert "summary" in args["result_data"]
        logger.info("test_save completed successfully")


class TestLoadNetworkCheckResult:
    """Test cases for load_network_check_result function"""

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_load_network_check_result_found(self, mock_get_db, mock_repo_class):
        """Test load_network_check_result when result is found"""
        logger.info("Starting test_load_network_check_result_found")
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            logger.info("Mock get_db generator called in test_load")
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()
        mock_repo = AsyncMock()

        mock_repo_class.return_value = mock_repo

        result_data = {
            "result_id": "test_result_id",
            "cluster_name": "test-cluster",
            "target_ip": "192.168.1.1",
            "target_port": 80,
        }

        mock_result = MagicMock()
        mock_result.result_data = result_data
        mock_result.inspection_type = "network"
        mock_repo.get_by_result_id = AsyncMock(return_value=mock_result)

        # Mock db methods
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_result)))
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()  # Added missing mock
        logger.info("Mocks set up for test_load_network_check_result_found")

        logger.info("Calling load_network_check_result")
        result = await load_network_check_result("test_result_id")
        logger.info(f"load_network_check_result returned: {result}")

        assert result is not None
        assert result["result_id"] == "test_result_id"
        assert result["cluster_name"] == "test-cluster"
        mock_repo.get_by_result_id.assert_called_once_with("test_result_id")
        logger.info("test_load_network_check_result_found completed successfully")

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_load_network_check_result_not_found(self, mock_get_db, mock_repo_class):
        """Test load_network_check_result when result is not found"""
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_result_id = AsyncMock(return_value=None)

        # Mock db methods
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()

        result = await load_network_check_result("nonexistent_result_id")

        assert result is None
        mock_repo.get_by_result_id.assert_called_once_with("nonexistent_result_id")

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_load_network_check_result_invalid_file(self, mock_get_db, mock_repo_class):
        """Test load_network_check_result with invalid result"""
        # Mock database functions to return None (simulating invalid or missing result)
        mock_db = MagicMock()

        async def mock_get_db_generator():
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_by_result_id = AsyncMock(return_value=None)

        # Mock db methods
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()

        result = await load_network_check_result("invalid_result")

        assert result is None
        mock_repo.get_by_result_id.assert_called_once_with("invalid_result")


class TestListNetworkCheckResults:
    """Test cases for list_network_check_results function"""

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_list_network_check_results(self, mock_get_db, mock_repo_class):
        """Test list_network_check_results function"""
        logger.info("Starting test_list_network_check_results")
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            logger.info("Mock get_db generator called in test_list")
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.list_results = AsyncMock(
            return_value={
                "results": [
                    {
                        "result_id": "result2",
                        "cluster_name": "cluster2",
                        "timestamp": "2023-01-02T12:00:00",
                        "summary": {"total_checks": 5, "successful": 5, "failed": 0},
                    },
                    {
                        "result_id": "result1",
                        "cluster_name": "cluster1",
                        "timestamp": "2023-01-01T12:00:00",
                        "summary": {"total_checks": 10, "successful": 8, "failed": 2},
                    },
                ],
                "total": 2,
                "limit": None,
                "offset": 0,
            }
        )

        # Mock db methods
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()  # Added missing mock
        logger.info("Mocks set up for test_list_network_check_results")

        logger.info("Calling list_network_check_results")
        results = await list_network_check_results()
        logger.info(f"list_network_check_results returned: {len(results)} results")

        assert len(results) == 2
        # Should be sorted by timestamp (newest first)
        assert results[0]["result_id"] == "result2"
        assert results[1]["result_id"] == "result1"
        mock_repo.list_results.assert_called_once_with(cluster_name=None, inspection_type="network", limit=None)
        logger.info("test_list_network_check_results completed successfully")

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_list_network_check_results_with_cluster_filter(self, mock_get_db, mock_repo_class):
        """Test list_network_check_results with cluster filter"""
        logger.info("Starting test_list_network_check_results_with_cluster_filter")
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            logger.info("Mock get_db generator called in test_list_with_filter")
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.list_results = AsyncMock(
            return_value={
                "results": [
                    {
                        "result_id": "result1",
                        "cluster_name": "cluster1",
                        "timestamp": "2023-01-01T12:00:00",
                        "summary": {"total_checks": 10, "successful": 8, "failed": 2},
                    }
                ],
                "total": 1,
                "limit": None,
                "offset": 0,
            }
        )

        # Mock db methods
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()  # Added missing mock
        logger.info("Mocks set up for test_list_network_check_results_with_cluster_filter")

        logger.info("Calling list_network_check_results with cluster filter")
        results = await list_network_check_results(cluster_name="cluster1")
        logger.info(f"list_network_check_results returned: {len(results)} results")

        assert len(results) == 1
        assert results[0]["result_id"] == "result1"
        mock_repo.list_results.assert_called_once_with(cluster_name="cluster1", inspection_type="network", limit=None)
        logger.info("test_list_network_check_results_with_cluster_filter completed successfully")

    @pytest.mark.asyncio
    @patch("db.repositories.inspection_result_repository.InspectionResultRepository")
    @patch("db.database.get_db")
    async def test_list_network_check_results_with_limit(self, mock_get_db, mock_repo_class):
        """Test list_network_check_results with limit"""
        logger.info("Starting test_list_network_check_results_with_limit")
        # Mock database functions
        mock_db = MagicMock()

        async def mock_get_db_generator():
            logger.info("Mock get_db generator called in test_list_with_limit")
            yield mock_db

        mock_get_db.return_value = mock_get_db_generator()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.list_results = AsyncMock(
            return_value={
                "results": [
                    {
                        "result_id": f"result{i}",
                        "cluster_name": "cluster1",
                        "timestamp": f"2023-01-0{i + 1}T12:00:00",
                        "summary": {"total_checks": 10, "successful": 8, "failed": 2},
                    }
                    for i in range(3)
                ],
                "total": 3,
                "limit": 3,
                "offset": 0,
            }
        )

        # Mock db methods
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.close = AsyncMock()  # Added missing mock
        logger.info("Mocks set up for test_list_network_check_results_with_limit")

        logger.info("Calling list_network_check_results with limit")
        results = await list_network_check_results(limit=3)
        logger.info(f"list_network_check_results returned: {len(results)} results")

        assert len(results) == 3
        mock_repo.list_results.assert_called_once_with(cluster_name=None, inspection_type="network", limit=3)
        logger.info("test_list_network_check_results_with_limit completed successfully")
