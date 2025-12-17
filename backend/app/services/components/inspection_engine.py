#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified inspection execution engine — core logic without UI dependencies
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple

from infrastructure.logging.enhanced_logging import log_execution_time
from services.components.inspection_coordinator import InspectionCoordinator
from services.components.gitops_sync_manager import GitOpsSyncManager
from services.components.inspection_config_manager import InspectionConfigManager
from services.components.inspection_result_manager import InspectionResultManager

logger = logging.getLogger(__name__)


class InspectionEngine:
    """Unified inspection execution engine - refactored with separated concerns"""

    def __init__(self):
        self.progress = None
        self.gitops_manager = GitOpsSyncManager()

    @log_execution_time
    async def execute_inspection(
        self,
        cluster_name: str,
        selected_rules: Optional[Dict[str, List[str]]] = None,
        inspection_type: str = "immediate",
        show_progress: bool = False,
        show_ui_feedback: bool = False,
        use_gitops: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute universal inspection using refactored components

        Args:
            cluster_name: cluster name
            selected_rules: selected rules {"node": [...], "prometheus": [...], "opa": [...]}
            inspection_type: inspection type ("immediate" or "scheduled")
            show_progress: whether to show progress bar
            show_ui_feedback: whether to show UI feedback
            use_gitops: whether to use GitOps rules

        Returns:
            (success, message, results)
        """
        try:
            # Step 1: Sync GitOps if needed
            gitops_success, gitops_message = await self.gitops_manager.sync_if_needed(use_gitops, show_progress)
            if not gitops_success:
                logger.warning(f"GitOps sync failed: {gitops_message}")

            # Step 2: Get and validate cluster configuration
            cluster_config, config_error = await InspectionConfigManager.get_cluster_configuration(
                cluster_name, show_progress
            )
            if not cluster_config:
                return False, config_error, None

            # Step 3: Extract cluster components
            components = InspectionConfigManager.extract_cluster_components(cluster_config)

            # Step 4: Validate inspection feasibility
            can_proceed, validation_error, inspection_decisions = (
                InspectionConfigManager.validate_inspection_feasibility(components, selected_rules)
            )
            if not can_proceed:
                return False, validation_error, None

            # Step 5: Execute inspections
            coordinator = InspectionCoordinator(use_gitops=use_gitops)
            all_results = await coordinator.execute_inspections(
                cluster_name=cluster_name,
                nodes=components["nodes"],
                prometheus_config=components["prometheus_config"],
                kubeconfig=components["kubeconfig"],
                selected_rules=selected_rules or {},
                show_progress=show_progress,
            )

            # Step 6: Process and save results
            result_manager = InspectionResultManager(use_gitops=use_gitops)
            success, message = await result_manager.process_and_save_results(
                all_results, cluster_name, cluster_config, inspection_type
            )

            return success, message, all_results

        except Exception as e:
            error_msg = f"Inspection execution error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    # Removed individual inspection methods - now handled by InspectionCoordinator
    # Removed result saving method - now handled by InspectionResultManager


inspection_engine = InspectionEngine()


async def execute_inspection_unified(
    cluster_name: str,
    selected_rules: Optional[Dict[str, List[str]]] = None,
    inspection_type: str = "immediate",
    show_progress: bool = False,
    show_ui_feedback: bool = False,
    use_gitops: bool = False,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Unified inspection launch interface for all components"""
    return await inspection_engine.execute_inspection(
        cluster_name,
        selected_rules,
        inspection_type,
        show_progress,
        show_ui_feedback,
        use_gitops,
    )
