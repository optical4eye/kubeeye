#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for inspection result manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestInspectionResultManager:
    """Test cases for InspectionResultManager"""

    @pytest.mark.asyncio
    async def test_process_and_save_results_success(self):
        """Test successful processing and saving of results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager(use_gitops=False)

        # Mock the _save_inspection_results method
        with patch.object(manager, "_save_inspection_results", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = "/path/to/results.json"

            # Test with successful results
            all_results = {
                "node": (True, MagicMock(items=[MagicMock(status="ok")])),
                "opa": (True, MagicMock(items=[MagicMock(status="ok")])),
            }

            success, message = await manager.process_and_save_results(all_results, "test-cluster", {}, "immediate")

            assert success is True
            assert "completed successfully" in message
            assert "/path/to/results.json" in message
            mock_save.assert_called_once_with(all_results, "test-cluster", {}, "immediate")

    @pytest.mark.asyncio
    async def test_process_and_save_results_with_errors(self):
        """Test processing results with some errors"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager(use_gitops=False)

        # Mock the _save_inspection_results method
        with patch.object(manager, "_save_inspection_results", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = "/path/to/results.json"

            # Test with mixed results (some errors)
            all_results = {
                "node": (True, MagicMock(items=[MagicMock(status="error")])),
                "opa": (True, MagicMock(items=[MagicMock(status="ok")])),
            }

            success, message = await manager.process_and_save_results(all_results, "test-cluster", {}, "immediate")

            assert success is True
            assert "completed successfully" in message
            assert "/path/to/results.json" in message
            mock_save.assert_called_once_with(all_results, "test-cluster", {}, "immediate")

    @pytest.mark.asyncio
    async def test_process_and_save_results_exception(self):
        """Test processing results with exception"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager(use_gitops=False)

        # Mock the _save_inspection_results method to raise an exception
        with patch.object(manager, "_save_inspection_results", new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = Exception("Test error")

            all_results = {"node": (True, MagicMock(items=[]))}

            success, message = await manager.process_and_save_results(all_results, "test-cluster", {}, "immediate")

            assert success is False
            assert "Error processing inspection results" in message
            assert "Test error" in message

    def test_has_successful_results_with_tuple_format(self):
        """Test _has_successful_results with tuple format results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with successful tuple format results
        all_results = {
            "node": (True, MagicMock(items=[MagicMock(status="ok")])),
            "opa": (True, MagicMock(items=[MagicMock(status="error")])),
        }

        result = manager._has_successful_results(all_results)
        assert result is True

        # Test with all error tuple format results
        all_results = {
            "node": (True, MagicMock(items=[MagicMock(status="error")])),
            "opa": (True, MagicMock(items=[MagicMock(status="error")])),
        }

        result = manager._has_successful_results(all_results)
        assert result is False

    def test_has_successful_results_with_object_format(self):
        """Test _has_successful_results with object format results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with successful object format results
        all_results = {
            "node": MagicMock(items=[MagicMock(status="ok")]),
            "opa": MagicMock(items=[MagicMock(status="error")]),
        }

        result = manager._has_successful_results(all_results)
        assert result is True

        # Test with all error object format results
        all_results = {
            "node": MagicMock(items=[MagicMock(status="error")]),
            "opa": MagicMock(items=[MagicMock(status="error")]),
        }

        result = manager._has_successful_results(all_results)
        assert result is False

    def test_has_successful_results_with_dict_items(self):
        """Test _has_successful_results with dict items"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with dict items
        all_results = {
            "node": (True, MagicMock(items=[{"status": "ok"}])),
            "opa": (True, MagicMock(items=[{"status": "error"}])),
        }

        result = manager._has_successful_results(all_results)
        assert result is True

        # Test with all error dict items
        all_results = {
            "node": (True, MagicMock(items=[{"status": "error"}])),
            "opa": (True, MagicMock(items=[{"status": "error"}])),
        }

        result = manager._has_successful_results(all_results)
        assert result is False

    def test_has_successful_results_with_none_results(self):
        """Test _has_successful_results with None results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with None results
        all_results = {"node": None, "opa": None}

        result = manager._has_successful_results(all_results)
        assert result is False

    @pytest.mark.asyncio
    async def test_save_inspection_results(self):
        """Test _save_inspection_results method"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager(use_gitops=False)

        # Mock dependencies
        with patch(
            "services.components.inspection_config_manager.InspectionConfigManager"
        ) as mock_config_manager, patch(
            "services.components.inspection_coordinator.InspectionController"
        ) as mock_controller:

            # Setup mocks
            mock_config_manager.get_config_dict.return_value = {"test": "config"}
            mock_controller_instance = AsyncMock()
            mock_controller_instance.save_inspection_result.return_value = "/path/to/results.json"
            mock_controller.return_value = mock_controller_instance

            # Call the method
            result_path = await manager._save_inspection_results(
                {"test": "data"}, "test-cluster", {"test": "config"}, "immediate"
            )

            # Verify
            assert result_path == "/app/data/results/inspection_result_test-cluster_20251218_054417.json"
            mock_config_manager.get_config_dict.assert_called_once_with({"test": "config"})
            mock_controller.assert_called_once_with({"test": "config"}, use_gitops=False)
            mock_controller_instance.save_inspection_result.assert_called_once_with(
                {"test": "data"}, "test-cluster", "immediate"
            )

    def test_get_results_summary(self):
        """Test get_results_summary method"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with tuple format results
        all_results = {
            "node": (
                True,
                MagicMock(items=[MagicMock(status="ok", severity="info"), MagicMock(status="error", severity="error")]),
            ),
            "opa": (True, MagicMock(items=[MagicMock(status="ok", severity="warning")])),
            "prometheus": None,  # Test with None result
        }

        summary = manager.get_results_summary(all_results)

        assert summary["total_inspections"] == 2  # Excluding None
        assert summary["successful_inspections"] == 1  # Only opa has no error items
        assert summary["failed_inspections"] == 1  # node has error items
        assert summary["total_items"] == 3
        assert summary["error_items"] == 1
        assert summary["warning_items"] == 1
        assert summary["info_items"] == 1
        assert "node" in summary["inspection_types"]
        assert "opa" in summary["inspection_types"]
        assert "prometheus" in summary["inspection_types"]

    def test_get_results_summary_with_object_format(self):
        """Test get_results_summary with object format results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with object format results
        all_results = {
            "node": MagicMock(
                items=[MagicMock(status="ok", severity="info"), MagicMock(status="error", severity="error")]
            ),
            "opa": MagicMock(items=[MagicMock(status="ok", severity="warning")]),
        }

        summary = manager.get_results_summary(all_results)

        assert summary["total_inspections"] == 2
        assert summary["successful_inspections"] == 1  # Only opa has no error items
        assert summary["failed_inspections"] == 1  # node has error items
        assert summary["total_items"] == 3
        assert summary["error_items"] == 1
        assert summary["warning_items"] == 1
        assert summary["info_items"] == 1

    def test_get_results_summary_with_dict_items(self):
        """Test get_results_summary with dict items"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with dict items
        all_results = {
            "node": (
                True,
                MagicMock(items=[{"status": "ok", "severity": "info"}, {"status": "error", "severity": "error"}]),
            ),
            "opa": (True, MagicMock(items=[{"status": "ok", "severity": "warning"}])),
        }

        summary = manager.get_results_summary(all_results)

        assert summary["total_inspections"] == 2
        assert summary["successful_inspections"] == 1  # Only opa has no error items
        assert summary["failed_inspections"] == 1  # node has error items
        assert summary["total_items"] == 3
        assert summary["error_items"] == 1
        assert summary["warning_items"] == 1
        assert summary["info_items"] == 1

    def test_get_results_summary_empty_results(self):
        """Test get_results_summary with empty results"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager()

        # Test with empty results
        all_results = {}

        summary = manager.get_results_summary(all_results)

        assert summary["total_inspections"] == 0
        assert summary["successful_inspections"] == 0
        assert summary["failed_inspections"] == 0
        assert summary["total_items"] == 0
        assert summary["error_items"] == 0
        assert summary["warning_items"] == 0
        assert summary["info_items"] == 0
        assert summary["inspection_types"] == []
