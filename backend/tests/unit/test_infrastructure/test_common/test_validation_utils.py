#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for validation_utils
"""

import pytest

from core.common.unified_validation import (
    validate_cluster_name,
    validate_namespace,
    validate_task_id,
)


class TestValidationUtils:
    """Test cases for validation utilities"""

    def test_validate_cluster_name_valid(self):
        """Test validate_cluster_name with valid names"""
        # Valid names
        assert validate_cluster_name("test-cluster") == "test-cluster"
        assert validate_cluster_name("cluster_123") == "cluster_123"
        assert validate_cluster_name("cluster.name") == "cluster.name"
        assert validate_cluster_name("cluster-name") == "cluster-name"
        assert validate_cluster_name("a") == "a"
        assert validate_cluster_name("A") == "A"

    def test_validate_cluster_name_invalid(self):
        """Test validate_cluster_name with invalid names"""
        # Empty string
        with pytest.raises(ValueError, match="Cluster name is required"):
            validate_cluster_name("")

        # Invalid characters
        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_cluster_name("cluster@name")

        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_cluster_name("cluster name")

        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_cluster_name("cluster/name")

        # Too long
        long_name = "a" * 101
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            validate_cluster_name(long_name)

    def test_validate_cluster_name_stripped(self):
        """Test validate_cluster_name strips whitespace"""
        assert validate_cluster_name("  test-cluster  ") == "test-cluster"

    def test_validate_namespace_valid(self):
        """Test validate_namespace with valid namespaces"""
        # Valid namespaces
        assert validate_namespace("default") == "default"
        assert validate_namespace("kube-system") == "kube-system"
        assert validate_namespace("namespace123") == "namespace123"
        assert validate_namespace("namespace.name") == "namespace.name"
        assert validate_namespace("namespace_name") == "namespace_name"
        assert validate_namespace("a") == "a"

    def test_validate_namespace_invalid(self):
        """Test validate_namespace with invalid namespaces"""
        # Empty string
        with pytest.raises(ValueError, match="Namespace is required"):
            validate_namespace("")

        # Starts with hyphen
        with pytest.raises(ValueError, match="cannot start or end with a hyphen"):
            validate_namespace("-namespace")

        # Ends with hyphen
        with pytest.raises(ValueError, match="cannot start or end with a hyphen"):
            validate_namespace("namespace-")

        # Invalid characters
        with pytest.raises(ValueError, match="lowercase alphanumeric characters"):
            validate_namespace("Namespace")

        with pytest.raises(ValueError, match="lowercase alphanumeric characters"):
            validate_namespace("namespace@")

        with pytest.raises(ValueError, match="lowercase alphanumeric characters"):
            validate_namespace("namespace space")

        # Too long
        long_namespace = "a" * 64
        with pytest.raises(ValueError, match="cannot exceed 63 characters"):
            validate_namespace(long_namespace)

    def test_validate_namespace_stripped(self):
        """Test validate_namespace strips whitespace"""
        assert validate_namespace("  default  ") == "default"

    def test_validate_task_id_valid(self):
        """Test validate_task_id with valid task IDs"""
        # Valid task IDs
        assert validate_task_id("task-123") == "task-123"
        assert validate_task_id("task_123") == "task_123"
        assert validate_task_id("task.123") == "task.123"
        assert validate_task_id("task123") == "task123"
        assert validate_task_id("a") == "a"
        assert validate_task_id("A") == "A"

    def test_validate_task_id_invalid(self):
        """Test validate_task_id with invalid task IDs"""
        # Empty string
        with pytest.raises(ValueError, match="Task ID is required"):
            validate_task_id("")

        # Invalid characters
        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_task_id("task@123")

        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_task_id("task 123")

        with pytest.raises(ValueError, match="can only contain alphanumeric characters"):
            validate_task_id("task/123")

        # Too long
        long_task_id = "a" * 101
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            validate_task_id(long_task_id)

    def test_validate_task_id_stripped(self):
        """Test validate_task_id strips whitespace"""
        assert validate_task_id("  task-123  ") == "task-123"
