#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network connectivity check utilities
"""

import socket
import time
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from infrastructure.cluster.node_connection import NodeConnection

logger = logging.getLogger(__name__)


def check_connection(
    node: Dict[str, Any], target_ip: str, target_port: int, timeout: int = 5
) -> Dict[str, Any]:
    """
    Check network connectivity from a node to a target IP and port

    Args:
        node: Node dictionary with connection info
        target_ip: Target IP address to connect to
        target_port: Target port to connect to
        timeout: Connection timeout in seconds

    Returns:
        Dict with status, response_time, and error if any
    """
    node_ip = node.get("ip")
    node_name = node.get("name", node_ip)

    try:
        start_time = time.time()

        # Use bash to check port connectivity
        # This creates a TCP connection attempt with timeout
        command = f"timeout {timeout} bash -c '</dev/tcp/{target_ip}/{target_port}' && echo 'SUCCESS' || echo 'FAILED'"

        with NodeConnection(node) as conn:
            if not conn.connected:
                return {
                    "status": "failed",
                    "error": "Cannot connect to node for checking",
                    "response_time": 0,
                    "node_ip": node_ip,
                    "target_ip": target_ip,
                    "target_port": target_port,
                }

            success, stdout, stderr = conn.execute_command(command)
            end_time = time.time()
            response_time = round(end_time - start_time, 2)

            if success and "SUCCESS" in stdout:
                return {
                    "status": "success",
                    "response_time": response_time,
                    "node_ip": node_ip,
                    "target_ip": target_ip,
                    "target_port": target_port,
                }
            else:
                error_msg = stderr.strip() if stderr else "Connection failed"
                return {
                    "status": "failed",
                    "error": error_msg,
                    "response_time": response_time,
                    "node_ip": node_ip,
                    "target_ip": target_ip,
                    "target_port": target_port,
                }

    except Exception as e:
        return {
            "status": "failed",
            "error": f"Check execution error: {str(e)}",
            "response_time": 0,
            "node_ip": node_ip,
            "target_ip": target_ip,
            "target_port": target_port,
        }


def check_connectivity_from_nodes(
    nodes: List[Dict[str, Any]], target_ip: str, target_port: int, timeout: int = 5
) -> List[Dict[str, Any]]:
    """
    Check connectivity from multiple nodes to a target

    Args:
        nodes: List of node dictionaries with connection info
        target_ip: Target IP address
        target_port: Target port
        timeout: Connection timeout in seconds

    Returns:
        List of connectivity check results
    """
    results = []

    def check_single_node(node):
        node_ip = node.get("ip")
        node_name = node.get("name", node_ip)
        logger.info(
            f"Checking connectivity from {node_name} ({node_ip}) to {target_ip}:{target_port}"
        )

        result = check_connection(node, target_ip, target_port, timeout)
        return result

    # Use ThreadPoolExecutor for parallel checks
    with ThreadPoolExecutor(max_workers=min(len(nodes), 10)) as executor:
        future_to_node = {
            executor.submit(check_single_node, node): node for node in nodes
        }
        for future in as_completed(future_to_node):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                node = future_to_node[future]
                node_name = node.get("name", node.get("ip"))
                logger.error(f"Error checking node {node_name}: {str(e)}")
                results.append(
                    {
                        "status": "failed",
                        "error": f"Check execution error: {str(e)}",
                        "response_time": 0,
                        "node_ip": node.get("ip"),
                        "target_ip": target_ip,
                        "target_port": target_port,
                    }
                )

    return results


def validate_ip(ip: str) -> bool:
    """Validate IPv4 address format"""
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False


def validate_port(port: int) -> bool:
    """Validate port number"""
    return isinstance(port, int) and 1 <= port <= 65535


class NetworkConnectivityResult:
    """Network connectivity check result class"""

    def __init__(self, cluster_name: str, target_ip: str, target_port: int):
        """
        Initialize network check results

        Args:
            cluster_name: cluster name
            target_ip: target IP address
            target_port: target port
        """
        self.cluster_name = cluster_name
        self.target_ip = target_ip
        self.target_port = target_port
        self.timestamp = datetime.now()
        self.result_id = f"network_{cluster_name}_{target_ip}_{target_port}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.checks = []

    def add_check(self, check_result: Dict[str, Any]) -> None:
        """
        Add network check result

        Args:
            check_result: check result dictionary
        """
        self.checks.append(check_result)

    def get_checks(self) -> List[Dict[str, Any]]:
        """Get all check results"""
        return self.checks

    def get_summary(self) -> Dict[str, Any]:
        """Get check summary"""
        total = len(self.checks)
        successful = len([c for c in self.checks if c.get("status") == "success"])
        failed = total - successful

        return {
            "cluster_name": self.cluster_name,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
            "timestamp": self.timestamp.isoformat(),
            "result_id": self.result_id,
            "total_checks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round((successful / total * 100), 1) if total > 0 else 0,
        }

    def save(self) -> str:
        """
        Save network check results

        Returns:
            path to results file
        """
        # Data directory
        data_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
        exports_dir = data_dir / "exports"
        cluster_dir = exports_dir / self.cluster_name
        network_checks_dir = cluster_dir / "network_reports"

        # Ensure directories exist
        network_checks_dir.mkdir(parents=True, exist_ok=True)

        result_data = {
            "cluster_name": self.cluster_name,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
            "timestamp": self.timestamp.isoformat(),
            "result_id": self.result_id,
            "checks": self.checks,
            "summary": self.get_summary(),
        }

        result_file = network_checks_dir / f"{self.result_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return str(result_file)


def load_network_check_result(result_id: str) -> Optional[Dict[str, Any]]:
    """
    Load network check results

    Args:
        result_id: network check results ID

    Returns:
        network check results dictionary, return None if not exists
    """
    data_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))

    # Search all json files in data/exports/*/network_reports/ directories
    for file_path in data_dir.rglob("exports/*/network_reports/*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Check if result_id matches
            if result_data.get("result_id") == result_id:
                return result_data
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            continue

    return None


def list_network_check_results(
    cluster_name: Optional[str] = None, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    List network check results

    Args:
        cluster_name: optional filtering by cluster name
        limit: maximum number of results

    Returns:
        list of network check result summaries
    """
    data_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))

    results = []

    # Search in data/exports/*/network_reports/ directories
    network_checks_pattern = (
        f"exports/{cluster_name}/network_reports/*.json"
        if cluster_name
        else "exports/*/network_reports/*.json"
    )

    for file_path in data_dir.glob(network_checks_pattern):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Filtering by cluster name (if specified)
            if cluster_name and result_data.get("cluster_name") != cluster_name:
                continue

            # Add summary
            summary = result_data.get("summary", {})
            summary["result_id"] = result_data.get("result_id")
            summary["timestamp"] = result_data.get("timestamp")
            results.append(summary)

        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            continue

    # Sorting by time (newest first)
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if limit:
        results = results[:limit]

    return results


def export_network_report(
    result_id: str, format_type: str = "json"
) -> Tuple[bool, str]:
    """
    Export network connectivity report in JSON format

    Args:
        result_id: network check results ID
        format_type: export format, supports "json"

    Returns:
        tuple (success, file path), return exported file path on success
    """
    # Load network check results
    result_data = load_network_check_result(result_id)
    if not result_data:
        return False, "Specified network check results not found"

    # Get cluster name from result_data
    cluster_name = result_data.get("cluster_name", "unknown")
    export_dir = (
        Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
        / "exports"
        / cluster_name
        / "network_reports"
    )

    # Export by format type
    if format_type == "json":
        # Network check results are already saved in the export directory
        # Just return the path to the existing file
        export_path = export_dir / f"{result_id}.json"

        if export_path.exists():
            return True, str(export_path)
        else:
            return False, "Result file not found"

    else:
        return False, f"Unsupported export format: {format_type}"
