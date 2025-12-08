#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster configuration management module for managing cluster connection configuration information
"""

import os
import json
import yaml
import logging
import streamlit as st
from pathlib import Path
from typing import Dict, List
from utils.inspection_result import get_latest_result_by_cluster

logger = logging.getLogger(__name__)

# Definition of data directories
DATA_DIR = Path(__file__).parent.parent / "data"
CLUSTERS_DIR = DATA_DIR / "clusters"
RESULTS_DIR = DATA_DIR / "results"

# Ensure that directories exist
os.makedirs(CLUSTERS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

class ClusterConfig:
    """Cluster configuration management class"""

    def __init__(self, cluster_name: str):
        self.cluster_name = cluster_name
        self.config_path = CLUSTERS_DIR / f"{cluster_name}.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load cluster configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'name': self.cluster_name,
            'nodes': [],
            'prometheus': {
                'url': '',
                'username': '',
                'password': '',
                'token': '',
                'enabled': False
            },
            'kubeconfig': '',
            'created_at': '',
            'updated_at': ''
        }

    def save_config(self) -> None:
        """Save cluster configuration"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def update_node(self, node_info: Dict) -> None:
        """Add or update node information"""
        # Create a copy of node information
        node_copy = node_info.copy()

        # Ensure password is stored in plain text
        if node_copy.get('auth_type') == 'password' and node_copy.get('password'):
            node_copy['password_encrypted'] = False

        # Update node information
        for i, node in enumerate(self.config['nodes']):
            if node['ip'] == node_info['ip']:
                self.config['nodes'][i] = node_copy
                self.save_config()
                return

        # If not exists, add new node
        self.config['nodes'].append(node_copy)
        self.save_config()

    def remove_node(self, node_ip: str) -> bool:
        """Remove node information"""
        for i, node in enumerate(self.config['nodes']):
            if node['ip'] == node_ip:
                del self.config['nodes'][i]
                self.save_config()
                return True
        return False

    def update_prometheus(self, prometheus_info: Dict) -> None:
        """Update Prometheus configuration"""
        # Create a copy of the configuration
        prometheus_copy = prometheus_info.copy()

        # Ensure password and token are stored in plain text
        if prometheus_copy.get('password'):
            prometheus_copy['password_encrypted'] = False

        if prometheus_copy.get('token'):
            prometheus_copy['token_encrypted'] = False

        self.config['prometheus'].update(prometheus_copy)
        self.save_config()

    def update_kubeconfig(self, kubeconfig: str) -> None:
        """Update Kubeconfig configuration"""
        self.config['kubeconfig'] = kubeconfig
        self.save_config()

    def get_nodes(self) -> List[Dict]:
        """Get cluster node list"""
        nodes = []
        for node in self.config['nodes']:
            node_copy = node.copy()
            # Explicitly remove password encryption flag, ensure all passwords are treated as plain text
            if node_copy.get('password_encrypted'):
                logger.info(f"Password for node {node_copy.get('ip')} is marked as encrypted, but will be used in plain text")
                node_copy['password_encrypted'] = False
            nodes.append(node_copy)
        return nodes

    def get_prometheus_config(self) -> Dict:
        """Get Prometheus configuration"""
        prometheus_config = self.config['prometheus'].copy()

        # Remove password encryption flag
        if prometheus_config.get('password_encrypted'):
            logger.info("Prometheus password is marked as encrypted, but will be used in plain text")
            prometheus_config['password_encrypted'] = False

        # Remove token encryption flag
        if prometheus_config.get('token_encrypted'):
            logger.info("Prometheus token is marked as encrypted, but will be used in plain text")
            prometheus_config['token_encrypted'] = False

        return prometheus_config

    def get_kubeconfig(self) -> str:
        """Get Kubeconfig"""
        return self.config['kubeconfig']

    def get_dict(self) -> Dict:
        """Get dictionary representation of cluster configuration"""
        config_dict = self.config.copy()

        # Add structured data for easy use by inspectors
        config_dict.update({
            'nodes': self.get_nodes(),
            'prometheus': self.get_prometheus_config(),
            'kubeconfig': {'kubeconfig': self.get_kubeconfig()},  # Wrap as dictionary
            'opa': {'kubeconfig': self.get_kubeconfig()}  # Format required by OPA inspector
        })

        return config_dict


def list_clusters() -> List[str]:
    """List all cluster names"""
    clusters = []
    for file_path in CLUSTERS_DIR.glob('*.json'):
        clusters.append(file_path.stem)
    return clusters


def get_cluster(cluster_name: str) -> ClusterConfig:
    """Get cluster configuration object"""
    return ClusterConfig(cluster_name)


def delete_cluster(cluster_name: str) -> bool:
    """Delete cluster configuration"""
    config_path = CLUSTERS_DIR / f"{cluster_name}.json"
    if config_path.exists():
        config_path.unlink()
        return True
    return False


def load_kubeconfig(kubeconfig_str: str) -> Dict:
    """Load kubeconfig content as dictionary"""
    try:
        return yaml.safe_load(kubeconfig_str)
    except yaml.YAMLError:
        return {}

@st.cache_data(ttl=600)  # Cache for 10 minutes
def list_clusters_cached() -> List[str]:
    """Cached loading of cluster list"""
    return list_clusters()

def get_cluster_status_counts_fast() -> Dict[str, int]:
    """Fast counting of cluster statuses without loading all results"""
    clusters = list_clusters_cached()
    counts = {'healthy': 0, 'warning': 0, 'critical': 0, 'unknown': 0}

    for cluster_name in clusters:
        try:
            status = get_cluster_quick_status(cluster_name)
            counts[status] += 1
        except:
            counts['unknown'] += 1

    return counts

def get_cluster_quick_status(cluster_name: str) -> str:
    """Quick cluster status check"""
    latest_result = get_latest_result_by_cluster(cluster_name)

    if not latest_result:
        # If no inspection results, consider cluster healthy by default
        return 'healthy'

    critical = latest_result.get('critical', 0)
    warning = latest_result.get('warning', 0)

    if critical > 0:
        return 'critical'
    elif warning > 0:
        return 'warning'
    else:
        return 'healthy'
