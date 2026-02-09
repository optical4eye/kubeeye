#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rules management routes
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends
from infra.rules.rule_manager import RuleManager
from infra.rules.rule_loader import load_rules
from api.dependencies import get_current_user
from db.models.user import User

from core.logging import get_logger

router = APIRouter()

logger = get_logger(__name__)


def _sync_gitops_repository(force: bool = False) -> bool:
    """Sync GitOps repository with time-based caching"""
    try:
        from infra.gitops.gitops_manager import GitOpsManager

        gitops_manager = GitOpsManager()
        config = gitops_manager.load_config()
        current_repo = config.get("repository")

        if not current_repo:
            return False

        success, message = gitops_manager.sync_repository_if_needed(current_repo, force=force)
        return success
    except Exception as e:
        logger.error(f"GitOps sync failed: {str(e)}")
        return False


def _load_rules_for_types(rule_types: List[str], use_gitops: bool) -> Dict[str, List]:
    """Load rules for specified types"""
    rules = {}
    for rule_type in rule_types:
        rules[rule_type] = load_rules(rule_type, use_gitops=use_gitops)
    return rules


def _log_rules_statistics(rules: Dict[str, List], use_gitops: bool) -> int:
    """Log loaded rules statistics"""
    total_rules = sum(len(rules.get(rule_type, [])) for rule_type in ["node", "opa"])
    logger.debug(f"Loaded {total_rules} rules total (GitOps: {use_gitops})")
    for rule_type, rule_list in rules.items():
        logger.debug(f"{rule_type}: {len(rule_list)} rules")
    return total_rules


@router.get("/rules")
async def get_rules(
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get rules"""
    try:
        use_gitops = RuleManager.should_use_gitops()
        logger.debug(f"GitOps mode: {use_gitops}")

        # Sync GitOps repository if necessary
        if use_gitops and not _sync_gitops_repository():
            use_gitops = False

        # Load rules
        rules = _load_rules_for_types(["node", "opa"], use_gitops)
        total_rules = _log_rules_statistics(rules, use_gitops)

        # Filter by tags if specified
        if tags:
            tag_filters = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_filters:
                filtered_rules = {}
                for rule_type, rule_list in rules.items():
                    filtered_rules[rule_type] = [
                        rule for rule in rule_list if any(tag in rule.tags for tag in tag_filters)
                    ]
                rules = filtered_rules
                logger.debug(
                    f"Filtered rules by tags {tag_filters}: {sum(len(rules.get(rt, [])) for rt in ['node', 'opa'])} rules remaining"
                )

        return {"rules": rules, "use_gitops": use_gitops}
    except Exception as e:
        logger.error(f"Failed to load rules: {str(e)}")
        # Return empty rules as fallback
        return {"rules": {"node": [], "opa": []}, "use_gitops": False}


@router.get("/rules/tags")
async def get_rule_tags(
    current_user: User = Depends(get_current_user)
):
    """Get all unique tags from rules"""
    try:
        use_gitops = RuleManager.should_use_gitops()
        logger.debug(f"GitOps mode: {use_gitops}")

        # Sync GitOps repository if necessary
        if use_gitops and not _sync_gitops_repository():
            use_gitops = False

        # Load rules
        rules = _load_rules_for_types(["node", "opa"], use_gitops)

        # Collect all unique tags with counts
        tag_count = {}
        for rule_type, rule_list in rules.items():
            for rule in rule_list:
                if rule.tags:
                    for tag in rule.tags:
                        tag_count[tag] = tag_count.get(tag, 0) + 1

        # Sort tags by count descending
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)

        logger.debug(f"Found {len(sorted_tags)} unique tags with counts: {sorted_tags}")

        return {"tags": [{"tag": tag, "count": count} for tag, count in sorted_tags], "use_gitops": use_gitops}
    except Exception as e:
        logger.error(f"Failed to load rule tags: {str(e)}")
        # Return empty tags as fallback
        return {"tags": [], "use_gitops": False}
