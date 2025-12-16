#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for OPA inspector
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open

from services.inspectors.opa.opa_inspector import OpaInspector, DateTimeEncoder
from infrastructure.rules.rule_loader import Rule


class TestDateTimeEncoder:
    """Test cases for DateTime JSON encoder"""

    def test_encode_datetime(self):
        """Test encoding datetime objects"""
        encoder = DateTimeEncoder()

        from datetime import datetime, timezone
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = encoder.default(dt)
        assert result == "2023-01-01T12:00:00+00:00"

    def test_encode_date(self):
        """Test encoding date objects"""
        encoder = DateTimeEncoder()

        from datetime import date
        date_obj = date(2023, 1, 1)

        result = encoder.default(date_obj)
        assert result == "2023-01-01"

    def test_encode_timedelta(self):
        """Test encoding timedelta objects"""
        encoder = DateTimeEncoder()

        from datetime import timedelta
        td = timedelta(days=1)

        result = encoder.default(td)
        assert str(result) == "1 day, 0:00:00"

    def test_encode_other_type(self):
        """Test encoding other types falls back to parent"""
        encoder = DateTimeEncoder()

        # Mock the parent default method
        with patch('json.JSONEncoder.default') as mock_parent:
            mock_parent.return_value = "parent_result"

            result = encoder.default("test_string")
            assert result == "parent_result"
            mock_parent.assert_called_once_with("test_string")


class TestOpaInspector:
    """Test cases for OPA inspector"""

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_init(self, mock_k8s_client_class):
        """Test inspector initialization"""
        mock_k8s_client = Mock()
        mock_k8s_client_class.return_value = mock_k8s_client

        config = {
            "kubeconfig": "test-config",
            "opa_path": "/custom/opa/path"
        }

        inspector = OpaInspector(config)

        assert inspector.inspector_type == "opa"
        assert inspector.opa_path == "/custom/opa/path"
        mock_k8s_client_class.assert_called_once_with("test-config")

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_init_default_opa_path(self, mock_k8s_client_class):
        """Test inspector initialization with default OPA path"""
        mock_k8s_client = Mock()
        mock_k8s_client_class.return_value = mock_k8s_client

        config = {}

        inspector = OpaInspector(config)

        assert inspector.opa_path == "/usr/local/bin/opa"
        mock_k8s_client_class.assert_called_once_with(None)

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_validate_rule_complete(self, mock_k8s_client_class):
        """Test rule validation with complete configuration"""
        inspector = OpaInspector({})

        rule = Mock(spec=Rule)
        rule.config = {
            "rego": {"inline": "package test"},
            "resources": [{"kind": "Pod"}],
            "assertions": [{"field": "violation_count", "op": "eq", "value": 0}]
        }

        # Mock the get_rule_config method
        def mock_get_rule_config(r, key, default=None):
            if key == "rego.inline":
                return rule.config.get("rego", {}).get("inline", default)
            elif key == "rego.file":
                return rule.config.get("rego", {}).get("file", default)
            elif key == "resources":
                return rule.config.get("resources", default)
            elif key == "assertions":
                return rule.config.get("assertions", default)
            return default

        inspector.get_rule_config = Mock(side_effect=mock_get_rule_config)

        issues = inspector.validate_rule(rule)

        # The validation checks for "rego.inline" or "rego.file", so it should pass
        assert len(issues) == 0

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_validate_rule_missing_rego(self, mock_k8s_client_class):
        """Test rule validation with missing Rego rules"""
        inspector = OpaInspector({})

        rule = Mock(spec=Rule)
        rule.config = {
            "resources": [{"kind": "Pod"}],
            "assertions": [{"field": "violation_count", "op": "eq", "value": 0}]
        }

        def mock_get_rule_config(r, key, default=None):
            if key == "rego.inline":
                return rule.config.get("rego", {}).get("inline", default)
            elif key == "rego.file":
                return rule.config.get("rego", {}).get("file", default)
            elif key == "resources":
                return rule.config.get("resources", default)
            elif key == "assertions":
                return rule.config.get("assertions", default)
            return default

        inspector.get_rule_config = Mock(side_effect=mock_get_rule_config)

        issues = inspector.validate_rule(rule)

        assert "Missing Rego rules configuration" in issues

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_validate_rule_missing_resources(self, mock_k8s_client_class):
        """Test rule validation with missing resources"""
        inspector = OpaInspector({})

        rule = Mock(spec=Rule)
        rule.config = {
            "rego": {"inline": "package test"},
            "assertions": [{"field": "violation_count", "op": "eq", "value": 0}]
        }

        def mock_get_rule_config(r, key, default=None):
            if key == "rego.inline":
                return rule.config.get("rego", {}).get("inline", default)
            elif key == "rego.file":
                return rule.config.get("rego", {}).get("file", default)
            elif key == "resources":
                return rule.config.get("resources", default)
            elif key == "assertions":
                return rule.config.get("assertions", default)
            return default

        inspector.get_rule_config = Mock(side_effect=mock_get_rule_config)

        issues = inspector.validate_rule(rule)

        assert "Missing resource configuration" in issues

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_validate_rule_missing_assertions(self, mock_k8s_client_class):
        """Test rule validation with missing assertions"""
        inspector = OpaInspector({})

        rule = Mock(spec=Rule)
        rule.config = {
            "rego": {"inline": "package test"},
            "resources": [{"kind": "Pod"}]
        }

        def mock_get_rule_config(r, key, default=None):
            if key == "rego.inline":
                return rule.config.get("rego", {}).get("inline", default)
            elif key == "rego.file":
                return rule.config.get("rego", {}).get("file", default)
            elif key == "resources":
                return rule.config.get("resources", default)
            elif key == "assertions":
                return rule.config.get("assertions", default)
            return default

        inspector.get_rule_config = Mock(side_effect=mock_get_rule_config)

        issues = inspector.validate_rule(rule)

        assert "Missing assertions configuration" in issues

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_get_rego_content_inline(self, mock_k8s_client_class):
        """Test getting Rego content from inline configuration"""
        inspector = OpaInspector({})

        rule = Mock()
        inspector.get_rule_config = Mock(return_value="package test\nallow = true")

        content = inspector._get_rego_content(rule)

        assert content == "package test\nallow = true"
        inspector.get_rule_config.assert_called_with(rule, "rego.inline")

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    @patch('builtins.open', new_callable=mock_open, read_data="package test\nfrom_file")
    @patch('os.path.exists')
    def test_get_rego_content_from_file(self, mock_exists, mock_file, mock_k8s_client_class):
        """Test getting Rego content from file"""
        mock_exists.return_value = True

        inspector = OpaInspector({})

        rule = Mock()
        inspector.get_rule_config = Mock(side_effect=lambda r, key: {
            "rego.inline": None,
            "rego.file": "/path/to/rules.rego"
        }.get(key))

        content = inspector._get_rego_content(rule)

        assert content == "package test\nfrom_file"
        mock_file.assert_called_once_with("/path/to/rules.rego", "r", encoding="utf-8")

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    @patch('os.path.exists')
    def test_get_rego_content_file_not_exists(self, mock_exists, mock_k8s_client_class):
        """Test getting Rego content when file doesn't exist"""
        mock_exists.return_value = False

        inspector = OpaInspector({})

        rule = Mock()
        inspector.get_rule_config = Mock(side_effect=lambda r, key: {
            "rego.inline": None,
            "rego.file": "/nonexistent/rules.rego"
        }.get(key))

        content = inspector._get_rego_content(rule)

        assert content is None

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_get_cluster_resources_success(self, mock_k8s_client_class):
        """Test successful cluster resources retrieval"""
        mock_k8s_client = Mock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_k8s_client.list_resources_from_config_optimized.return_value = {
            "pods": [{"name": "pod1"}, {"name": "pod2"}],
            "services": [{"name": "svc1"}]
        }

        inspector = OpaInspector({})
        rule = Mock()
        rule.config = {"resources": []}

        resources = inspector._get_cluster_resources(rule)

        assert len(resources) == 3
        assert resources[0]["name"] == "pod1"
        assert resources[1]["name"] == "pod2"
        assert resources[2]["name"] == "svc1"

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_get_cluster_resources_fallback(self, mock_k8s_client_class):
        """Test cluster resources retrieval fallback to non-optimized method"""
        mock_k8s_client = Mock()
        mock_k8s_client_class.return_value = mock_k8s_client

        # Remove optimized method
        del mock_k8s_client.list_resources_from_config_optimized

        mock_k8s_client.list_resources_from_config.return_value = {
            "pods": [{"name": "pod1"}]
        }

        inspector = OpaInspector({})
        rule = Mock()
        rule.config = {"resources": []}

        resources = inspector._get_cluster_resources(rule)

        assert len(resources) == 1
        assert resources[0]["name"] == "pod1"
        mock_k8s_client.list_resources_from_config.assert_called_once_with(rule.config)

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    @patch('os.path.exists')
    def test_evaluate_opa_opa_not_found(self, mock_exists, mock_k8s_client_class):
        """Test OPA evaluation when OPA binary not found"""
        mock_exists.return_value = False

        inspector = OpaInspector({})

        with pytest.raises(Exception) as exc_info:
            inspector._evaluate_opa("package test", [{"name": "test"}])

        assert "OPA binary not found" in str(exc_info.value)

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    @patch('os.path.exists')
    @patch('os.access')
    def test_evaluate_opa_not_executable(self, mock_access, mock_exists, mock_k8s_client_class):
        """Test OPA evaluation when OPA binary not executable"""
        mock_exists.return_value = True
        mock_access.return_value = False

        inspector = OpaInspector({})

        with pytest.raises(Exception) as exc_info:
            inspector._evaluate_opa("package test", [{"name": "test"}])

        assert "not executable" in str(exc_info.value)

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_evaluate_assertions_pass(self, mock_k8s_client_class):
        """Test assertion evaluation that passes"""
        inspector = OpaInspector({})

        rule = Mock()
        violations = []
        resource_count = 5

        # Mock rule processor
        inspector.rule_processor = Mock()
        inspector.rule_processor.assertion_manager = Mock()
        inspector.rule_processor.assertion_manager.evaluate_assertions.return_value = {
            "passed": True,
            "pass_description": "All checks passed"
        }
        inspector.rule_processor.result_formatter = Mock()
        inspector.rule_processor.result_formatter.pass_result.return_value = {"status": "passed"}
        inspector.get_rule_config = Mock(return_value=[])

        result = inspector._evaluate_assertions(rule, violations, resource_count)

        # Result should be a dict with pass/fail information
        assert isinstance(result, dict)
        assert "status" in result or "passed" in str(result).lower()

    @patch('services.inspectors.opa.opa_inspector.K8sDynamicClient')
    def test_evaluate_assertions_fail(self, mock_k8s_client_class):
        """Test assertion evaluation that fails"""
        inspector = OpaInspector({})

        rule = Mock()
        violations = [{"message": "Security violation"}]
        resource_count = 3

        # Mock rule processor
        inspector.rule_processor = Mock()
        inspector.rule_processor.assertion_manager = Mock()
        inspector.rule_processor.assertion_manager.evaluate_assertions.return_value = {
            "passed": False,
            "fail_description": "Violations found",
            "severity": "high"
        }
        inspector.rule_processor.result_formatter = Mock()
        inspector.rule_processor.result_formatter.fail_result.return_value = {"status": "failed"}
        inspector.get_rule_config = Mock(return_value=[])

        result = inspector._evaluate_assertions(rule, violations, resource_count)

        # Result should be a dict with fail information
        assert isinstance(result, dict)
        assert "status" in result or "failed" in str(result).lower()

    def test_format_violations_with_dict_violations(self):
        """Test formatting violations with dictionary violations"""
        inspector = OpaInspector({})

        violations = [
            {
                "kind": "Pod",
                "name": "bad-pod",
                "namespace": "default",
                "message": "Security violation detected"
            },
            {
                "kind": "Service",
                "name": "bad-service",
                "message": "Configuration issue"
            }
        ]

        result = inspector._format_violations(violations)

        assert "Pod/bad-pod (namespace: default): Security violation detected" in result
        assert "Service/bad-service: Configuration issue" in result

    def test_format_violations_with_string_violations(self):
        """Test formatting violations with string violations"""
        inspector = OpaInspector({})

        violations = ["Violation 1", "Violation 2"]

        result = inspector._format_violations(violations)

        assert "- Violation 1" in result
        assert "- Violation 2" in result

    def test_format_violations_empty(self):
        """Test formatting empty violations list"""
        inspector = OpaInspector({})

        result = inspector._format_violations([])

        assert "No resources with violations" in result