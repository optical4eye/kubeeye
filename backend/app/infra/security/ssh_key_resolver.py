#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Key Resolver for standardizing node authentication configurations
"""

import hashlib
from typing import Dict, Any, Optional
from infra.security.secret_service import SecretService
from core.common.cache_utils import CacheManager
from core.logging import get_logger

logger = get_logger(__name__)


class SSHKeyResolver:
    """
    Resolver for SSH authentication configurations in node configs.

    This class standardizes node configurations by resolving authentication sources
    (secrets, direct values) into unified fields: 'password' and 'ssh_key' as strings.
    Supports password, SSH key, or both authentication types with caching for optimization.
    """

    def __init__(self, secret_service: SecretService):
        """
        Initialize the SSH Key Resolver.

        Args:
            secret_service: Service for accessing encrypted secrets
        """
        self.secret_service = secret_service
        self.cache_manager = CacheManager()
        self.cache = self.cache_manager.get_or_create_cache("ssh_key_resolver", maxsize=100, ttl=600)  # 10 minutes TTL

    def invalidate_cache(self, ip: Optional[str] = None) -> int:
        """
        Invalidate cached node configurations.

        Args:
            ip: Optional IP address to invalidate specific node, or None to clear all

        Returns:
            Number of cache entries invalidated
        """
        if ip is None:
            # Clear entire cache
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Invalidated all {count} cache entries in SSHKeyResolver")
            return count
        else:
            # Clear specific entries for IP
            keys_to_remove = [k for k in self.cache.keys() if f"ip:{ip}" in k]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for IP {ip}")
            return len(keys_to_remove)

    async def resolve_node_config(self, node_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve and standardize node authentication configuration.

        Takes a node configuration with various authentication source specifications
        and returns a standardized version with 'auth_type', 'password', and 'ssh_key' fields.

        Args:
            node_config: Node configuration dictionary that may contain:
                - password: Direct password string
                - password_secret_id: ID of password secret
                - password_secret_name: Name of password secret
                - ssh_key: Direct SSH key string
                - ssh_key_secret_id: ID of SSH key secret
                - ssh_key_secret_name: Name of SSH key secret
                - auth_type: Optional explicit auth type ("password", "key", "both")

        Returns:
            Standardized node configuration with:
                - auth_type: "password", "key", or "both"
                - password: Password string (if applicable)
                - ssh_key: SSH key string (if applicable)

        Raises:
            ValueError: If authentication sources are invalid or missing
        """
        # Generate cache key based on authentication sources
        cache_key = self._generate_cache_key(node_config)

        # Check cache first
        if cache_key in self.cache:
            logger.debug("Using cached resolved config for node")
            return self.cache[cache_key].copy()

        # Create a copy to modify
        resolved = node_config.copy()

        # Determine auth_type if not explicitly set
        auth_type = node_config.get("auth_type")
        if not auth_type:
            has_password = self._has_password_source(node_config)
            has_key = self._has_key_source(node_config)

            if has_password and has_key:
                auth_type = "both"
            elif has_key:
                auth_type = "key"
            elif has_password:
                auth_type = "password"
            else:
                raise ValueError("No authentication source provided in node configuration")

        resolved["auth_type"] = auth_type

        # Resolve password if needed
        if auth_type in ["password", "both"]:
            password = await self._get_password(node_config)
            resolved["password"] = password

        # Resolve SSH key if needed
        if auth_type in ["key", "both"]:
            ssh_key = await self._get_ssh_key(node_config)
            resolved["ssh_key"] = ssh_key

        # Cache the resolved configuration
        self.cache[cache_key] = resolved.copy()

        logger.debug(f"Resolved node config with auth_type: {auth_type}")
        return resolved

    def _generate_cache_key(self, node_config: Dict[str, Any]) -> str:
        """
        Generate a cache key based on authentication source identifiers.

        Uses secret IDs/names, IP address, and hashes of direct values to create a unique key
        without exposing sensitive data in the key itself.
        """
        key_parts = []

        # Add IP address to key to prevent incorrect cache hits for different nodes
        if "ip" in node_config:
            key_parts.append(f"ip:{node_config['ip']}")

        # Add secret identifiers
        for field in ["ssh_key_secret_id", "ssh_key_secret_name", "password_secret_id", "password_secret_name"]:
            if field in node_config:
                key_parts.append(f"{field}:{node_config[field]}")

        # Add hashes of direct values (if no secret sources)
        if "ssh_key" in node_config and not any(k in node_config for k in ["ssh_key_secret_id", "ssh_key_secret_name"]):
            key_hash = hashlib.sha256(node_config["ssh_key"].encode()).hexdigest()
            key_parts.append(f"ssh_key_hash:{key_hash}")

        if "password" in node_config and not any(
            k in node_config for k in ["password_secret_id", "password_secret_name"]
        ):
            pass_hash = hashlib.sha256(node_config["password"].encode()).hexdigest()
            key_parts.append(f"password_hash:{pass_hash}")

        return "|".join(key_parts) or "no_auth"

    def _has_password_source(self, node_config: Dict[str, Any]) -> bool:
        """Check if node config has any password authentication source."""
        return any(k in node_config for k in ["password", "password_secret_id", "password_secret_name"])

    def _has_key_source(self, node_config: Dict[str, Any]) -> bool:
        """Check if node config has any SSH key authentication source."""
        return any(k in node_config for k in ["ssh_key", "ssh_key_secret_id", "ssh_key_secret_name"])

    async def _get_password(self, node_config: Dict[str, Any]) -> str:
        """
        Retrieve password from the specified source.

        Supports direct password, secret by ID, or secret by name.
        """
        if "password" in node_config:
            return node_config["password"]
        elif "password_secret_id" in node_config:
            decrypted_data, _ = await self.secret_service.reveal_secret(node_config["password_secret_id"])
            return decrypted_data
        elif "password_secret_name" in node_config:
            secret = await self.secret_service.get_secret_by_name(node_config["password_secret_name"])
            if not secret:
                raise ValueError(f"Password secret '{node_config['password_secret_name']}' not found")
            decrypted_data, _ = await self.secret_service.reveal_secret(secret.id)
            return decrypted_data
        else:
            raise ValueError("No password source specified")

    async def _get_ssh_key(self, node_config: Dict[str, Any]) -> str:
        """
        Retrieve SSH key from the specified source.

        Supports direct key content, secret by ID, or secret by name.
        """
        if "ssh_key" in node_config:
            return node_config["ssh_key"]
        elif "ssh_key_secret_id" in node_config:
            decrypted_data, _ = await self.secret_service.reveal_secret(node_config["ssh_key_secret_id"])
            return decrypted_data
        elif "ssh_key_secret_name" in node_config:
            secret = await self.secret_service.get_secret_by_name(node_config["ssh_key_secret_name"])
            if not secret:
                raise ValueError(f"SSH key secret '{node_config['ssh_key_secret_name']}' not found")
            decrypted_data, _ = await self.secret_service.reveal_secret(secret.id)
            return decrypted_data
        else:
            raise ValueError("No SSH key source specified")
