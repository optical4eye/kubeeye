#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Result Processor - centralized result processing and formatting utilities
"""

from typing import Dict, List, Any, Tuple, Optional
from core.logging import get_logger

logger = get_logger(__name__)


class ResultProcessor:
    """Centralized processor for inspection results"""

    @staticmethod
    def has_successful_results(all_results: Dict[str, Any]) -> bool:
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
                        item_dict = (
                            item if isinstance(item, dict) else item.__dict__ if hasattr(item, "__dict__") else {}
                        )
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

    @staticmethod
    def calculate_statistics(all_results: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
        """Calculate inspection statistics efficiently"""
        total_items = 0
        total_passed = 0
        total_failed = 0
        total_warning = 0
        total_error = 0

        for result in all_results.values():
            # Handle tuple format (success, result_object) from InspectionCoordinator
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "get_items"):
                    items = result_obj.get_items()
                elif hasattr(result_obj, "items"):
                    items = result_obj.items
                else:
                    items = []
            elif not isinstance(result, tuple):
                # Only check for methods if result is not a tuple
                if hasattr(result, "get_items"):
                    items = result.get_items()
                elif hasattr(result, "items"):
                    items = result.items
                else:
                    items = []
            else:
                items = []

            total_items += len(items)
            for item in items:
                status = ResultProcessor._get_item_status(item)
                severity = ResultProcessor._get_item_severity(item)

                if status == "passed":
                    total_passed += 1
                elif status == "exception":
                    if severity == "critical":
                        total_failed += 1
                    elif severity == "warning":
                        total_warning += 1
                    else:
                        total_error += 1
                else:
                    total_error += 1

        return total_items, total_passed, total_failed, total_warning, total_error

    @staticmethod
    def serialize_inspection_results(all_results: Dict[str, Any]) -> Dict[str, Dict]:
        """Serialize inspection results efficiently"""
        serialized_results = {}

        for inspector_type, result in all_results.items():
            # Handle tuple format (success, result_object) from InspectionCoordinator
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "get_items"):
                    items = result_obj.get_items()
                elif hasattr(result_obj, "items"):
                    items = result_obj.items
                else:
                    items = []
            elif not isinstance(result, tuple):
                # Only check for methods if result is not a tuple
                if hasattr(result, "get_items"):
                    items = result.get_items()
                elif hasattr(result, "items"):
                    items = result.items
                else:
                    items = []
            else:
                items = []

            serialized_items = []
            for item in items:
                item_dict = ResultProcessor._convert_item_to_dict(item)
                # Normalize status
                if item_dict.get("status") in ["failed", "warning", "error"]:
                    item_dict["status"] = "exception"
                serialized_items.append(item_dict)

            serialized_results[inspector_type] = {
                "inspector_type": inspector_type,
                "items": serialized_items,
            }

        return serialized_results

    @staticmethod
    def get_results_summary(all_results: Dict[str, Any]) -> Dict[str, Any]:
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

    @staticmethod
    def _get_item_status(item) -> str:
        """Safely get item status"""
        if hasattr(item, "__dict__"):
            status = getattr(item, "status", "unknown")
        elif isinstance(item, dict):
            status = item.get("status", "unknown")
        elif isinstance(item, (tuple, list)) and len(item) > 1:
            status = str(item[1])
        else:
            status = "unknown"

        # Normalize status
        if status in ["failed", "warning", "error"]:
            status = "exception"
        return status

    @staticmethod
    def _get_item_severity(item) -> str:
        """Safely get item severity"""
        if hasattr(item, "__dict__"):
            return getattr(item, "severity", "unknown")
        elif isinstance(item, dict):
            return item.get("severity", "unknown")
        return "unknown"

    @staticmethod
    def _convert_item_to_dict(item) -> Dict:
        """Convert inspection item to dictionary format"""
        if hasattr(item, "__dict__"):
            return item.__dict__.copy()
        elif isinstance(item, dict):
            return item.copy()
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            return {
                "name": str(item[0]) if len(item) > 0 else "Unknown",
                "status": str(item[1]) if len(item) > 1 else "unknown",
                "description": str(item[2]) if len(item) > 2 else "",
                "severity": "info",
                "details": str(item),
                "solution": "",
            }
        else:
            return {
                "name": str(item),
                "status": "unknown",
                "description": f"Converted from {type(item).__name__}",
                "severity": "info",
                "details": str(item),
                "solution": "",
            }
