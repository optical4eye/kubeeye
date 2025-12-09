#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule management module - provides unified interface for processing rules for various components
Updated version, supports assertion system
"""
from typing import Dict, List, Tuple, Optional
from utils.rule_loader import load_rules, Rule


class RuleManager:
    """Rule management class providing unified interface for rule operations"""

    @staticmethod
    def get_rule_type_display_names() -> Dict[str, str]:
        """Get display names for rule types"""
        return {
            "node": "Node status check rules",
            "prometheus": "Prometheus metrics rules",
            "opa": "OPA compliance check rules",
        }

    @staticmethod
    def get_enabled_rules(rule_type: str, use_gitops: bool = False) -> List[Rule]:
        """Get enabled rules of specified type"""
        all_rules = load_rules(rule_type, use_gitops=use_gitops)
        enabled_rules = [rule for rule in all_rules if rule.enabled]

        # Debug information
        if use_gitops:
            print(
                f"GitOps rules for {rule_type}: found {len(all_rules)} total, {len(enabled_rules)} enabled"
            )
            for rule in enabled_rules:
                print(f"  - {rule.id}: {rule.name} (enabled: {rule.enabled})")

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
        """Determine whether to use GitOps rules"""
        try:
            from utils.gitops_manager import GitOpsRuleManager

            gitops_manager = GitOpsRuleManager()
            config = gitops_manager.load_config()

            # If there is configuration from ENV variables, use GitOps
            if config.get("from_env"):
                return True

            # If no ENV variables, but GitOps mode is saved in config
            if config.get("mode") == "gitops" and config.get("repository") is not None:
                # Check if required ENV variables are set
                if not gitops_manager.has_env_config():
                    print(
                        "GitOps configured in config, but ENV variables not set - using local mode"
                    )
                    return False
                return True

            return False
        except Exception:
            return False
