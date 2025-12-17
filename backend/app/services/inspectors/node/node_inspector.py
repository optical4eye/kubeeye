#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node inspector with centralized SSH connection error management
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Union

from services.inspectors.base_inspector import BaseInspector
from infrastructure.results.inspection_result import InspectionResult
from infrastructure.rules.rule_loader import Rule
from infrastructure.cluster.node_connection import NodeConnection, test_node_connection
from infrastructure.security.command_security import CommandSecurityChecker
from infrastructure.results.result_formatter import ResultFormatter

# Logging setup
logger = logging.getLogger(__name__)


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
        class ConnectionRule:
            id = "ssh_connection"
            name = "SSH connection"
            solution = "Resolve network connection or SSH configuration issues"

        rule = ConnectionRule()

        formatted_details = f"""Connection error to node {node_name} ({node_ip}:{node_port})

Error message: {error_msg}

Diagnostics:
• Check port {node_port} availability: telnet {node_ip} {node_port} or nc -zv {node_ip} {node_port}
• Ensure SSH service is running on the node
• Check credentials correctness (username, password/SSH key)
• Check firewall settings and network policies
• Check DNS name resolution correctness

Recommended actions:
1. Check SSH service status on the node
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


class NodeInspector(BaseInspector):
    """
    Node inspector with guaranteed unified SSH error display
    """

    def __init__(
        self,
        config: List[Dict[str, Any]],
        enable_concurrent: bool = True,
        max_workers: int = 5,
        timeout: int = 30,
        enable_security_check: bool = True,
        use_gitops: bool = False,
    ):
        """
        Initialize node inspector
        """
        inspector_config = {"nodes": config}
        super().__init__(inspector_config, use_gitops=use_gitops)

        self.nodes = config
        self.enable_concurrent = enable_concurrent
        self.max_workers = min(max_workers, len(config)) if enable_concurrent else 1
        self.timeout = timeout
        self.enable_security_check = enable_security_check

        # SSH error manager
        self.ssh_error_manager = SSHConnectionErrorManager()

        # Security check
        self.security_checker = CommandSecurityChecker()
        logger.info("Security check forcibly enabled")

        # Local connection status cache for current inspection
        self.connection_status_cache = {}

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
            "total_time": 0,
        }

        source_type = "GitOps" if use_gitops else "local"
        logger.info(f"Node inspector initialized - nodes: {len(config)}, rules: {source_type}")

    @property
    def inspector_type(self) -> str:
        return "node"

    async def run_inspection(self, cluster_name: str, rule_ids: List[str] = None) -> InspectionResult:
        """
        Run inspection with guaranteed unified SSH error display
        """
        source_type = "GitOps" if self.use_gitops else "local"
        logger.info(f"Start node inspection - cluster: {cluster_name}, rules: {source_type}")

        # Reset error registry before new inspection
        self.ssh_error_manager.reset_for_inspection()

        # Reset local status cache
        self.connection_status_cache = {}

        # Perform SSH connection check and determine available nodes
        available_nodes = self._check_all_node_connections()
        self.execution_stats["available_nodes"] = len(available_nodes)
        self.execution_stats["unavailable_nodes"] = len(self.nodes) - len(available_nodes)

        # If no available nodes, return only SSH errors
        if not available_nodes:
            logger.error("No available nodes for inspection")
            ssh_errors = self.ssh_error_manager.get_all_connection_errors()
            result = InspectionResult(cluster_name, self.inspector_type)
            for error in ssh_errors:
                result.add_item(error)
            return result

        # Execute inspection rules only on available nodes
        result = await super().run_inspection(cluster_name, rule_ids)

        # Add SSH connection errors to the beginning of the report
        ssh_errors = self.ssh_error_manager.get_all_connection_errors()
        if ssh_errors:
            result.items = ssh_errors + result.items
            logger.info(f"Added {len(ssh_errors)} SSH connection errors to report")

        logger.info(f"Inspection completed - total results: {len(result.items)}")
        logger.info(
            f"Statistics: {self.execution_stats['available_nodes']} available, {self.execution_stats['unavailable_nodes']} unavailable nodes"
        )

        return result

    def _check_all_node_connections(self) -> List[Dict]:
        """
        Check SSH connection to all nodes in parallel using ThreadPoolExecutor
        Returns list of available nodes
        """
        logger.info("Checking SSH connection to all nodes in parallel...")

        import concurrent.futures
        import os

        available_nodes = []

        # Get configurable SSH timeout and max concurrent checks
        ssh_timeout = int(os.getenv("KUBEYE_SSH_CONNECTION_TIMEOUT", "10"))
        max_concurrent_checks = int(os.getenv("KUBEYE_SSH_MAX_CONCURRENT_CHECKS", "10"))

        # Calculate derived timeouts based on base SSH timeout
        connection_check_timeout = ssh_timeout * 1.5  # 15s for 10s base
        total_check_timeout = ssh_timeout * 2  # 20s for 10s base

        max_workers = min(max_concurrent_checks, len(self.nodes))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all connection checks
            future_to_node = {}
            for node in self.nodes:
                node_key = self.ssh_error_manager._get_node_key(node)
                node_name = node.get("name", node["ip"])

                # Check if there was already an error for this node
                if self.ssh_error_manager.has_connection_error(node):
                    logger.debug(f"Node {node_name} already has SSH error, skipping")
                    continue

                # Check status cache
                if node_key in self.connection_status_cache:
                    status = self.connection_status_cache[node_key]
                    node["connection_status"] = status
                    if status["success"]:
                        available_nodes.append(node)
                    else:
                        # Register error in manager
                        self.ssh_error_manager.register_connection_error(node, status["message"])
                    continue

                # Submit connection check to thread pool
                future = executor.submit(self._check_single_node_connection_with_timeout, node)
                future_to_node[future] = node

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_node):
                node = future_to_node[future]
                node_key = self.ssh_error_manager._get_node_key(node)
                node_name = node.get("name", node["ip"])

                try:
                    success, message = future.result(timeout=total_check_timeout)

                    # Save status
                    status = {"success": success, "message": message}
                    self.connection_status_cache[node_key] = status
                    node["connection_status"] = status

                    if success:
                        available_nodes.append(node)
                        logger.info(f"SSH connection to node {node_name} successful")
                    else:
                        logger.error(f"SSH connection to node {node_name} unavailable: {message}")
                        # Register error in manager
                        self.ssh_error_manager.register_connection_error(node, message)

                except concurrent.futures.TimeoutError:
                    error_msg = f"Connection check timeout (20s) for node {node_name}"
                    logger.error(error_msg)
                    self.ssh_error_manager.register_connection_error(node, error_msg)
                except Exception as e:
                    error_msg = f"Connection check error for node {node_name}: {str(e)}"
                    logger.error(error_msg)
                    self.ssh_error_manager.register_connection_error(node, error_msg)

        logger.info(
            f"Connection check completed. Available: {len(available_nodes)}, Unavailable: {len(self.nodes) - len(available_nodes)}"
        )
        return available_nodes

    def _check_single_node_connection_with_timeout(self, node: Dict) -> Tuple[bool, str]:
        """
        Check connection to single node with timeout
        """
        import concurrent.futures
        import os

        node_name = node.get("name", node["ip"])

        # Get configurable SSH timeout
        ssh_timeout = int(os.getenv("KUBEYE_SSH_CONNECTION_TIMEOUT", "10"))
        connection_check_timeout = ssh_timeout * 1.5  # 15s for 10s base

        try:
            # Run connection test with timeout using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(test_node_connection, node)
                success, message = future.result(timeout=connection_check_timeout)
                return success, message

        except concurrent.futures.TimeoutError:
            return (
                False,
                f"Connection timeout ({connection_check_timeout}s) for node {node_name}",
            )
        except Exception as e:
            return False, f"Connection check error for node {node_name}: {str(e)}"

    async def _apply_rule(self, rule: Rule, context: Dict) -> Union[Dict, List[Dict], None]:
        """
        Apply inspection rule only to available nodes
        """
        logger.info(f"Applying rule: {rule.id} - {rule.name}")
        rule_start_time = time.time()

        # Get rule configuration - use extractors from rule object
        extractors = rule.extractors
        assertions = rule.assertions

        # Get command from first extractor if available
        command = ""
        if extractors:
            command_extractor = next((e for e in extractors if e.get("type") == "command"), None)
            if command_extractor:
                command = command_extractor.get("command", "")

        # Command security check
        if self.enable_security_check and command:
            is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
            if not is_safe:
                logger.error(f"Rule {rule.id} blocked by security: {risk_desc}")
                self.execution_stats["blocked_by_security"] += 1
                return self._format_security_blocked_result(rule, risk_desc, command)

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

        # If no available nodes, rule is not executed
        if not available_nodes:
            logger.warning(f"Rule {rule.id} - no available nodes for execution")
            return self._format_no_nodes_result(rule, "No available nodes for rule execution")

        # Execute rule on available nodes
        if self.enable_concurrent and len(available_nodes) > 1:
            node_results = self._execute_rule_concurrently(rule, command, assertions, available_nodes)
        else:
            node_results = self._execute_rule_sequentially(rule, command, assertions, available_nodes)

        # Update statistics
        rule_duration = time.time() - rule_start_time
        self.execution_stats["total_node_executions"] += len(available_nodes)
        self.execution_stats["total_time"] += rule_duration

        logger.info(f"Rule {rule.id} executed in {rule_duration:.2f}sec")
        return node_results

    def _execute_rule_concurrently(
        self, rule: Rule, command: str, assertions: List[Dict], target_nodes: List[Dict]
    ) -> List[Dict]:
        """Concurrent rule execution only on available nodes"""
        node_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_node = {}
            for node in target_nodes:
                # Additional check before execution
                if self.ssh_error_manager.has_connection_error(node):
                    continue

                future = executor.submit(self._execute_rule_on_single_node, rule, command, assertions, node)
                future_to_node[future] = node

            for future in as_completed(future_to_node, timeout=self.timeout * len(target_nodes)):
                node = future_to_node[future]
                try:
                    result = future.result(timeout=self.timeout)
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

    def _execute_rule_sequentially(
        self, rule: Rule, command: str, assertions: List[Dict], target_nodes: List[Dict]
    ) -> List[Dict]:
        """Sequential rule execution only on available nodes"""
        node_results = []

        for node in target_nodes:
            # Additional check before execution
            if self.ssh_error_manager.has_connection_error(node):
                continue

            try:
                result = self._execute_rule_on_single_node(rule, command, assertions, node)
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

    def _execute_rule_on_single_node(
        self, rule: Rule, command: str, assertions: List[Dict], node: Dict
    ) -> Optional[Dict]:
        """Execute rule on single node (only if node is available)"""
        node_name = node.get("name", node["ip"])

        # Final check: ensure no SSH connection error
        if self.ssh_error_manager.has_connection_error(node):
            logger.warning(f"Node {node_name} has SSH error, skipping execution")
            return None

        # Execute command
        output, error = self._execute_command(command, node)

        if error:
            # If SSH error occurred, register it and don't execute rules on this node anymore
            if self._is_ssh_connection_error(error):
                self.ssh_error_manager.register_connection_error(node, error)
                return None
            return self._format_execution_error_result(rule, node, error)
        else:
            # Evaluate assertions
            variables = {
                "output": output.strip(),
                "node_ip": node["ip"],
                "node_name": node_name,
            }
            return self._evaluate_assertions(rule, assertions, variables, node)

    def _is_ssh_connection_error(self, error_msg: str) -> bool:
        """Checks if error is related to SSH connection"""
        ssh_keywords = [
            "connection",
            "connect",
            "ssh",
            "timeout",
            "refused",
            "authentication",
            "auth",
            "handshake",
            "socket",
            "network",
            "unreachable",
            "closed",
            "reset",
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in ssh_keywords)

    def _execute_command(self, command: str, node: Dict) -> Tuple[str, str]:
        """Execute command on node (only if node is available)"""
        try:
            node_name = node.get("name", node["ip"])

            # Final check before execution
            if self.ssh_error_manager.has_connection_error(node):
                return "", "SSH connection unavailable"

            # Command security check
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    error_msg = f"Command blocked by security: {risk_desc}"
                    logger.error(f"Node {node_name}: {error_msg}")
                    return "", error_msg

            # Execute command via SSH
            with NodeConnection(node) as conn:
                if not conn.connected:
                    error_msg = "SSH connection failed"
                    logger.error(f"Node {node_name}: {error_msg}")
                    # Register SSH error
                    self.ssh_error_manager.register_connection_error(node, error_msg)
                    return "", error_msg

                success, stdout, stderr = conn.execute_command(command)
                if success:
                    return stdout, ""
                else:
                    # Check if error is SSH-related
                    if self._is_ssh_connection_error(stderr):
                        self.ssh_error_manager.register_connection_error(node, stderr)
                    return stdout, stderr

        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            logger.error(f"Node {node.get('name', node['ip'])}: {error_msg}")

            # Check if exception is SSH-related
            if self._is_ssh_connection_error(error_msg):
                self.ssh_error_manager.register_connection_error(node, error_msg)

            return "", error_msg

    def _evaluate_assertions(self, rule: Rule, assertions: List[Dict], variables: Dict[str, Any], node: Dict) -> Dict:
        """Evaluate rule assertions"""
        assertion_result = self.rule_processor.evaluate_assertions(assertions, variables)

        if assertion_result["passed"]:
            status = "passed"
            severity = "info"
            description = f"{rule.name}: check passed"
            # Use the name from the first assertion if available, otherwise use default message
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
        issues = []
        command = self.get_rule_config(rule, "execution.command", "")
        if not command:
            issues.append("Missing execution command")
        else:
            if self.enable_security_check:
                is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
                if not is_safe:
                    issues.append(f"Security check failed: {risk_desc}")

        assertions = self.get_rule_config(rule, "assertions", [])
        if not assertions:
            issues.append("Missing assertions")

        return issues

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """Determine rule applicability"""
        node_selector = self.get_rule_config(rule, "scope.node_selector", {})
        return not node_selector or any(self._filter_nodes_by_selector(self.nodes, node_selector))

    def _format_security_blocked_result(self, rule: Rule, risk_desc: str, command: str) -> Dict:
        """Format security blocked result"""
        return self.rule_processor.result_formatter.error_result(
            rule,
            f"Command contains security risks: {risk_desc}",
            "Security check failed",
        )

    def _format_execution_error_result(self, rule: Rule, node: Dict, error_msg: str) -> Optional[Dict]:
        """Format execution error result"""
        # Do not create execution error for nodes with SSH connection error
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
            stats["success_rate"] = stats["successful_executions"] / stats["total_node_executions"] * 100
        else:
            stats["success_rate"] = 0

        return stats

    def print_execution_summary(self):
        """Print execution summary"""
        stats = self.get_execution_stats()
        logger.info("=== Node inspection execution summary ===")
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
        node_count = len(config)
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(8, node_count)  # Increased from 5 to 8
            timeout = 25
        elif node_count <= 20:
            max_workers = min(15, node_count)  # Support for medium clusters
            timeout = 20
        else:
            max_workers = min(25, node_count)  # Support for large clusters
            timeout = 15  # Reduced timeout for large clusters

        return cls(
            config=config,
            use_gitops=use_gitops,
            enable_concurrent=node_count > 1,
            max_workers=max_workers,
            timeout=timeout,
        )
