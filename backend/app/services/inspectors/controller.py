#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection controller, responsible for planning and coordinating different types of inspections
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from services.inspectors.inspector_registry import inspector_registry
from infrastructure.results.inspection_result import InspectionResult

# Logging setup
logger = logging.getLogger(__name__)


class InspectionController:
    """Inspection controller, responsible for coordinating the inspection process"""

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Initialize inspection controller

        Args:
            config: controller configuration
            use_gitops: whether to use GitOps rules
        """
        self.config = config
        self.use_gitops = use_gitops
        self.inspectors = {}
        self._initialize_inspectors()

    def _initialize_inspectors(self):
        """Initialize all inspectors using registry"""
        # Output configuration information for debugging
        logger.info(f"Controller configuration: {list(self.config.keys())}")
        logger.info(f"GitOps mode: {self.use_gitops}")

        # Use registry to create inspectors dynamically
        self.inspectors = inspector_registry.create_inspectors(self.config, self.use_gitops)

        logger.info(f"Initialized {len(self.inspectors)} inspectors: {list(self.inspectors.keys())}")

    def get_available_inspectors(self) -> List[str]:
        """
        Get available inspector types

        Returns:
            List of inspector types
        """
        return list(self.inspectors.keys())

    async def run_inspection(
        self,
        cluster_name: str,
        inspector_types: Optional[List[str]] = None,
        rule_ids: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute inspection

        Args:
            cluster_name: cluster name
            inspector_types: list of inspector types to execute, if None, execute all inspectors
            rule_ids: dictionary of rule IDs for each inspector, format {inspector_type: [rule_id1, rule_id2]}

        Returns:
            Dictionary of inspection results, format {inspector_type: inspection_result}
        """
        results = {}

        # Determine inspectors to execute
        if inspector_types:
            active_inspectors = {k: v for k, v in self.inspectors.items() if k in inspector_types}
        else:
            active_inspectors = self.inspectors

        if not active_inspectors:
            logger.warning("No available inspectors")
            return results

        # Execute inspection
        for inspector_type, inspector in active_inspectors.items():
            try:
                # Get rule IDs for this inspector
                inspector_rule_ids = None
                if rule_ids and inspector_type in rule_ids:
                    inspector_rule_ids = rule_ids[inspector_type]

                logger.info(f"Executing {inspector_type} inspection...")
                result = await inspector.run_inspection(cluster_name, inspector_rule_ids or [])
                results[inspector_type] = result
                if hasattr(result, "items"):
                    logger.info(f"{inspector_type} inspection completed, found {len(result.items)} results")
                else:
                    logger.info(f"{inspector_type} inspection completed")

            except Exception as e:
                logger.exception(f"Error executing {inspector_type} inspection: {str(e)}")

        return results

    def _calculate_statistics(self, all_results: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
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
                if hasattr(result_obj, "items"):
                    items = result_obj.items
                else:
                    items = []
            elif hasattr(result, "items"):
                items = result.items
            else:
                items = []

            total_items += len(items)
            for item in items:
                status = self._get_item_status(item)
                severity = self._get_item_severity(item)

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

    def _get_item_status(self, item) -> str:
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

    def _get_item_severity(self, item) -> str:
        """Safely get item severity"""
        if hasattr(item, "__dict__"):
            return getattr(item, "severity", "unknown")
        elif isinstance(item, dict):
            return item.get("severity", "unknown")
        return "unknown"

    def _serialize_inspection_results(self, all_results: Dict[str, Any]) -> Dict[str, Dict]:
        """Serialize inspection results efficiently"""
        serialized_results = {}

        for inspector_type, result in all_results.items():
            # Handle tuple format (success, result_object) from InspectionCoordinator
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "items"):
                    items = result_obj.items
                else:
                    items = []
            elif hasattr(result, "items"):
                items = result.items
            else:
                items = []

            serialized_items = []
            for item in items:
                item_dict = self._convert_item_to_dict(item)
                # Normalize status
                if item_dict.get("status") in ["failed", "warning", "error"]:
                    item_dict["status"] = "exception"
                serialized_items.append(item_dict)

            serialized_results[inspector_type] = {
                "inspector_type": inspector_type,
                "items": serialized_items,
            }

        return serialized_results

    def _convert_item_to_dict(self, item) -> Dict:
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

    async def save_inspection_result(
        self,
        all_results: Dict[str, Any],
        cluster_name: str,
        inspection_type: str = "immediate",
    ) -> str:
        """
        Save inspection results to file

        Args:
            all_results: dictionary of inspection results
            cluster_name: cluster name
            inspection_type: inspection type ('immediate' or 'scheduled')

        Returns:
            Path to saved file
        """
        import json
        from datetime import datetime

        # Ensure results directory exists
        from infrastructure.results.inspection_result import RESULTS_DIR

        results_dir = RESULTS_DIR
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate result ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_id = f"{inspection_type}_{timestamp}"
        filename = f"inspection_result_{cluster_name}_{timestamp}.json"
        result_path = results_dir / filename

        # Calculate statistics efficiently
        total_items, total_passed, total_failed, total_warning, total_error = self._calculate_statistics(all_results)

        # Serialize inspection results
        serialized_results = self._serialize_inspection_results(all_results)

        # Build complete result structure
        result_data = {
            "result_id": result_id,
            "cluster_name": cluster_name,
            "timestamp": datetime.now().isoformat(),
            "inspection_type": inspection_type,
            "execution_info": {
                "triggered_by": ("user" if inspection_type == "immediate" else "scheduler"),
                "inspectors_used": list(all_results.keys()),
                "execution_duration": "N/A",
            },
            "inspection_results": serialized_results,
            "summary": {
                "total_items": total_items,
                "passed": total_passed,
                "failed": total_failed,
                "warning": total_warning,
                "error": total_error,
            },
            # Compatibility with old fields
            "critical": total_failed,
            "warning": total_warning,
            "passed": total_passed,
        }

        # Save to file
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        # Start data cleanup
        try:
            from infrastructure.common.data_cleanup import get_cleanup_manager

            cleanup_manager = get_cleanup_manager()
            cleanup_manager.cleanup_inspection_results()
        except Exception as e:
            logger.warning(f"Error cleaning up old reports: {e}")

        logger.info(f"Inspection results saved to: {result_path}")
        return str(result_path)
