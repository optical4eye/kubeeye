#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection result manager - handles result processing and saving
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from services.inspectors.controller import InspectionController

logger = logging.getLogger(__name__)


class InspectionResultManager:
    """Manages inspection results processing and saving"""

    def __init__(self, use_gitops: bool = False):
        self.use_gitops = use_gitops

    async def process_and_save_results(
        self, all_results: Dict[str, Any], cluster_name: str, cluster_config: Any, inspection_type: str = "immediate"
    ) -> tuple[bool, str]:
        """
        Process inspection results and save them

        Args:
            all_results: dictionary with results from all inspection types
            cluster_name: name of the cluster
            cluster_config: cluster configuration object
            inspection_type: type of inspection (immediate/scheduled)

        Returns:
            (success, message) tuple
        """
        try:
            # Check if we have any successful results
            has_successful_results = self._has_successful_results(all_results)

            # Save results
            result_path = await self._save_inspection_results(all_results, cluster_name, cluster_config, inspection_type)

            if has_successful_results:
                return True, f"Inspection completed successfully, results saved: {result_path}"
            else:
                return True, f"Inspection completed with errors, results saved: {result_path}"

        except Exception as e:
            error_msg = f"Error processing inspection results: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _has_successful_results(self, all_results: Dict[str, Any]) -> bool:
        """
        Check if any inspection results are successful

        Args:
            all_results: dictionary with results from all inspection types

        Returns:
            True if any successful results found
        """
        logger.debug(f"Checking for successful results in: {list(all_results.keys())}")

        for key, result in all_results.items():
            # Handle different result formats
            if isinstance(result, tuple) and len(result) >= 2:
                # Result is in format (success, result_object)
                success, result_obj = result
                if success and result_obj and hasattr(result_obj, "items"):
                    # Check if any item is not an error
                    items = result_obj.items
                    successful_items = []
                    for item in items:
                        item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, "__dict__") else {}
                        if item_dict.get("status") != "error":
                            successful_items.append(item)
                    if successful_items:
                        logger.debug(f"Found {len(successful_items)} successful items in {key} results")
                        return True
            elif result and not isinstance(result, tuple) and hasattr(result, "items"):
                # Check if any item is not an error
                items = result.items
                successful_items = []
                for item in items:
                    item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, "__dict__") else {}
                    if item_dict.get("status") != "error":
                        successful_items.append(item)
                if successful_items:
                    logger.debug(f"Found {len(successful_items)} successful items in {key} results")
                    return True
            elif result is not None:
                # Result exists but might not have items attribute
                logger.debug(f"Result {key} exists but doesn't have items attribute")

        return False

    async def _save_inspection_results(
        self,
        all_results: Dict,
        cluster_name: str,
        cluster_config: Any,
        inspection_type: str,
    ) -> str:
        """
        Save inspection results using InspectionController

        Returns:
            Path to saved results
        """
        from services.components.inspection_config_manager import InspectionConfigManager

        config_dict = InspectionConfigManager.get_config_dict(cluster_config)
        controller = InspectionController(config_dict, use_gitops=self.use_gitops)
        result_path = await controller.save_inspection_result(all_results, cluster_name, inspection_type)
        return result_path

    def get_results_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of inspection results

        Args:
            all_results: dictionary with results from all inspection types

        Returns:
            Summary dictionary with statistics
        """
        summary = {
            "total_inspections": 0,
            "successful_inspections": 0,
            "failed_inspections": 0,
            "total_items": 0,
            "error_items": 0,
            "warning_items": 0,
            "info_items": 0,
            "inspection_types": list(all_results.keys()),
        }

        for inspection_type, result in all_results.items():
            if result is None:
                continue

            summary["total_inspections"] += 1

            # Handle tuple format (success, result_object) from InspectionCoordinator
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "items"):
                    items = result_obj.items
                else:
                    items = []
            elif not isinstance(result, tuple) and hasattr(result, "items"):
                items = result.items
            else:
                items = []

            summary["total_items"] += len(items)

            # Count items by severity
            for item in items:
                item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, "__dict__") else {}
                status = item_dict.get("status", "unknown")
                severity = item_dict.get("severity", "info")

                if status == "error":
                    summary["error_items"] += 1
                elif severity == "warning":
                    summary["warning_items"] += 1
                elif severity == "info":
                    summary["info_items"] += 1

            # Check if inspection was successful
            error_items = []
            for item in items:
                item_dict = item if isinstance(item, dict) else item.__dict__ if hasattr(item, "__dict__") else {}
                if item_dict.get("status") == "error":
                    error_items.append(item)
            if not error_items:
                summary["successful_inspections"] += 1
            else:
                summary["failed_inspections"] += 1

        return summary
