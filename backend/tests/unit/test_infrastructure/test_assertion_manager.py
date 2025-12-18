#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for assertion manager module
"""

import pytest
from unittest.mock import patch, MagicMock
from infrastructure.common.assertion_manager import AssertionManager, AssertionEvaluator


class TestAssertionManager:
    """Test cases for AssertionManager class"""

    @pytest.fixture
    def assertion_manager(self):
        """Create AssertionManager instance"""
        return AssertionManager()

    def test_init(self, assertion_manager):
        """Test AssertionManager initialization"""
        assert assertion_manager.env is not None
        assert hasattr(assertion_manager, "env")

    def test_evaluate_condition_simple_true(self, assertion_manager):
        """Test evaluate_condition with simple true condition"""
        condition = "1 == 1"
        context = {}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is True

    def test_evaluate_condition_simple_false(self, assertion_manager):
        """Test evaluate_condition with simple false condition"""
        condition = "1 == 2"
        context = {}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is False

    def test_evaluate_condition_with_context(self, assertion_manager):
        """Test evaluate_condition with context variables"""
        condition = "value > 10"
        context = {"value": 15}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is True

    def test_evaluate_condition_with_context_false(self, assertion_manager):
        """Test evaluate_condition with context variables that evaluate to false"""
        condition = "value > 10"
        context = {"value": 5}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is False

    def test_evaluate_condition_with_none_value(self, assertion_manager):
        """Test evaluate_condition with None value in context"""
        condition = "value > 10"
        context = {"value": None}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is False  # None should be converted to 0

    def test_evaluate_condition_with_empty_string(self, assertion_manager):
        """Test evaluate_condition with empty string in context"""
        condition = "value > 10"
        context = {"value": ""}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is False  # Empty string should be converted to 0

    def test_evaluate_condition_invalid_expression(self, assertion_manager):
        """Test evaluate_condition with invalid expression"""
        condition = "invalid syntax +++"
        context = {}

        result = assertion_manager.evaluate_condition(condition, context)
        assert result is False  # Should return False on error

    def test_render_template_simple(self, assertion_manager):
        """Test render_template with simple template"""
        template = "Hello {{ name }}!"
        context = {"name": "World"}

        result = assertion_manager.render_template(template, context)
        assert result == "Hello World!"

    def test_render_template_with_condition(self, assertion_manager):
        """Test render_template with conditional logic"""
        template = "{% if value > 10 %}High{% else %}Low{% endif %}"
        context = {"value": 15}

        result = assertion_manager.render_template(template, context)
        assert result == "High"

    def test_render_template_with_condition_false(self, assertion_manager):
        """Test render_template with conditional logic that evaluates to false"""
        template = "{% if value > 10 %}High{% else %}Low{% endif %}"
        context = {"value": 5}

        result = assertion_manager.render_template(template, context)
        assert result == "Low"

    def test_render_template_with_undefined_variable(self, assertion_manager):
        """Test render_template with undefined variable"""
        template = "Hello {{ undefined_var }}!"
        context = {}

        result = assertion_manager.render_template(template, context)
        # Should handle undefined variable gracefully
        assert "undefined_var" in result or "ERROR" in result

    def test_render_template_invalid_template(self, assertion_manager):
        """Test render_template with invalid template syntax"""
        template = "Hello {{ name"
        context = {"name": "World"}

        result = assertion_manager.render_template(template, context)
        assert "ERROR" in result

    def test_evaluate_assertions_empty(self, assertion_manager):
        """Test evaluate_assertions with empty assertions list"""
        assertions = []
        context = {}

        result = assertion_manager.evaluate_assertions(assertions, context)

        assert result["passed"] is True
        assert result["failed_assertions"] == []
        assert result["severity"] == "info"
        assert result["description"] == "No assertions to evaluate"

    def test_evaluate_assertions_simple_mode_passed(self, assertion_manager):
        """Test evaluate_assertions in simple mode with passing assertion"""
        assertions = [
            {"condition": "value > 10", "severity": "warning", "description": "Value should be greater than 10"}
        ]
        context = {"value": 15}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="simple")

        assert result["passed"] is True
        assert result["pass_description"] == "Value should be greater than 10"
        assert result["fail_description"] == ""
        assert result["severity"] == "info"

    def test_evaluate_assertions_simple_mode_failed(self, assertion_manager):
        """Test evaluate_assertions in simple mode with failing assertion"""
        assertions = [
            {"condition": "value > 10", "severity": "warning", "description": "Value should be greater than 10"}
        ]
        context = {"value": 5}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="simple")

        assert result["passed"] is False
        assert result["pass_description"] == ""
        assert result["fail_description"] == "Value should be greater than 10"
        assert result["severity"] == "warning"

    def test_evaluate_assertions_simple_mode_with_template(self, assertion_manager):
        """Test evaluate_assertions in simple mode with template in description"""
        assertions = [
            {
                "condition": "value > 10",
                "severity": "warning",
                "description": "Value {{ value }} is not greater than 10",
            }
        ]
        context = {"value": 5}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="simple")

        assert result["passed"] is False
        assert result["fail_description"] == "Value 5 is not greater than 10"
        assert result["severity"] == "warning"

    def test_evaluate_assertions_detailed_mode_all_passed(self, assertion_manager):
        """Test evaluate_assertions in detailed mode with all assertions passing"""
        assertions = [
            {
                "name": "First assertion",
                "condition": "value > 5",
                "severity": "warning",
                "description": "Value should be greater than 5",
            },
            {
                "name": "Second assertion",
                "condition": "value < 20",
                "severity": "error",
                "description": "Value should be less than 20",
            },
        ]
        context = {"value": 10}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

        assert result["passed"] is True
        assert result["failed_assertions"] == []
        assert result["severity"] == "info"
        assert result["description"] == "All assertions passed"

    def test_evaluate_assertions_detailed_mode_some_failed(self, assertion_manager):
        """Test evaluate_assertions in detailed mode with some assertions failing"""
        assertions = [
            {
                "name": "First assertion",
                "condition": "value > 5",
                "severity": "warning",
                "description": "Value should be greater than 5",
            },
            {
                "name": "Second assertion",
                "condition": "value > 15",
                "severity": "error",
                "description": "Value should be greater than 15",
            },
        ]
        context = {"value": 10}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

        assert result["passed"] is False
        assert len(result["failed_assertions"]) == 1
        assert result["failed_assertions"][0]["name"] == "Second assertion"
        assert result["severity"] == "error"
        assert "Value should be greater than 15" in result["description"]

    def test_evaluate_assertions_detailed_mode_no_condition(self, assertion_manager):
        """Test evaluate_assertions in detailed mode with assertion without condition"""
        assertions = [{"name": "No condition assertion", "severity": "warning", "description": "No condition provided"}]
        context = {}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

        assert result["passed"] is True
        assert result["failed_assertions"] == []

    def test_evaluate_assertions_detailed_mode_error_in_condition(self, assertion_manager):
        """Test evaluate_assertions in detailed mode with error in condition"""
        assertions = [
            {
                "name": "Error assertion",
                "condition": "invalid syntax +++",
                "severity": "warning",
                "description": "Invalid condition",
            }
        ]
        context = {}

        result = assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

        assert result["passed"] is False
        assert len(result["failed_assertions"]) == 1
        assert result["failed_assertions"][0]["name"] == "Error assertion"
        assert result["failed_assertions"][0]["severity"] == "warning"
        assert result["failed_assertions"][0]["description"] == "Invalid condition"

    def test_create_safe_context(self, assertion_manager):
        """Test _create_safe_context method"""
        context = {"normal_value": 10, "none_value": None, "empty_string": "", "normal_string": "hello"}

        safe_context = assertion_manager._create_safe_context(context)

        assert safe_context["normal_value"] == 10
        assert safe_context["none_value"] == 0  # None converted to 0
        assert safe_context["empty_string"] == 0  # Empty string converted to 0
        assert safe_context["normal_string"] == "hello"

    def test_get_highest_severity(self, assertion_manager):
        """Test _get_highest_severity method"""
        # Test with different severities
        severities = ["info", "warning", "error", "critical"]
        result = assertion_manager._get_highest_severity(severities)
        assert result == "critical"

        # Test with some severities
        severities = ["info", "warning"]
        result = assertion_manager._get_highest_severity(severities)
        assert result == "warning"

        # Test with single severity
        severities = ["error"]
        result = assertion_manager._get_highest_severity(severities)
        assert result == "error"

        # Test with empty list
        severities = []
        result = assertion_manager._get_highest_severity(severities)
        assert result == "info"

        # Test with unknown severity
        severities = ["unknown", "info"]
        result = assertion_manager._get_highest_severity(severities)
        assert result == "unknown"


class TestAssertionEvaluator:
    """Test cases for AssertionEvaluator alias"""

    def test_assertion_evaluator_alias(self):
        """Test that AssertionEvaluator is an alias for AssertionManager"""
        assert AssertionEvaluator == AssertionManager

        # Test that we can create an instance
        evaluator = AssertionEvaluator()
        assert isinstance(evaluator, AssertionManager)
