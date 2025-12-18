#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for rule processor module
"""

import pytest
from unittest.mock import Mock, patch
from services.inspectors.rule_processor import RuleProcessor
from infrastructure.rules.rule_loader import Rule


class TestRuleProcessor:
    """Test cases for RuleProcessor class"""

    def test_rule_processor_initialization(self):
        """Test RuleProcessor initialization"""
        processor = RuleProcessor()

        assert processor is not None
        assert hasattr(processor, "assertion_manager")
        assert hasattr(processor, "result_formatter")
        assert hasattr(processor, "result_extractor")
        assert hasattr(processor, "assertion_evaluator")  # Backward compatibility

    def test_get_rule_config(self):
        """Test getting rule configuration"""
        rule = Mock()
        rule.config = {"execution": {"command": "ls -la", "timeout": 30}}

        result = RuleProcessor.get_rule_config(rule, "execution.command")

        assert result == "ls -la"

        # Test with default value
        result = RuleProcessor.get_rule_config(rule, "execution.nonexistent", "default")

        assert result == "default"

        # Test with nested path
        result = RuleProcessor.get_rule_config(rule, "execution.timeout")

        assert result == 30

    def test_get_rule_config_without_config(self):
        """Test getting rule configuration without config dict"""
        rule = Mock()
        rule.config = {}
        rule.command = "ls -la"
        rule.timeout = 30

        result = RuleProcessor.get_rule_config(rule, "command")

        assert result == "ls -la"

        # Test with nested path when attribute is not a dict
        rule.command = "ls -la"
        result = RuleProcessor.get_rule_config(rule, "command.nonexistent", "default")

        assert result == "default"

    def test_get_rule_config_no_config_and_no_attribute(self):
        """Test getting rule configuration when no config and no attribute"""

        # Create a simple mock object without using Mock() to avoid recursion issues
        class SimpleRule:
            def __init__(self):
                self.config = {}

        rule = SimpleRule()

        result = RuleProcessor.get_rule_config(rule, "nonexistent", "default")

        assert result == "default"

    def test_format_rule_result(self):
        """Test formatting rule result"""
        rule = Mock()
        rule.name = "test_rule"
        rule.type = "node"

        processor = RuleProcessor()

        with patch.object(processor.result_formatter, "format_result") as mock_format:
            mock_format.return_value = {"rule_name": "test_rule", "status": "failed", "severity": "high"}

            result = processor.format_rule_result(
                rule=rule,
                status="failed",
                description="Test failed",
                severity="high",
                details="CPU usage is too high",
                solution="Reduce CPU usage",
            )

            assert result["rule_name"] == "test_rule"
            assert result["status"] == "failed"
            assert result["severity"] == "high"

            # Verify the formatter was called with correct parameters
            mock_format.assert_called_once_with(
                rule=rule,
                status="failed",
                description="Test failed",
                severity="high",
                details="CPU usage is too high",
                solution="Reduce CPU usage",
                violations=None,
            )

    def test_get_severity_order(self):
        """Test getting severity order"""
        assert RuleProcessor.get_severity_order("critical") == 4
        assert RuleProcessor.get_severity_order("high") == 3
        assert RuleProcessor.get_severity_order("warning") == 2
        assert RuleProcessor.get_severity_order("info") == 1
        assert RuleProcessor.get_severity_order("unknown") == 0
        assert RuleProcessor.get_severity_order("invalid") == 0

    def test_get_highest_severity(self):
        """Test getting highest severity"""
        severities = ["info", "warning", "high", "critical"]
        result = RuleProcessor.get_highest_severity(severities)

        assert result == "critical"

        # Test with empty list
        result = RuleProcessor.get_highest_severity([])

        assert result == "unknown"

        # Test with mixed case
        severities = ["INFO", "warning", "High"]
        result = RuleProcessor.get_highest_severity(severities)

        assert result == "High"

    def test_evaluate_assertions(self):
        """Test evaluating assertions"""
        processor = RuleProcessor()
        assertions = [{"type": "condition", "condition": "cpu > 80"}, {"type": "condition", "condition": "memory > 90"}]
        context = {"cpu": 85, "memory": 95}

        with patch.object(processor.assertion_manager, "evaluate_assertions") as mock_evaluate:
            mock_evaluate.return_value = {
                "passed": 2,
                "failed": 0,
                "total": 2,
                "results": [
                    {"status": "passed", "condition": "cpu > 80"},
                    {"status": "passed", "condition": "memory > 90"},
                ],
            }

            result = processor.evaluate_assertions(assertions, context)

            assert result["passed"] == 2
            assert result["failed"] == 0
            assert result["total"] == 2

            # Verify the assertion manager was called with correct parameters
            mock_evaluate.assert_called_once_with(assertions, context, mode="detailed")

    def test_extract_variables(self):
        """Test extracting variables from output"""
        processor = RuleProcessor()
        output = "CPU: 85%, Memory: 95%, Disk: 50%"
        extractors = [
            {"type": "regex", "pattern": r"CPU: (\d+)%", "name": "cpu"},
            {"type": "regex", "pattern": r"Memory: (\d+)%", "name": "memory"},
        ]
        context = {"node": "test-node"}

        with patch.object(processor.result_extractor, "extract") as mock_extract:
            mock_extract.return_value = {"cpu": 85, "memory": 95}

            result = processor.extract_variables(output, extractors, context)

            assert result["cpu"] == 85
            assert result["memory"] == 95

            # Verify the extractor was called with correct parameters
            mock_extract.assert_called_once_with(output, extractors, context)

    def test_extract_variables_without_context(self):
        """Test extracting variables without context"""
        processor = RuleProcessor()
        output = "CPU: 85%, Memory: 95%"
        extractors = [{"type": "regex", "pattern": r"CPU: (\d+)%", "name": "cpu"}]

        with patch.object(processor.result_extractor, "extract") as mock_extract:
            mock_extract.return_value = {"cpu": 85}

            result = processor.extract_variables(output, extractors)

            assert result["cpu"] == 85
            mock_extract.assert_called_once_with(output, extractors, None)
