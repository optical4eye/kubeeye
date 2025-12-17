#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection coordinator - manages execution of different inspection types
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple

from infrastructure.results.inspection_result import InspectionResult
from services.inspectors.node.node_inspector import NodeInspector
from services.inspectors.prometheus.prometheus_inspector import PrometheusInspector
from services.inspectors.opa.opa_inspector import OpaInspector

logger = logging.getLogger(__name__)


class InspectionCoordinator:
    """Coordinates execution of different inspection types"""

    def __init__(self, use_gitops: bool = False):
        self.use_gitops = use_gitops

    async def execute_inspections(
        self,
        cluster_name: str,
        nodes: List[Dict],
        prometheus_config: Dict,
        kubeconfig: str,
        selected_rules: Dict[str, List[str]],
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute all configured inspections

        Returns:
            Dictionary with results for each inspection type
        """
        all_results = {}

        # Determine which inspections to run
        # If no selected_rules provided (None or empty dict), run all available inspections
        if not selected_rules:
            run_node_check = bool(nodes)
            run_prometheus_check = bool(prometheus_config and prometheus_config.get("enabled", False))
            run_opa_check = bool(kubeconfig)
        else:
            run_node_check = bool(nodes) and selected_rules.get("node")
            run_prometheus_check = bool(
                prometheus_config and prometheus_config.get("enabled", False)
            ) and selected_rules.get("prometheus")
            run_opa_check = bool(kubeconfig) and selected_rules.get("opa")

        logger.info(
            f"Inspection decisions - nodes: {run_node_check}, Prometheus: {run_prometheus_check}, OPA: {run_opa_check}"
        )

        # Execute inspections in parallel where possible
        tasks = []

        if run_node_check:
            node_rules = selected_rules.get("node") if selected_rules else None
            # Extract the actual list of rule IDs if it's a dict with 'rules' key
            if node_rules and isinstance(node_rules, dict) and 'rules' in node_rules:
                node_rules = node_rules['rules']
            tasks.append(self._execute_node_inspection(cluster_name, nodes, node_rules, show_progress))

        if run_prometheus_check:
            prometheus_rules = selected_rules.get("prometheus") if selected_rules else None
            # Extract the actual list of rule IDs if it's a dict with 'rules' key
            if prometheus_rules and isinstance(prometheus_rules, dict) and 'rules' in prometheus_rules:
                prometheus_rules = prometheus_rules['rules']
            tasks.append(
                self._execute_prometheus_inspection(
                    cluster_name, prometheus_config, prometheus_rules, show_progress
                )
            )

        if run_opa_check:
            opa_rules = selected_rules.get("opa") if selected_rules else None
            # Extract the actual list of rule IDs if it's a dict with 'rules' key
            if opa_rules and isinstance(opa_rules, dict) and 'rules' in opa_rules:
                opa_rules = opa_rules['rules']
            tasks.append(self._execute_opa_inspection(cluster_name, kubeconfig, opa_rules, show_progress))

        # Wait for all inspections to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Map results back to inspection types
            inspection_types = []
            if run_node_check:
                inspection_types.append("node")
            if run_prometheus_check:
                inspection_types.append("prometheus")
            if run_opa_check:
                inspection_types.append("opa")

            for i, inspection_type in enumerate(inspection_types):
                if i < len(results):
                    result = results[i]
                    if isinstance(result, Exception):
                        logger.error(f"{inspection_type} inspection failed: {result}")
                        all_results[inspection_type] = self._create_error_result(
                            cluster_name, inspection_type, str(result)
                        )
                    else:
                        all_results[inspection_type] = result

        return all_results

    async def _execute_node_inspection(
        self,
        cluster_name: str,
        nodes: List[Dict],
        selected_rules: Optional[List[str]],
        show_progress: bool,
    ) -> Tuple[bool, Any]:
        """Execute node inspection"""
        node_inspector = None
        try:
            node_inspector = NodeInspector(nodes, use_gitops=self.use_gitops)

            if show_progress:
                logger.info("Executing node inspection...")
            result = await node_inspector.run_inspection(cluster_name, selected_rules or [])
            if show_progress:
                logger.info("Node inspection completed")
            return True, result
        except Exception as e:
            logger.error(f"Node inspection error: {e}")
            # Create error result with SSH connection errors
            error_result = InspectionResult(cluster_name, "node")
            error_result.add_item(
                {
                    "name": "Node inspection failed",
                    "status": "error",
                    "description": f"Node inspection could not be completed: {str(e)}",
                    "severity": "critical",
                    "details": str(e),
                    "solution": "Check cluster node connectivity and configuration",
                }
            )
            # Add SSH connection errors if available
            if node_inspector and hasattr(node_inspector, "ssh_error_manager"):
                ssh_errors = node_inspector.ssh_error_manager.get_all_connection_errors()
                for error in ssh_errors:
                    error_result.add_item(error)
            return True, error_result

    async def _execute_prometheus_inspection(
        self,
        cluster_name: str,
        prometheus_config: Dict,
        selected_rules: Optional[List[str]],
        show_progress: bool,
    ) -> Tuple[bool, Any]:
        """Execute Prometheus inspection"""
        try:
            if prometheus_config and prometheus_config.get("enabled", False):
                prometheus_inspector = PrometheusInspector(prometheus_config, use_gitops=self.use_gitops)
                if show_progress:
                    logger.info("Executing Prometheus metrics inspection...")
                result = await prometheus_inspector.run_inspection(cluster_name, selected_rules or [])
                if show_progress:
                    logger.info("Prometheus metrics inspection completed")
                return True, result
            else:
                if show_progress:
                    logger.info("Prometheus inspection skipped (no configuration)")
                return True, None
        except Exception as e:
            logger.error(f"Prometheus metrics inspection error: {e}")
            # Create error result
            error_result = InspectionResult(cluster_name, "prometheus")
            error_result.add_item(
                {
                    "name": "Prometheus inspection failed",
                    "status": "error",
                    "description": f"Prometheus inspection could not be completed: {str(e)}",
                    "severity": "critical",
                    "details": str(e),
                    "solution": "Check Prometheus server connectivity and configuration",
                }
            )
            return True, error_result

    async def _execute_opa_inspection(
        self,
        cluster_name: str,
        kubeconfig: str,
        selected_rules: Optional[List[str]],
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
                result = await opa_inspector.run_inspection(cluster_name, selected_rules or [])
                if show_progress:
                    logger.info("OPA compliance inspection completed")
                return True, result
            else:
                if show_progress:
                    logger.info("OPA compliance inspection skipped (no configuration)")
                return True, None
        except Exception as e:
            logger.error(f"OPA compliance inspection error: {e}")
            # Create error result
            error_result = InspectionResult(cluster_name, "opa")
            error_result.add_item(
                {
                    "name": "OPA inspection failed",
                    "status": "error",
                    "description": f"OPA inspection could not be completed: {str(e)}",
                    "severity": "critical",
                    "details": str(e),
                    "solution": "Check Kubernetes API connectivity and kubeconfig",
                }
            )
            return True, error_result

    def _create_error_result(self, cluster_name: str, inspection_type: str, error_message: str) -> InspectionResult:
        """Create error result for failed inspection"""
        error_result = InspectionResult(cluster_name, inspection_type)
        error_result.add_item(
            {
                "name": f"{inspection_type} inspection failed",
                "status": "error",
                "description": f"{inspection_type} inspection could not be completed: {error_message}",
                "severity": "critical",
                "details": error_message,
                "solution": f"Check {inspection_type} configuration and connectivity",
            }
        )
        return error_result
