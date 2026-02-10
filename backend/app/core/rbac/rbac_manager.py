#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified RBAC system with YAML configuration

This module provides a centralized RBAC system that works
with the existing User model without requiring complex async/sync bridging.
Roles and permissions are loaded from a YAML configuration file.
"""

import os
from typing import List, Dict, Any
from pathlib import Path
import yaml
from core.logging import get_logger

logger = get_logger(__name__)

# Path to the RBAC configuration file
CONFIG_PATH = Path(__file__).parent / "rbac_config.yaml"

# Cache for loaded configuration
_config_cache: Dict[str, Any] | None = None


def _load_config() -> Dict[str, Any]:
    """
    Load RBAC configuration from YAML file

    Returns:
        Dictionary containing roles and permissions configuration

    Raises:
        FileNotFoundError: If configuration file is not found
        yaml.YAMLError: If configuration file is invalid
        ValueError: If configuration file is empty
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("Configuration file is empty")
            _config_cache = config
        logger.info(f"RBAC configuration loaded from {CONFIG_PATH}")
        return _config_cache
    except FileNotFoundError:
        logger.error(f"RBAC configuration file not found: {CONFIG_PATH}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing RBAC configuration: {e}")
        raise


def reload_config() -> None:
    """
    Reload RBAC configuration from YAML file

    This can be called to reload the configuration without restarting the application.
    """
    global _config_cache
    _config_cache = None
    _load_config()
    logger.info("RBAC configuration reloaded")


class Permission:
    """
    Permission definitions for RBAC system

    Each permission follows the pattern: <resource>:<action>
    """

    # User permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_CHANGE_PASSWORD = "user:change_password"

    # Cluster permissions
    CLUSTER_READ = "cluster:read"
    CLUSTER_CREATE = "cluster:create"
    CLUSTER_UPDATE = "cluster:update"
    CLUSTER_DELETE = "cluster:delete"

    # Inspection permissions
    INSPECTION_READ = "inspection:read"
    INSPECTION_RUN = "inspection:run"
    INSPECTION_CREATE = "inspection:create"
    INSPECTION_DELETE = "inspection:delete"

    # Report permissions
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_DELETE = "report:delete"
    REPORT_EXPORT = "report:export"

    # Secret permissions
    SECRET_READ = "secret:read"
    SECRET_CREATE = "secret:create"
    SECRET_UPDATE = "secret:update"
    SECRET_DELETE = "secret:delete"

    # Task permissions
    TASK_READ = "task:read"
    TASK_RUN = "task:run"
    TASK_CREATE = "task:create"
    TASK_DELETE = "task:delete"

    # Schedule permissions
    SCHEDULE_READ = "schedule:read"
    SCHEDULE_CREATE = "schedule:create"
    SCHEDULE_UPDATE = "schedule:update"
    SCHEDULE_DELETE = "schedule:delete"

    # Rule permissions
    RULE_READ = "rule:read"
    RULE_CREATE = "rule:create"
    RULE_UPDATE = "rule:update"
    RULE_DELETE = "rule:delete"

    # GitOps permissions
    GITOPS_READ = "gitops:read"
    GITOPS_SYNC = "gitops:sync"
    GITOPS_CONFIGURE = "gitops:configure"

    # Network permissions
    NETWORK_CHECK = "network:check"

    # Popeye permissions
    POPEYE_SCAN = "popeye:scan"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_DELETE = "audit:delete"
    AUDIT_STATS = "audit:stats"

    # System permissions
    SYSTEM_HEALTH = "system:health"
    SYSTEM_CONFIG = "system:config"

    @classmethod
    def all(cls) -> List[str]:
        """Get all permissions"""
        return [
            # User permissions
            cls.USER_READ,
            cls.USER_CREATE,
            cls.USER_UPDATE,
            cls.USER_DELETE,
            cls.USER_CHANGE_PASSWORD,
            # Cluster permissions
            cls.CLUSTER_READ,
            cls.CLUSTER_CREATE,
            cls.CLUSTER_UPDATE,
            cls.CLUSTER_DELETE,
            # Inspection permissions
            cls.INSPECTION_READ,
            cls.INSPECTION_RUN,
            cls.INSPECTION_CREATE,
            cls.INSPECTION_DELETE,
            # Report permissions
            cls.REPORT_READ,
            cls.REPORT_CREATE,
            cls.REPORT_DELETE,
            cls.REPORT_EXPORT,
            # Secret permissions
            cls.SECRET_READ,
            cls.SECRET_CREATE,
            cls.SECRET_UPDATE,
            cls.SECRET_DELETE,
            # Task permissions
            cls.TASK_READ,
            cls.TASK_RUN,
            cls.TASK_CREATE,
            cls.TASK_DELETE,
            # Schedule permissions
            cls.SCHEDULE_READ,
            cls.SCHEDULE_CREATE,
            cls.SCHEDULE_UPDATE,
            cls.SCHEDULE_DELETE,
            # Rule permissions
            cls.RULE_READ,
            cls.RULE_CREATE,
            cls.RULE_UPDATE,
            cls.RULE_DELETE,
            # GitOps permissions
            cls.GITOPS_READ,
            cls.GITOPS_SYNC,
            cls.GITOPS_CONFIGURE,
            # Network permissions
            cls.NETWORK_CHECK,
            # Popeye permissions
            cls.POPEYE_SCAN,
            # Audit permissions
            cls.AUDIT_READ,
            cls.AUDIT_DELETE,
            cls.AUDIT_STATS,
            # System permissions
            cls.SYSTEM_HEALTH,
            cls.SYSTEM_CONFIG,
        ]

    @classmethod
    def by_resource(cls, resource: str) -> List[str]:
        """Get all permissions for a specific resource"""
        resource_permissions = []
        for perm in cls.all():
            if perm.startswith(f"{resource}:"):
                resource_permissions.append(perm)
        return resource_permissions

    @classmethod
    def is_valid(cls, permission: str) -> bool:
        """Check if a permission is valid"""
        return permission in cls.all()


class Role:
    """
    Role definitions for RBAC system

    Each role has a set of permissions that define what actions
    users with that role can perform. Roles are loaded from YAML configuration.
    """

    ADMIN = "admin"
    OPERATOR = "operator"

    @classmethod
    def all(cls) -> List[str]:
        """Get all available roles from configuration"""
        config = _load_config()
        return list(config.get("roles", {}).keys())

    @classmethod
    def is_valid(cls, role: str) -> bool:
        """Check if a role is valid"""
        return role in cls.all()

    @classmethod
    def get_permissions(cls, role: str) -> List[str]:
        """
        Get all permissions for a specific role from configuration

        Args:
            role: Role name

        Returns:
            List of permissions for the role
        """
        config = _load_config()
        roles_config = config.get("roles", {})
        role_config = roles_config.get(role, {})
        return role_config.get("permissions", [])

    @classmethod
    def get_role_info(cls, role: str) -> Dict[str, Any]:
        """
        Get role information from configuration

        Args:
            role: Role name

        Returns:
            Dictionary with role information (name, description, permissions)
        """
        config = _load_config()
        roles_config = config.get("roles", {})
        return roles_config.get(role, {})

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """
        Check if a role has a specific permission

        Args:
            role: Role name
            permission: Permission to check

        Returns:
            True if role has the permission, False otherwise
        """
        return permission in cls.get_permissions(role)


class RBACManager:
    """
    RBAC Manager for checking permissions

    This class provides methods to check permissions based on user roles.
    All configuration is loaded from the YAML file.
    """

    @staticmethod
    def check_permission(user_role: str, permission: str) -> bool:
        """
        Check if a user with a specific role has a permission

        Args:
            user_role: User's role (e.g., "admin", "operator")
            permission: Permission to check (e.g., "cluster:read")

        Returns:
            True if user has the permission, False otherwise
        """
        try:
            # Check if role is valid
            if not Role.is_valid(user_role):
                logger.warning(f"Invalid role: {user_role}")
                return False

            # Check if permission is valid
            if not Permission.is_valid(permission):
                logger.warning(f"Invalid permission: {permission}")
                return False

            # Check if role has the permission
            has_permission = Role.has_permission(user_role, permission)

            logger.debug(f"Permission check: role={user_role}, " f"permission={permission}, allowed={has_permission}")

            return has_permission
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False

    @staticmethod
    def check_any_permission(user_role: str, *permissions: str) -> bool:
        """
        Check if a user has at least one of the specified permissions

        Args:
            user_role: User's role
            *permissions: List of permissions to check

        Returns:
            True if user has any of the permissions, False otherwise
        """
        try:
            # Get all permissions for the role
            role_permissions = Role.get_permissions(user_role)

            # Check if any of the required permissions are in the role's permissions
            has_any = any(perm in role_permissions for perm in permissions)

            logger.debug(
                f"Any permission check: role={user_role}, " f"required_permissions={permissions}, allowed={has_any}"
            )

            return has_any
        except Exception as e:
            logger.error(f"Error checking any permission: {e}")
            return False

    @staticmethod
    def check_all_permissions(user_role: str, *permissions: str) -> bool:
        """
        Check if a user has all of the specified permissions

        Args:
            user_role: User's role
            *permissions: List of permissions to check

        Returns:
            True if user has all of the permissions, False otherwise
        """
        try:
            # Get all permissions for the role
            role_permissions = Role.get_permissions(user_role)

            # Check if all required permissions are in the role's permissions
            has_all = all(perm in role_permissions for perm in permissions)

            logger.debug(
                f"All permission check: role={user_role}, " f"required_permissions={permissions}, allowed={has_all}"
            )

            return has_all
        except Exception as e:
            logger.error(f"Error checking all permissions: {e}")
            return False
