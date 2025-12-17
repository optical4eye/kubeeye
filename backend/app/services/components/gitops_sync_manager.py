#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps synchronization manager - handles GitOps repository synchronization
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


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
