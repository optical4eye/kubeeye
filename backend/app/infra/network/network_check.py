#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network connectivity check utilities
"""

import time
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.logging import get_logger
from db.database_context import with_db_session

# Attempt import for PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import cm

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from infra.cluster.node_connection import AsyncNodeConnection
from infra.security.ssh_key_resolver import SSHKeyResolver
from infra.dependency_injection.container import get_service_sync
from core.common.unified_validation import validate_ipv4_address

logger = get_logger(__name__)


async def check_connection(node: Dict[str, Any], target_ip: str, target_port: int, timeout: int = 5) -> Dict[str, Any]:
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

        async_conn = AsyncNodeConnection(node)
        success, message = await async_conn.connect()
        if not success:
            return {
                "status": "failed",
                "error": f"Cannot connect to node for checking: {message}",
                "response_time": 0,
                "node_ip": node_ip,
                "target_ip": target_ip,
                "target_port": target_port,
            }

        try:
            # Use SSHService for async command execution
            ssh_service = get_service_sync("ssh_service")
            stdout, stderr = await ssh_service.execute_command(
                node, command, timeout=timeout, enable_security_check=False
            )

            end_time = time.time()
            response_time = round(end_time - start_time, 2)

            if "SUCCESS" in stdout:
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

        finally:
            # Close the connection
            async_conn.close()

    except Exception as e:
        return {
            "status": "failed",
            "error": f"Check execution error: {str(e)}",
            "response_time": 0,
            "node_ip": node_ip,
            "target_ip": target_ip,
            "target_port": target_port,
        }


async def check_connectivity_from_nodes(
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

    async def check_single_node(node):
        node_ip = node.get("ip")
        node_name = node.get("name", node_ip)
        logger.info(f"Checking connectivity from {node_name} ({node_ip}) to {target_ip}:{target_port}")

        try:
            result = await check_connection(node, target_ip, target_port, timeout)
            return result
        except Exception as e:
            logger.error(f"Error checking node {node_name}: {str(e)}")
            return {
                "status": "failed",
                "error": f"Check execution error: {str(e)}",
                "response_time": 0,
                "node_ip": node_ip,
                "target_ip": target_ip,
                "target_port": target_port,
            }

    # Use asyncio.gather for parallel async checks
    tasks = [check_single_node(node) for node in nodes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions that occurred
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            node = nodes[i]
            node_name = node.get("name", node.get("ip"))
            logger.error(f"Exception checking node {node_name}: {str(result)}")
            processed_results.append(
                {
                    "status": "failed",
                    "error": f"Check execution error: {str(result)}",
                    "response_time": 0,
                    "node_ip": node.get("ip"),
                    "target_ip": target_ip,
                    "target_port": target_port,
                }
            )
        else:
            processed_results.append(result)

    return processed_results


# validate_ip function moved to core.common.validation


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
        self.result_id = f"network_{cluster_name}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
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

    async def save(self) -> str:
        """
        Save network check results to database

        Returns:
            result_id string
        """
        try:
            # Import here to avoid circular imports
            from db.repositories.inspection_result_repository import InspectionResultRepository
            from db.database import get_db

            # Prepare result data for database storage
            result_data = {
                "cluster_name": self.cluster_name,
                "target_ip": self.target_ip,
                "target_port": self.target_port,
                "timestamp": self.timestamp.isoformat(),
                "result_id": self.result_id,
                "checks": self.checks,
                "summary": self.get_summary(),
            }

            # Save to database
            async def save_to_db():
                async with with_db_session() as db:
                    repo = InspectionResultRepository(db)
                    result = await repo.create(
                        {
                            "result_id": self.result_id,
                            "cluster_name": self.cluster_name,
                            "inspection_type": "network",
                            "result_data": result_data,
                        }
                    )
                    await db.commit()
                    logger.info(f"Network check results saved to database: {self.result_id}")
                    return self.result_id

            # Run async function
            result = await save_to_db()
            return getattr(result, "result_id", self.result_id) if result else self.result_id

        except Exception as e:
            logger.error(f"Failed to save network check results: {e}")
            # Return result_id even if saving fails
            return self.result_id


async def load_network_check_result(result_id: str) -> Optional[Dict[str, Any]]:
    """
    Load network check results from database

    Args:
        result_id: network check results ID

    Returns:
        network check results dictionary, return None if not exists
    """
    try:
        # Import here to avoid circular imports
        from db.repositories.inspection_result_repository import InspectionResultRepository
        from db.database import get_db

        # Try to load from database first
        async def load_from_db():
            async with with_db_session() as db:
                repo = InspectionResultRepository(db)
                result = await repo.get_by_result_id(result_id)
                if result and result.inspection_type == "network":
                    return result.result_data
                return None

        # Run async function
        result = await load_from_db()
        if result:
            return result

    except Exception as e:
        logger.error(f"Failed to load network check result from database: {e}")
        return None


async def list_network_check_results(
    cluster_name: Optional[str] = None, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    List network check results from database

    Args:
        cluster_name: optional filtering by cluster name
        limit: maximum number of results

    Returns:
        list of network check result summaries
    """
    try:
        # Import here to avoid circular imports
        from db.repositories.inspection_result_repository import InspectionResultRepository
        from db.database import get_db

        # Try to load from database first
        async def load_from_db():
            async with with_db_session() as db:
                repo = InspectionResultRepository(db)
                # Get network inspection results
                result_data = await repo.list_results(cluster_name=cluster_name, inspection_type="network", limit=limit)
                return result_data

        # Run async function
        db_results = await load_from_db()
        if db_results:
            # Extract results from the paginated response
            return db_results.get("results", [])
        return []

    except Exception as e:
        logger.error(f"Failed to list network check results from database: {e}")
        return []


async def export_network_stream(result_id: str, format_type: str = "json"):
    """
    Stream network connectivity report without saving to disk

    Args:
        result_id: network check results ID
        format_type: export format, supports "json"

    Yields:
        bytes: Chunks of the export data
    """
    # Load network check results
    result_data = await load_network_check_result(result_id)
    if not result_data:
        raise ValueError("Specified network check results not found")

    if format_type == "json":
        # Stream JSON data
        yield json.dumps(result_data, ensure_ascii=False, indent=2).encode("utf-8")
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
