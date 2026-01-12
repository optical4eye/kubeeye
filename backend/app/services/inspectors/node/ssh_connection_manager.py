#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Connection Manager for Node Inspector
Handles SSH connection checking and error management
"""

import asyncio
import time
import os
from typing import Dict, List, Any, Optional

from infra.cluster.node_connection import async_test_node_connection
from infra.results.result_formatter import ResultFormatter
from infra.rules.rule_loader import Rule
from core.logging import get_logger

logger = get_logger(__name__)


class SSHConnectionErrorManager:
    """
    Centralized SSH connection error manager
    Ensures each host error is displayed only once
    """

    def __init__(self):
        self._errors_registry = {}  # {node_key: error_data}
        self._result_formatter = ResultFormatter()

    def reset_for_inspection(self):
        """Reset error registry before new inspection"""
        self._errors_registry = {}
        logger.info("SSH connection error registry reset for new inspection")

    def register_connection_error(self, node: Dict, error_message: str) -> str:
        """
        Register connection error for node
        """
        node_key = self._get_node_key(node)

        # If error already registered, don't register again
        if node_key in self._errors_registry:
            return node_key

        # Register new error
        self._errors_registry[node_key] = {
            "node": node.copy(),
            "error_message": error_message,
            "timestamp": time.time(),
            "formatted_result": None,
        }

        logger.warning(f"SSH error registered for node {node_key}: {error_message}")
        return node_key

    def has_connection_error(self, node: Dict) -> bool:
        """Check for connection error for node"""
        node_key = self._get_node_key(node)
        return node_key in self._errors_registry

    def get_connection_error_result(self, node: Dict) -> Optional[Dict]:
        """Get formatted error result for node"""
        node_key = self._get_node_key(node)
        if node_key not in self._errors_registry:
            return None

        error_data = self._errors_registry[node_key]

        # Create formatted result on first request
        if error_data["formatted_result"] is None:
            error_data["formatted_result"] = self._format_connection_error_result(
                error_data["node"], error_data["error_message"]
            )

        return error_data["formatted_result"]

    def get_all_connection_errors(self) -> List[Dict]:
        """Get all registered connection errors"""
        errors = []
        for error_data in self._errors_registry.values():
            if error_data["formatted_result"] is None:
                error_data["formatted_result"] = self._format_connection_error_result(
                    error_data["node"], error_data["error_message"]
                )
            errors.append(error_data["formatted_result"])

        logger.info(f"Retrieved {len(errors)} SSH connection errors from registry")
        return errors

    def get_error_count(self) -> int:
        """Get number of registered errors"""
        return len(self._errors_registry)

    def _format_connection_error_result(self, node: Dict, error_msg: str) -> Dict:
        """
        Format result with connection error
        """
        node_name = node.get("name", node["ip"])
        node_ip = node["ip"]
        node_port = node.get("port", 22)

        # Create dummy rule for formatting
        rule_data = {
            "id": "ssh_connection",
            "name": "SSH connection",
            "solution": "Resolve network connection or SSH configuration issues",
            "config": {"extractors": [], "assertions": []},
        }
        rule = Rule(rule_data)

        formatted_details = f"""Connection error to node {node_name} ({node_ip}:{node_port})

Error message: {error_msg}

Diagnostics:
вЂў Check port {node_port} availability: telnet {node_ip} {node_port} or nc -zv {node_ip} {node_port}
вЂў Ensure SSH service is running on the node
вЂў Check credentials correctness (username, password/SSH key)
вЂў Check firewall settings and network policies
вЂў Check DNS name resolution correctness

Recommended actions:
1. Check SSH service status on node
2. Check authentication settings
3. Check SSH logs on the target node
4. Check network availability of port {node_port}"""

        result = self._result_formatter.error_result(
            rule, error_msg, f"Failed to establish SSH connection with node {node_name}"
        )

        # Supplement result with specific information
        result.update(
            {
                "name": f"SSH connection - {node_name}",
                "details": formatted_details,
                "node": {"ip": node_ip, "name": node_name, "port": node_port},
                "connection_error": True,
                "inspector_type": "node_connection",
                "error_source": "ssh_connection_manager",
            }
        )

        return result

    @staticmethod
    def _get_node_key(node: Dict) -> str:
        """Generate unique key for node"""
        return f"{node['ip']}:{node.get('port', 22)}"
