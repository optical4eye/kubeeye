#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rules management routes
"""

import logging
from fastapi import APIRouter, HTTPException
from utils.rule_manager import RuleManager
from utils.rule_loader import load_rules

router = APIRouter()

# Setup logger
logger = logging.getLogger(__name__)


def _sync_gitops_repository() -> bool:
    """Sync GitOps repository"""
    try:
        from utils.gitops_manager import GitOpsRuleManager

        gitops_manager = GitOpsRuleManager()
        config = gitops_manager.load_config()
        current_repo = config.get("repository")

        if not current_repo:
            return False

        logger.debug(
            f"GitOps mode enabled, syncing repository {current_repo['name']}..."
        )
        success, message = gitops_manager.clone_or_update_repo(current_repo)
        if success:
            logger.debug(f"Repository synchronized: {message}")
            return True
        else:
            logger.error(f"Failed to sync repository: {message}")
            return False
    except Exception as e:
        logger.error(f"GitOps sync failed: {str(e)}")
        return False


def _load_rules_for_types(rule_types: list[str], use_gitops: bool) -> dict[str, list]:
    """Load rules for specified types"""
    rules = {}
    for rule_type in rule_types:
        rules[rule_type] = load_rules(rule_type, use_gitops=use_gitops)
    return rules


def _log_rules_statistics(rules: dict[str, list], use_gitops: bool) -> int:
    """Log loaded rules statistics"""
    total_rules = sum(
        len(rules.get(rule_type, [])) for rule_type in ["node", "prometheus", "opa"]
    )
    logger.debug(f"Loaded {total_rules} rules total (GitOps: {use_gitops})")
    for rule_type, rule_list in rules.items():
        logger.debug(f"{rule_type}: {len(rule_list)} rules")
    return total_rules


def _fallback_to_local_rules() -> tuple[dict[str, list], bool]:
    """Execute fallback to local rules"""
    logger.debug("GitOps enabled but no rules found, trying local fallback")
    local_rules = _load_rules_for_types(["node", "prometheus", "opa"], use_gitops=False)
    local_total = _log_rules_statistics(local_rules, False)
    return local_rules, local_total > 0


@router.get("/rules")
async def get_rules():
    """Get rules"""
    try:
        use_gitops = RuleManager.should_use_gitops()
        logger.debug(f"GitOps mode: {use_gitops}")

        # Sync GitOps repository if necessary
        if use_gitops and not _sync_gitops_repository():
            use_gitops = False

        # Load rules
        rules = _load_rules_for_types(["node", "prometheus", "opa"], use_gitops)
        total_rules = _log_rules_statistics(rules, use_gitops)

        # Fallback to local rules if GitOps didn't work
        if use_gitops and total_rules == 0:
            rules, has_local_rules = _fallback_to_local_rules()
            if has_local_rules:
                use_gitops = False
            else:
                return {
                    "rules": {"node": [], "prometheus": [], "opa": []},
                    "use_gitops": False,
                }

        return {"rules": rules, "use_gitops": use_gitops}
    except Exception as e:
        logger.error(f"Failed to load rules: {str(e)}")
        # Return empty rules as fallback
        return {"rules": {"node": [], "prometheus": [], "opa": []}, "use_gitops": False}
