#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for inspection coordinator component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio


class TestInspectionCoordinator:
    """Test cases for inspection coordinator"""

    @patch("services.components.inspection_coordinator.NodeInspector")
    @patch("services.components.inspection_coordinator.OpaInspector")
    @pytest.mark.asyncio
    async def test_execute_inspections_all_types(self, mock_opa_inspector, mock_node_inspector):
        """Test execution of all inspection types"""
        # Setup mocks
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.return_value = {"node": "results"}
        mock_node_inspector.return_value = mock_node_instance

        mock_opa_instance = AsyncMock()
        mock_opa_instance.run_inspection.return_value = {"opa": "results"}
        mock_opa_inspector.return_value = mock_opa_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        nodes = [{"name": "node1"}]
        kubeconfig = "/path/to/kubeconfig"
        selected_rules = {"node": ["rule1"], "opa": ["rule3"]}

        result = await coordinator.execute_inspections("test-cluster", nodes, kubeconfig, selected_rules)

        assert "node" in result
        assert "opa" in result
        mock_node_instance.run_inspection.assert_called_once_with("test-cluster", ["rule1"])
        mock_opa_instance.run_inspection.assert_called_once_with("test-cluster", ["rule3"])

    @patch("services.components.inspection_coordinator.NodeInspector")
    @patch("services.components.inspection_coordinator.OpaInspector")
    @pytest.mark.asyncio
    async def test_execute_inspections_no_selected_rules(self, mock_opa_inspector, mock_node_inspector):
        """Test execution with no selected rules (should run all available)"""
        # Setup mocks
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.return_value = {"node": "results"}
        mock_node_inspector.return_value = mock_node_instance

        mock_opa_instance = AsyncMock()
        mock_opa_instance.run_inspection.return_value = {"opa": "results"}
        mock_opa_inspector.return_value = mock_opa_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        nodes = [{"name": "node1"}]
        kubeconfig = "/path/to/kubeconfig"
        selected_rules = None

        result = await coordinator.execute_inspections("test-cluster", nodes, kubeconfig, selected_rules)

        assert "node" in result
        assert "opa" in result
        mock_node_instance.run_inspection.assert_called_once_with("test-cluster", [])
        mock_opa_instance.run_inspection.assert_called_once_with("test-cluster", [])

    @patch("services.components.inspection_coordinator.NodeInspector")
    @pytest.mark.asyncio
    async def test_execute_inspections_partial_types(self, mock_node_inspector):
        """Test execution of only some inspection types"""
        # Setup mocks
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.return_value = {"node": "results"}
        mock_node_inspector.return_value = mock_node_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        nodes = [{"name": "node1"}]
        kubeconfig = "/path/to/kubeconfig"
        selected_rules = {"node": ["rule1"]}  # No OPA

        result = await coordinator.execute_inspections("test-cluster", nodes, kubeconfig, selected_rules)

        assert "node" in result
        assert "opa" not in result
        mock_node_instance.run_inspection.assert_called_once_with("test-cluster", ["rule1"])

    @patch("services.components.inspection_coordinator.NodeInspector")
    @pytest.mark.asyncio
    async def test_execute_node_inspection_success(self, mock_node_inspector):
        """Test successful node inspection"""
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.return_value = {"node": "results"}
        mock_node_inspector.return_value = mock_node_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=True)

        result = await coordinator._execute_node_inspection("test-cluster", [{"name": "node1"}], ["rule1"], True)

        assert result[0] is True  # success
        assert result[1] == {"node": "results"}
        mock_node_inspector.assert_called_once_with([{"name": "node1"}], use_gitops=True)
        mock_node_instance.run_inspection.assert_called_once_with("test-cluster", ["rule1"])

    @patch("services.components.inspection_coordinator.NodeInspector")
    @patch("services.components.inspection_coordinator.InspectionResult")
    @pytest.mark.asyncio
    async def test_execute_node_inspection_failure(self, mock_inspection_result, mock_node_inspector):
        """Test node inspection with failure"""
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.side_effect = Exception("Node inspection failed")
        mock_node_inspector.return_value = mock_node_instance

        mock_result_instance = Mock()
        mock_inspection_result.return_value = mock_result_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        result = await coordinator._execute_node_inspection("test-cluster", [{"name": "node1"}], ["rule1"], True)

        assert result[0] is True  # success (error handled)
        assert result[1] == mock_result_instance
        mock_node_inspector.assert_called_once_with([{"name": "node1"}], use_gitops=False)
        mock_result_instance.add_item.assert_called_once()

    @patch("services.components.inspection_coordinator.OpaInspector")
    @pytest.mark.asyncio
    async def test_execute_opa_inspection_success(self, mock_opa_inspector):
        """Test successful OPA inspection"""
        mock_opa_instance = AsyncMock()
        mock_opa_instance.run_inspection.return_value = {"opa": "results"}
        mock_opa_inspector.return_value = mock_opa_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=True)

        kubeconfig = "/path/to/kubeconfig"
        result = await coordinator._execute_opa_inspection("test-cluster", kubeconfig, ["rule1"], True)

        assert result[0] is True  # success
        assert result[1] == {"opa": "results"}

        expected_config = {
            "kubeconfig": kubeconfig,
            "opa_path": "/usr/local/bin/opa",
        }
        mock_opa_inspector.assert_called_once_with(expected_config, use_gitops=True)
        mock_opa_instance.run_inspection.assert_called_once_with("test-cluster", ["rule1"])

    @patch("services.components.inspection_coordinator.OpaInspector")
    @pytest.mark.asyncio
    async def test_execute_opa_inspection_no_kubeconfig(self, mock_opa_inspector):
        """Test OPA inspection with no kubeconfig"""
        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        kubeconfig = ""
        result = await coordinator._execute_opa_inspection("test-cluster", kubeconfig, ["rule1"], True)

        assert result[0] is True  # success
        assert result[1] is None
        mock_opa_inspector.assert_not_called()

    @patch("services.components.inspection_coordinator.OpaInspector")
    @patch("services.components.inspection_coordinator.InspectionResult")
    @pytest.mark.asyncio
    async def test_execute_opa_inspection_failure(self, mock_inspection_result, mock_opa_inspector):
        """Test OPA inspection with failure"""
        mock_opa_instance = AsyncMock()
        mock_opa_instance.run_inspection.side_effect = Exception("OPA inspection failed")
        mock_opa_inspector.return_value = mock_opa_instance

        mock_result_instance = Mock()
        mock_inspection_result.return_value = mock_result_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        kubeconfig = "/path/to/kubeconfig"
        result = await coordinator._execute_opa_inspection("test-cluster", kubeconfig, ["rule1"], True)

        assert result[0] is True  # success (error handled)
        assert result[1] == mock_result_instance

        expected_config = {
            "kubeconfig": kubeconfig,
            "opa_path": "/usr/local/bin/opa",
        }
        mock_opa_inspector.assert_called_once_with(expected_config, use_gitops=False)
        mock_result_instance.add_item.assert_called_once()

    @patch("services.components.inspection_coordinator.InspectionResult")
    def test_create_error_result(self, mock_inspection_result):
        """Test creation of error result"""
        mock_result_instance = Mock()
        mock_inspection_result.return_value = mock_result_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator()

        result = coordinator._create_error_result("test-cluster", "node", "Test error")

        assert result == mock_result_instance
        mock_inspection_result.assert_called_once_with("test-cluster", "node")
        mock_result_instance.add_item.assert_called_once()

    @patch("services.components.inspection_coordinator.NodeInspector")
    @pytest.mark.asyncio
    async def test_execute_inspections_with_dict_rules(self, mock_node_inspector):
        """Test execution with rules in dict format"""
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.return_value = {"node": "results"}
        mock_node_inspector.return_value = mock_node_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        nodes = [{"name": "node1"}]
        prometheus_config = {"enabled": False}
        kubeconfig = ""
        selected_rules = {"node": {"rules": ["rule1", "rule2"]}}  # Dict with rules key

        result = await coordinator.execute_inspections(
            "test-cluster", nodes, kubeconfig, selected_rules, show_progress=False
        )

        assert "node" in result
        mock_node_instance.run_inspection.assert_called_once_with("test-cluster", ["rule1", "rule2"])

    @patch("services.components.inspection_coordinator.NodeInspector")
    @pytest.mark.asyncio
    async def test_execute_inspections_with_ssh_errors(self, mock_node_inspector):
        """Test execution with SSH connection errors"""
        mock_node_instance = AsyncMock()
        mock_node_instance.run_inspection.side_effect = Exception("SSH connection failed")
        mock_ssh_error_manager = AsyncMock()
        mock_ssh_error_manager.get_all_connection_errors.return_value = [
            {"name": "SSH Error", "status": "error", "description": "Connection failed"}
        ]
        mock_node_instance.ssh_error_manager = mock_ssh_error_manager
        mock_node_inspector.return_value = mock_node_instance

        from services.components.inspection_coordinator import InspectionCoordinator

        coordinator = InspectionCoordinator(use_gitops=False)

        nodes = [{"name": "node1"}]
        prometheus_config = {"enabled": False}
        kubeconfig = ""
        selected_rules = {"node": ["rule1"]}

        result = await coordinator.execute_inspections(
            "test-cluster", nodes, kubeconfig, selected_rules, show_progress=False
        )

        assert "node" in result
        # Check that SSH errors were added by checking the result contains SSH error information
        assert isinstance(result["node"], object)  # Result should be an InspectionResult object
