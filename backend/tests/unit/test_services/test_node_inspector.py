#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for node inspector
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.inspectors.node.node_inspector import NodeInspector, SSHConnectionErrorManager
from infrastructure.results.inspection_result import InspectionResult


class TestSSHConnectionErrorManager:
    """Test cases for SSH connection error manager"""

    def test_register_connection_error_new(self):
        """Test registering new connection error"""
        manager = SSHConnectionErrorManager()

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        error_msg = "Connection refused"

        node_key = manager.register_connection_error(node, error_msg)

        assert node_key == "192.168.1.1:22"
        assert manager.has_connection_error(node)
        assert len(manager._errors_registry) == 1

    def test_register_connection_error_duplicate(self):
        """Test registering duplicate connection error"""
        manager = SSHConnectionErrorManager()

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        error_msg1 = "Connection refused"
        error_msg2 = "Connection timeout"

        # Register first error
        key1 = manager.register_connection_error(node, error_msg1)
        # Try to register second error for same node
        key2 = manager.register_connection_error(node, error_msg2)

        assert key1 == key2
        assert len(manager._errors_registry) == 1
        # Should keep first error message
        assert manager._errors_registry[key1]["error_message"] == error_msg1

    def test_get_connection_error_result(self):
        """Test getting formatted connection error result"""
        manager = SSHConnectionErrorManager()

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        error_msg = "Connection refused"

        manager.register_connection_error(node, error_msg)
        result = manager.get_connection_error_result(node)

        assert result is not None
        assert "SSH connection" in result["name"]
        assert result["connection_error"] is True
        assert "node1" in result["details"]

    def test_get_all_connection_errors(self):
        """Test getting all connection errors"""
        manager = SSHConnectionErrorManager()

        node1 = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        node2 = {"ip": "192.168.1.2", "port": 22, "name": "node2"}

        manager.register_connection_error(node1, "Error 1")
        manager.register_connection_error(node2, "Error 2")

        errors = manager.get_all_connection_errors()

        assert len(errors) == 2
        assert all(error["connection_error"] for error in errors)

    def test_reset_for_inspection(self):
        """Test resetting error registry"""
        manager = SSHConnectionErrorManager()

        node = {"ip": "192.168.1.1", "port": 22, "name": "node1"}
        manager.register_connection_error(node, "Error")

        assert len(manager._errors_registry) == 1

        manager.reset_for_inspection()

        assert len(manager._errors_registry) == 0
        assert not manager.has_connection_error(node)


class TestNodeInspector:
    """Test cases for node inspector"""

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_init(self, mock_security_checker):
        """Test inspector initialization"""
        nodes_config = [
            {"ip": "192.168.1.1", "port": 22, "name": "node1"},
            {"ip": "192.168.1.2", "port": 22, "name": "node2"},
        ]

        inspector = NodeInspector(nodes_config)

        assert inspector.nodes == nodes_config
        assert inspector.inspector_type == "node"
        assert len(inspector.nodes) == 2
        assert isinstance(inspector.ssh_error_manager, SSHConnectionErrorManager)

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    @patch("services.inspectors.node.node_inspector.NodeInspector._check_all_node_connections")
    @patch("services.inspectors.base_inspector.BaseInspector.run_inspection")
    @pytest.mark.asyncio
    async def test_run_inspection_with_available_nodes(
        self, mock_base_run, mock_check_connections, mock_security_checker
    ):
        """Test inspection run with available nodes"""
        nodes_config = [{"ip": "192.168.1.1", "port": 22, "name": "node1"}]
        inspector = NodeInspector(nodes_config)

        # Mock available nodes
        available_nodes = [{"ip": "192.168.1.1", "port": 22, "name": "node1"}]
        mock_check_connections.return_value = available_nodes

        # Mock base inspection result
        mock_result = InspectionResult("test-cluster", "node")
        mock_base_run.return_value = mock_result

        result = await inspector.run_inspection("test-cluster")

        assert isinstance(result, InspectionResult)
        assert result.cluster_name == "test-cluster"
        assert result.inspection_type == "node"  # Fix: it's inspection_type, not inspector_type
        mock_check_connections.assert_called_once()

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    @patch("services.inspectors.node.node_inspector.NodeInspector._check_all_node_connections")
    @pytest.mark.asyncio
    async def test_run_inspection_no_available_nodes(self, mock_check_connections, mock_security_checker):
        """Test inspection run with no available nodes"""
        nodes_config = [{"ip": "192.168.1.1", "port": 22, "name": "node1"}]
        inspector = NodeInspector(nodes_config)

        # Mock no available nodes
        mock_check_connections.return_value = []

        # Mock SSH error
        mock_error = {"connection_error": True, "name": "SSH connection - node1"}
        with patch.object(inspector.ssh_error_manager, "get_all_connection_errors", return_value=[mock_error]):
            result = await inspector.run_inspection("test-cluster")

        assert isinstance(result, InspectionResult)
        assert len(result.items) == 1  # Should have SSH error
        assert result.items[0]["connection_error"] is True

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_filter_nodes_by_selector(self, mock_security_checker):
        """Test filtering nodes by selector"""
        nodes_config = [
            {"ip": "192.168.1.1", "port": 22, "name": "node1", "labels": {"env": "prod", "type": "worker"}},
            {"ip": "192.168.1.2", "port": 22, "name": "node2", "labels": {"env": "dev", "type": "worker"}},
        ]
        inspector = NodeInspector(nodes_config)

        # Test matching selector
        selector = {"env": "prod"}
        filtered = inspector._filter_nodes_by_selector(nodes_config, selector)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "node1"

        # Test non-matching selector
        selector = {"env": "staging"}
        filtered = inspector._filter_nodes_by_selector(nodes_config, selector)
        assert len(filtered) == 0

        # Test empty selector
        filtered = inspector._filter_nodes_by_selector(nodes_config, {})
        assert len(filtered) == 2

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_is_ssh_connection_error(self, mock_security_checker):
        """Test SSH connection error detection"""
        inspector = NodeInspector([])

        # Test SSH-related errors
        ssh_errors = [
            "connection refused",
            "ssh: connect to host",
            "timeout",
            "authentication failed",
            "network unreachable",
        ]

        for error in ssh_errors:
            assert inspector._is_ssh_connection_error(error)

        # Test non-SSH errors
        non_ssh_errors = ["command not found", "permission denied", "file not found"]

        for error in non_ssh_errors:
            assert not inspector._is_ssh_connection_error(error)

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_get_execution_stats(self, mock_security_checker):
        """Test getting execution statistics"""
        nodes_config = [{"ip": "192.168.1.1", "port": 22, "name": "node1"}]
        inspector = NodeInspector(nodes_config)

        # Update some stats
        inspector.execution_stats["successful_executions"] = 5
        inspector.execution_stats["total_node_executions"] = 10

        stats = inspector.get_execution_stats()

        assert stats["total_nodes"] == 1
        assert stats["successful_executions"] == 5
        assert stats["total_node_executions"] == 10
        assert stats["success_rate"] == 50.0
        assert stats["ssh_connection_errors"] == 0

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_create_optimized_small_cluster(self, mock_security_checker):
        """Test creating optimized inspector for small cluster"""
        nodes_config = [{"ip": "192.168.1.1", "port": 22, "name": "node1"}]

        inspector = NodeInspector.create_optimized(nodes_config)

        assert inspector.max_workers == 1
        assert inspector.enable_concurrent is False
        assert inspector.timeout == 30

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_create_optimized_medium_cluster(self, mock_security_checker):
        """Test creating optimized inspector for medium cluster"""
        nodes_config = [{"ip": f"192.168.1.{i}", "port": 22, "name": f"node{i}"} for i in range(1, 8)]

        inspector = NodeInspector.create_optimized(nodes_config)

        assert inspector.max_workers == 7
        assert inspector.enable_concurrent is True
        assert inspector.timeout == 25

    @patch("services.inspectors.node.node_inspector.CommandSecurityChecker")
    def test_create_optimized_large_cluster(self, mock_security_checker):
        """Test creating optimized inspector for large cluster"""
        nodes_config = [{"ip": f"192.168.1.{i}", "port": 22, "name": f"node{i}"} for i in range(1, 25)]

        inspector = NodeInspector.create_optimized(nodes_config)

        assert inspector.max_workers == 24  # 25 nodes, min(25, 25) = 25, but wait, let's check the logic
        assert inspector.enable_concurrent is True
        assert inspector.timeout == 15
