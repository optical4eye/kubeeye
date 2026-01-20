#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps synchronization manager - handles GitOps repository synchronization
"""

from core.logging import get_logger

logger = get_logger(__name__)

# Import RuleManager for compatibility with tests
from infra.rules.rule_manager import RuleManager

# Import GitOpsManager (unified manager)
from infra.gitops.gitops_manager import GitOpsManager

# Alias for backward compatibility
GitOpsSyncManager = GitOpsManager


# Standalone functions for compatibility with tests - using GitOpsManager
async def sync_rules_from_gitops() -> bool:
    """
    Sync rules from GitOps repository

    Returns:
        True if sync was successful, False otherwise
    """
    try:
        rule_manager = RuleManager()
        should_use = rule_manager.should_use_gitops()

        if not should_use:
            return False

        gitops_manager = GitOpsManager()
        success, _ = await gitops_manager.sync_if_needed(use_gitops=True)
        return success
    except Exception as e:
        logger.error(f"Error syncing rules from GitOps: {str(e)}")
        return False


def sync_rules() -> bool:
    """
    Sync rules from GitOps repository (synchronous version for tests)

    Returns:
        True if sync was successful, False otherwise
    """
    try:
        rule_manager = RuleManager()

        if not rule_manager.should_use_gitops():
            return False

        gitops_manager = GitOpsManager()
        # For synchronous version, we'll just check if GitOps is configured
        return gitops_manager.is_configured()
    except Exception as e:
        logger.error(f"Error syncing rules from GitOps: {str(e)}")
        return False


async def get_gitops_status() -> dict:
    """
    Get GitOps status

    Returns:
        Dictionary with GitOps status information
    """
    try:
        gitops_manager = GitOpsManager()
        return gitops_manager.get_gitops_status()
    except Exception as e:
        logger.error(f"Error getting GitOps status: {str(e)}")
        return {"enabled": False, "error": str(e)}


def get_repository_info() -> dict:
    """
    Get repository information (synchronous version for tests)

    Returns:
        Dictionary with repository information
    """
    try:
        gitops_manager = GitOpsManager()
        status = gitops_manager.get_gitops_status()

        if status.get("enabled") and status.get("repository"):
            return {
                "url": status.get("url"),
                "branch": status.get("branch", "main"),
                "last_sync": "Unknown",  # We don't track this in the current implementation
            }
        else:
            return {}
    except Exception as e:
        logger.error(f"Error getting repository info: {str(e)}")
        return {}
