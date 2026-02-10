#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control) module

This module provides centralized access control using a simplified RBAC system
with YAML configuration.
"""

from .rbac_manager import Permission, Role, RBACManager, reload_config
from .decorators import require_permission, require_any_permission, require_all_permissions, require_role

__all__ = [
    "Permission",
    "Role",
    "RBACManager",
    "reload_config",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
]
