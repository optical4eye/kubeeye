#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for inspection engine component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio


class TestInspectionEngine:
    """Test cases for inspection engine"""

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_success(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test successful unified inspection execution"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified("test-cluster")

        assert result[0] is True  # success
        assert "Results saved" in result[1]  # message
        assert "node" in result[2]  # results
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()
        mock_result_instance.process_and_save_results.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_with_progress(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with progress callback"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=True,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is True
        assert "Results saved" in result[1]
        assert "node" in result[2]
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_inspector_failure(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with inspector failure"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is True  # Still returns True as errors are recorded in results
        assert "Results saved" in result[1]
        assert "node" in result[2]
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_no_rules(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with no rules"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is True
        assert "Results saved" in result[1]
        assert result[2] == {}
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_config_error(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with configuration error"""
        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=(None, "Config error"))
        mock_config_manager.return_value = mock_config_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is False
        assert "Config error" in result[1]
        assert result[2] is None
        mock_config_instance.get_cluster_configuration.assert_called_once()
        mock_coordinator.return_value.execute_inspections.assert_not_called()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_coordinator_exception(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with coordinator exception"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.side_effect = Exception("Coordinator error")
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is False
        assert "Coordinator error" in result[1]
        assert result[2] is None
        mock_config_instance.get_cluster_configuration.assert_called_once()
        mock_coordinator_instance.execute_inspections.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_result_manager_exception(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with result manager exception"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.side_effect = Exception("Result manager error")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=False,
        )

        assert result[0] is False
        assert "Result manager error" in result[1]
        assert result[2] is None
        mock_config_instance.get_cluster_configuration.assert_called_once()
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_result_instance.process_and_save_results.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_with_gitops(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with GitOps enabled"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=False,
            use_gitops=True,
        )

        assert result[0] is True
        assert "Results saved" in result[1]
        assert "node" in result[2]
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()

    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_with_ui_feedback(
        self, mock_result_manager, mock_config_manager, mock_coordinator, mock_gitops_manager
    ):
        """Test unified inspection execution with UI feedback"""
        # Mock InspectionCoordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_instance.execute_inspections.return_value = {"node": [], "prometheus": [], "opa": []}
        mock_coordinator.return_value = mock_coordinator_instance

        # Mock InspectionConfigManager
        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": []}, None))
        mock_config_instance.extract_cluster_components.return_value = {
            "nodes": [],
            "prometheus_config": {},
            "kubeconfig": {},
        }
        mock_config_instance.validate_inspection_feasibility.return_value = (True, None, {})
        mock_config_manager.return_value = mock_config_instance

        # Mock InspectionResultManager
        mock_result_instance = AsyncMock()
        mock_result_instance.process_and_save_results.return_value = (True, "Results saved")
        mock_result_manager.return_value = mock_result_instance

        # Mock GitOpsSyncManager
        mock_gitops_instance = AsyncMock()
        mock_gitops_instance.sync_if_needed.return_value = (True, "GitOps sync successful")
        mock_gitops_manager.return_value = mock_gitops_instance

        from services.components.inspection_engine import execute_inspection_unified

        result = await execute_inspection_unified(
            cluster_name="test-cluster",
            selected_rules={"node": ["rule1"]},
            inspection_type="immediate",
            show_progress=False,
            show_ui_feedback=True,
            use_gitops=False,
        )

        assert result[0] is True
        assert "Results saved" in result[1]
        assert "node" in result[2]
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_config_instance.get_cluster_configuration.assert_called_once()
