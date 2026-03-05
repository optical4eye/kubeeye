#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core.logging import get_logger

"""
Rule management module - provides unified interface for processing rules for various components
Updated version, supports assertion system
"""
from typing import Dict, List
from infra.rules.rule_loader import load_rules, Rule

logger = get_logger(__name__)


class RuleManager:
    """Rule management class providing unified interface for rule operations"""

    @staticmethod
    def get_rule_type_display_names() -> Dict[str, str]:
        """Get display names for rule types"""
        return {
            "node": "Node status check rules",
            "opa": "OPA compliance check rules",
        }

    @staticmethod
    def get_enabled_rules(rule_type: str) -> List[Rule]:
        """Get enabled rules of specified type"""
        all_rules = load_rules(rule_type)
        enabled_rules = [rule for rule in all_rules if rule.enabled]

        # Debug information
        logger.info(f"GitOps rules for {rule_type}: found {len(all_rules)} total, {len(enabled_rules)} enabled")
        for rule in enabled_rules:
            logger.info(f"  - {rule.id}: {rule.name} (enabled: {rule.enabled})")

        return enabled_rules

    @staticmethod
    def get_rule_display_names(rules: List[Rule]) -> Dict[str, str]:
        """Get display names for rules by their ID"""
        return {rule.id: rule.name for rule in rules}

    @staticmethod
    def get_rule_options(rules: List[Rule]) -> List[str]:
        """Get list of rule IDs"""
        return [rule.id for rule in rules]

    @classmethod
    def should_use_gitops(cls) -> bool:
        """Determine whether to use GitOps rules - always returns True since GitOps is the only source"""
        return True
