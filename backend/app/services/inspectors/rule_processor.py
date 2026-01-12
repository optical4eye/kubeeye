#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule processor module providing assertion-based rule processing functionality
"""

from typing import Dict, List, Any, Optional

from infra.rules.rule_loader import Rule
from core.common.assertion_manager import AssertionManager
from infra.results.result_formatter import ResultFormatter
from infra.results.result_extractor import ResultExtractor
from core.logging import get_logger

# Set up logging
logger = get_logger(__name__)


class RuleProcessor:
    """
    Rule processor providing common rule processing functionality
    """

    def __init__(self):
        """Initialize the rule processor"""
        self.assertion_manager = AssertionManager()
        self.result_formatter = ResultFormatter()
        self.result_extractor = ResultExtractor()

    @staticmethod
    def get_rule_config(rule: Rule, path: str, default_value: Any = None) -> Any:
        """
        Safely get value from rule configuration, supports dot notation paths

        Args:
            rule: Rule object
            path: Configuration path using dot notation, e.g. "execution.command"
            default_value: Default value if path does not exist

        Returns:
            Value pointed to by the path, or default value if path does not exist
        """
        parts = path.split(".")
        current = getattr(rule, "config", {})

        # Handle case without config, directly get top-level attribute from rule
        if not current and hasattr(rule, parts[0]):
            if len(parts) == 1:
                return getattr(rule, parts[0])
            else:
                # If attribute value is a dictionary, continue processing subpath
                current = getattr(rule, parts[0])
                if not isinstance(current, dict):
                    return default_value
                parts = parts[1:]

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default_value

        return current

    def format_rule_result(
        self,
        rule: Rule,
        status: str,
        description: str,
        severity: str,
        details: str,
        solution: Optional[str] = None,
        violations: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        """
        Format rule check result (delegated to ResultFormatter)

        Args:
            rule: Rule object
            status: Status (passed, failed, error, warning, skipped, unknown)
            description: Brief result description
            severity: Severity level
            details: Detailed information
            solution: Optional solution
            violations: Optional list of violations
            **kwargs: Other additional fields

        Returns:
            Formatted result dictionary
        """
        return self.result_formatter.format_result(
            rule=rule,
            status=status,
            description=description,
            severity=severity,
            details=details,
            solution=solution,
            violations=violations,
            **kwargs
        )

    @staticmethod
    def get_severity_order(severity: str) -> int:
        """
        Get ordinal value of severity level for sorting

        Args:
            severity: Severity level name

        Returns:
            Integer ordinal value of severity level
        """
        severity_order = {
            "critical": 4,
            "high": 3,
            "warning": 2,
            "info": 1,
            "unknown": 0,
        }

        return severity_order.get(severity.lower(), 0)

    @staticmethod
    def get_highest_severity(severities: List[str]) -> str:
        """
        Get the highest severity level

        Args:
            severities: List of severity levels

        Returns:
            Highest severity level
        """
        if not severities:
            return "unknown"

        highest = "unknown"
        highest_order = 0

        for severity in severities:
            order = RuleProcessor.get_severity_order(severity)
            if order > highest_order:
                highest = severity
                highest_order = order

        return highest

    def evaluate_assertions(self, assertions: List[Dict], context: Dict[str, Any]) -> Dict:
        """
        Evaluate set of assertions (delegated to AssertionManager)

        Args:
            assertions: List of assertions
            context: Dictionary of context variables

        Returns:
            Dictionary of evaluation results containing passed, failed assertions, etc.
        """
        return self.assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

    def extract_variables(self, output: str, extractors: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        Extract variables from output

        Args:
            output: Command output
            extractors: List of extractor configurations
            context: Context variables

        Returns:
            Dictionary of extracted variables
        """
        return self.result_extractor.extract(output, extractors, context)
