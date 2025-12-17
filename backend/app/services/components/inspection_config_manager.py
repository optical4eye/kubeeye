#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection configuration manager - handles cluster configuration and validation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple

from infrastructure.cluster.cluster_config import get_cluster

logger = logging.getLogger(__name__)


class InspectionConfigManager:
    """Manages inspection configuration and validation"""

    @staticmethod
    async def get_cluster_configuration(cluster_name: str, show_progress: bool = False) -> Tuple[Optional[Any], str]:
        """
        Get and validate cluster configuration

        Args:
            cluster_name: name of the cluster
            show_progress: whether to show progress messages

        Returns:
            (cluster_config, error_message) tuple
        """
        try:
            if show_progress:
                logger.info("Getting cluster configuration...")

            cluster_config = await asyncio.to_thread(get_cluster, cluster_name)
            if not cluster_config:
                error_msg = f"Cluster configuration not found: {cluster_name}"
                return None, error_msg

            return cluster_config, ""
        except Exception as e:
            error_msg = f"Error getting cluster configuration: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def extract_cluster_components(cluster_config: Any) -> Dict[str, Any]:
        """
        Extract components from cluster configuration

        Returns:
            Dictionary with nodes, prometheus_config, and kubeconfig
        """
        try:
            nodes = cluster_config.get_nodes() if hasattr(cluster_config, "get_nodes") else []
            prometheus_config = (
                cluster_config.get_prometheus_config() if hasattr(cluster_config, "get_prometheus_config") else {}
            )
            kubeconfig = cluster_config.get_kubeconfig() if hasattr(cluster_config, "get_kubeconfig") else ""

            return {"nodes": nodes, "prometheus_config": prometheus_config, "kubeconfig": kubeconfig}
        except Exception as e:
            logger.error(f"Error extracting cluster components: {str(e)}")
            return {"nodes": [], "prometheus_config": {}, "kubeconfig": ""}

    @staticmethod
    def validate_inspection_feasibility(
        components: Dict[str, Any], selected_rules: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate if inspection can be performed with available components

        Returns:
            (can_proceed, error_message, inspection_decisions) tuple
        """
        nodes = components["nodes"]
        prometheus_config = components["prometheus_config"]
        kubeconfig = components["kubeconfig"]

        # Determine which inspections can run
        # If no selected_rules provided, run all available inspections
        if selected_rules is None:
            run_node_check = bool(nodes)
            run_prometheus_check = bool(prometheus_config and prometheus_config.get("enabled", False))
            run_opa_check = bool(kubeconfig)
        else:
            run_node_check = bool(nodes) and selected_rules.get("node")
            run_prometheus_check = bool(prometheus_config and prometheus_config.get("enabled", False)) and selected_rules.get("prometheus")
            run_opa_check = bool(kubeconfig) and selected_rules.get("opa")

        inspection_decisions = {"node": run_node_check, "prometheus": run_prometheus_check, "opa": run_opa_check}

        logger.info(
            f"Inspection types check - node count: {len(nodes)}, "
            f"Prometheus enabled: {prometheus_config.get('enabled', False) if prometheus_config else False}, "
            f"kubeconfig: {'present' if kubeconfig else 'absent'}"
        )
        logger.info(f"Selected rules: {selected_rules}")
        logger.info(
            f"Inspection decisions - nodes: {run_node_check}, Prometheus: {run_prometheus_check}, OPA: {run_opa_check}"
        )

        # Check if any inspection can run
        if not (run_node_check or run_prometheus_check or run_opa_check):
            error_msg = "No available inspection types. Check cluster configuration and rule selection."
            return False, error_msg, inspection_decisions

        return True, "", inspection_decisions

    @staticmethod
    def get_config_dict(cluster_config: Any) -> Dict[str, Any]:
        """
        Convert cluster configuration to dictionary format

        Returns:
            Dictionary representation of cluster configuration
        """
        try:
            if hasattr(cluster_config, "get_dict"):
                return cluster_config.get_dict()
            else:
                return {
                    "nodes": (cluster_config.get_nodes() if hasattr(cluster_config, "get_nodes") else []),
                    "prometheus": (
                        cluster_config.get_prometheus_config()
                        if hasattr(cluster_config, "get_prometheus_config")
                        else {}
                    ),
                    "opa": {
                        "kubeconfig": (
                            cluster_config.get_kubeconfig() if hasattr(cluster_config, "get_kubeconfig") else ""
                        )
                    },
                }
        except Exception as e:
            logger.error(f"Error converting config to dict: {str(e)}")
            return {"nodes": [], "prometheus": {}, "opa": {"kubeconfig": ""}}
