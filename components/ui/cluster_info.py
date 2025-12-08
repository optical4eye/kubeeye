#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster information display component
"""
import streamlit as st
from utils.cluster_config import get_cluster

def display_cluster_info(cluster_name):
    """Display basic cluster information"""
    cluster_config = get_cluster(cluster_name)
    if not cluster_config:
        st.error(f"Failed to load cluster configuration: {cluster_name}")
        return None, None, None

    with st.expander("Basic cluster information", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Cluster name:** {cluster_name}")
            description = getattr(cluster_config, 'description', '') or cluster_config.config.get('description', 'No description available')
            st.markdown(f"**Cluster description:** {description}")
            nodes = cluster_config.get_nodes()
            st.markdown(f"**Number of nodes:** {len(nodes)}")

        with col2:
            prometheus_config = cluster_config.get_prometheus_config() or {}
            if prometheus_config and prometheus_config.get('enabled', False):
                st.markdown(f"**Prometheus URL:** {prometheus_config.get('url', 'N/A')}")
            else:
                st.markdown("**Prometheus:** not configured")

            kubeconfig = cluster_config.get_kubeconfig()
            if kubeconfig:
                st.markdown("**Kubeconfig:** configured")
            else:
                st.markdown("**Kubeconfig:** not configured")

    return cluster_config, cluster_config.get_nodes(), cluster_config.get_prometheus_config() or {}
