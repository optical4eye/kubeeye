#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster configuration management module for managing cluster connection configuration information
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from infra.results.inspection_result import get_latest_result_by_cluster
from core.logging import get_logger
from core.common.cache_utils import CacheManager

logger = get_logger(__name__)

# Clusters and results are now stored in PostgreSQL - no local file storage needed

# Cache for cluster status using CacheManager
_cache_manager = CacheManager()
_cluster_status_cache = _cache_manager.get_or_create_cache("cluster_status", maxsize=128, ttl=300)  # 5 minutes TTL


class ClusterConfig:
    """Cluster configuration management class"""

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        # Config is stored in PostgreSQL - no local file storage needed
        self.config = None  # Will be loaded from database

    async def _load_config(self) -> Dict:
        """Load cluster configuration from database"""
        from db.database import get_session_local
        from db.repositories.cluster_repository import ClusterRepository

        session_local = get_session_local()
        async with session_local() as db:
            try:
                repo = ClusterRepository(db)
                config = await repo.get_cluster_config(self.cluster_name)
                if config:
                    return config

                # Return default config if not found
                return {
                    "name": self.cluster_name,
                    "nodes": [],
                    "kubeconfig": "",
                    "created_at": "",
                    "updated_at": "",
                }
            finally:
                await db.close()

    async def save_config(self) -> None:
        """Save cluster configuration to database"""
        from db.database import get_session_local
        from db.repositories.cluster_repository import ClusterRepository

        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        session_local = get_session_local()
        async with session_local() as db:
            try:
                repo = ClusterRepository(db)

                # Check if cluster exists
                existing = await repo.get_by_name(self.cluster_name)
                if existing:
                    # Update existing
                    await repo.update_cluster(
                        self.cluster_name,
                        nodes=self.config.get("nodes", []),
                        kubeconfig=self.config.get("kubeconfig", ""),
                    )
                else:
                    # Create new
                    await repo.create_cluster(
                        name=self.cluster_name,
                        nodes=self.config.get("nodes", []),
                        kubeconfig=self.config.get("kubeconfig", ""),
                    )
            finally:
                await db.close()

    async def update_node(self, node_info: Dict) -> None:
        """Add or update node information"""
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        # Create a copy of node information
        node_copy = node_info.copy()

        # Ensure password is stored in plain text
        if node_copy.get("auth_type") == "password" and node_copy.get("password"):
            node_copy["password_encrypted"] = False

        # Update node information
        for i, node in enumerate(self.config["nodes"]):
            if node["ip"] == node_info["ip"]:
                self.config["nodes"][i] = node_copy
                await self.save_config()
                return

        # If not exists, add new node
        self.config["nodes"].append(node_copy)
        await self.save_config()

    async def remove_node(self, node_ip: str) -> bool:
        """Remove node information"""
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        for i, node in enumerate(self.config["nodes"]):
            if node["ip"] == node_ip:
                del self.config["nodes"][i]
                await self.save_config()
                return True
        return False

    async def update_kubeconfig(self, kubeconfig: str) -> None:
        """Update Kubeconfig configuration"""
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        self.config["kubeconfig"] = kubeconfig
        await self.save_config()

    async def get_nodes(self, parse_secrets: bool = False) -> List[Dict]:
        """
        Get cluster node list

        Args:
            parse_secrets: If True, parse secret variables (for inspections/tests).
                          If False, keep secret variables as-is (for UI display).
        """
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        nodes = []

        if parse_secrets:
            # Resolve node configurations using SSHKeyResolver for inspections/tests
            from db.database import get_session_local
            from infra.security.secret_service import SecretService
            from infra.security.ssh_key_resolver import SSHKeyResolver

            # Get database session for secret resolution
            session_local = get_session_local()
            async with session_local() as db:
                try:
                    secret_service = SecretService(db)
                    resolver = SSHKeyResolver(secret_service)

                    for node in self.config["nodes"]:
                        node_copy = node.copy()

                        # First, parse secret variables in strings (for backward compatibility)
                        from infra.security.secret_variable_parser import SecretVariableParser

                        parser = SecretVariableParser(db)

                        # Parse secret variables in password
                        if "password" in node_copy and node_copy["password"]:
                            password_text = node_copy["password"]
                            processed_password, parse_errors = await parser.replace_variables(password_text)
                            if parse_errors:
                                logger.warning(f"Secret parsing errors for node {node_copy.get('ip')}: {parse_errors}")
                            node_copy["password"] = processed_password

                        # Parse secret variables in ssh_key
                        if "ssh_key" in node_copy and node_copy["ssh_key"]:
                            ssh_key_text = node_copy["ssh_key"]
                            processed_ssh_key, parse_errors = await parser.replace_variables(ssh_key_text)
                            if parse_errors:
                                logger.warning(f"Secret parsing errors for node {node_copy.get('ip')}: {parse_errors}")
                            node_copy["ssh_key"] = processed_ssh_key

                        # Resolve node configuration using SSHKeyResolver
                        resolved_node = await resolver.resolve_node_config(node_copy)

                        # Ensure password and ssh_key are strings
                        if "password" in resolved_node and resolved_node["password"] is not None:
                            resolved_node["password"] = str(resolved_node["password"])
                        if "ssh_key" in resolved_node and resolved_node["ssh_key"] is not None:
                            resolved_node["ssh_key"] = str(resolved_node["ssh_key"])

                        # Explicitly remove password encryption flag
                        if resolved_node.get("password_encrypted"):
                            logger.info(
                                f"Password for node {resolved_node.get('ip')} is marked as encrypted, but will be used in plain text"
                            )
                            resolved_node["password_encrypted"] = False

                        nodes.append(resolved_node)
                finally:
                    await db.close()
        else:
            # Return nodes without parsing secrets (for UI display)
            for node in self.config["nodes"]:
                node_copy = node.copy()
                # Explicitly remove password encryption flag
                if node_copy.get("password_encrypted"):
                    node_copy["password_encrypted"] = False
                nodes.append(node_copy)

        return nodes

    async def get_kubeconfig(self, parse_secrets: bool = False) -> str:
        """
        Get Kubeconfig

        Args:
            parse_secrets: If True, parse secret variables (for inspections/tests).
                          If False, keep secret variables as-is (for UI display).
        """
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        kubeconfig = self.config.get("kubeconfig", "")
        # Handle case where kubeconfig might be stored as a dict
        if isinstance(kubeconfig, dict):
            kubeconfig = kubeconfig.get("kubeconfig", "")

        if not isinstance(kubeconfig, str):
            return ""

        if parse_secrets:
            # Parse secret variables in kubeconfig for inspections/tests
            from db.database import get_session_local
            from infra.security.secret_variable_parser import SecretVariableParser

            session_local = get_session_local()
            async with session_local() as db:
                try:
                    parser = SecretVariableParser(db)
                    processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
                    if parse_errors:
                        logger.warning(f"Secret parsing errors for kubeconfig: {parse_errors}")
                    return processed_kubeconfig
                finally:
                    await db.close()
        else:
            # Return kubeconfig without parsing secrets (for UI display)
            return kubeconfig

    async def get_dict(self, parse_secrets: bool = False) -> Dict:
        """
        Get dictionary representation of cluster configuration

        Args:
            parse_secrets: If True, parse secret variables (for inspections/tests).
                          If False, keep secret variables as-is (for UI display).
        """
        # Ensure config is loaded
        if self.config is None:
            self.config = await self._load_config()

        config_dict = self.config.copy()

        # Add structured data for easy use by inspectors
        config_dict.update(
            {
                "nodes": await self.get_nodes(parse_secrets=parse_secrets),
                "kubeconfig": {
                    "kubeconfig": await self.get_kubeconfig(parse_secrets=parse_secrets)
                },  # Wrap as dictionary
                "opa": {
                    "kubeconfig": await self.get_kubeconfig(parse_secrets=parse_secrets)
                },  # Format required by OPA inspector
            }
        )

        return config_dict


async def list_clusters() -> List[str]:
    """List all cluster names from database"""
    from db.database import get_session_local
    from db.repositories.cluster_repository import ClusterRepository

    session_local = get_session_local()
    async with session_local() as db:
        try:
            repo = ClusterRepository(db)
            return await repo.get_all_names()
        finally:
            await db.close()


async def get_cluster(cluster_name: str) -> ClusterConfig:
    """Get cluster configuration object"""
    config = ClusterConfig(cluster_name)
    # Force load config to ensure it's available
    config.config = await config._load_config()
    return config


async def delete_cluster(cluster_name: str) -> bool:
    """Delete cluster configuration from database"""
    from db.database import get_session_local
    from db.repositories.cluster_repository import ClusterRepository

    session_local = get_session_local()
    async with session_local() as db:
        try:
            repo = ClusterRepository(db)
            return await repo.delete_cluster(cluster_name)
        finally:
            await db.close()


def load_kubeconfig(kubeconfig_str: str) -> Dict:
    """Load kubeconfig content as dictionary"""
    try:
        # Handle multi-line strings properly
        if isinstance(kubeconfig_str, str):
            # Replace literal \n with actual newlines for YAML parsing
            processed_str = kubeconfig_str.replace("\\n", "\n")
            return yaml.safe_load(processed_str)
        else:
            return yaml.safe_load(kubeconfig_str)
    except yaml.YAMLError:
        return {}


async def list_clusters_cached() -> List[str]:
    """Cached loading of cluster list"""
    return await list_clusters()


async def get_cluster_status_counts_fast(exclude_inspection_types: Optional[List[str]] = None) -> Dict[str, int]:
    """Fast counting of cluster statuses with caching"""
    import time

    current_time = time.time()
    cache_key = f"status_counts_{exclude_inspection_types}"

    # Check if cache is still valid
    cached_data = _cluster_status_cache.get(cache_key)
    if cached_data and (current_time - cached_data.get("timestamp", 0)) < 300:
        counts = cached_data.get("counts", {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0})
        return dict(counts)  # Return a copy of counts dict

    # Recalculate and cache
    clusters = await list_clusters_cached()
    counts = {"healthy": 0, "warning": 0, "critical": 0, "unknown": 0}

    for cluster_name in clusters:
        try:
            status = await get_cluster_quick_status(cluster_name, exclude_inspection_types=exclude_inspection_types)
            counts[status] += 1
        except Exception:
            counts["unknown"] += 1

    # Update cache
    _cluster_status_cache[cache_key] = {"counts": dict(counts), "timestamp": current_time}

    return dict(counts)


async def get_cluster_quick_status(cluster_name: str, exclude_inspection_types: Optional[List[str]] = None) -> str:
    """Quick cluster status check"""
    latest_result = await get_latest_result_by_cluster(cluster_name, exclude_inspection_types=exclude_inspection_types)

    if not latest_result:
        # If no inspection results, consider cluster healthy by default
        return "healthy"

    critical = latest_result.get("critical", 0)
    warning = latest_result.get("warning", 0)

    if critical > 0:
        return "critical"
    elif warning > 0:
        return "warning"
    else:
        return "healthy"
