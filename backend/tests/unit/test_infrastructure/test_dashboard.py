#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for dashboard module
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytz

# We'll test the function with extensive mocking due to its many dependencies


class TestDashboardDataApi:
    """Test cases for get_dashboard_data_api function"""

    @patch("infrastructure.common.dashboard.get_cluster_status_counts_fast")
    @patch("infrastructure.common.dashboard.get_latest_result_by_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_quick_status")
    @patch("infrastructure.common.dashboard.get_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_cert_status")
    @patch("infrastructure.results.inspection_result.list_results")
    @patch("infrastructure.common.dashboard.load_rules")
    @patch("infrastructure.common.dashboard.GitOpsRuleManager")
    @patch("infrastructure.common.dashboard.list_clusters")
    def test_get_dashboard_data_api_basic(
        self,
        mock_list_clusters,
        mock_gitops_manager_class,
        mock_load_rules,
        mock_list_results,
        mock_get_cluster_cert_status,
        mock_get_cluster,
        mock_get_cluster_quick_status,
        mock_get_latest_result_by_cluster,
        mock_get_cluster_status_counts_fast,
    ):
        """Test get_dashboard_data_api with basic mocked data"""
        # Setup mocks
        mock_list_clusters.return_value = ["cluster1", "cluster2"]
        mock_load_rules.side_effect = lambda rule_type: [{"name": f"{rule_type}_rule1"}, {"name": f"{rule_type}_rule2"}]
        mock_list_results.return_value = [
            {"timestamp": "2023-01-01T12:00:00", "critical": 1, "warning": 2, "passed": 10}
        ]
        mock_get_cluster_status_counts_fast.return_value = {"healthy": 1, "warning": 1, "error": 0}

        # Mock GitOps manager
        mock_gitops_manager = MagicMock()
        mock_gitops_manager.load_config.return_value = {"mode": "local"}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock cluster data
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_nodes.return_value = ["node1", "node2"]
        mock_cluster_config.get_kubeconfig.return_value = "kubeconfig_content"
        mock_get_cluster.return_value = mock_cluster_config

        mock_get_cluster_quick_status.return_value = "healthy"
        mock_get_latest_result_by_cluster.return_value = {
            "timestamp": "2023-01-01T12:00:00",
            "critical": 1,
            "warning": 2,
            "passed": 10,
        }
        mock_get_cluster_cert_status.return_value = {"status": "valid", "days_remaining": 30}

        # Import and test function
        from infrastructure.common.dashboard import get_dashboard_data_api

        result = get_dashboard_data_api()

        # Verify structure
        assert isinstance(result, dict)
        assert "clusters" in result
        assert "cluster_statuses" in result
        assert "total_clusters" in result
        assert "recent_scans" in result
        assert "recent_issues" in result
        assert "latest_scan_time" in result
        assert "total_rules" in result
        assert "status_counts" in result
        assert "recent_results" in result

        # Verify values
        assert result["clusters"] == ["cluster1", "cluster2"]
        assert result["total_clusters"] == 2
        assert result["total_rules"] == 6  # 2 rules each for node, prometheus, opa
        assert result["status_counts"] == {"healthy": 1, "warning": 1, "error": 0}
        assert len(result["cluster_statuses"]) == 2
        assert len(result["recent_results"]) == 1
        assert mock_load_rules.call_count == 3

    @patch("infrastructure.common.dashboard.get_cluster_status_counts_fast")
    @patch("infrastructure.common.dashboard.get_latest_result_by_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_quick_status")
    @patch("infrastructure.common.dashboard.get_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_cert_status")
    @patch("infrastructure.results.inspection_result.list_results")
    @patch("infrastructure.common.dashboard.load_rules")
    @patch("infrastructure.common.dashboard.GitOpsRuleManager")
    @patch("infrastructure.common.dashboard.list_clusters")
    def test_get_dashboard_data_api_with_gitops(
        self,
        mock_list_clusters,
        mock_gitops_manager_class,
        mock_load_rules,
        mock_list_results,
        mock_get_cluster_cert_status,
        mock_get_cluster,
        mock_get_cluster_quick_status,
        mock_get_latest_result_by_cluster,
        mock_get_cluster_status_counts_fast,
    ):
        """Test get_dashboard_data_api with GitOps enabled"""
        # Setup mocks
        mock_list_clusters.return_value = ["cluster1"]
        mock_load_rules.side_effect = lambda rule_type: [{"name": f"{rule_type}_rule"}]
        mock_list_results.return_value = []
        mock_get_cluster_status_counts_fast.return_value = {"healthy": 1}

        # Mock GitOps manager with GitOps mode
        mock_gitops_manager = MagicMock()
        mock_gitops_manager.load_config.return_value = {"mode": "gitops", "repository": {"name": "test-repo"}}
        mock_gitops_manager.get_repo_rules.return_value = [{"name": "gitops_rule1"}, {"name": "gitops_rule2"}]
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock cluster data
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_nodes.return_value = []
        mock_cluster_config.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster_config

        mock_get_cluster_quick_status.return_value = "healthy"
        mock_get_latest_result_by_cluster.return_value = None

        from infrastructure.common.dashboard import get_dashboard_data_api

        result = get_dashboard_data_api()

        # Verify GitOps rules are included
        assert result["total_rules"] == 5  # 3 local rules + 2 GitOps rules
        mock_gitops_manager.get_repo_rules.assert_called_once_with("test-repo")

    @patch("infrastructure.common.dashboard.get_cluster_status_counts_fast")
    @patch("infrastructure.common.dashboard.get_latest_result_by_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_quick_status")
    @patch("infrastructure.common.dashboard.get_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_cert_status")
    @patch("infrastructure.results.inspection_result.list_results")
    @patch("infrastructure.common.dashboard.load_rules")
    @patch("infrastructure.common.dashboard.GitOpsRuleManager")
    @patch("infrastructure.common.dashboard.list_clusters")
    def test_get_dashboard_data_api_gitops_error(
        self,
        mock_list_clusters,
        mock_gitops_manager_class,
        mock_load_rules,
        mock_list_results,
        mock_get_cluster_cert_status,
        mock_get_cluster,
        mock_get_cluster_quick_status,
        mock_get_latest_result_by_cluster,
        mock_get_cluster_status_counts_fast,
    ):
        """Test get_dashboard_data_api with GitOps error"""
        # Setup mocks
        mock_list_clusters.return_value = ["cluster1"]
        mock_load_rules.side_effect = lambda rule_type: [{"name": f"{rule_type}_rule"}]
        mock_list_results.return_value = []
        mock_get_cluster_status_counts_fast.return_value = {"healthy": 1}

        # Mock GitOps manager with error
        mock_gitops_manager = MagicMock()
        mock_gitops_manager.load_config.return_value = {"mode": "gitops", "repository": {"name": "test-repo"}}
        mock_gitops_manager.get_repo_rules.side_effect = Exception("GitOps error")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock cluster data
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_nodes.return_value = []
        mock_cluster_config.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster_config

        mock_get_cluster_quick_status.return_value = "healthy"
        mock_get_latest_result_by_cluster.return_value = None

        from infrastructure.common.dashboard import get_dashboard_data_api

        # Should not raise exception, just handle it gracefully
        result = get_dashboard_data_api()

        # Verify only local rules are counted
        assert result["total_rules"] == 3  # Only local rules

    @patch("infrastructure.common.dashboard.get_cluster_status_counts_fast")
    @patch("infrastructure.common.dashboard.get_latest_result_by_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_quick_status")
    @patch("infrastructure.common.dashboard.get_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_cert_status")
    @patch("infrastructure.results.inspection_result.list_results")
    @patch("infrastructure.common.dashboard.load_rules")
    @patch("infrastructure.common.dashboard.GitOpsRuleManager")
    @patch("infrastructure.common.dashboard.list_clusters")
    def test_get_dashboard_data_api_cluster_error(
        self,
        mock_list_clusters,
        mock_gitops_manager_class,
        mock_load_rules,
        mock_list_results,
        mock_get_cluster_cert_status,
        mock_get_cluster,
        mock_get_cluster_quick_status,
        mock_get_latest_result_by_cluster,
        mock_get_cluster_status_counts_fast,
    ):
        """Test get_dashboard_data_api with cluster processing error"""
        # Setup mocks
        mock_list_clusters.return_value = ["cluster1", "cluster2"]
        mock_load_rules.side_effect = lambda rule_type: []
        mock_list_results.return_value = []
        mock_get_cluster_status_counts_fast.return_value = {}

        # Mock GitOps manager
        mock_gitops_manager = MagicMock()
        mock_gitops_manager.load_config.return_value = {"mode": "local"}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock cluster data with error for first cluster
        mock_get_cluster_quick_status.side_effect = ["healthy", Exception("Cluster error")]
        mock_get_latest_result_by_cluster.return_value = None

        from infrastructure.common.dashboard import get_dashboard_data_api

        # Should not raise exception, just handle it gracefully
        result = get_dashboard_data_api()

        # Verify both clusters are processed despite error
        assert len(result["cluster_statuses"]) == 2

        # First cluster should have normal data
        cluster1_status = next(s for s in result["cluster_statuses"] if s["name"] == "cluster1")
        assert cluster1_status["status"] == "healthy"

        # Second cluster should have minimal data due to error
        cluster2_status = next(s for s in result["cluster_statuses"] if s["name"] == "cluster2")
        assert cluster2_status["status"] == "unknown"
        assert cluster2_status["node_count"] == 0
        assert cluster2_status["cert_status"] == "unknown"

    @patch("infrastructure.common.dashboard.get_cluster_status_counts_fast")
    @patch("infrastructure.common.dashboard.get_latest_result_by_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_quick_status")
    @patch("infrastructure.common.dashboard.get_cluster")
    @patch("infrastructure.common.dashboard.get_cluster_cert_status")
    @patch("infrastructure.common.dashboard.list_results")
    @patch("infrastructure.common.dashboard.load_rules")
    @patch("infrastructure.common.dashboard.GitOpsRuleManager")
    @patch("infrastructure.common.dashboard.list_clusters")
    def test_get_dashboard_data_api_no_results(
        self,
        mock_list_clusters,
        mock_gitops_manager_class,
        mock_load_rules,
        mock_list_results,
        mock_get_cluster_cert_status,
        mock_get_cluster,
        mock_get_cluster_quick_status,
        mock_get_latest_result_by_cluster,
        mock_get_cluster_status_counts_fast,
    ):
        """Test get_dashboard_data_api with no results"""
        # Setup mocks
        mock_list_clusters.return_value = []
        mock_load_rules.side_effect = lambda rule_type: []
        mock_list_results.return_value = []
        mock_get_cluster_status_counts_fast.return_value = {}

        # Mock GitOps manager
        mock_gitops_manager = MagicMock()
        mock_gitops_manager.load_config.return_value = {"mode": "local"}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock cluster data
        mock_cluster_config = MagicMock()
        mock_cluster_config.get_nodes.return_value = []
        mock_cluster_config.get_kubeconfig.return_value = None
        mock_get_cluster.return_value = mock_cluster_config

        # Mock cluster status and result
        mock_get_cluster_quick_status.return_value = "healthy"
        mock_get_latest_result_by_cluster.return_value = None

        from infrastructure.common.dashboard import get_dashboard_data_api

        result = get_dashboard_data_api()

        # Verify default values
        assert result["recent_scans"] == 0
        assert result["recent_issues"] == 0
        assert result["latest_scan_time"] == "No data"
        assert result["total_rules"] == 0
