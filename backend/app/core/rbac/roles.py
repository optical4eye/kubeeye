#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roles for RBAC system

This module defines all available roles and their permissions.
Roles and permissions are loaded from the YAML configuration file.
"""

from .rbac_manager import Role

# Re-export Role class for backward compatibility
__all__ = ["Role"]
