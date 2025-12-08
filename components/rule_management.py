#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern rule management component — GitOps mode support
"""
import streamlit as st
from typing import Dict
import pandas as pd
from utils.gitops_manager import GitOpsRuleManager
from utils.rule_loader import load_rules

def render_rule_management_tab():
    """Display rule management tab"""
    st.markdown("### Rule Management Center")

    gitops_manager = GitOpsRuleManager()
    config = gitops_manager.load_config()

    # Mode selection
    render_mode_selector(gitops_manager, config)

    # Display interface depending on mode
    if config["mode"] == "local":
        render_local_mode(gitops_manager)
    else:
        render_gitops_mode(gitops_manager, config)


def render_mode_selector(gitops_manager: GitOpsRuleManager, config: Dict):
    """Display mode selector"""
    st.markdown("#### Rule Management Mode")

    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        current_mode = config.get("mode", "local")
        mode_options = {
            "local": "Local mode",
            "gitops": "GitOps mode"
        }

        # If repository from ENV, block mode selection
        if is_env_config or is_env_repo:
            st.selectbox(
                "Select management mode",
                options=["gitops"],
                format_func=lambda x: " GitOps mode (managed via ENV)",
                index=0,
                disabled=True
            )
            st.info("Mode is managed via environment variables")
        else:
            # Check if ENV variables are set
            has_env = gitops_manager.has_env_config()

            if has_env:
                # ENV variables set - can select mode
                selected_mode = st.selectbox(
                    "Select management mode",
                    options=list(mode_options.keys()),
                    format_func=lambda x: mode_options[x],
                    index=list(mode_options.keys()).index(current_mode)
                )

                if selected_mode != current_mode:
                    config["mode"] = selected_mode
                    gitops_manager.save_config(config)
                    st.success(f"Switched to {mode_options[selected_mode]}")
                    st.rerun()
            else:
                # ENV variables not set - local mode only
                st.selectbox(
                    "Select management mode",
                    options=["local"],
                    format_func=lambda x: " Local mode (ENV variables not set)",
                    index=0,
                    disabled=True
                )
                st.info("Set environment variables to use GitOps")

    with col2:
        # Show local rules count only in local mode
        if config.get("mode") == "local":
            local_rules_count = sum(len(load_rules(rt)) for rt in ["node", "prometheus", "opa"])
            st.metric("Local rules", local_rules_count)
        else:
            # In GitOps mode show GitOps rules information
            current_repo = config.get("repository")
            if current_repo:
                repo_name = current_repo.get("name", "Unknown")
                git_rules = gitops_manager.get_repo_rules(repo_name)
                st.metric("GitOps rules", len(git_rules))
            else:
                st.metric("GitOps rules", 0)

    with col3:
        if st.button(" Refresh", type="primary", help="Refresh rules list"):
            st.rerun()


def render_local_mode(gitops_manager: GitOpsRuleManager):
    """Display local mode interface"""
    st.markdown("#### Local rules")
    render_local_rule_list()


def render_gitops_mode(gitops_manager: GitOpsRuleManager, config: Dict):
    """Display GitOps mode interface"""
    st.markdown("#### GitOps Rule Management")

    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    if is_env_config or is_env_repo:
        st.info(" Configuration is managed via environment variables")

    tab_manage, tab_browse = st.tabs([" Repository setup", " Browse rules"])

    with tab_manage:
        render_repository_management(gitops_manager, config)

    with tab_browse:
        render_git_rule_browser(gitops_manager, config)


def render_local_rule_list():
    """Display local rules list"""
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_types = st.multiselect(
            "Select rule types",
            ["node", "prometheus", "opa"],
            default=["node", "prometheus", "opa"],
            format_func=lambda x: {"node": " Node rules", "prometheus": " Monitoring rules", "opa": " Security rules"}[x]
        )

    with col2:
        show_disabled = st.checkbox("Show disabled", value=False)

    all_rules = []
    for rule_type in selected_types:
        rules = load_rules(rule_type, include_disabled=show_disabled)
        all_rules.extend(rules)

    if not all_rules:
        st.info("No rules found, check directory or create new rules.")
        return

    rule_data = []
    severity_map = {
        "info": "Information",
        "low": "Low",
        "warning": "Warning",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical"
    }

    for rule in all_rules:
        rule_data.append({
            "ID": rule.id,
            "Name": rule.name,
            "Type": {"node": "Node", "prometheus": "Monitoring", "opa": "Security"}[rule.type],
            "Status": "Enabled" if rule.enabled else "Disabled",
            "Severity": severity_map.get(rule.severity, rule.severity),
            "Description": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description
        })

    if rule_data:
        df = pd.DataFrame(rule_data)
        st.dataframe(df, use_container_width=True)


def render_repository_management(gitops_manager: GitOpsRuleManager, config: Dict):
    """Manage single repository"""
    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    if current_repo and not (is_env_config or is_env_repo):
        # Display current repository - view and delete only
        st.markdown("### Current repository")
        st.info(" Repository cannot be changed. To change repository, first delete the current one.")

        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**Rules name:** `{current_repo['name']}`")
                st.markdown(f"**URL:** `{current_repo['url']}`")
                st.markdown(f"**Branch:** `{current_repo.get('branch', 'main')}`")
                if current_repo.get('username'):
                    st.markdown(f"**Username:** `{current_repo['username']}`")
                if current_repo.get('token'):
                    st.markdown(" **Access: with token**")
                ssl_verification_status = "Enabled" if not current_repo.get('insecure') else "Disabled"
                st.markdown(f"**SSL verification:** `{ssl_verification_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Description:** {current_repo['description']}")

                # Check synchronization
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("Repository synchronized")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Rules found:** {rules_count} (all automatically enabled)")
                else:
                    st.warning(" Repository not synchronized")

            with col2:
                if st.button(" Synchronize", type="primary"):
                    sync_repository(gitops_manager, current_repo)

            with col3:
                if st.button(" Delete", type="primary", use_container_width=True):
                    success, message = gitops_manager.remove_repository()
                    if success:
                        st.success(message)
                        st.rerun()

        st.markdown("---")
        st.warning("To add a new repository, first delete the current one")

    elif current_repo and (is_env_config or is_env_repo):
        # Repository from ENV variables - view only
        st.markdown("### Repository from environment variables")
        st.info(" This repository is configured via environment variables and cannot be changed through the interface.")

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Rules name:** `{current_repo['name']}`")
                st.markdown(f"**URL:** `{current_repo['url']}`")
                st.markdown(f"**Branch:** `{current_repo.get('branch', 'main')}`")
                if current_repo.get('username'):
                    st.markdown(f"**Username:** `{current_repo['username']}`")
                if current_repo.get('token'):
                    st.markdown(" **Access: with token**")
                insecure_status = "Disabled" if current_repo.get('insecure') else "Enabled"
                st.markdown(f"**SSL verification:** `{insecure_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Description:** {current_repo['description']}")

                # Check synchronization
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("Repository synchronized")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Rules found:** {rules_count} (all automatically enabled)")
                else:
                    st.warning(" Repository not synchronized")

            with col2:
                if st.button(" Synchronize", type="primary"):
                    sync_repository(gitops_manager, current_repo)

    else:
        # Form for adding new repository
        st.markdown("### Adding rules repository")
        st.info(" In GitOps mode, only one repository can be used. After adding, it can only be deleted, not changed.")

        with st.form("add_repo_form"):
            col1, col2 = st.columns(2)

            with col1:
                repo_name = st.text_input("Repository name*",
                                        placeholder="My rules repository")
                repo_url = st.text_input("Repository URL*",
                                       placeholder="https://github.com/user/repo.git")
                repo_branch = st.text_input("Branch",
                                          value="main",
                                          placeholder="main")
                repo_username = st.text_input("Username",
                                            placeholder="username (optional)",
                                            help="Username for authentication")

            with col2:
                repo_description = st.text_area("Description",
                                              placeholder="Rules repository description")
                repo_token = st.text_input("Access token", type="password",
                                         placeholder="ghp_... for GitHub, glpat_... for GitLab",
                                         help="Token for access to private repositories")
                repo_insecure = st.checkbox(
                    "Disable SSL certificate verification",
                    value=False,
                    help="Use only for testing or internal repositories with self-signed certificates"
                )

            submitted = st.form_submit_button("Add repository", type="primary")

            if submitted:
                if not repo_name or not repo_url:
                    st.error("Please fill in required fields (name and URL)")
                else:
                    repo_config = {
                        "name": repo_name,
                        "url": repo_url,
                        "branch": repo_branch or "main",
                        "username": repo_username if repo_username else None,
                        "token": repo_token if repo_token else None,
                        "description": repo_description,
                        "insecure": repo_insecure
                    }

                    success, message = gitops_manager.set_repository(repo_config)
                    if success:
                        st.success(message)
                        sync_repository(gitops_manager, repo_config)
                    else:
                        st.error(message)


def render_git_rule_browser(gitops_manager: GitOpsRuleManager, config: Dict):
    """Browse rules from Git"""
    current_repo = config.get("repository")

    if not current_repo:
        st.warning(" First add a Git repository in the 'Repository setup' section")
        return

    repo_path = gitops_manager.git_rules_dir / current_repo["name"]
    if not repo_path.exists():
        st.warning(f" Repository **{current_repo['name']}** is not synchronized")
        if st.button(" Synchronize now", type="primary"):
            sync_repository(gitops_manager, current_repo)
        return

    git_rules = gitops_manager.get_repo_rules(current_repo["name"])

    if not git_rules:
        st.info(" This repository has no rule files or the structure does not match the expected format")
        st.markdown("""
        **Expected repository structure:**
        ```
        repository-root/
        ├── node/           # Node rules
        │   └── *.yaml
        ├── prometheus/     # Monitoring rules
        │   └── *.yaml
        └── opa/            # Security rules
            └── *.yaml
        ```
        **Note:** All GitOps rules are automatically enabled after synchronization.
        """)
        return

    st.success(f" Repository: **{current_repo['name']}** | Total rules: **{len(git_rules)}** (all automatically enabled)")

    # Filters for rules
    col1, col2 = st.columns([2, 1])
    with col1:
        rule_type_filter = st.multiselect(
            "Filter by type",
            ["node", "prometheus", "opa"],
            default=["node", "prometheus", "opa"],
            format_func=lambda x: {"node": "Nodes", "prometheus": "Monitoring", "opa": "Security"}[x]
        )

    with col2:
        search_term = st.text_input("Search by name")

    filtered_rules = [
        rule for rule in git_rules
        if rule.type in rule_type_filter and
        (not search_term or search_term.lower() in rule.name.lower() or search_term.lower() in rule.description.lower())
    ]

    if not filtered_rules:
        st.info("No rules found for the specified filters")
        return

    for i, rule in enumerate(filtered_rules):
        with st.expander(f"{rule.name} ({rule.type})", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Description:** {rule.description}")
                st.markdown(f"**Type:** {rule.type} | **Severity:** {rule.severity}")
                st.markdown(f"**Category:** {rule.category}")
                if rule.tags:
                    st.markdown(f"**Tags:** {', '.join(rule.tags)}")
                st.markdown(f"**Status:** {'Enabled (automatically)' if rule.enabled else 'Disabled'}")
            with col2:
                if st.button(f"Import", key=f"import_{rule.id}_{i}", type="primary"):
                    if gitops_manager.sync_git_rule_to_local(rule, rule.type):
                        st.success("Imported locally")
                        st.rerun()
                    else:
                        st.error("Import error")


def sync_repository(gitops_manager: GitOpsRuleManager, repo: Dict):
    """Repository synchronization"""
    with st.spinner(f"Synchronizing repository {repo['name']}..."):
        success, message = gitops_manager.clone_or_update_repo(repo)

        if success:
            st.success(message)
            rules_count = len(gitops_manager.get_repo_rules(repo["name"]))
            st.info(f"Rules found: {rules_count} (all automatically enabled)")
        else:
            st.error(message)

        st.rerun()
