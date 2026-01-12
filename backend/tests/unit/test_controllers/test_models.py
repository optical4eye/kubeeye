# -*- coding: utf-8 -*-
"""
Unit tests for API models validation
"""

import pytest
from pydantic import ValidationError

from api.models import (
    ClusterCreate,
    NodesTestRequest,
    KubeconfigTestRequest,
    InspectionRequest,
    ScheduledTaskCreate,
    GitOpsConfig,
    RuleUpdate,
    QueueStatusRequest,
    QueueTasksRequest,
    TaskIdRequest,
)


class TestClusterCreate:
    """Test cases for ClusterCreate model"""

    def test_valid_cluster_create(self):
        """Test valid cluster creation data with secrets"""
        data = {
            "name": "test-cluster",
            "nodes": [
                {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "name": "node1",
                    "username": "testuser",
                    "auth_type": "password",
                    "password": "${secret:test-password-secret}",
                }
            ],
            "kubeconfig": "${secret:test-kubeconfig-secret}",
        }

        cluster = ClusterCreate(**data)
        assert cluster.name == "test-cluster"
        assert len(cluster.nodes) == 1
        assert cluster.kubeconfig == "${secret:test-kubeconfig-secret}"

    def test_invalid_cluster_name_empty(self):
        """Test cluster creation with empty name"""
        data = {
            "name": "",
            "nodes": [],
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "name" in str(exc_info.value)

    def test_invalid_cluster_name_too_long(self):
        """Test cluster creation with name too long"""
        data = {
            "name": "a" * 101,
            "nodes": [],
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "name" in str(exc_info.value)

    def test_invalid_nodes_not_list(self):
        """Test cluster creation with invalid nodes type"""
        data = {
            "name": "test-cluster",
            "nodes": "not_a_list",
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "nodes" in str(exc_info.value)

    def test_invalid_node_missing_ip(self):
        """Test cluster creation with node missing IP"""
        data = {
            "name": "test-cluster",
            "nodes": [{"port": 22}],
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "validation error" in str(exc_info.value).lower()

    def test_invalid_direct_password_input(self):
        """Test cluster creation with direct password input (should fail)"""
        data = {
            "name": "test-cluster",
            "nodes": [
                {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "name": "node1",
                    "username": "testuser",
                    "auth_type": "password",
                    "password": "direct-password",  # Direct input, not a secret reference
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "Direct password input is not allowed" in str(exc_info.value)

    def test_invalid_direct_kubeconfig_input(self):
        """Test cluster creation with direct kubeconfig input (should fail)"""
        data = {
            "name": "test-cluster",
            "nodes": [],
            "kubeconfig": "YXBpVmVyc2lvbjogdjEK",  # Direct input, not a secret reference
        }

        with pytest.raises(ValidationError) as exc_info:
            ClusterCreate(**data)

        assert "Direct kubeconfig input is not allowed" in str(exc_info.value)

    def test_valid_secret_reference_password(self):
        """Test cluster creation with secret reference for password"""
        data = {
            "name": "test-cluster",
            "nodes": [
                {
                    "ip": "192.168.1.1",
                    "port": 22,
                    "name": "node1",
                    "username": "testuser",
                    "auth_type": "password",
                    "password": "${secret:my-password-secret}",
                }
            ],
        }

        cluster = ClusterCreate(**data)
        assert cluster.nodes[0]["password"] == "${secret:my-password-secret}"

    def test_valid_secret_reference_kubeconfig(self):
        """Test cluster creation with secret reference for kubeconfig"""
        data = {
            "name": "test-cluster",
            "nodes": [],
            "kubeconfig": "${secret:my-kubeconfig-secret}",
        }

        cluster = ClusterCreate(**data)
        assert cluster.kubeconfig == "${secret:my-kubeconfig-secret}"


class TestNodesTestRequest:
    """Test cases for NodesTestRequest model"""

    def test_valid_test_nodes_request(self):
        """Test valid test nodes request"""
        data = {
            "nodes": [
                {"ip": "192.168.1.1", "port": 22},
                {"ip": "192.168.1.2"},
            ]
        }

        request = NodesTestRequest(**data)
        assert len(request.nodes) == 2
        assert request.nodes[0]["ip"] == "192.168.1.1"
        assert request.nodes[0]["port"] == 22
        assert request.nodes[1]["port"] == 22  # default port

    def test_invalid_test_nodes_not_list(self):
        """Test test nodes request with invalid nodes type"""
        data = {"nodes": "not_a_list"}

        with pytest.raises(ValidationError) as exc_info:
            NodesTestRequest(**data)

        assert "nodes" in str(exc_info.value)

    def test_invalid_node_ip(self):
        """Test test nodes request with invalid IP"""
        data = {"nodes": [{"ip": "invalid_ip"}]}

        with pytest.raises(ValidationError) as exc_info:
            NodesTestRequest(**data)

        assert "validation error" in str(exc_info.value).lower()


class TestKubeconfigTestRequest:
    """Test cases for KubeconfigTestRequest model"""

    def test_valid_kubeconfig_request(self):
        """Test valid kubeconfig test request"""
        data = {"kubeconfig": "base64content"}

        request = KubeconfigTestRequest(**data)
        assert request.kubeconfig == "base64content"

    def test_invalid_kubeconfig_missing(self):
        """Test kubeconfig request with missing field"""
        data = {}

        with pytest.raises(ValidationError) as exc_info:
            KubeconfigTestRequest(**data)

        assert "kubeconfig" in str(exc_info.value)


class TestInspectionRequest:
    """Test cases for InspectionRequest model"""

    def test_valid_inspection_request(self):
        """Test valid inspection request"""
        data = {
            "cluster_name": "test-cluster",
            "selected_rules": {"node": ["rule1"], "opa": ["rule2"]},
            "inspection_type": "immediate",
        }

        request = InspectionRequest(**data)
        assert request.cluster_name == "test-cluster"
        assert request.selected_rules == {"node": ["rule1"], "opa": ["rule2"]}
        assert request.inspection_type == "immediate"

    def test_invalid_cluster_name(self):
        """Test inspection request with invalid cluster name"""
        data = {"cluster_name": ""}

        with pytest.raises(ValidationError) as exc_info:
            InspectionRequest(**data)

        assert "cluster_name" in str(exc_info.value)

    def test_invalid_inspection_type(self):
        """Test inspection request with invalid inspection type"""
        data = {
            "cluster_name": "test-cluster",
            "inspection_type": "invalid_type",
        }

        with pytest.raises(ValidationError) as exc_info:
            InspectionRequest(**data)

        assert "inspection_type" in str(exc_info.value)


class TestScheduledTaskCreate:
    """Test cases for ScheduledTaskCreate model"""

    def test_valid_scheduled_task_create(self):
        """Test valid scheduled task creation"""
        data = {
            "name": "test-task",
            "description": "Test task description",
            "cluster": "test-cluster",
            "cron_expr": "0 0 * * *",
            "rules": {"node": ["rule1"]},
            "enabled": True,
        }

        task = ScheduledTaskCreate(**data)
        assert task.name == "test-task"
        assert task.description == "Test task description"
        assert task.cluster == "test-cluster"
        assert task.cron_expr == "0 0 * * *"
        assert task.enabled is True

    def test_invalid_task_name_empty(self):
        """Test scheduled task with empty name"""
        data = {
            "name": "",
            "description": "desc",
            "cluster": "cluster",
            "cron_expr": "* * * * *",
            "rules": {},
        }

        with pytest.raises(ValidationError) as exc_info:
            ScheduledTaskCreate(**data)

        assert "name" in str(exc_info.value)

    def test_invalid_cluster_name(self):
        """Test scheduled task with invalid cluster name"""
        data = {
            "name": "task",
            "description": "desc",
            "cluster": "",
            "cron_expr": "* * * * *",
            "rules": {},
        }

        with pytest.raises(ValidationError) as exc_info:
            ScheduledTaskCreate(**data)

        assert "cluster" in str(exc_info.value)


class TestGitOpsConfig:
    """Test cases for GitOpsConfig model"""

    def test_valid_gitops_config(self):
        """Test valid GitOps config"""
        data = {"repository": {"url": "https://github.com/user/repo"}}

        config = GitOpsConfig(**data)
        assert config.repository == {"url": "https://github.com/user/repo"}

    def test_empty_gitops_config(self):
        """Test empty GitOps config"""
        config = GitOpsConfig()
        assert config.repository is None


class TestRuleUpdate:
    """Test cases for RuleUpdate model"""

    def test_valid_rule_update(self):
        """Test valid rule update"""
        data = {"enabled": True, "config": {"key": "value"}}

        update = RuleUpdate(**data)
        assert update.enabled is True
        assert update.config == {"key": "value"}

    def test_partial_rule_update(self):
        """Test partial rule update"""
        data = {"enabled": False}

        update = RuleUpdate(**data)
        assert update.enabled is False
        assert update.config is None


class TestQueueStatusRequest:
    """Test cases for QueueStatusRequest model"""

    def test_valid_queue_status_request(self):
        """Test valid queue status request"""
        request = QueueStatusRequest()
        # No fields to validate
        assert request is not None


class TestQueueTasksRequest:
    """Test cases for QueueTasksRequest model"""

    def test_valid_queue_tasks_request(self):
        """Test valid queue tasks request"""
        data = {"limit": 100, "status_filter": "pending"}

        request = QueueTasksRequest(**data)
        assert request.limit == 100
        assert request.status_filter == "pending"

    def test_invalid_limit_too_low(self):
        """Test queue tasks request with limit too low"""
        data = {"limit": 0}

        with pytest.raises(ValidationError) as exc_info:
            QueueTasksRequest(**data)

        assert "limit" in str(exc_info.value)

    def test_invalid_limit_too_high(self):
        """Test queue tasks request with limit too high"""
        data = {"limit": 1001}

        with pytest.raises(ValidationError) as exc_info:
            QueueTasksRequest(**data)

        assert "limit" in str(exc_info.value)

    def test_invalid_status_filter(self):
        """Test queue tasks request with invalid status filter"""
        data = {"status_filter": "invalid_status"}

        with pytest.raises(ValidationError) as exc_info:
            QueueTasksRequest(**data)

        assert "status_filter" in str(exc_info.value)


class TestTaskIdRequest:
    """Test cases for TaskIdRequest model"""

    def test_valid_task_id_request(self):
        """Test valid task ID request"""
        data = {"task_id": "task-123"}

        request = TaskIdRequest(**data)
        assert request.task_id == "task-123"

    def test_invalid_task_id_empty(self):
        """Test task ID request with empty ID"""
        data = {"task_id": ""}

        with pytest.raises(ValidationError) as exc_info:
            TaskIdRequest(**data)

        assert "task_id" in str(exc_info.value)
