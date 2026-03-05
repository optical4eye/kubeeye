#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection configuration manager - handles cluster configuration and validation
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple

from infra.cluster.cluster_config import get_cluster
from infra.rules.rule_manager import RuleManager
from core.common.unified_validation import ValidationManager
from core.logging import get_logger

logger = get_logger(__name__)


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

            cluster_config = await get_cluster(cluster_name)
            if not cluster_config:
                error_msg = f"Cluster configuration not found: {cluster_name}"
                return None, error_msg

            return cluster_config, ""
        except Exception as e:
            error_msg = f"Error getting cluster configuration: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    async def extract_cluster_components(cluster_config: Any) -> Dict[str, Any]:
        """
        Extract components from cluster configuration

        Returns:
            Dictionary with nodes and kubeconfig
        """
        try:
            # Parse secrets for inspections (get decrypted values)
            nodes = await cluster_config.get_nodes(parse_secrets=True) if hasattr(cluster_config, "get_nodes") else []
            kubeconfig = (
                await cluster_config.get_kubeconfig(parse_secrets=True)
                if hasattr(cluster_config, "get_kubeconfig")
                else ""
            )

            return {"nodes": nodes, "kubeconfig": kubeconfig}
        except Exception as e:
            logger.error(f"Error extracting cluster components: {str(e)}")
            return {"nodes": [], "kubeconfig": ""}

    @staticmethod
    def validate_inspection_feasibility(
        components: Dict[str, Any], selected_rules: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate if inspection can be performed with available components

        Returns:
            (can_proceed, error_message, inspection_decisions) tuple
        """
        return ValidationManager.validate_inspection_feasibility(components, selected_rules)

    @staticmethod
    async def get_config_dict(cluster_config: Any) -> Dict[str, Any]:
        """
        Convert cluster configuration to dictionary format

        Returns:
            Dictionary representation of cluster configuration
        """
        try:
            if hasattr(cluster_config, "get_dict"):
                result = cluster_config.get_dict()
                # Check if result is a coroutine and await it
                if hasattr(result, "__await__") or asyncio.iscoroutine(result):
                    return await result
                else:
                    return result
            else:
                # Handle sync methods for nodes and kubeconfig
                nodes_result = cluster_config.get_nodes() if hasattr(cluster_config, "get_nodes") else []
                kubeconfig_result = cluster_config.get_kubeconfig() if hasattr(cluster_config, "get_kubeconfig") else ""

                # Check if these are coroutines and await them
                if hasattr(nodes_result, "__await__") or asyncio.iscoroutine(nodes_result):
                    nodes = await nodes_result
                else:
                    nodes = nodes_result

                if hasattr(kubeconfig_result, "__await__") or asyncio.iscoroutine(kubeconfig_result):
                    kubeconfig = await kubeconfig_result
                else:
                    kubeconfig = kubeconfig_result

                return {
                    "nodes": nodes,
                    "opa": {"kubeconfig": kubeconfig},
                }
        except Exception as e:
            logger.error(f"Error converting config to dict: {str(e)}")
            return {"nodes": [], "opa": {"kubeconfig": ""}}


# Additional functions for rule management
async def get_inspection_config(types=None):
    """Get inspection configuration for specified types"""
    try:
        use_gitops = RuleManager.should_use_gitops()
        logger.info(f"DEBUG: use_gitops in get_inspection_config: {use_gitops}")
        if types:
            result = {}
            for rule_type in types:
                try:
                    rules = RuleManager.get_enabled_rules(rule_type)
                    logger.info(f"DEBUG: rules for {rule_type}: {rules}")
                    result[rule_type] = [{"name": rule.id, "enabled": rule.enabled} for rule in rules]
                except Exception as e:
                    logger.error(f"Error getting rules for {rule_type}: {str(e)}")
                    result[rule_type] = []
            return result
        else:
            # Get all available rule types
            rule_types = ["node", "opa"]
            result = {}
            for rule_type in rule_types:
                try:
                    rules = RuleManager.get_enabled_rules(rule_type)
                    logger.info(f"DEBUG: rules for {rule_type}: {rules}")
                    result[rule_type] = [{"name": rule.id, "enabled": rule.enabled} for rule in rules]
                except Exception as e:
                    logger.error(f"Error getting rules for {rule_type}: {str(e)}")
                    result[rule_type] = []
            return result
    except Exception as e:
        logger.error(f"Error getting inspection config: {str(e)}")
        return {"node": [], "opa": []}


async def validate_inspection_config(config):
    """Validate inspection configuration"""
    try:
        # Simple validation - check if config is a dictionary
        if isinstance(config, dict):
            # Additional validation: check if it has valid structure
            valid_types = ["node", "opa"]
            for key in config.keys():
                if key not in valid_types:
                    return False, f"Invalid inspection type: {key}"
                if not isinstance(config[key], list):
                    return False, f"Invalid format for {key}: should be a list"
            return True, "Valid config"
        else:
            return False, "Invalid config: should be a dictionary"
    except Exception as e:
        logger.error(f"Error validating inspection config: {str(e)}")
        return False, f"Validation error: {str(e)}"


async def get_default_inspection_config():
    """Get default inspection configuration"""
    try:
        use_gitops = RuleManager.should_use_gitops()
        logger.info(f"DEBUG: use_gitops in get_default_inspection_config: {use_gitops}")
        rule_types = ["node", "opa"]
        result = {}
        for rule_type in rule_types:
            try:
                rules = RuleManager.get_enabled_rules(rule_type)
                logger.info(f"DEBUG: rules for {rule_type}: {rules}")
                result[rule_type] = [{"name": rule.id, "enabled": rule.enabled} for rule in rules]
            except Exception as e:
                logger.error(f"Error getting rules for {rule_type}: {str(e)}")
                result[rule_type] = []
        return result
    except Exception as e:
        logger.error(f"Error getting default inspection config: {str(e)}")
        return {"node": [], "opa": []}


async def merge_inspection_configs(config1, config2):
    """Merge two inspection configurations"""
    try:
        result = {}
        # Get all unique keys from both configs
        all_keys = set(config1.keys()) | set(config2.keys())

        for key in all_keys:
            rules1 = config1.get(key, [])
            rules2 = config2.get(key, [])

            # Merge rules, avoiding duplicates
            merged_rules = []
            seen = set()

            for rule in rules1 + rules2:
                rule_id = rule.get("name")
                if rule_id and rule_id not in seen:
                    merged_rules.append(rule)
                    seen.add(rule_id)

            result[key] = merged_rules

        return result
    except Exception as e:
        logger.error(f"Error merging inspection configs: {str(e)}")
        return {}
