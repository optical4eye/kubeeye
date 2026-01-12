#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for simplified validation using Pydantic V2
"""

import pytest
from core.common.simplified_validation import (
    ClusterValidationModel,
    InspectionValidationModel,
    NodeValidationModel,
    validate_cluster,
    validate_inspection,
    validate_node,
)


class TestClusterValidationModel:
    """Tests for ClusterValidationModel"""

    def test_valid_cluster(self):
        """Test validation of valid cluster data"""
        data = {
            "name": "test-cluster",
            "nodes": [{"ip": "192.168.1.1", "username": "admin"}],
            "kubeconfig": "test-config",
        }
        validated = ClusterValidationModel(**data)
        assert validated.name == "test-cluster"
        assert len(validated.nodes) == 1
        assert validated.kubeconfig == "test-config"

    def test_cluster_name_normalization(self):
        """Test that cluster name is normalized to lowercase"""
        data = {"name": "Test-Cluster_123", "nodes": []}
        validated = ClusterValidationModel(**data)
        assert validated.name == "test-cluster_123"

    def test_invalid_cluster_name(self):
        """Test validation of invalid cluster name"""
        data = {"name": "test@cluster", "nodes": []}
        with pytest.raises(ValueError, match="Cluster name must contain only"):
            ClusterValidationModel(**data)

    def test_node_without_ip(self):
        """Test validation of node without IP"""
        data = {"name": "test-cluster", "nodes": [{"username": "admin"}]}
        with pytest.raises(ValueError, match='Node at index 0 must have an "ip" field'):
            ClusterValidationModel(**data)

    def test_node_default_name(self):
        """Test that node name defaults to IP"""
        data = {"name": "test-cluster", "nodes": [{"ip": "192.168.1.1"}]}
        validated = ClusterValidationModel(**data)
        assert validated.nodes[0]["name"] == "192.168.1.1"

    def test_empty_nodes(self):
        """Test validation with empty nodes list"""
        data = {"name": "test-cluster", "nodes": []}
        validated = ClusterValidationModel(**data)
        assert validated.nodes == []

    def test_name_too_short(self):
        """Test validation of cluster name that is too short"""
        data = {"name": "", "nodes": []}
        with pytest.raises(ValueError):
            ClusterValidationModel(**data)

    def test_name_too_long(self):
        """Test validation of cluster name that is too long"""
        data = {"name": "a" * 256, "nodes": []}
        with pytest.raises(ValueError):
            ClusterValidationModel(**data)


class TestInspectionValidationModel:
    """Tests for InspectionValidationModel"""

    def test_valid_inspection(self):
        """Test validation of valid inspection data"""
        data = {
            "cluster_name": "test-cluster",
            "inspection_type": "immediate",
            "selected_rules": {"node": ["rule1", "rule2"]},
        }
        validated = InspectionValidationModel(**data)
        assert validated.cluster_name == "test-cluster"
        assert validated.inspection_type == "immediate"
        assert validated.selected_rules == {"node": ["rule1", "rule2"]}

    def test_default_inspection_type(self):
        """Test default inspection type"""
        data = {"cluster_name": "test-cluster"}
        validated = InspectionValidationModel(**data)
        assert validated.inspection_type == "immediate"

    def test_invalid_inspection_type(self):
        """Test validation of invalid inspection type"""
        data = {"cluster_name": "test-cluster", "inspection_type": "invalid"}
        with pytest.raises(ValueError, match="Inspection type must be one of"):
            InspectionValidationModel(**data)

    def test_scheduled_inspection_type(self):
        """Test scheduled inspection type"""
        data = {"cluster_name": "test-cluster", "inspection_type": "scheduled"}
        validated = InspectionValidationModel(**data)
        assert validated.inspection_type == "scheduled"

    def test_cluster_name_too_short(self):
        """Test validation of cluster name that is too short"""
        data = {"cluster_name": ""}
        with pytest.raises(ValueError):
            InspectionValidationModel(**data)


class TestNodeValidationModel:
    """Tests for NodeValidationModel"""

    def test_valid_node(self):
        """Test validation of valid node data"""
        data = {"ip": "192.168.1.1", "port": 22, "username": "admin", "auth_type": "password", "password": "secret"}
        validated = NodeValidationModel(**data)
        assert validated.ip == "192.168.1.1"
        assert validated.port == 22
        assert validated.username == "admin"
        assert validated.auth_type == "password"

    def test_default_port(self):
        """Test default SSH port"""
        data = {"ip": "192.168.1.1", "username": "admin"}
        validated = NodeValidationModel(**data)
        assert validated.port == 22

    def test_default_auth_type(self):
        """Test default authentication type"""
        data = {"ip": "192.168.1.1", "username": "admin"}
        validated = NodeValidationModel(**data)
        assert validated.auth_type == "password"

    def test_invalid_ip(self):
        """Test validation of invalid IP address"""
        data = {"ip": "invalid-ip", "username": "admin"}
        with pytest.raises(ValueError, match="Invalid IP address"):
            NodeValidationModel(**data)

    def test_invalid_auth_type(self):
        """Test validation of invalid authentication type"""
        data = {"ip": "192.168.1.1", "username": "admin", "auth_type": "invalid"}
        with pytest.raises(ValueError, match="Authentication type must be one of"):
            NodeValidationModel(**data)

    def test_port_out_of_range(self):
        """Test validation of port out of range"""
        data = {"ip": "192.168.1.1", "username": "admin", "port": 70000}
        with pytest.raises(ValueError):
            NodeValidationModel(**data)

    def test_key_auth_type(self):
        """Test key authentication type"""
        data = {"ip": "192.168.1.1", "username": "admin", "auth_type": "key", "key_path": "/path/to/key"}
        validated = NodeValidationModel(**data)
        assert validated.auth_type == "key"
        assert validated.key_path == "/path/to/key"


class TestValidateCluster:
    """Tests for validate_cluster function"""

    def test_validate_cluster_success(self):
        """Test successful cluster validation"""
        data = {"name": "test-cluster", "nodes": [{"ip": "192.168.1.1"}]}
        result = validate_cluster(data)
        assert result["name"] == "test-cluster"
        assert len(result["nodes"]) == 1

    def test_validate_cluster_failure(self):
        """Test failed cluster validation"""
        data = {"name": "test@cluster", "nodes": []}
        with pytest.raises(ValueError, match="Invalid cluster data"):
            validate_cluster(data)


class TestValidateInspection:
    """Tests for validate_inspection function"""

    def test_validate_inspection_success(self):
        """Test successful inspection validation"""
        data = {"cluster_name": "test-cluster", "inspection_type": "immediate"}
        result = validate_inspection(data)
        assert result["cluster_name"] == "test-cluster"
        assert result["inspection_type"] == "immediate"

    def test_validate_inspection_failure(self):
        """Test failed inspection validation"""
        data = {"cluster_name": "test-cluster", "inspection_type": "invalid"}
        with pytest.raises(ValueError, match="Invalid inspection data"):
            validate_inspection(data)


class TestValidateNode:
    """Tests for validate_node function"""

    def test_validate_node_success(self):
        """Test successful node validation"""
        data = {"ip": "192.168.1.1", "username": "admin"}
        result = validate_node(data)
        assert result["ip"] == "192.168.1.1"
        assert result["username"] == "admin"

    def test_validate_node_failure(self):
        """Test failed node validation"""
        data = {"ip": "invalid-ip", "username": "admin"}
        with pytest.raises(ValueError, match="Invalid node data"):
            validate_node(data)
