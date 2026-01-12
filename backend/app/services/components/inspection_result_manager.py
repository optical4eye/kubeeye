#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core.logging import get_logger

"""
Inspection result manager - handles result processing and saving
"""

import asyncio
from typing import Dict, Any, Optional, Tuple

from services.inspectors.controller import InspectionController
from infra.results.result_processor import ResultProcessor

logger = get_logger(__name__)


class InspectionResultManager:
    """Manages inspection results processing and saving"""

    def __init__(self, use_gitops: bool = False):
        self.use_gitops = use_gitops

    async def process_and_save_results(
        self, all_results: Dict[str, Any], cluster_name: str, cluster_config: Any, inspection_type: str = "immediate"
    ) -> Tuple[bool, str]:
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
            has_successful_results = ResultProcessor.has_successful_results(all_results)

            # Save results
            result_path = await self._save_inspection_results(
                all_results, cluster_name, cluster_config, inspection_type
            )

            if has_successful_results:
                return True, f"Inspection completed successfully, results saved: {result_path}"
            else:
                return True, f"Inspection completed with errors, results saved: {result_path}"

        except Exception as e:
            error_msg = f"Error processing inspection results: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def _save_inspection_results(
        self,
        all_results: Dict,
        cluster_name: str,
        cluster_config: Any,
        inspection_type: str,
    ) -> str | None:
        """
        Save inspection results using InspectionController

        Returns:
            Path to saved results
        """
        from services.components.inspection_config_manager import InspectionConfigManager

        # Get config dict - handle both sync and async cases
        try:
            config_dict = await InspectionConfigManager.get_config_dict(cluster_config)
        except Exception as e:
            logger.error(f"Error getting config dict: {str(e)}")
            # Fallback to empty config
            config_dict = {"nodes": [], "opa": {"kubeconfig": ""}}

        controller = InspectionController(config_dict, use_gitops=self.use_gitops)
        result_path = await controller.save_inspection_result(all_results, cluster_name, inspection_type)
        return result_path
