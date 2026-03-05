#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refactored Node Inspector - simplified version with separated concerns
"""

from core.logging import get_logger
from core.config.settings import settings

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple

from services.inspectors.base_inspector import BaseInspector
from infra.results.inspection_result import InspectionResult
from infra.rules.rule_loader import Rule
from infra.cluster.node_connection import async_test_node_connection
from infra.results.result_formatter import ResultFormatter
from infra.dependency_injection.container import get_service
from infra.security.ssh_service import SSHService
from infra.security.command_security import CommandSecurityChecker
from .ssh_connection_manager import SSHConnectionErrorManager
from core.common.unified_validation import ValidationManager
from core.common.unified_error_handler import ErrorHandler

logger = get_logger(__name__)


@dataclass
class NodeInspectorConfig:
    """Node inspector configuration"""

    # Parallelism management (supports up to 50 hosts)
    max_workers: int = 10  # Maximum number of parallel threads
    timeout: int = 30  # Command execution timeout for one node (seconds)

    # Connection configuration (defaults synchronized with settings)
    connection_timeout: int = 15  # SSH connection timeout (seconds), default from settings.kubeeye_ssh_connection_timeout
    retry_attempts: int = 2  # Number of retry attempts, default from settings.kubeeye_ssh_retry_attempts
    retry_delay: int = 2  # Interval between retry attempts (seconds), default from settings.kubeeye_ssh_retry_delay

    # Performance optimization
    enable_connection_pool: bool = True  # Enable connection pool
    pool_size: int = 50  # Connection pool size (supports up to 50 hosts)
    keep_alive: bool = True  # Keep connection alive

    # Logging configuration
    verbose_logging: bool = False  # Verbose logging
    log_command_output: bool = False  # Log command output

    @classmethod
    def from_env(cls) -> "NodeInspectorConfig":
        """Create configuration from environment variables (unified KUBEEYE_SSH_*)"""
        return cls(
            max_workers=settings.kubeeye_ssh_max_concurrent_checks,
            timeout=settings.kubeeye_ssh_command_timeout,
            connection_timeout=settings.kubeeye_ssh_connection_timeout,
            retry_attempts=settings.kubeeye_ssh_retry_attempts,
            retry_delay=settings.kubeeye_ssh_retry_delay,
            enable_connection_pool=settings.kubeeye_ssh_pool_enabled,
            pool_size=settings.kubeeye_ssh_pool_size,
            keep_alive=settings.kubeeye_ssh_keep_alive,
            verbose_logging=settings.kubeeye_ssh_verbose,
            log_command_output=settings.kubeeye_ssh_log_output,
        )

    @classmethod
    def adaptive(cls, node_count: int) -> "NodeInspectorConfig":
        """Adaptive configuration based on node count (supports up to 50 hosts)"""
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(10, node_count)
            timeout = 25
        elif node_count <= 20:
            max_workers = min(20, node_count)
            timeout = 20
        elif node_count <= 35:
            max_workers = min(35, node_count)
            timeout = 18
        else:
            # For 36-50 nodes: use up to 50 workers
            max_workers = min(50, node_count)
            timeout = 15

        return cls(
            max_workers=max_workers,
            timeout=timeout,
            connection_timeout=min(10, timeout // 3),
            retry_attempts=2 if node_count <= 10 else 1,
            verbose_logging=node_count <= 5,  # Enable verbose logging for small node counts
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_workers": self.max_workers,
            "timeout": self.timeout,
            "connection_timeout": self.connection_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "enable_connection_pool": self.enable_connection_pool,
            "pool_size": self.pool_size,
            "keep_alive": self.keep_alive,
            "verbose_logging": self.verbose_logging,
            "log_command_output": self.log_command_output,
        }

    def validate(self) -> List[str]:
        """Validate configuration"""
        issues = []

        if self.max_workers < 1:
            issues.append("max_workers must be greater than 0")
        if self.max_workers > 50:
            issues.append("max_workers should not exceed 50, may cause resource overload")

        if self.timeout < 5:
            issues.append("timeout should not be less than 5 seconds")
        if self.timeout > 300:
            issues.append("timeout should not exceed 5 minutes")

        if self.connection_timeout < 1:
            issues.append("connection_timeout must be greater than 0")

        if self.retry_attempts < 0:
            issues.append("retry_attempts cannot be less than 0")
        if self.retry_attempts > 5:
            issues.append("retry_attempts should not exceed 5 times")

        return issues


class NodeInspector(BaseInspector):
    """
    Refactored Node Inspector with separated concerns
    """

    def __init__(
        self,
        config: List[Dict[str, Any]],
        inspector_config: Optional[NodeInspectorConfig] = None,
        enable_security_check: bool = True,
        use_gitops: bool = False,
    ):
        """
        Initialize refactored node inspector
        """
        if inspector_config is None:
            inspector_config = NodeInspectorConfig.adaptive(len(config))

        inspector_config_dict = {"nodes": config}
        super().__init__(inspector_config_dict, use_gitops=use_gitops)

        self.nodes = config
        self.inspector_config = inspector_config
        self.enable_concurrent = len(config) > 1
        self.max_workers = min(inspector_config.max_workers, len(config)) if self.enable_concurrent else 1
        self.timeout = inspector_config.timeout
        self.enable_security_check = enable_security_check

        # SSH error manager
        self.ssh_error_manager = SSHConnectionErrorManager()

        # SSH service and security checker
        self.ssh_service: Optional[SSHService] = None
        self.security_checker = CommandSecurityChecker() if enable_security_check else None

        # Local connection status cache for current inspection
        self.connection_status_cache = {}

        # Track reported unavailable nodes to avoid duplicates
        self.unavailable_nodes_reported = set()

        # Execution statistics
        self.execution_stats = {
            "total_nodes": len(config),
            "available_nodes": 0,
            "unavailable_nodes": 0,
            "total_node_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "blocked_by_security": 0,
            "security_warnings": 0,
            "total_time": 0.0,
        }

        source_type = "GitOps" if use_gitops else "local"
        logger.info(f"Refactored Node inspector initialized - nodes: {len(config)}, rules: {source_type}")

    @property
    def inspector_type(self) -> str:
        return "node"

    async def run_inspection(
        self, cluster_name: str, rule_ids: Optional[List[str]] = None, selected_tags: Optional[List[str]] = None
    ) -> InspectionResult:
        """
        Run inspection with simplified architecture
        """
        import time

        inspection_start_time = time.time()

        source_type = "GitOps" if self.use_gitops else "local"
        logger.info(f"Start refactored node inspection - cluster: {cluster_name}, rules: {source_type}")

        # Log configured nodes
        logger.info(f"Configured nodes: {len(self.nodes)}")
        for node in self.nodes:
            logger.info(f"  Node: {node.get('name', node['ip'])} ({node['ip']}:{node.get('port', 22)})")

        # Reset error registry before new inspection
        self.ssh_error_manager.reset_for_inspection()

        # Reset local status cache
        self.connection_status_cache = {}

        # Perform SSH connection check and determine available nodes
        available_nodes = await self._check_all_node_connections()
        self.execution_stats["available_nodes"] = len(available_nodes)
        self.execution_stats["unavailable_nodes"] = len(self.nodes) - len(available_nodes)

        logger.info(
            f"SSH connection check results: {len(available_nodes)} available, {len(self.nodes) - len(available_nodes)} unavailable"
        )

        # If no available nodes, log and continue with rule execution (unavailable nodes will be reported in _apply_rule)
        if not available_nodes:
            logger.error("No available nodes for inspection - unavailable nodes will be reported per rule")

        # Log available nodes
        logger.info(f"Available nodes for rule execution: {[node.get('name', node['ip']) for node in available_nodes]}")

        # Execute inspection rules only on available nodes
        result = await super().run_inspection(cluster_name, rule_ids or [], selected_tags)

        # Ensure all unavailable nodes are reported
        for node in self.nodes:
            if self.ssh_error_manager.has_connection_error(node):
                node_key = self.ssh_error_manager._get_node_key(node)
                if node_key not in self.unavailable_nodes_reported:
                    result.add_item(self._format_unavailable_node_result(node))
                    self.unavailable_nodes_reported.add(node_key)

        inspection_duration = time.time() - inspection_start_time
        logger.info(f"Inspection completed - total results: {len(result.items)}")
        logger.info(
            f"Statistics: {self.execution_stats['available_nodes']} available, {self.execution_stats['unavailable_nodes']} unavailable nodes"
        )
        logger.info(
            f"Inspection performance: total_time={inspection_duration:.2f}s, "
            f"node_executions={self.execution_stats['total_node_executions']}, "
            f"success_rate={self.execution_stats.get('success_rate', 0):.1f}%"
        )

        return result

    async def _check_all_node_connections(self) -> List[Dict]:
        """
        Check SSH connection to all nodes using connection pool and async operations
        Returns list of available nodes
        """
        logger.info("Checking SSH connection to all nodes using connection pool...")

        import os

        available_nodes = []

        # Get configurable SSH timeout and max concurrent checks
        ssh_timeout = settings.kubeeye_ssh_connection_timeout
        max_concurrent_checks = settings.kubeeye_ssh_max_concurrent_checks

        # Calculate derived timeouts based on base SSH timeout and node count
        # For large node counts, increase timeout to allow more time for connections
        if len(self.nodes) > 20:
            connection_check_timeout = ssh_timeout * 2.5  # 25s for 10s base with many nodes
        else:
            connection_check_timeout = ssh_timeout * 1.5  # 15s for 10s base

        logger.info(
            f"Connection check parameters: nodes={len(self.nodes)}, max_concurrent={max_concurrent_checks}, timeout={connection_check_timeout}s"
        )

        # Create semaphore to limit concurrent connections
        semaphore = asyncio.Semaphore(max_concurrent_checks)

        # Track checked nodes to ensure all get a status
        checked_nodes = {}

        async def check_single_node(node, index):
            async with semaphore:
                node_key = self.ssh_error_manager._get_node_key(node)
                node_name = node.get("name", node["ip"])

                logger.debug(f"[{index}/{len(self.nodes)}] Starting connection check for node {node_name}")

                # Mark node as being checked
                checked_nodes[node_key] = {"node": node, "status": None}

                # Check if there was already an error for this node
                if self.ssh_error_manager.has_connection_error(node):
                    logger.debug(f"Node {node_name} already has SSH error, skipping")
                    checked_nodes[node_key]["status"] = {"success": False, "message": "Already has SSH error"}
                    return None

                # Check status cache
                if node_key in self.connection_status_cache:
                    status = self.connection_status_cache[node_key]
                    node["connection_status"] = status
                    checked_nodes[node_key]["status"] = status
                    if status["success"]:
                        return node
                    else:
                        # Register error in manager
                        self.ssh_error_manager.register_connection_error(node, status["message"])
                        return None

                # Check connection using pool
                try:
                    success, message = await asyncio.wait_for(
                        async_test_node_connection(node), timeout=connection_check_timeout
                    )
                    status = {"success": success, "message": message}
                    self.connection_status_cache[node_key] = status
                    node["connection_status"] = status
                    checked_nodes[node_key]["status"] = status

                    if success:
                        logger.info(f"[{index}/{len(self.nodes)}] SSH connection to node {node_name} successful")
                        return node
                    else:
                        logger.error(
                            f"[{index}/{len(self.nodes)}] SSH connection to node {node_name} unavailable: {message}"
                        )
                        # Register error in manager
                        self.ssh_error_manager.register_connection_error(node, message)
                        return None

                except asyncio.TimeoutError:
                    error_msg = f"Connection check timeout ({connection_check_timeout}s) for node {node_name}"
                    logger.error(f"[{index}/{len(self.nodes)}] {error_msg}")
                    status = {"success": False, "message": error_msg}
                    node["connection_status"] = status
                    checked_nodes[node_key]["status"] = status
                    self.ssh_error_manager.register_connection_error(node, error_msg)
                    return None
                except Exception as e:
                    error_msg = f"Connection check error for node {node_name}: {str(e)}"
                    logger.error(f"[{index}/{len(self.nodes)}] {error_msg}")
                    status = {"success": False, "message": error_msg}
                    node["connection_status"] = status
                    checked_nodes[node_key]["status"] = status
                    self.ssh_error_manager.register_connection_error(node, error_msg)
                    return None

        # Create tasks for all nodes with index
        tasks = [check_single_node(node, i + 1) for i, node in enumerate(self.nodes)]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and ensure all nodes have connection_status
        for i, result in enumerate(results):
            node = self.nodes[i]
            node_key = self.ssh_error_manager._get_node_key(node)
            node_name = node.get("name", node["ip"])

            if isinstance(result, Exception):
                logger.error(f"Unexpected error during connection check for {node_name}: {str(result)}")
                # Ensure node has a failed status
                error_msg = f"Unexpected error: {str(result)}"
                status = {"success": False, "message": error_msg}
                node["connection_status"] = status
                self.ssh_error_manager.register_connection_error(node, error_msg)
            elif result is not None:
                available_nodes.append(result)

        # Log summary of connection checks
        successful = sum(1 for n in self.nodes if n.get("connection_status", {}).get("success", False))
        failed = len(self.nodes) - successful
        logger.info(f"Connection check completed. Available: {successful}, Unavailable: {failed}")

        # Log details for unavailable nodes
        for node in self.nodes:
            status = node.get("connection_status", {})
            if not status.get("success", False):
                node_name = node.get("name", node["ip"])
                error_msg = status.get("message", "No status recorded")
                logger.warning(f"Node {node_name} unavailable: {error_msg}")

        return available_nodes

    async def _apply_rule(self, rule: Rule, context: Dict) -> Optional[Dict]:
        """
        Apply inspection rule only to available nodes
        """
        logger.info(f"Applying rule: {rule.id} - {rule.name}")
        logger.debug(f"Rule config: extractors={len(rule.extractors)}, assertions={len(rule.assertions)}")
        rule_start_time = time.time()

        # Get rule configuration
        extractors = rule.extractors
        assertions = rule.assertions

        # Get command from first extractor if available
        command = ""
        if extractors:
            command_extractor = next((e for e in extractors if e.get("type") == "command"), None)
            if command_extractor:
                command = command_extractor.get("command", "")

        # Filter nodes by selector
        node_selector = self.get_rule_config(rule, "scope.node_selector", {})
        target_nodes = self._filter_nodes_by_selector(self.nodes, node_selector)

        if not target_nodes:
            logger.warning(f"Rule {rule.id} - no suitable nodes")
            return self._format_no_nodes_result(rule, "No suitable nodes found for rule execution")

        # Filter only nodes with successful SSH connection
        available_nodes = []
        for node in target_nodes:
            node_name = node.get("name", node["ip"])

            # Skip nodes with SSH connection errors
            if self.ssh_error_manager.has_connection_error(node):
                logger.debug(f"Rule {rule.id} - node {node_name} has SSH error, skipping")
                continue

            # Check connection status
            status = node.get("connection_status", {})
            if status.get("success", False):
                available_nodes.append(node)
            else:
                logger.warning(f"Rule {rule.id} - node {node_name} failed connection check")

        logger.info(f"Rule {rule.id} - available nodes: {len(available_nodes)} out of {len(target_nodes)}")

        # Initialize results list
        node_results = []

        # If no available nodes, add results for unavailable nodes
        if not available_nodes:
            logger.info(f"Rule {rule.id} - no nodes for execution, adding unavailable results")
            node_results = []
            for node in target_nodes:
                if self.ssh_error_manager.has_connection_error(node):
                    node_key = self.ssh_error_manager._get_node_key(node)
                    if node_key not in self.unavailable_nodes_reported:
                        result = self._format_unavailable_node_result(node)
                        node_results.append(result)
                        self.unavailable_nodes_reported.add(node_key)
            return {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "results": node_results,
                "total_nodes": len(target_nodes),
                "executed_nodes": 0,
                "execution_time": 0.0,
            }

        # Execute rule on available nodes and add to results
        if available_nodes:
            if self.enable_concurrent and len(available_nodes) > 1:
                available_results = await self._execute_rule_concurrently(rule, command, assertions, available_nodes)
            else:
                available_results = await self._execute_rule_sequentially_async(
                    rule, command, assertions, available_nodes
                )
            node_results.extend(available_results)

        # Update statistics
        rule_duration = time.time() - rule_start_time
        self.execution_stats["total_node_executions"] += len(available_nodes)
        self.execution_stats["total_time"] = self.execution_stats["total_time"] + rule_duration

        logger.info(
            f"Rule {rule.id} executed in {rule_duration:.2f}s on {len(available_nodes)} nodes, "
            f"avg_time_per_node={rule_duration / max(len(available_nodes), 1):.2f}s"
        )
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "results": node_results,
            "total_nodes": len(target_nodes),
            "executed_nodes": len(node_results),
            "execution_time": time.time() - rule_start_time,
        }

    async def _execute_rule_concurrently(
        self, rule: Rule, command: str, assertions: List[Dict], target_nodes: List[Dict]
    ) -> List[Dict]:
        """Concurrent rule execution only on available nodes using asyncio"""
        node_results = []

        # Create semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(self.max_workers)

        async def execute_single_node_async(node):
            async with semaphore:
                # Additional check before execution
                if self.ssh_error_manager.has_connection_error(node):
                    return None

                try:
                    # Get SSH service
                    if not self.ssh_service:
                        self.ssh_service = await get_service("ssh_service")

                    # Security check
                    if self.security_checker and command:
                        is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                        if not is_safe:
                            error_msg = f"Command blocked by security: {risk_desc}"
                            logger.error(f"Node {node.get('name', node['ip'])}: {error_msg}")
                            return self._format_execution_error_result(rule, node, error_msg)

                    # Execute command using SSH service
                    if self.ssh_service:
                        output, error = await self.ssh_service.execute_command(
                            node_info=node,
                            command=command,
                            timeout=self.timeout,
                            enable_security_check=False,  # Security check already done above
                        )
                        if error:
                            # If SSH error occurred, register it
                            if self.ssh_service.is_ssh_connection_error(error):
                                self.ssh_error_manager.register_connection_error(node, error)
                                return None
                            return self._format_execution_error_result(rule, node, error)
                        else:
                            # Evaluate assertions
                            variables = {
                                "output": output.strip(),
                                "node_ip": node["ip"],
                                "node_name": node.get("name", node["ip"]),
                            }
                            return self._evaluate_assertions(rule, assertions, variables, node)
                except Exception as e:
                    logger.error(f"Execution error on node {node.get('name', node['ip'])}: {str(e)}")
                    # Do not create execution error for nodes with SSH error
                    if not self.ssh_error_manager.has_connection_error(node):
                        error_result = self._format_execution_error_result(rule, node, str(e))
                        if error_result:
                            node_results.append(error_result)
                    return None

        # Create tasks for all nodes
        tasks = [asyncio.create_task(execute_single_node_async(node)) for node in target_nodes]

        # Wait for all tasks to complete with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.timeout * len(target_nodes)
            )
        except asyncio.TimeoutError:
            logger.warning(f"Concurrent execution timeout after {self.timeout * len(target_nodes)} seconds")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            results = []

        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task execution error: {str(result)}")
            elif result is not None:
                node_results.append(result)

        return node_results

    async def _execute_rule_sequentially_async(
        self, rule: Rule, command: str, assertions: List[Dict], target_nodes: List[Dict]
    ) -> List[Dict]:
        """Sequential rule execution only on available nodes using async operations"""
        node_results = []

        for node in target_nodes:
            # Additional check before execution
            if self.ssh_error_manager.has_connection_error(node):
                continue

            try:
                # Get SSH service
                if not self.ssh_service:
                    self.ssh_service = await get_service("ssh_service")

                # Security check
                if self.security_checker and command:
                    is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                    if not is_safe:
                        error_msg = f"Command blocked by security: {risk_desc}"
                        logger.error(f"Node {node.get('name', node['ip'])}: {error_msg}")
                        error_result = self._format_execution_error_result(rule, node, error_msg)
                        if error_result:
                            node_results.append(error_result)
                        continue

                # Execute command using SSH service
                if self.ssh_service:
                    output, error = await self.ssh_service.execute_command(
                        node_info=node,
                        command=command,
                        timeout=self.timeout,
                        enable_security_check=False,  # Security check already done above
                    )
                    if error:
                        # If SSH error occurred, register it
                        if self.ssh_service.is_ssh_connection_error(error):
                            self.ssh_error_manager.register_connection_error(node, error)
                            continue
                        error_result = self._format_execution_error_result(rule, node, error)
                        if error_result:
                            node_results.append(error_result)
                    else:
                        # Evaluate assertions
                        variables = {
                            "output": output.strip(),
                            "node_ip": node["ip"],
                            "node_name": node.get("name", node["ip"]),
                        }
                        result = self._evaluate_assertions(rule, assertions, variables, node)
                        if result:
                            node_results.append(result)
                            self.execution_stats["successful_executions"] += 1
            except Exception as e:
                logger.error(f"Execution error on node {node.get('name', node['ip'])}: {str(e)}")
                # Do not create execution error for nodes with SSH error
                if not self.ssh_error_manager.has_connection_error(node):
                    error_result = self._format_execution_error_result(rule, node, str(e))
                    if error_result:
                        node_results.append(error_result)
                self.execution_stats["failed_executions"] += 1

        return node_results

    def _evaluate_assertions(self, rule: Rule, assertions: List[Dict], variables: Dict[str, Any], node: Dict) -> Dict:
        """Evaluate rule assertions"""
        assertion_result = self.rule_processor.evaluate_assertions(assertions, variables)

        if assertion_result["passed"]:
            status = "passed"
            severity = "info"
            description = f"{rule.name}: check passed"
            # Use name from the first assertion if available, otherwise use default message
            details = (
                assertions[0].get("name", "System state meets requirements")
                if assertions
                else "System state meets requirements"
            )
            solution = ""
        else:
            status = "failed"
            severity = assertion_result["severity"]
            description = assertion_result["description"].replace("Assertion failed: ", "")
            details = "Failed check details:\n" + "\n".join(
                [f"- {fa['description']}" for fa in assertion_result["failed_assertions"]]
            )
            solution = rule.solution

        # Format result
        result = self.rule_processor.format_rule_result(
            rule=rule,
            status=status,
            description=description,
            severity=severity,
            details=details,
            solution=solution,
        )

        # Add node information
        node_name = node.get("name", node["ip"])
        result["name"] = f"{rule.name} - {node_name}"
        result["node"] = {"ip": node["ip"], "name": node_name}
        result["variables"] = variables

        return result

    def _filter_nodes_by_selector(self, nodes: List[Dict], node_selector: Dict) -> List[Dict]:
        """Filter nodes by selector"""
        if not node_selector:
            return nodes

        filtered_nodes = []
        for node in nodes:
            node_labels = node.get("labels", {})
            match = True
            for label_key, label_value in node_selector.items():
                if label_key not in node_labels or str(node_labels[label_key]) != str(label_value):
                    match = False
                    break
            if match:
                filtered_nodes.append(node)

        return filtered_nodes

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """Validate rule configuration"""
        # Use ValidationManager with security checker
        security_checker = self.security_checker if self.enable_security_check else None

        return ValidationManager.validate_node_rule_config(rule.config, security_checker)

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """Determine rule applicability"""
        node_selector = self.get_rule_config(rule, "scope.node_selector", {})
        return not node_selector or any(self._filter_nodes_by_selector(self.nodes, node_selector))

    def _format_execution_error_result(self, rule: Rule, node: Dict, error_msg: str) -> Optional[Dict]:
        """Format execution error result"""
        # Do not create execution error for nodes with SSH error
        if self.ssh_error_manager.has_connection_error(node):
            return None

        node_name = node.get("name", node["ip"])
        result = self.rule_processor.result_formatter.error_result(
            rule, error_msg, f"Execution error on node {node_name}"
        )
        result["node"] = {"ip": node["ip"], "name": node_name}
        result["name"] = f"{rule.name} - {node_name}"
        return result

    def _format_no_nodes_result(self, rule: Rule, reason: str) -> Dict:
        """Format result when no nodes are available for rule execution"""
        result = self.rule_processor.result_formatter.error_result(rule, reason, f"Rule execution skipped: {reason}")
        result["status"] = "skipped"
        result["severity"] = "info"
        return result

    def _format_unavailable_node_result(self, node: Dict) -> Dict:
        """Format result for unavailable node using dummy rule"""
        node_name = node.get("name", node["ip"])
        rule_data = {
            "id": "node_unavailable",
            "name": "Node unavailable",
            "solution": "Resolve SSH connection issues",
            "config": {"extractors": [], "assertions": []},
        }
        rule = Rule(rule_data)
        error_msg = f"Node {node_name} is unavailable for inspection due to SSH connection failure"
        result = self.rule_processor.result_formatter.error_result(rule, error_msg, f"Node {node_name} unavailable")
        result["node"] = {"ip": node["ip"], "name": node_name}
        result["name"] = f"Node {node_name} unavailable"
        result["status"] = "exception"
        result["severity"] = "critical"
        result["details"] = (
            f"SSH connection to node {node_name} ({node['ip']}:{node.get('port', 22)}) failed. "
            "The node was not accessible during the inspection period."
        )
        return result

    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        stats = self.execution_stats.copy()
        stats.update(
            {
                "concurrent_mode": self.enable_concurrent,
                "max_workers": self.max_workers,
                "timeout": self.timeout,
                "security_enabled": self.enable_security_check,
                "ssh_connection_errors": self.ssh_error_manager.get_error_count(),
            }
        )

        if stats["total_node_executions"] > 0:
            stats["success_rate"] = stats["successful_executions"] / stats["total_node_executions"] * 100.0
        else:
            stats["success_rate"] = 0

        return stats

    def print_execution_summary(self):
        """Print execution summary"""
        stats = self.get_execution_stats()
        logger.info("=== Refactored Node inspection execution summary ===")
        logger.info(f"Total nodes: {stats['total_nodes']}")
        logger.info(f"Available nodes: {stats['available_nodes']}")
        logger.info(f"Unavailable nodes: {stats['unavailable_nodes']}")
        logger.info(f"SSH connection errors: {stats['ssh_connection_errors']}")
        logger.info(f"Node executions: {stats['total_node_executions']}")
        logger.info(f"Successful executions: {stats['successful_executions']}")
        logger.info(f"Failed executions: {stats['failed_executions']}")
        logger.info(f"Success rate: {stats['success_rate']:.1f}%")
        logger.info(f"Total time: {stats['total_time']:.2f}sec")

    @classmethod
    def create_optimized(cls, config: List[Dict[str, Any]], use_gitops: bool = False) -> "NodeInspector":
        """Create optimized inspector"""
        inspector_config = NodeInspectorConfig.adaptive(len(config))
        return cls(
            config=config,
            inspector_config=inspector_config,
            use_gitops=use_gitops,
        )
