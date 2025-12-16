#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified inspection execution engine — core logic without UI dependencies
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple

from infrastructure.cluster.cluster_config import get_cluster
from infrastructure.results.inspection_result import InspectionResult
from infrastructure.logging.enhanced_logging import ErrorBoundary, log_execution_time
from services.inspectors.node.node_inspector import NodeInspector
from services.inspectors.prometheus.prometheus_inspector import PrometheusInspector
from services.inspectors.opa.opa_inspector import OpaInspector
from services.inspectors.controller import InspectionController

logger = logging.getLogger(__name__)


class InspectionEngine:
    """Unified inspection execution engine"""

    def __init__(self):
        self.progress = None

    @log_execution_time
    def execute_inspection(
        self,
        cluster_name: str,
        selected_rules: Optional[Dict[str, List[str]]] = None,
        inspection_type: str = "immediate",
        show_progress: bool = False,
        show_ui_feedback: bool = False,
        use_gitops: bool = False,  # Add parameter to determine rules source
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute universal inspection

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
        self.use_gitops = use_gitops  # Save rules source information

        # If GitOps mode, ensure repository is synchronized
        if self.use_gitops:
            from infrastructure.gitops.gitops_manager import GitOpsRuleManager

            gitops_manager = GitOpsRuleManager()
            config = gitops_manager.load_config()
            current_repo = config.get("repository")

            if current_repo:
                if show_progress:
                    logger.info(f"Syncing GitOps repository {current_repo['name']}...")
                success, message = gitops_manager.clone_or_update_repo(current_repo)
                if success:
                    logger.info(f"GitOps repository synchronized: {message}")
                else:
                    logger.warning(f"Failed to sync GitOps repository: {message}")
                    # Keep GitOps mode, assume rules are already available

        try:
            if show_progress:
                logger.info("Getting cluster configuration...")

            cluster_config = get_cluster(cluster_name)
            if not cluster_config:
                error_msg = f"Cluster configuration not found: {cluster_name}"
                return False, error_msg, None

            nodes = (
                cluster_config.get_nodes()
                if hasattr(cluster_config, "get_nodes")
                else []
            )
            prometheus_config = (
                cluster_config.get_prometheus_config()
                if hasattr(cluster_config, "get_prometheus_config")
                else {}
            )
            kubeconfig = (
                cluster_config.get_kubeconfig()
                if hasattr(cluster_config, "get_kubeconfig")
                else ""
            )

            run_node_check = bool(nodes) and (
                selected_rules and selected_rules.get("node")
            )
            run_prometheus_check = bool(
                prometheus_config and prometheus_config.get("enabled", False)
            ) and (selected_rules and selected_rules.get("prometheus"))
            run_opa_check = bool(kubeconfig) and (
                selected_rules and selected_rules.get("opa")
            )

            logger.info(
                f"Inspection types check - node count: {len(nodes)}, Prometheus enabled: {prometheus_config.get('enabled', False) if prometheus_config else False}, kubeconfig: {'present' if kubeconfig else 'absent'}"
            )
            logger.info(f"Selected rules: {selected_rules}")
            logger.info(
                f"Inspection decisions - nodes: {run_node_check}, Prometheus: {run_prometheus_check}, OPA: {run_opa_check}"
            )
            logger.info(f"GitOps mode: {use_gitops}")

            if not (run_node_check or run_prometheus_check or run_opa_check):
                error_msg = "No available inspection types. Check cluster configuration and rule selection."
                return False, error_msg, None

            all_results = {}

            if run_node_check:
                success, result = self._execute_node_inspection(
                    cluster_name, nodes, selected_rules["node"], show_progress
                )
                if success:
                    all_results["node"] = result
                else:
                    logger.warning(f"Node inspection failed: {result}")
                    # Create error result for failed inspection
                    error_result = InspectionResult(cluster_name, "node")
                    error_result.add_item(
                        {
                            "name": "Node inspection failed",
                            "status": "error",
                            "description": f"Node inspection could not be completed: {result}",
                            "severity": "critical",
                            "details": str(result),
                            "solution": "Check cluster node connectivity and configuration",
                        }
                    )
                    all_results["node"] = error_result

            if run_prometheus_check:
                success, result = self._execute_prometheus_inspection(
                    cluster_name,
                    prometheus_config,
                    selected_rules["prometheus"],
                    show_progress,
                )
                if success:
                    all_results["prometheus"] = result
                else:
                    logger.warning(f"Prometheus inspection failed: {result}")
                    # Create error result for failed inspection
                    error_result = InspectionResult(cluster_name, "prometheus")
                    error_result.add_item(
                        {
                            "name": "Prometheus inspection failed",
                            "status": "error",
                            "description": f"Prometheus inspection could not be completed: {result}",
                            "severity": "critical",
                            "details": str(result),
                            "solution": "Check Prometheus server connectivity and configuration",
                        }
                    )
                    all_results["prometheus"] = error_result

            if run_opa_check:
                success, result = self._execute_opa_inspection(
                    cluster_name, kubeconfig, selected_rules["opa"], show_progress
                )
                if success:
                    all_results["opa"] = result
                else:
                    logger.warning(f"OPA inspection failed: {result}")
                    # Create error result for failed inspection
                    error_result = InspectionResult(cluster_name, "opa")
                    error_result.add_item(
                        {
                            "name": "OPA inspection failed",
                            "status": "error",
                            "description": f"OPA inspection could not be completed: {result}",
                            "severity": "critical",
                            "details": str(result),
                            "solution": "Check Kubernetes API connectivity and kubeconfig",
                        }
                    )
                    all_results["opa"] = error_result

            if all_results:
                result_path = self._save_inspection_results(
                    all_results, cluster_name, cluster_config, inspection_type
                )
                # Check if we have any successful results (not just error results)
                has_successful_results = any(
                    result
                    and hasattr(result, "items")
                    and any(item.get("status") != "error" for item in result.items)
                    for result in all_results.values()
                    if result is not None
                )

                if has_successful_results:
                    return (
                        True,
                        f"Inspection completed successfully, results saved: {result_path}",
                        all_results,
                    )
                else:
                    return (
                        True,
                        f"Inspection completed with errors, results saved: {result_path}",
                        all_results,
                    )
            else:
                error_msg = "No inspection types were configured to run."
                return False, error_msg, None
        except Exception as e:
            error_msg = f"Inspection execution error: {str(e)}"
            return False, error_msg, None

    def _execute_node_inspection(
        self,
        cluster_name: str,
        nodes: List[Dict],
        selected_rules: List[str],
        show_progress: bool,
    ) -> Tuple[bool, Any]:
        """Execute node inspection"""
        try:
            node_inspector = NodeInspector(nodes, use_gitops=self.use_gitops)

            if show_progress:
                logger.info("Executing node inspection...")
            result = node_inspector.run_inspection(cluster_name, selected_rules)
            if show_progress:
                logger.info("Node inspection completed")
            return True, result
        except Exception as e:
            logger.error(f"Node inspection error: {e}")
            return False, str(e)

    def _execute_prometheus_inspection(
        self,
        cluster_name: str,
        prometheus_config: Dict,
        selected_rules: List[str],
        show_progress: bool,
    ) -> Tuple[bool, Any]:
        """Execute Prometheus inspection"""
        try:
            if prometheus_config and prometheus_config.get("enabled", False):
                prometheus_inspector = PrometheusInspector(
                    prometheus_config, use_gitops=self.use_gitops
                )
                if show_progress:
                    logger.info("Executing Prometheus metrics inspection...")
                result = prometheus_inspector.run_inspection(
                    cluster_name, selected_rules
                )
                if show_progress:
                    logger.info("Prometheus metrics inspection completed")
                return True, result
            else:
                if show_progress:
                    logger.info("Prometheus inspection skipped (no configuration)")
                return True, None
        except Exception as e:
            logger.error(f"Prometheus metrics inspection error: {e}")
            return False, str(e)

    def _execute_opa_inspection(
        self,
        cluster_name: str,
        kubeconfig: str,
        selected_rules: List[str],
        show_progress: bool,
    ) -> Tuple[bool, Any]:
        """Execute OPA inspection"""
        try:
            if kubeconfig:
                opa_config = {
                    "kubeconfig": kubeconfig,
                    "opa_path": "/usr/local/bin/opa",
                }
                opa_inspector = OpaInspector(opa_config, use_gitops=self.use_gitops)
                if show_progress:
                    logger.info("Executing OPA compliance inspection...")
                result = opa_inspector.run_inspection(cluster_name, selected_rules)
                if show_progress:
                    logger.info("OPA compliance inspection completed")
                return True, result
            else:
                if show_progress:
                    logger.info("OPA compliance inspection skipped (no configuration)")
                return True, None
        except Exception as e:
            logger.error(f"OPA compliance inspection error: {e}")
            return False, str(e)

    def _save_inspection_results(
        self,
        all_results: Dict,
        cluster_name: str,
        cluster_config: Any,
        inspection_type: str,
    ) -> str:
        """Save inspection results"""
        try:
            if hasattr(cluster_config, "get_dict"):
                config_dict = cluster_config.get_dict()
            else:
                config_dict = {
                    "nodes": (
                        cluster_config.get_nodes()
                        if hasattr(cluster_config, "get_nodes")
                        else []
                    ),
                    "prometheus": (
                        cluster_config.get_prometheus_config()
                        if hasattr(cluster_config, "get_prometheus_config")
                        else {}
                    ),
                    "opa": {
                        "kubeconfig": (
                            cluster_config.get_kubeconfig()
                            if hasattr(cluster_config, "get_kubeconfig")
                            else ""
                        )
                    },
                }
        except Exception:
            config_dict = {"nodes": [], "prometheus": {}, "opa": {"kubeconfig": ""}}

        controller = InspectionController(config_dict, use_gitops=self.use_gitops)
        return controller.save_inspection_result(
            all_results, cluster_name, inspection_type
        )


inspection_engine = InspectionEngine()


def execute_inspection_unified(
    cluster_name: str,
    selected_rules: Optional[Dict[str, List[str]]] = None,
    inspection_type: str = "immediate",
    show_progress: bool = False,
    show_ui_feedback: bool = False,
    use_gitops: bool = False,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Unified inspection launch interface for all components"""
    return inspection_engine.execute_inspection(
        cluster_name,
        selected_rules,
        inspection_type,
        show_progress,
        show_ui_feedback,
        use_gitops,
    )
