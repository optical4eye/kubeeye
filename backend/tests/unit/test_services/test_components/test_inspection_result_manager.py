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

    @pytest.mark.asyncio
    async def test_save_inspection_results(self):
        """Test _save_inspection_results method"""
        from services.components.inspection_result_manager import InspectionResultManager

        manager = InspectionResultManager(use_gitops=False)

        # Mock dependencies
        with patch(
            "services.components.inspection_config_manager.InspectionConfigManager"
        ) as mock_config_manager, patch(
            "services.components.inspection_result_manager.InspectionController"
        ) as mock_controller:

            # Setup mocks
            mock_config_manager.get_config_dict.return_value = {"test": "config"}
            mock_controller_instance = AsyncMock()
            mock_controller_instance.save_inspection_result.return_value = (
                "/app/data/results/inspection_result_test-cluster_20251218_120000.json"
            )
            mock_controller.return_value = mock_controller_instance

            # Call the method
            result_path = await manager._save_inspection_results(
                {"test": "data"}, "test-cluster", {"test": "config"}, "immediate"
            )

            # Verify
            # The timestamp will be different, so check the pattern
            assert result_path.startswith("/app/data/results/inspection_result_test-cluster_20251218_")
            assert result_path.endswith(".json")
            mock_config_manager.get_config_dict.assert_called_once_with({"test": "config"})
            # Check that controller was called at least once
            assert mock_controller_instance.save_inspection_result.called
