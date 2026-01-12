#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection controller, responsible for planning and coordinating different types of inspections
"""

import asyncio
from typing import Dict, List, Any, Tuple, Optional

from services.inspectors.inspector_registry import inspector_registry
from infra.results.inspection_result import InspectionResult
from infra.results.result_processor import ResultProcessor
from core.logging import get_logger

# Logging setup
logger = get_logger(__name__)


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
        return ResultProcessor.calculate_statistics(all_results)

    def _serialize_inspection_results(self, all_results: Dict[str, Any]) -> Dict[str, Dict]:
        """Serialize inspection results efficiently"""
        return ResultProcessor.serialize_inspection_results(all_results)

    async def save_inspection_result(
        self,
        all_results: Dict[str, Any],
        cluster_name: str,
        inspection_type: str = "immediate",
    ) -> str | None:
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

        # Results are now stored in PostgreSQL, no need to create results directory
        logger.info(f"Saving inspection results to database for cluster {cluster_name}, type {inspection_type}")
        pass

        # Save to database using InspectionResult
        from infra.results.inspection_result import InspectionResult

        inspection_result = InspectionResult(cluster_name, inspection_type)

        # Add all items to result
        # Handle case where results might contain coroutines
        processed_results = {}
        for inspector_type, result in all_results.items():
            # Check if result is a coroutine and await it
            if hasattr(result, "__await__") or asyncio.iscoroutine(result):
                try:
                    logger.info(f"Awaiting coroutine result for {inspector_type}")
                    processed_results[inspector_type] = await result
                except Exception as e:
                    logger.error(f"Error awaiting result for {inspector_type}: {str(e)}")
                    processed_results[inspector_type] = result
            else:
                processed_results[inspector_type] = result

        # Use processed results
        for inspector_type, result in processed_results.items():
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

            # Add each item to inspection result
            for item in items:
                inspection_result.add_item(item)

        # Save to database
        result_id = await inspection_result.save()

        logger.info(f"Inspection results saved to database with ID: {result_id}")
        return result_id
