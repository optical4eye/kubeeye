#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Immediate scan component - reworked version, using unified inspection engine
"""
import streamlit as st
from utils.cluster_config import list_clusters
from components.ui import display_cluster_info, select_inspectors
from components.ui.inspection_engine import execute_inspection_unified
from utils.rule_manager import RuleManager
from utils.rule_loader import load_rules

def render_immediate_scan_tab():
    """Display immediate scan tab - using unified inspection engine"""
    # Load cluster list
    clusters = list_clusters()

    if not clusters:
        st.warning("No clusters configured yet. Go to the Cluster Info page to add clusters.")
        if st.button("Go to cluster info page", key="goto_cluster_info_btn1"):
            st.switch_page("pages/1_cluster_info.py")
    else:
        # Cluster selection
        selected_cluster = st.selectbox("Select cluster for inspection", clusters)

        if selected_cluster:
            # Display cluster information and get its settings
            cluster_config, nodes, prometheus_config = display_cluster_info(selected_cluster)
            if not cluster_config:
                return

            # Get kubeconfig
            kubeconfig = cluster_config.get_kubeconfig()

            # Determine available inspection types
            run_node_check, run_prometheus_check, run_opa_check = select_inspectors(nodes, prometheus_config, kubeconfig)

            # Determine whether to use GitOps rules
            use_gitops = RuleManager.should_use_gitops()

            if use_gitops:
                st.success("Using GitOps rules (all rules automatically enabled)")

                # Show debugging information about rules - COLLAPSED by default
                with st.expander("GitOps rules information", expanded=False):
                    for rule_type in ["node", "prometheus", "opa"]:
                        rules = load_rules(rule_type, use_gitops=True)
                        enabled_rules = [r for r in rules if r.enabled]
                        st.write(f"**{rule_type} rules:** {len(enabled_rules)} enabled out of {len(rules)} total")

                        if enabled_rules:
                            st.write("Available rules:")
                            for rule in enabled_rules:
                                st.write(f"- {rule.name} (ID: {rule.id})")
                        else:
                            st.warning(f"No enabled rules for type: {rule_type}")

                            # Show all rules (including disabled) for debugging
                            all_rules = load_rules(rule_type, include_disabled=True, use_gitops=True)
                            if all_rules:
                                st.write("All rules (including disabled):")
                                for rule in all_rules:
                                    status = "enabled" if rule.enabled else "disabled"
                                    st.write(f"- {rule.id}: {rule.name} ({status}: {rule.enabled})")
                            else:
                                st.error(f"No rule files found for type {rule_type} in GitOps")

                                # Show directory structure for debugging
                                from pathlib import Path
                                git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
                                if git_rules_dir.exists():
                                    st.write("GitOps directory contents:")
                                    for item in git_rules_dir.rglob("*"):
                                        if item.is_file():
                                            st.write(f"- File: {item.relative_to(git_rules_dir)}")
                                        elif item.is_dir():
                                            st.write(f"- Directory: {item.relative_to(git_rules_dir)}/")

            # Use new RuleManager to create rule selection area
            selected_node_rules, selected_prometheus_rules, selected_opa_rules = RuleManager.create_rule_selection_tabs(
                run_node_check, run_prometheus_check, run_opa_check, key_suffix="_run", use_gitops=use_gitops
            )

            # Show warning if no rules selected
            total_selected = len(selected_node_rules) + len(selected_prometheus_rules) + len(selected_opa_rules)
            if total_selected == 0:
                st.warning("No rules selected for inspection. Please select at least one rule.")

            # Inspection start button
            run_inspection = st.button("Start inspection", type="primary", disabled=total_selected==0)

            if run_inspection:
                # Form selected rules dictionary
                selected_rules = {}
                if run_node_check and selected_node_rules:
                    selected_rules["node"] = selected_node_rules
                if run_prometheus_check and selected_prometheus_rules:
                    selected_rules["prometheus"] = selected_prometheus_rules
                if run_opa_check and selected_opa_rules:
                    selected_rules["opa"] = selected_opa_rules

                # Execute inspection using unified engine
                success, message, results = execute_inspection_unified(
                    cluster_name=selected_cluster,
                    selected_rules=selected_rules,
                    inspection_type="immediate",
                    show_progress=True,
                    show_ui_feedback=True,
                    use_gitops=use_gitops  # Pass rule source information
                )

                if not success:
                    st.error(f"Inspection error: {message}")
