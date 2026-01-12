#!/usr/bin/env python3
from core.logging import get_logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for inspection engine component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import asyncio
import logging

from services.components.inspection_engine import InspectionEngine, execute_inspection_unified

logger = get_logger(__name__)


class TestInspectionEngine:
    """Test cases for inspection engine"""

    @pytest.fixture
    def inspection_engine(self):
        """Create inspection engine instance"""
        return InspectionEngine()

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    def test_init(self, mock_gitops_manager, inspection_engine):
        """Test inspection engine initialization"""
        mock_gitops_manager.return_value = Mock()

        engine = InspectionEngine()

        assert engine.progress is None
        assert hasattr(engine, "gitops_manager")

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_success(
        self, mock_result_manager, mock_coordinator, mock_config_manager, mock_gitops_manager, inspection_engine
    ):
        """Test successful inspection execution"""
        # Setup mocks
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(return_value=(True, "GitOps synced"))
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": [], "kubeconfig": ""}, None))
        mock_config_instance.extract_cluster_components = AsyncMock(return_value={"nodes": [], "kubeconfig": ""})
        mock_config_instance.validate_inspection_feasibility = Mock(return_value=(True, None, {}))
        mock_config_manager.return_value = mock_config_instance

        mock_coordinator_instance = Mock()
        mock_coordinator_instance.execute_inspections = AsyncMock(return_value={"node": "results", "opa": "results"})
        mock_coordinator.return_value = mock_coordinator_instance

        mock_result_instance = Mock()
        mock_result_instance.process_and_save_results = AsyncMock(return_value=(True, "Results saved"))
        mock_result_manager.return_value = mock_result_instance

        # Override gitops_manager with mock
        inspection_engine.gitops_manager = mock_gitops_instance

        # Execute
        success, message, results = await inspection_engine.execute_inspection("test-cluster")

        # Assert
        assert success is True
        assert "Results saved" in message
        assert results == {"node": "results", "opa": "results"}

        # Verify calls
        mock_gitops_instance.sync_if_needed.assert_called_once_with(False, False)
        mock_config_instance.get_cluster_configuration.assert_called_once_with("test-cluster", False)
        mock_config_instance.extract_cluster_components.assert_called_once()
        mock_config_instance.validate_inspection_feasibility.assert_called_once()
        mock_coordinator_instance.execute_inspections.assert_called_once()
        mock_result_instance.process_and_save_results.assert_called_once()

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_gitops_failure(
        self, mock_result_manager, mock_coordinator, mock_config_manager, mock_gitops_manager, inspection_engine
    ):
        """Test inspection execution with GitOps sync failure"""
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(
            return_value=(True, "GitOps sync failed but continuing: GitOps sync failed")
        )
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": [], "kubeconfig": ""}, None))
        mock_config_instance.extract_cluster_components = AsyncMock(return_value={"nodes": [], "kubeconfig": ""})
        mock_config_instance.validate_inspection_feasibility = Mock(return_value=(True, None, {}))
        mock_config_manager.return_value = mock_config_instance

        mock_coordinator_instance = Mock()
        mock_coordinator_instance.execute_inspections = AsyncMock(return_value={"node": "results", "opa": "results"})
        mock_coordinator.return_value = mock_coordinator_instance

        mock_result_instance = Mock()
        mock_result_instance.process_and_save_results = AsyncMock(return_value=(True, "Results saved"))
        mock_result_manager.return_value = mock_result_instance

        # Override gitops_manager with mock
        inspection_engine.gitops_manager = mock_gitops_instance

        success, message, results = await inspection_engine.execute_inspection("test-cluster", use_gitops=True)

        # Should continue despite GitOps failure
        assert success is True
        assert "Results saved" in message

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_config_failure(self, mock_config_manager, mock_gitops_manager, inspection_engine):
        """Test inspection execution with configuration failure"""
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(return_value=(True, "GitOps synced"))
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=(None, "Config error"))
        mock_config_manager.return_value = mock_config_instance

        success, message, results = await inspection_engine.execute_inspection("test-cluster")

        assert success is False
        assert "Config error" in message
        assert results is None

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_validation_failure(
        self, mock_config_manager, mock_gitops_manager, inspection_engine
    ):
        """Test inspection execution with validation failure"""
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(return_value=(True, "GitOps synced"))
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": [], "kubeconfig": ""}, None))
        mock_config_instance.extract_cluster_components = AsyncMock(return_value={"nodes": [], "kubeconfig": ""})
        mock_config_instance.validate_inspection_feasibility = Mock(return_value=(False, "Validation failed", {}))
        mock_config_manager.return_value = mock_config_instance

        success, message, results = await inspection_engine.execute_inspection("test-cluster")

        assert success is False
        assert "Validation failed" in message
        assert results is None

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_result_processing_failure(
        self, mock_result_manager, mock_coordinator, mock_config_manager, mock_gitops_manager, inspection_engine
    ):
        """Test inspection execution with result processing failure"""
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(return_value=(True, "GitOps synced"))
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": [], "kubeconfig": ""}, None))
        mock_config_instance.extract_cluster_components = AsyncMock(return_value={"nodes": [], "kubeconfig": ""})
        mock_config_instance.validate_inspection_feasibility = Mock(return_value=(True, None, {}))
        mock_config_manager.return_value = mock_config_instance

        mock_coordinator_instance = Mock()
        mock_coordinator_instance.execute_inspections = AsyncMock(return_value={"node": "results"})
        mock_coordinator.return_value = mock_coordinator_instance

        mock_result_instance = Mock()
        mock_result_instance.process_and_save_results = AsyncMock(return_value=(False, "Processing failed"))
        mock_result_manager.return_value = mock_result_instance

        success, message, results = await inspection_engine.execute_inspection("test-cluster")

        assert success is False
        assert "Processing failed" in message

    @patch("services.components.inspection_engine.inspection_engine")
    @pytest.mark.asyncio
    async def test_execute_inspection_unified_function(self, mock_engine_instance):
        """Test unified inspection function"""
        mock_engine_instance.execute_inspection = AsyncMock(return_value=(False, "Error", None))

        success, message, results = await execute_inspection_unified(
            "test-cluster", {"node": ["rule1"]}, "immediate", True, False, True
        )

        assert success is False
        assert message == "Error"
        assert results is None

        mock_engine_instance.execute_inspection.assert_called_once_with(
            "test-cluster", {"node": ["rule1"]}, "immediate", True, False, True
        )

    @patch("services.components.inspection_engine.GitOpsSyncManager")
    @patch("services.components.inspection_engine.InspectionConfigManager")
    @patch("services.components.inspection_engine.InspectionCoordinator")
    @patch("services.components.inspection_engine.InspectionResultManager")
    @pytest.mark.asyncio
    async def test_execute_inspection_with_selected_rules(
        self, mock_result_manager, mock_coordinator, mock_config_manager, mock_gitops_manager, inspection_engine
    ):
        """Test inspection execution with selected rules"""
        mock_gitops_instance = Mock()
        mock_gitops_instance.sync_if_needed = AsyncMock(return_value=(True, "GitOps synced"))
        mock_gitops_manager.return_value = mock_gitops_instance

        mock_config_instance = Mock()
        mock_config_instance.get_cluster_configuration = AsyncMock(return_value=({"nodes": [], "kubeconfig": ""}, None))
        mock_config_instance.extract_cluster_components = AsyncMock(return_value={"nodes": [], "kubeconfig": ""})
        mock_config_instance.validate_inspection_feasibility = Mock(return_value=(True, None, {}))
        mock_config_manager.return_value = mock_config_instance

        mock_coordinator_instance = Mock()
        mock_coordinator_instance.execute_inspections = AsyncMock(return_value={"node": "results"})
        mock_coordinator.return_value = mock_coordinator_instance

        mock_result_instance = Mock()
        mock_result_instance.process_and_save_results = AsyncMock(return_value=(True, "Results saved"))
        mock_result_manager.return_value = mock_result_instance

        selected_rules = {"node": ["rule1", "rule2"], "opa": ["rule3"]}

        success, message, results = await inspection_engine.execute_inspection(
            "test-cluster",
            selected_rules=selected_rules,
            inspection_type="scheduled",
            show_progress=True,
            show_ui_feedback=True,
            use_gitops=True,
        )

        assert success is True
        mock_coordinator_instance.execute_inspections.assert_called_once_with(
            cluster_name="test-cluster", nodes=[], kubeconfig="", selected_rules=selected_rules, show_progress=True
        )
