#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule management module - provides unified interface for processing rules for various components
Updated version, supports assertion system and rule display in table format
"""
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import pandas as pd
import yaml
from utils.rule_loader import load_rules, Rule


class RuleManager:
    """Rule management class providing unified interface for rule operations"""

    @staticmethod
    def get_rule_type_display_names() -> Dict[str, str]:
        """Get display names for rule types"""
        return {
            'node': 'Node status check rules',
            'prometheus': 'Prometheus metrics rules',
            'opa': 'OPA compliance check rules'
        }

    @staticmethod
    def get_enabled_rules(rule_type: str, use_gitops: bool = False) -> List[Rule]:
        """Get enabled rules of specified type"""
        all_rules = load_rules(rule_type, use_gitops=use_gitops)
        enabled_rules = [rule for rule in all_rules if rule.enabled]

        # Debug information
        if use_gitops:
            print(f"GitOps rules for {rule_type}: found {len(all_rules)} total, {len(enabled_rules)} enabled")
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
    def get_rule_selection_data(cls, rule_type: str, use_gitops: bool = False) -> Tuple[List[Rule], List[str], Dict[str, str]]:
        """Get data necessary for rule selection"""
        rules = cls.get_enabled_rules(rule_type, use_gitops)
        options = cls.get_rule_options(rules)
        display_names = cls.get_rule_display_names(rules)
        return rules, options, display_names

    @classmethod
    def rule_to_dataframe(cls, rules: List[Rule]) -> pd.DataFrame:
        """Convert list of rules to DataFrame for table display"""
        if not rules:
            return pd.DataFrame()

        data = []
        for rule in rules:
            data.append({
                "ID": rule.id,
                "Name": rule.name,
                "Category": rule.category,
                "Severity": rule.severity,
                "Description": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Assertions count": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Source": " Git" if rule.source == 'git' else " Local"
            })
        return pd.DataFrame(data)

    @classmethod
    def create_rule_selection(cls, rule_type: str, key_suffix: str = "", use_gitops: bool = False) -> List[str]:
        """
        Simplified version: rule selection via data_editor without additional table binding
        Update session_state based on data_editor editing results
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type, use_gitops)
        if not rules:
            source_type = "GitOps" if use_gitops else "local"
            st.info(f"No enabled rules found for {cls.get_rule_type_display_names()[rule_type]} in {source_type} rules.")

            # Show additional debug information
            all_rules = load_rules(rule_type, include_disabled=True, use_gitops=use_gitops)
            if all_rules:
                st.warning(f"Found {len(all_rules)} rules, but all are disabled or have loading issues")
                for rule in all_rules:
                    st.write(f"- {rule.id}: {rule.name} (enabled: {rule.enabled})")

            return []

        form_key = f"rule_selection_{rule_type}{key_suffix}"
        table_key = f"rule_table_{rule_type}{key_suffix}"

        # Initialize session state if not yet initialized
        if form_key not in st.session_state:
            st.session_state[form_key] = options.copy()  # All selected by default

        data = []
        for rule in rules:
            selected = rule.id in st.session_state[form_key]
            data.append({
                "Selection": selected,
                "ID": rule.id,
                "Name": rule.name,
                "Category": rule.category,
                "Severity": rule.severity,
                "Description": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Assertions count": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Source": " Git" if rule.source == 'git' else " Local"
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Selection": st.column_config.CheckboxColumn("Selection", help="Select rules for execution", width="small"),
                "ID": st.column_config.TextColumn("Rule ID", width="medium"),
                "Name": st.column_config.TextColumn("Rule name", width="medium"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Severity": st.column_config.TextColumn("Severity", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Assertions count": st.column_config.NumberColumn("Assertions count", width="small"),
                "Source": st.column_config.TextColumn("Source", width="small"),
            },
            disabled=["ID", "Name", "Category", "Severity", "Description", "Assertions count", "Source"],
            key=table_key,
            on_change=None
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Selection"]]

        # Update session_state without page reload
        st.session_state[form_key] = selected_rules

        source_type = "GitOps" if use_gitops else "local"
        st.caption(f"Selected: {len(selected_rules)}/{len(options)} {source_type} rules")
        return selected_rules

    @classmethod
    def create_rule_selection_in_form(cls, rule_type: str, key_suffix: str = "", use_gitops: bool = False) -> List[str]:
        """
        Rule selection in form via data_editor with optimization to reduce number of updates
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type, use_gitops)
        if not rules:
            source_type = "GitOps" if use_gitops else "local"
            st.info(f"No enabled rules found for {cls.get_rule_type_display_names()[rule_type]} in {source_type} rules.")
            return []

        form_key = f"rule_selection_form_{rule_type}{key_suffix}"
        table_key = f"rule_table_form_{rule_type}{key_suffix}"

        if form_key not in st.session_state:
            st.session_state[form_key] = options.copy()

        data = []
        for rule in rules:
            selected = rule.id in st.session_state[form_key]
            data.append({
                "Selection": selected,
                "ID": rule.id,
                "Name": rule.name,
                "Category": rule.category,
                "Severity": rule.severity,
                "Description": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Assertions count": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Source": " Git" if rule.source == 'git' else " Local"
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Selection": st.column_config.CheckboxColumn("Selection", help="Select rules for execution", width="small"),
                "ID": st.column_config.TextColumn("Rule ID", width="medium"),
                "Name": st.column_config.TextColumn("Rule name", width="medium"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Severity": st.column_config.TextColumn("Severity", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Assertions count": st.column_config.NumberColumn("Assertions count", width="small"),
                "Source": st.column_config.TextColumn("Source", width="small"),
            },
            disabled=["ID", "Name", "Category", "Severity", "Description", "Assertions count", "Source"],
            key=table_key,
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Selection"]]

        if st.session_state[form_key] != selected_rules:
            st.session_state[form_key] = selected_rules

        source_type = "GitOps" if use_gitops else "local"
        st.caption(f"Selected: {len(selected_rules)}/{len(options)} {source_type} rules")
        return selected_rules

    @classmethod
    def create_rule_selection_tabs(
        cls, node_check: bool, prometheus_check: bool, opa_check: bool, key_suffix: str = "",
        in_form: bool = False, use_gitops: bool = False
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Create rule selection tabs, showing only available rule types,
        allowing user to select rules in each tab.
        """
        selected_node_rules = []
        selected_prometheus_rules = []
        selected_opa_rules = []

        rule_configs = [
            {
                "available": node_check,
                "type": "node",
                "tab_label": "Node check rules",
                "result_var": "selected_node_rules"
            },
            {
                "available": prometheus_check,
                "type": "prometheus",
                "tab_label": "Prometheus check rules",
                "result_var": "selected_prometheus_rules"
            },
            {
                "available": opa_check,
                "type": "opa",
                "tab_label": "OPA check rules",
                "result_var": "selected_opa_rules"
            }
        ]

        available_configs = [cfg for cfg in rule_configs if cfg["available"]]

        if not available_configs:
            st.warning("No available inspection types, please check cluster configuration.")
            return selected_node_rules, selected_prometheus_rules, selected_opa_rules

        for cfg in available_configs:
            key_suffix_type = f"{key_suffix}_{cfg['type']}"
            selection_key = f"rule_selection_{cfg['type']}{key_suffix_type}"
            if selection_key not in st.session_state:
                cls.get_rule_selection_data(cfg["type"], use_gitops)

        tab_labels = [cfg["tab_label"] for cfg in available_configs]

        tab_key = f"rule_tabs{key_suffix}"

        if tab_key not in st.session_state or st.session_state[tab_key] >= len(tab_labels):
            st.session_state[tab_key] = 0

        rule_tabs = st.tabs(tab_labels)

        for i, cfg in enumerate(available_configs):
            with rule_tabs[i]:
                if in_form:
                    selected_rules = cls.create_rule_selection_in_form(
                        cfg["type"],
                        key_suffix=f"{key_suffix}_{cfg['type']}",
                        use_gitops=use_gitops
                    )
                else:
                    selected_rules = cls.create_rule_selection(
                        cfg["type"],
                        key_suffix=f"{key_suffix}_{cfg['type']}",
                        use_gitops=use_gitops
                    )

                if cfg["result_var"] == "selected_node_rules":
                    selected_node_rules = selected_rules
                elif cfg["result_var"] == "selected_prometheus_rules":
                    selected_prometheus_rules = selected_rules
                elif cfg["result_var"] == "selected_opa_rules":
                    selected_opa_rules = selected_rules

        return selected_node_rules, selected_prometheus_rules, selected_opa_rules

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
                    print("GitOps configured in config, but ENV variables not set - using local mode")
                    return False
                return True

            return False
        except Exception:
            return False
