#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for InspectionOrchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from services.components.inspection_orchestrator import InspectionOrchestrator
from services.inspectors.base_inspector import BaseInspector


class MockInspector(BaseInspector):
    """Mock inspector for testing"""

    def __init__(self, name: str, should_fail: bool = False):
        # Set _name BEFORE calling parent constructor
        self._name = name
        self.should_fail = should_fail
        # Call parent constructor with empty config
        super().__init__(config={}, use_gitops=False)

    @property
    def inspector_type(self) -> str:
        """Returns inspector type"""
        return self._name

    async def _apply_rule(self, rule, context: dict):
        """Mock rule application"""
        if self.should_fail:
            raise Exception(f"{self._name} failed")
        return {"inspector": self._name, "cluster": context.get("cluster_name", "unknown")}

    async def run_inspection(self, cluster_name: str):
        """Mock inspection run"""
        if self.should_fail:
            raise Exception(f"{self._name} failed")
        return {"inspector": self._name, "cluster": cluster_name}


class TestInspectionOrchestrator:
    """Tests for InspectionOrchestrator"""

    @pytest.fixture
    def mock_inspectors(self):
        """Create mock inspectors"""
        return {"node": MockInspector("node"), "opa": MockInspector("opa"), "popeye": MockInspector("popeye")}

    @pytest.fixture
    def orchestrator(self, mock_inspectors):
        """Create orchestrator instance"""
        return InspectionOrchestrator(mock_inspectors)

    @pytest.mark.asyncio
    async def test_orchestrate_all_inspectors(self, orchestrator):
        """Test orchestration of all inspectors"""
        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}

        results = await orchestrator.orchestrate("test-cluster", config)

        assert len(results) == 3
        assert "node" in results
        assert "opa" in results
        assert "popeye" in results
        assert results["node"]["status"] == "completed"
        assert results["opa"]["status"] == "completed"
        assert results["popeye"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_orchestrate_partial_inspectors(self, orchestrator):
        """Test orchestration with only some inspectors enabled"""
        config = {"enable_node": True, "enable_opa": False, "enable_popeye": True}

        results = await orchestrator.orchestrate("test-cluster", config)

        assert len(results) == 2
        assert "node" in results
        assert "popeye" in results
        assert "opa" not in results

    @pytest.mark.asyncio
    async def test_orchestrate_no_active_inspectors(self, orchestrator):
        """Test orchestration with no active inspectors"""
        config = {"enable_node": False, "enable_opa": False, "enable_popeye": False}

        results = await orchestrator.orchestrate("test-cluster", config)

        assert results["status"] == "skipped"
        assert results["message"] == "No active inspectors"

    @pytest.mark.asyncio
    async def test_orchestrate_with_failed_inspector(self):
        """Test orchestration with a failed inspector"""
        mock_inspectors = {
            "node": MockInspector("node"),
            "opa": MockInspector("opa", should_fail=True),
            "popeye": MockInspector("popeye"),
        }
        orchestrator = InspectionOrchestrator(mock_inspectors)

        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}

        results = await orchestrator.orchestrate("test-cluster", config)

        assert len(results) == 3
        assert results["node"]["status"] == "completed"
        assert results["opa"]["status"] == "failed"
        assert "error" in results["opa"]
        assert results["popeye"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_results(self, orchestrator):
        """Test getting inspection results"""
        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}
        await orchestrator.orchestrate("test-cluster", config)

        results = orchestrator.get_results()

        assert len(results) == 3
        assert "node" in results
        assert "opa" in results
        assert "popeye" in results

    @pytest.mark.asyncio
    async def test_get_inspector_status(self, orchestrator):
        """Test getting status of a specific inspector"""
        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}
        await orchestrator.orchestrate("test-cluster", config)

        status = orchestrator.get_inspector_status("node")
        assert status == "completed"

        status = orchestrator.get_inspector_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_failed_inspectors(self):
        """Test getting list of failed inspectors"""
        mock_inspectors = {
            "node": MockInspector("node"),
            "opa": MockInspector("opa", should_fail=True),
            "popeye": MockInspector("popeye", should_fail=True),
        }
        orchestrator = InspectionOrchestrator(mock_inspectors)

        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}
        await orchestrator.orchestrate("test-cluster", config)

        failed = orchestrator.get_failed_inspectors()
        assert len(failed) == 2
        assert "opa" in failed
        assert "popeye" in failed
        assert "node" not in failed

    @pytest.mark.asyncio
    async def test_get_successful_inspectors(self):
        """Test getting list of successful inspectors"""
        mock_inspectors = {
            "node": MockInspector("node"),
            "opa": MockInspector("opa", should_fail=True),
            "popeye": MockInspector("popeye"),
        }
        orchestrator = InspectionOrchestrator(mock_inspectors)

        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}
        await orchestrator.orchestrate("test-cluster", config)

        successful = orchestrator.get_successful_inspectors()
        assert len(successful) == 2
        assert "node" in successful
        assert "popeye" in successful
        assert "opa" not in successful

    @pytest.mark.asyncio
    async def test_reset_results(self, orchestrator):
        """Test resetting inspection results"""
        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}
        await orchestrator.orchestrate("test-cluster", config)

        assert len(orchestrator.get_results()) == 3

        orchestrator.reset_results()

        assert len(orchestrator.get_results()) == 0

    @pytest.mark.asyncio
    async def test_should_run_inspector_default(self, orchestrator):
        """Test default behavior for inspector activation"""
        config = {}  # Empty config

        # All inspectors should run by default
        active = orchestrator._get_active_inspectors(config)
        assert len(active) == 3

    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestrator):
        """Test that inspectors run in parallel"""
        import time

        async def slow_inspection(cluster_name):
            await asyncio.sleep(0.1)
            return {"result": "done"}

        mock_inspectors = {
            "node": MockInspector("node"),
            "opa": MockInspector("opa"),
            "popeye": MockInspector("popeye"),
        }

        # Override run_inspection to be slow
        for inspector in mock_inspectors.values():
            inspector.run_inspection = slow_inspection

        orchestrator = InspectionOrchestrator(mock_inspectors)

        config = {"enable_node": True, "enable_opa": True, "enable_popeye": True}

        start_time = time.time()
        await orchestrator.orchestrate("test-cluster", config)
        elapsed_time = time.time() - start_time

        # Should complete in ~0.1s if parallel, ~0.3s if sequential
        assert elapsed_time < 0.2, "Inspectors should run in parallel"
