#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps management routes
"""

import logging
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Setup logger
logger = logging.getLogger(__name__)


@router.get("/gitops")
async def get_gitops_status():
    """Get GitOps status"""
    try:
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        manager = GitOpsRuleManager()
        config = manager.load_config()
        has_repo = bool(config.get("repository"))

        return {
            "enabled": has_repo,
            "repository": config.get("repository", {}).get("name") if has_repo else None,
            "last_sync": config.get("last_sync"),
            "status": "configured" if has_repo else "not_configured"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gitops/config")
async def get_gitops_config():
    """Get GitOps config (without sensitive information)"""
    try:
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        manager = GitOpsRuleManager()
        config = manager.load_config()

        if config.get("repository"):
            # Remove sensitive information
            repo = config["repository"].copy()
            repo.pop("token", None)
            repo.pop("username", None)
            config["repository"] = repo

        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gitops/sync")
async def sync_gitops_repository():
    """Force sync GitOps repository"""
    try:
        from infrastructure.gitops.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        config = gitops_manager.load_config()
        current_repo = config.get("repository")

        if not current_repo:
            return {"success": False, "message": "GitOps repository not configured"}

        logger.debug(
            f"GitOps mode enabled, syncing repository {current_repo['name']}..."
        )
        success, message = gitops_manager.clone_or_update_repo(current_repo)
        if success:
            logger.debug(f"Repository synchronized: {message}")
            return {"message": "GitOps repository synchronized successfully"}
        else:
            logger.error(f"Failed to sync repository: {message}")
            raise HTTPException(
                status_code=500, detail="Failed to sync GitOps repository"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
