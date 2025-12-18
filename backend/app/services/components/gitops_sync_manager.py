#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps synchronization manager - handles GitOps repository synchronization
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Import RuleManager for compatibility with tests
from infrastructure.rules.rule_manager import RuleManager

# Import GitOpsRuleManager for compatibility with tests
from infrastructure.gitops.gitops_manager import GitOpsRuleManager


class GitOpsSyncManager:
    """Manages GitOps repository synchronization"""

    def __init__(self):
        self._gitops_manager = None

    def _get_gitops_manager(self):
        """Lazy initialization of GitOps manager"""
        if self._gitops_manager is None:
            from infrastructure.gitops.gitops_manager import GitOpsRuleManager

            self._gitops_manager = GitOpsRuleManager()
        return self._gitops_manager

    async def sync_if_needed(self, use_gitops: bool, show_progress: bool = False) -> Tuple[bool, str]:
        """
        Synchronize GitOps repository if needed

        Args:
            use_gitops: whether GitOps mode is enabled
            show_progress: whether to show progress messages

        Returns:
            (success, message) tuple
        """
        if not use_gitops:
            return True, "GitOps not enabled"

        try:
            gitops_manager = self._get_gitops_manager()
            config = gitops_manager.load_config()
            current_repo = config.get("repository")

            if not current_repo:
                return True, "No GitOps repository configured"

            if show_progress:
                logger.info(f"Syncing GitOps repository {current_repo['name']}...")

            success, message = gitops_manager.clone_or_update_repo(current_repo)

            if success:
                logger.info(f"GitOps repository synchronized: {message}")
                return True, message
            else:
                logger.warning(f"Failed to sync GitOps repository: {message}")
                # Return True to keep GitOps mode, assume rules are already available
                return True, f"GitOps sync failed but continuing: {message}"

        except Exception as e:
            error_msg = f"GitOps synchronization error: {str(e)}"
            logger.error(error_msg)
            # Return True to keep GitOps mode, assume rules are already available
            return True, f"GitOps sync error but continuing: {error_msg}"

    def is_configured(self) -> bool:
        """Check if GitOps is configured"""
        try:
            gitops_manager = self._get_gitops_manager()
            config = gitops_manager.load_config()
            repository = config.get("repository")
            return bool(repository)
        except Exception as e:
            logger.error(f"Error checking GitOps configuration: {str(e)}")
            return False

    def get_gitops_status(self) -> dict:
        """Get current GitOps status"""
        try:
            gitops_manager = self._get_gitops_manager()
            config = gitops_manager.load_config()
            current_repo = config.get("repository")

            return {
                "enabled": bool(current_repo),
                "repository": current_repo.get("name") if current_repo else None,
                "url": current_repo.get("url") if current_repo else None,
                "branch": current_repo.get("branch") if current_repo else None,
            }
        except Exception as e:
            logger.error(f"Error getting GitOps status: {str(e)}")
            return {"enabled": False, "error": str(e)}


# Standalone functions for compatibility with tests
async def sync_rules_from_gitops() -> bool:
    """
    Sync rules from GitOps repository

    Returns:
        True if sync was successful, False otherwise
    """
    try:
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        rule_manager = RuleManager()

        # Check if GitOps should be used
        should_use = rule_manager.should_use_gitops()
        logger.info(f"DEBUG: should_use_gitops returned: {should_use}")
        if not should_use:
            logger.info("DEBUG: GitOps not enabled, returning False")
            return False

        # Get configuration
        config = gitops_manager.load_config()
        repository = config.get("repository")
        logger.info(f"DEBUG: repository config: {repository}")

        if not repository:
            logger.info("DEBUG: No repository configured, returning False")
            return False

        # Clone or update repository
        success, message = gitops_manager.clone_or_update_repo(repository)
        logger.info(f"DEBUG: clone_or_update_repo success: {success}, message: {message}")
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
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        rule_manager = RuleManager()

        # Check if GitOps should be used
        if not rule_manager.should_use_gitops():
            return False

        # Get configuration
        config = gitops_manager.load_config()
        repository = config.get("repository")

        if not repository:
            return False

        # Clone or update repository
        success, _ = gitops_manager.clone_or_update_repo(repository)
        return success
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
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        rule_manager = RuleManager()

        logger.debug("About to call should_use_gitops")
        should_use_gitops = rule_manager.should_use_gitops()
        logger.debug(f"should_use_gitops returned: {should_use_gitops}, type: {type(should_use_gitops)}")
        logger.info(
            f"DEBUG: should_use_gitops in get_gitops_status: {should_use_gitops}, type: {type(should_use_gitops)}"
        )
        config = gitops_manager.load_config()
        logger.info(f"DEBUG: config loaded: {config}, type: {type(config)}")
        repository = config.get("repository")
        logger.info(f"DEBUG: repository in get_gitops_status: {repository}, type: {type(repository)}")

        result = {"configured": should_use_gitops and bool(repository), "repository": None}
        logger.info(
            f"DEBUG: result configured: {result['configured']}, should_use_gitops: {should_use_gitops}, bool(repository): {bool(repository)}"
        )

        if repository:
            result["repository"] = {
                "url": repository.get("url"),
                "branch": repository.get("branch", "main"),
                "last_sync": "Unknown",  # We don't track this in the current implementation
            }
            logger.info(f"DEBUG: repository dict created: {result['repository']}")

        logger.info(f"DEBUG: final result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error getting GitOps status: {str(e)}")
        return {"configured": False, "repository": None, "error": str(e)}


def get_repository_info() -> dict:
    """
    Get repository information (synchronous version for tests)

    Returns:
        Dictionary with repository information
    """
    try:
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        config = gitops_manager.load_config()
        repository = config.get("repository")

        if repository:
            return {
                "url": repository.get("url"),
                "branch": repository.get("branch", "main"),
                "last_sync": "Unknown",  # We don't track this in the current implementation
            }
        else:
            return {}
    except Exception as e:
        logger.error(f"Error getting repository info: {str(e)}")
        return {}
