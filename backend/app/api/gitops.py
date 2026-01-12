#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps management routes
"""

from fastapi import APIRouter, HTTPException

from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/gitops")
async def get_gitops_status():
    """Get GitOps status"""
    try:
        from infra.gitops.gitops_manager import GitOpsManager

        manager = GitOpsManager()
        config = manager.load_config()
        has_repo = bool(config.get("repository"))

        return {
            "enabled": has_repo,
            "repository": (config.get("repository", {}).get("name") if has_repo else None),
            "last_sync": config.get("last_sync"),
            "status": "configured" if has_repo else "not_configured",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gitops/config")
async def get_gitops_config():
    """Get GitOps config (without sensitive information)"""
    try:
        from infra.gitops.gitops_manager import GitOpsManager

        manager = GitOpsManager()
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
        from infra.gitops.gitops_manager import GitOpsManager

        gitops_manager = GitOpsManager()
        config = gitops_manager.load_config()
        current_repo = config.get("repository")

        if not current_repo:
            return {"success": False, "message": "GitOps repository not configured"}

        logger.debug(f"GitOps mode enabled, forcing sync of repository {current_repo['name']}...")
        success, message = gitops_manager.sync_repository_if_needed(current_repo, force=True)
        if success:
            logger.debug(f"Repository synchronized: {message}")
            return {"message": "GitOps repository synchronized successfully"}
        else:
            logger.error(f"Failed to sync repository: {message}")
            raise HTTPException(status_code=500, detail="Failed to sync GitOps repository")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
