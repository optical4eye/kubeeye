#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for custom exceptions
"""

import pytest
from core.common.exceptions import (
    KubeEyeException,
    ClusterNotFoundError,
    InspectorError,
    RuleLoadError,
    CommandSecurityError,
    ValidationError,
    GitOpsError,
)


class TestKubeEyeException:
    """Test cases for KubeEyeException base class"""

    def test_kubeye_exception_with_message_only(self):
        """Test KubeEyeException with only message"""
        message = "Test error message"
        exception = KubeEyeException(message)

        assert str(exception) == message
        assert exception.message == message
        assert exception.details == {}

    def test_kubeye_exception_with_message_and_details(self):
        """Test KubeEyeException with message and details"""
        message = "Test error message"
        details = {"code": 500, "context": "test"}
        exception = KubeEyeException(message, details)

        assert str(exception) == message
        assert exception.message == message
        assert exception.details == details

    def test_kubeye_exception_with_none_details(self):
        """Test KubeEyeException with None details"""
        message = "Test error message"
        exception = KubeEyeException(message, None)

        assert str(exception) == message
        assert exception.message == message
        assert exception.details == {}

    def test_kubeye_exception_inheritance(self):
        """Test KubeEyeException inherits from Exception"""
        exception = KubeEyeException("Test")

        assert isinstance(exception, Exception)
        assert isinstance(exception, KubeEyeException)


class TestClusterNotFoundError:
    """Test cases for ClusterNotFoundError"""

    def test_cluster_not_found_error(self):
        """Test ClusterNotFoundError"""
        message = "Cluster not found"
        exception = ClusterNotFoundError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, ClusterNotFoundError)

    def test_cluster_not_found_error_with_details(self):
        """Test ClusterNotFoundError with details"""
        message = "Cluster not found"
        details = {"cluster_name": "test-cluster"}
        exception = ClusterNotFoundError(message, details)

        assert str(exception) == message
        assert exception.message == message
        assert exception.details == details


class TestInspectorError:
    """Test cases for InspectorError"""

    def test_inspector_error(self):
        """Test InspectorError"""
        message = "Inspector failed"
        exception = InspectorError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, InspectorError)


class TestRuleLoadError:
    """Test cases for RuleLoadError"""

    def test_rule_load_error(self):
        """Test RuleLoadError"""
        message = "Failed to load rule"
        exception = RuleLoadError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, RuleLoadError)


class TestCommandSecurityError:
    """Test cases for CommandSecurityError"""

    def test_command_security_error(self):
        """Test CommandSecurityError"""
        message = "Command failed security check"
        exception = CommandSecurityError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, CommandSecurityError)


class TestValidationError:
    """Test cases for ValidationError"""

    def test_validation_error(self):
        """Test ValidationError"""
        message = "Validation failed"
        exception = ValidationError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, ValidationError)


class TestGitOpsError:
    """Test cases for GitOpsError"""

    def test_gitops_error(self):
        """Test GitOpsError"""
        message = "GitOps operation failed"
        exception = GitOpsError(message)

        assert str(exception) == message
        assert exception.message == message
        assert isinstance(exception, KubeEyeException)
        assert isinstance(exception, GitOpsError)


class TestExceptionHierarchy:
    """Test cases for exception hierarchy"""

    def test_all_exceptions_inherit_from_kubeye_exception(self):
        """Test that all custom exceptions inherit from KubeEyeException"""
        exceptions = [
            ClusterNotFoundError,
            InspectorError,
            RuleLoadError,
            CommandSecurityError,
            ValidationError,
            GitOpsError,
        ]

        for exception_class in exceptions:
            exception = exception_class("Test message")
            assert isinstance(exception, KubeEyeException)
            assert isinstance(exception, Exception)

    def test_exception_catching(self):
        """Test that exceptions can be caught properly"""
        # Test catching base exception
        try:
            raise ClusterNotFoundError("Test")
        except KubeEyeException as e:
            assert str(e) == "Test"
            caught = True
        else:
            caught = False

        assert caught

        # Test catching specific exception
        try:
            raise InspectorError("Test")
        except InspectorError as e:
            assert str(e) == "Test"
            caught = True
        else:
            caught = False

        assert caught
