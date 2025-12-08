#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified result formatting module
Provides unified result formatting functions, eliminating duplication of _pass_result, _fail_result, _error_result methods in various inspectors
"""

import logging
from typing import Dict, List, Optional
from utils.rule_loader import Rule

# Logging setup
logger = logging.getLogger(__name__)

class ResultFormatter:
    """
    Unified result formatter
    Combines duplicate result formatting methods from various inspectors
    """

    @staticmethod
    def format_result(rule: Rule, status: str, description: str, severity: str,
                     details: str, solution: Optional[str] = None,
                     violations: Optional[List[Dict]] = None,
                     **kwargs) -> Dict:
        """
        Formatting inspection result (unified version)

        Args:
            rule: rule object
            status: status (passed, failed, error, warning, skipped, etc.)
            description: brief description of result
            severity: severity level
            details: detailed information
            solution: optional problem solution
            violations: optional list of violations
            **kwargs: other additional fields (e.g. node, variables, assertions, etc.)

        Returns:
            formatted result dictionary
        """
        if solution is None:
            solution = rule.solution if hasattr(rule, 'solution') else ""

        result = {
            'name': rule.name,
            'status': status,
            'description': description,
            'severity': severity,
            'details': details,
            'solution': solution,
            'rule_id': rule.id
        }

        # If there are violations, add to result
        if violations is not None:
            result['violations'] = violations

        # Adding other additional fields
        result.update(kwargs)

        return result

    @staticmethod
    def pass_result(rule: Rule, description: str, details: str = "", **kwargs) -> Dict:
        """
        Generate "Passed" result

        Args:
            rule: rule object
            description: description information
            details: detailed information
            **kwargs: other additional fields

        Returns:
            formatted "Passed" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="passed",
            description=description,
            severity="info",
            details=details,
            solution="",
            **kwargs
        )

    @staticmethod
    def fail_result(rule: Rule, description: str, details: str,
                   severity: str = "warning", violations: Optional[List[Dict]] = None,
                   **kwargs) -> Dict:
        """
        Generate "Failed" result

        Args:
            rule: rule object
            description: description information
            details: detailed information
            severity: severity level
            violations: list of violations
            **kwargs: other additional fields

        Returns:
            formatted "Failed" result
        """
        solution = rule.solution if hasattr(rule, 'solution') else ""
        return ResultFormatter.format_result(
            rule=rule,
            status="failed",
            description=description,
            severity=severity,
            details=details,
            solution=solution,
            violations=violations or [],
            **kwargs
        )

    @staticmethod
    def error_result(rule: Rule, error_msg: str, description: Optional[str] = None, **kwargs) -> Dict:
        """
        Generate "Error" result

        Args:
            rule: rule object
            error_msg: error message
            description: custom description, default "Rule execution failed"
            **kwargs: other additional fields

        Returns:
            formatted "Error" result
        """
        if description is None:
            description = "Rule execution failed"

        return ResultFormatter.format_result(
            rule=rule,
            status="error",
            description=description,
            severity="error",
            details=error_msg,
            solution="",
            **kwargs
        )

    @staticmethod
    def warning_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Generate "Warning" result

        Args:
            rule: rule object
            description: description information
            details: detailed information
            **kwargs: other additional fields

        Returns:
            formatted "Warning" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="warning",
            description=description,
            severity="warning",
            details=details,
            solution=rule.solution if hasattr(rule, 'solution') else "",
            **kwargs
        )

    @staticmethod
    def skipped_result(rule: Rule, reason: str, **kwargs) -> Dict:
        """
        Generate "Skipped" result

        Args:
            rule: rule object
            reason: skip reason
            **kwargs: other additional fields

        Returns:
            formatted "Skipped" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="skipped",
            description=f"{rule.name} skipped: {reason}",
            severity="info",
            details=reason,
            solution="",
            **kwargs
        )

    @staticmethod
    def not_applicable_result(rule: Rule, reason: str, **kwargs) -> Dict:
        """
        Generate "Not Applicable" result

        Args:
            rule: rule object
            reason: inapplicability reason
            **kwargs: other additional fields

        Returns:
            formatted "Not Applicable" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="not_applicable",
            description=f"Rule not applicable: {reason}",
            severity="info",
            details=f"Rule {rule.name} not applicable to current environment: {reason}",
            solution="",
            **kwargs
        )

    @staticmethod
    def invalid_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Generate "Invalid Configuration" result

        Args:
            rule: rule object
            description: brief description
            details: detailed information
            **kwargs: other additional fields

        Returns:
            formatted "Invalid Configuration" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="invalid",
            description=description,
            severity="warning",
            details=details,
            solution="Please check rule configuration and fix issues",
            **kwargs
        )

    @staticmethod
    def critical_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Generate "Critical Issue" result

        Args:
            rule: rule object
            description: description information
            details: detailed information
            **kwargs: other additional fields

        Returns:
            formatted "Critical Issue" result
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="failed",
            description=description,
            severity="critical",
            details=details,
            solution=rule.solution if hasattr(rule, 'solution') else "",
            **kwargs
        )