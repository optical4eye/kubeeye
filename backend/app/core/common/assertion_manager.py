#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified assertion manager module
Provides unified assertion evaluation and template rendering functionality, eliminating duplication between AssertionEvaluator and RuleProcessor
"""

from typing import Dict, List, Any
import jinja2
from simpleeval import simple_eval

from core.logging import get_logger

logger = get_logger(__name__)


class AssertionManager:
    """
    Unified assertion manager
    Merges assertion evaluation functionality of AssertionEvaluator and RuleProcessor
    """

    def __init__(self):
        """Initialize assertion manager"""
        # Create Jinja2 environment for template rendering
        self.env = jinja2.Environment(
            undefined=jinja2.DebugUndefined,  # Use debug mode, undefined variables show debug information
            autoescape=False,
        )

    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate single condition expression

        Args:
            condition: condition expression string
            context: context variable dictionary

        Returns:
            whether condition is satisfied
        """
        try:
            # Provide default values for undefined variables
            safe_context = self._create_safe_context(context)

            # Use simpleeval to evaluate expression
            result = simple_eval(condition, names=safe_context)
            return bool(result)

        except Exception as e:
            logger.error(f"Error evaluating condition expression: {str(e)}")
            logger.debug(f"Condition: {condition}, Context: {context}")
            return False

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Use Jinja2 to render template

        Args:
            template: template string
            context: context variables

        Returns:
            rendered string
        """
        try:
            # Provide default values for undefined variables
            safe_context = self._create_safe_context(context)

            # Render template using safe context
            jinja_template = self.env.from_string(template)
            return jinja_template.render(**safe_context)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return f"ERROR: {str(e)}"

    def evaluate_assertions(
        self, assertions: List[Dict], context: Dict[str, Any], mode: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Evaluate assertion list, supports two modes

        Args:
            assertions: assertion configuration list
            context: context variable dictionary
            mode: evaluation mode
                - "simple": simplified mode, only process first assertion (compatible with old AssertionEvaluator)
                - "detailed": detailed mode, process all assertions (compatible with RuleProcessor)

        Returns:
            evaluation result dictionary
        """
        if not assertions:
            return {
                "passed": True,
                "failed_assertions": [],
                "severity": "info",
                "description": "No assertions to evaluate",
                "pass_description": "No assertions to evaluate",
                "fail_description": "",
            }

        if mode == "simple":
            return self._evaluate_simple_mode(assertions, context)
        else:
            return self._evaluate_detailed_mode(assertions, context)

    def _evaluate_simple_mode(self, assertions: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplified mode: only process first assertion (compatible with original AssertionEvaluator)
        """
        assertion = assertions[0]
        condition = assertion.get("condition", "True")
        severity = assertion.get("severity", "warning")
        description = assertion.get("description", "Assertion check")

        try:
            # Evaluate condition
            passed = self.evaluate_condition(condition, context)

            if passed:
                # Generate pass description
                if "{{" in description:
                    pass_description = self.render_template(description, context)
                else:
                    pass_description = description

                return {
                    "passed": True,
                    "pass_description": pass_description,
                    "fail_description": "",
                    "severity": "info",
                }
            else:
                # Generate fail description
                if "{{" in description:
                    fail_description = self.render_template(description, context)
                else:
                    fail_description = description

                return {
                    "passed": False,
                    "pass_description": "",
                    "fail_description": fail_description,
                    "severity": severity,
                }

        except Exception as e:
            logger.error(f"Error evaluating assertion: {str(e)}")
            return {
                "passed": False,
                "pass_description": "",
                "fail_description": f"Assertion evaluation error: {str(e)}",
                "severity": "error",
            }

    def _evaluate_detailed_mode(self, assertions: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detailed mode: process all assertions (compatible with original RuleProcessor)
        """
        failed_assertions = []

        for assertion in assertions:
            name = assertion.get("name", "Unnamed assertion")
            condition = assertion.get("condition", "")
            severity = assertion.get("severity", "warning")
            description = assertion.get("description", "Assertion failed")

            if not condition:
                logger.warning(f"Assertion '{name}' has no defined condition")
                continue

            try:
                # Evaluate condition
                passed = self.evaluate_condition(condition, context)
                if not passed:
                    # Assertion failed
                    failed_assertion = {
                        "name": name,
                        "condition": condition,
                        "severity": severity,
                        "description": self.render_template(description, context),
                    }
                    failed_assertions.append(failed_assertion)
            except Exception as e:
                logger.exception(f"Error evaluating assertion '{name}': {str(e)}")
                failed_assertion = {
                    "name": name,
                    "condition": condition,
                    "severity": "error",
                    "description": f"Error evaluating assertion: {str(e)}",
                }
                failed_assertions.append(failed_assertion)

        # Determine overall evaluation result
        passed = len(failed_assertions) == 0

        # Get highest severity level
        severities = [fa["severity"] for fa in failed_assertions]
        highest_severity = self._get_highest_severity(severities) if severities else "info"

        # Build description information
        if failed_assertions:
            descriptions = [fa["description"] for fa in failed_assertions]
            result_description = "; ".join(descriptions)
        else:
            result_description = "All assertions passed"

        return {
            "passed": passed,
            "failed_assertions": failed_assertions,
            "severity": highest_severity,
            "description": result_description,
        }

    def _create_safe_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create safe context, provide default values for undefined variables

        Args:
            context: original context variable dictionary

        Returns:
            safe context dictionary
        """
        safe_context = {}
        for key, value in context.items():
            if value is None:
                safe_context[key] = 0
            elif isinstance(value, str) and value.strip() == "":
                safe_context[key] = 0
            else:
                safe_context[key] = value
        return safe_context

    def _get_highest_severity(self, severities: List[str]) -> str:
        """
        Get highest severity level

        Args:
            severities: severity level list

        Returns:
            highest severity level
        """
        severity_order = {"critical": 4, "error": 3, "warning": 2, "info": 1}

        max_order = 0
        highest_severity = "info"

        for severity in severities:
            order = severity_order.get(severity.lower(), 1)
            if order > max_order:
                max_order = order
                highest_severity = severity

        return highest_severity
