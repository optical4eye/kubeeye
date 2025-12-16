#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus inspector - simplified version, supports "one rule = one query = one check item"
"""

import logging
from typing import Dict, List, Any

from services.inspectors.base_inspector import BaseInspector
from infrastructure.prometheus.prometheus_client import PrometheusClient
from infrastructure.rules.rule_loader import Rule

# Logging setup
logger = logging.getLogger(__name__)


class PrometheusInspector(BaseInspector):
    """
    Prometheus rule inspector - simplified version
    """

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Initialize Prometheus inspector

        Args:
            config: Prometheus configuration dictionary, must contain the following fields:
                - url: Prometheus server URL
                - username: optional username
                - password: optional password
                - token: optional access token
                - enabled: whether enabled
            use_gitops: whether to use GitOps rules
        """
        # Ensure configuration is valid
        if not isinstance(config, dict):
            raise TypeError("Configuration must be a dictionary")

        # If passed configuration lacks required fields, add default values
        if "url" not in config:
            raise ValueError("Prometheus configuration missing url field")

        # Create PrometheusClient instance
        self.prometheus_client = PrometheusClient(config)

        # Call parent class initialization
        super().__init__(config, use_gitops=use_gitops)

    @property
    def inspector_type(self) -> str:
        return "prometheus"

    def _prepare_context(self, cluster_name: str) -> Dict:
        """
        Prepare Prometheus check context

        Args:
            cluster_name: cluster name

        Returns:
            Prepared context
        """
        context = super()._prepare_context(cluster_name)
        return context

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """
        Check if rule configuration is valid

        Args:
            rule: rule object

        Returns:
            List of configuration issues, if no issues, returns empty list
        """
        issues = []

        # Check required query configuration
        query = self.get_rule_config(rule, "query", "")
        if not query:
            issues.append("Missing required Prometheus query (query)")

        # Check required assertions configuration
        assertions = self.get_rule_config(rule, "assertions", [])
        if not assertions:
            issues.append("Missing required assertions configuration (assertions)")

        return issues

    def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """
        Apply Prometheus rule for checking - simplified version

        Args:
            rule: rule object
            context: context

        Returns:
            Check result
        """
        # Get query and assertions configuration
        query = self.get_rule_config(rule, "query", "")
        assertions = self.get_rule_config(rule, "assertions", [])

        # Execute query
        try:
            # Execute instant query (simplified version, no longer supports complex range queries)
            result = self.prometheus_client.query(query)

            # Process result
            metrics = self._process_query_result(result)
            if not metrics:
                return self.rule_processor.format_rule_result(
                    rule=rule,
                    status="passed",
                    description=f"{rule.name}: no data",
                    severity="info",
                    details="Prometheus query returned no matching metric data",
                    solution="",
                )

            # Extract data for assertion evaluation
            variables = self._extract_metrics_variables(metrics)

            # Generate name suffix containing context information
            name_suffix = self._generate_context_suffix(metrics, variables)

            # Evaluate assertions
            assertion_result = self.rule_processor.evaluate_assertions(
                assertions, variables
            )

            # Return check result based on assertion result
            if assertion_result["passed"]:
                # For passed checks, display specific monitoring data in description
                first_assertion = assertions[0] if assertions else {}
                first_assertion_desc = first_assertion.get("description", "")
                if first_assertion_desc:
                    # Render template to display specific values
                    rendered_desc = (
                        self.rule_processor.assertion_manager.render_template(
                            first_assertion_desc, variables
                        )
                    )
                    description = f"{rule.name}: {rendered_desc}"
                else:
                    # Display key metric values
                    if "max_value" in variables:
                        description = (
                            f"{rule.name}: maximum value {variables['max_value']:.2f}"
                        )
                    elif "value" in variables:
                        description = (
                            f"{rule.name}: current value {variables['value']:.2f}"
                        )
                    else:
                        description = f"{rule.name}: check passed"

                result = self.rule_processor.format_rule_result(
                    rule=rule,
                    status="passed",
                    description=description,
                    severity="info",
                    details="Monitoring metrics are normal",
                    solution="",
                )
            else:
                # Remove "Assertion failed: " prefix, use description directly
                clean_description = assertion_result["description"].replace(
                    "Assertion failed: ", ""
                )

                result = self.rule_processor.format_rule_result(
                    rule=rule,
                    status="failed",
                    description=clean_description,
                    severity=assertion_result["severity"],
                    details=f"Monitoring alert triggered\nQuery: {query}\nResult value: {self._format_simple_metrics(metrics)}",
                    solution=rule.solution,
                )

            # Add context information to name
            if name_suffix:
                result["name"] = f"{rule.name} - {name_suffix}"

            return result

        except Exception as e:
            logger.exception(f"Error executing Prometheus query: {str(e)}")
            return self._format_error_result(
                rule, "Error executing Prometheus query", str(e)
            )

    def _process_query_result(self, result: Dict) -> List[Dict]:
        """
        Process Prometheus query result - simplified version, supports only vector type

        Args:
            result: Prometheus query result

        Returns:
            Processed metrics list
        """
        metrics = []

        # Check result format
        if not result or not isinstance(result, dict):
            return metrics

        data = result.get("data", {})
        result_type = data.get("resultType")
        result_data = data.get("result", [])

        if not result_data:
            return metrics

        # Only process instant query results (vector type)
        if result_type == "vector":
            for item in result_data:
                metric = {
                    "metric": item.get("metric", {}),
                    "value": (
                        float(item.get("value", [0, "0"])[1])
                        if item.get("value")
                        else 0
                    ),
                }
                metrics.append(metric)
        else:
            # No longer supports matrix type complex time series
            logger.warning(
                f"Unsupported query result type: {result_type}, use instant query"
            )

        return metrics

    def _extract_metrics_variables(self, metrics: List[Dict]) -> Dict[str, Any]:
        """
        Extract variables from metrics for assertion evaluation

        Args:
            metrics: metrics list

        Returns:
            Variables dictionary
        """
        variables = {
            # Store list of all values for easy calculation of average, maximum, etc.
            "values": [m.get("value", 0) for m in metrics],
        }

        # If only one metric, use its value directly
        if len(metrics) == 1:
            variables["value"] = metrics[0].get("value", 0)

            # Add labels as variables
            metric_labels = metrics[0].get("metric", {})
            for label, label_value in metric_labels.items():
                variables[f"label_{label}"] = label_value

        # Add aggregated values
        if variables["values"]:
            variables["max_value"] = max(variables["values"])
            variables["min_value"] = min(variables["values"])
            variables["avg_value"] = sum(variables["values"]) / len(variables["values"])

        return variables

    def _generate_context_suffix(
        self, metrics: List[Dict], variables: Dict[str, Any]
    ) -> str:
        """
        Generate name suffix containing context information

        Args:
            metrics: metrics list
            variables: variables dictionary

        Returns:
            Context suffix string
        """
        if not metrics:
            return ""

        # If only one metric, try to extract meaningful labels
        if len(metrics) == 1:
            metric_labels = metrics[0].get("metric", {})

            # Prioritize displaying node-related information
            if "instance" in metric_labels:
                instance = metric_labels["instance"]
                # Clean instance format (usually IP:PORT or hostname:PORT)
                if ":" in instance:
                    instance = instance.split(":")[0]
                return f"Node {instance}"
            elif "node" in metric_labels:
                return f"Node {metric_labels['node']}"
            elif "job" in metric_labels:
                return f"Job {metric_labels['job']}"
            elif "__name__" in metric_labels:
                return f"Metric {metric_labels['__name__']}"

        # If multiple metrics, display number of metrics
        elif len(metrics) > 1:
            # Try to find common labels
            first_metric_labels = metrics[0].get("metric", {})
            if "job" in first_metric_labels:
                job_name = first_metric_labels["job"]
                return f"{len(metrics)} instances of {job_name}"
            else:
                return f"{len(metrics)} instances"

        return ""

    def _format_simple_metrics(self, metrics: List[Dict]) -> str:
        """
        Simplified metrics formatting method

        Args:
            metrics: metrics list

        Returns:
            Formatted metrics string
        """
        if not metrics:
            return "No data"

        if len(metrics) == 1:
            metric = metrics[0]
            value = metric.get("value", "N/A")
            return f"Current value: {value}"
        else:
            values = [m.get("value", 0) for m in metrics]
            max_val = max(values)
            avg_val = sum(values) / len(values)
            return f"Maximum value: {max_val:.2f}, Average value: {avg_val:.2f}, Total {len(metrics)} instances"

    def get_rule_config(self, rule: Rule, key: str, default: Any = None) -> Any:
        """
        Get value of specific key from rule configuration

        Args:
            rule: rule object
            key: configuration key
            default: default value returned if key does not exist

        Returns:
            Configuration value or default value
        """
        if rule.config and key in rule.config:
            return rule.config[key]
        return default

    def _format_skipped_result(self, rule: Rule, reason: str) -> Dict:
        """
        Format skipped rule result (delegated to ResultFormatter)

        Args:
            rule: rule object
            reason: skip reason

        Returns:
            Result dictionary
        """
        return self.rule_processor.result_formatter.skipped_result(rule, reason)

    def _format_error_result(self, rule: Rule, error_type: str, error_msg: str) -> Dict:
        """
        Format error result (delegated to ResultFormatter)

        Args:
            rule: rule object
            error_type: error type
            error_msg: error message

        Returns:
            Result dictionary
        """
        full_error_msg = f"Error type: {error_type}\nError information: {error_msg}\nSolution recommendation: Check Prometheus connection configuration and query syntax"
        return self.rule_processor.result_formatter.error_result(
            rule, full_error_msg, f"{rule.name} error: {error_type}"
        )
