#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Permissions for RBAC system

This module defines all available permissions in the system.
Permissions are loaded from the YAML configuration file.
"""

from .rbac_manager import Permission

# Re-export Permission class for backward compatibility
__all__ = ["Permission"]
