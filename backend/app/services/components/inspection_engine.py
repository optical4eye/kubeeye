#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified inspection execution engine вЂ” core logic without UI dependencies
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple

from core.logging import log_execution_time
from infra.dependency_injection.container import injectable, inject
from services.components.inspection_coordinator import InspectionCoordinator
from services.components.gitops_sync_manager import GitOpsSyncManager
from services.components.inspection_config_manager import InspectionConfigManager
from services.components.inspection_result_manager import InspectionResultManager
from core.logging import get_logger

logger = get_logger(__name__)


@injectable()
class InspectionEngine:
    """Unified inspection execution engine - refactored with separated concerns"""

    def __init__(self, gitops_manager: GitOpsSyncManager = None):
        self.progress = None
        self.gitops_manager = gitops_manager or GitOpsSyncManager()

    @log_execution_time
    async def execute_inspection(
        self,
        cluster_name: str,
        selected_rules: Optional[Dict[str, List[str]]] = None,
        selected_tags: Optional[Dict[str, List[str]]] = None,
        inspection_type: str = "immediate",
        show_progress: bool = False,
        show_ui_feedback: bool = False,
        use_gitops: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute universal inspection using refactored components

        Args:
            cluster_name: cluster name
            selected_rules: selected rules {"node": [...], "opa": [...]}
            inspection_type: inspection type ("immediate" or "scheduled")
            show_progress: whether to show progress bar
            show_ui_feedback: whether to show UI feedback
            use_gitops: whether to use GitOps rules

        Returns:
            (success, message, results)
        """
        from core.logging import ErrorBoundary

        with ErrorBoundary("inspection_execution", logger) as eb:
            logger.info("Starting inspection execution")
            # Step 1: Sync GitOps if needed
            gitops_success, gitops_message = await self.gitops_manager.sync_if_needed(use_gitops, show_progress)
            logger.info(f"GitOps sync result: success={gitops_success}, message={gitops_message}")
            if not gitops_success:
                logger.warning(f"GitOps sync failed: {gitops_message}")

            # Step 2: Get and validate cluster configuration
            logger.info("Getting cluster configuration")
            config_manager = InspectionConfigManager()
            with ErrorBoundary("cluster_configuration", logger) as config_eb:
                result = await config_manager.get_cluster_configuration(cluster_name, show_progress)
                cluster_config, config_error = result
                if not cluster_config:
                    return False, config_error or "Configuration error", None

            # Step 3: Extract cluster components
            logger.info("Extracting cluster components")
            components = await config_manager.extract_cluster_components(cluster_config)

            # Step 4: Validate inspection feasibility
            logger.info("Validating inspection feasibility")
            can_proceed, validation_error, inspection_decisions = config_manager.validate_inspection_feasibility(
                components, selected_rules
            )
            if not can_proceed:
                return False, validation_error, None

            # Step 5: Execute inspections
            logger.info("Executing inspections via coordinator")
            coordinator = InspectionCoordinator(use_gitops=use_gitops)
            with ErrorBoundary("inspection_coordination", logger) as coord_eb:
                all_results = await coordinator.execute_inspections(
                    cluster_name=cluster_name,
                    nodes=components["nodes"],
                    kubeconfig=components["kubeconfig"],
                    selected_rules=selected_rules,
                    selected_tags=selected_tags,
                    show_progress=show_progress,
                )

            # Step 6: Process and save results
            logger.info("Processing and saving results")
            result_manager = InspectionResultManager(use_gitops=use_gitops)
            with ErrorBoundary("result_processing", logger) as result_eb:
                success, message = await result_manager.process_and_save_results(
                    all_results, cluster_name, cluster_config, inspection_type
                )

            # Publish inspection completed event
            from core.events import publish_inspection_completed

            # Serialize results for event
            results_serializable = {}
            if all_results:
                for inspector_name, inspection_result in all_results.items():
                    if hasattr(inspection_result, "get_summary"):
                        results_serializable[inspector_name] = inspection_result.get_summary()
                    elif hasattr(inspection_result, "to_dict"):
                        results_serializable[inspector_name] = inspection_result.to_dict()
                    else:
                        results_serializable[inspector_name] = str(inspection_result)
            await publish_inspection_completed(cluster_name, results_serializable)

            return success, message, all_results


inspection_engine = InspectionEngine()


async def execute_inspection_unified(
    cluster_name: str,
    selected_rules: Optional[Dict[str, List[str]]] = None,
    selected_tags: Optional[Dict[str, List[str]]] = None,
    inspection_type: str = "immediate",
    show_progress: bool = False,
    show_ui_feedback: bool = False,
    use_gitops: bool = False,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Unified inspection launch interface for all components"""
    return await inspection_engine.execute_inspection(
        cluster_name,
        selected_rules,
        selected_tags,
        inspection_type,
        show_progress,
        show_ui_feedback,
        use_gitops,
    )
