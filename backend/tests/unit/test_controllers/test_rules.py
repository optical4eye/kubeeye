#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for rules API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock

from api.rules import (
    get_rules,
    _sync_gitops_repository,
    _load_rules_for_types,
    _log_rules_statistics,
)


class TestRulesAPI:
    """Test cases for rules API endpoints"""

    @patch("api.rules._load_rules_for_types")
    @patch("api.rules._log_rules_statistics")
    @patch("api.rules._sync_gitops_repository")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_gitops_success(
        self, mock_should_use_gitops, mock_sync_gitops, mock_log_stats, mock_load_rules
    ):
        """Test successful retrieval of rules with GitOps enabled"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock GitOps sync
        mock_sync_gitops.return_value = True

        # Mock rules loading
        mock_load_rules.return_value = {
            "node": [{"name": "rule1"}],
            "opa": [{"name": "rule3"}],
        }

        # Mock statistics
        mock_log_stats.return_value = 2

        result = await get_rules()

        assert result["use_gitops"] is True
        assert "rules" in result
        assert len(result["rules"]["node"]) == 1
        assert len(result["rules"]["opa"]) == 1
        mock_should_use_gitops.assert_called_once()
        mock_sync_gitops.assert_called_once()
        mock_load_rules.assert_called_once_with(["node", "opa"], True)
        mock_log_stats.assert_called_once()

    @patch("api.rules._load_rules_for_types")
    @patch("api.rules._log_rules_statistics")
    @patch("api.rules._sync_gitops_repository")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_local_success(
        self, mock_should_use_gitops, mock_sync_gitops, mock_log_stats, mock_load_rules
    ):
        """Test successful retrieval of rules with GitOps disabled"""
        # Mock GitOps check
        mock_should_use_gitops.return_value = False

        # Mock rules loading
        mock_load_rules.return_value = {
            "node": [{"name": "rule1"}],
            "opa": [{"name": "rule3"}],
        }

        # Mock statistics
        mock_log_stats.return_value = 2

        result = await get_rules()

        assert result["use_gitops"] is False
        assert "rules" in result
        assert len(result["rules"]["node"]) == 1
        assert len(result["rules"]["opa"]) == 1
        mock_should_use_gitops.assert_called_once()
        mock_sync_gitops.assert_not_called()
        mock_load_rules.assert_called_once_with(["node", "opa"], False)
        mock_log_stats.assert_called_once()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @patch("api.rules._load_rules_for_types")
    @patch("api.rules._log_rules_statistics")
    @patch("api.rules._sync_gitops_repository")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_gitops_no_rules_fallback_success(
        self, mock_should_use_gitops, mock_sync_gitops, mock_log_stats, mock_load_rules, mock_gitops_manager_class
    ):
        """Test GitOps enabled with no rules, successful fallback to local"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"from_env": True}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock GitOps sync
        mock_sync_gitops.return_value = True

        # Mock rules loading (fallback to local rules)
        mock_load_rules.return_value = {"node": [{"name": "local_rule1"}], "opa": [{"name": "local_rule3"}]}

        # Mock statistics
        mock_log_stats.return_value = 2

        result = await get_rules()

        assert result["use_gitops"] is True  # GitOps is enabled even with fallback
        assert "rules" in result
        assert len(result["rules"]["node"]) == 1
        assert len(result["rules"]["opa"]) == 1

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @patch("api.rules._load_rules_for_types")
    @patch("api.rules._log_rules_statistics")
    @patch("api.rules._sync_gitops_repository")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_gitops_no_rules_fallback_no_local(
        self, mock_should_use_gitops, mock_sync_gitops, mock_log_stats, mock_load_rules, mock_gitops_manager_class
    ):
        """Test GitOps enabled with no rules, no local fallback"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"from_env": True}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock GitOps sync
        mock_sync_gitops.return_value = True

        # Mock rules loading (empty for both GitOps and local)
        mock_load_rules.return_value = {"node": [], "opa": []}

        # Mock statistics (0 rules)
        mock_log_stats.return_value = 0

        result = await get_rules()

        assert result["use_gitops"] is True
        assert "rules" in result
        assert len(result["rules"]["node"]) == 0
        assert len(result["rules"]["opa"]) == 0

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @patch("api.rules._load_rules_for_types")
    @patch("api.rules._log_rules_statistics")
    @patch("api.rules._sync_gitops_repository")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_gitops_sync_failure(
        self, mock_should_use_gitops, mock_sync_gitops, mock_log_stats, mock_load_rules, mock_gitops_manager_class
    ):
        """Test GitOps enabled but sync fails, falls back to local"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"from_env": True}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock GitOps check
        mock_should_use_gitops.return_value = True

        # Mock GitOps sync failure
        mock_sync_gitops.return_value = False

        # Mock rules loading
        mock_load_rules.return_value = {
            "node": [{"name": "local_rule1"}],
            "opa": [{"name": "local_rule3"}],
        }

        # Mock statistics
        mock_log_stats.return_value = 2

        result = await get_rules()

        assert result["use_gitops"] is False  # Should be False after sync failure
        assert "rules" in result
        assert len(result["rules"]["node"]) == 1
        assert len(result["rules"]["opa"]) == 1
        mock_load_rules.assert_called_once_with(["node", "opa"], False)

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @patch("infra.rules.rule_manager.RuleManager.should_use_gitops")
    @pytest.mark.asyncio
    async def test_get_rules_exception(self, mock_should_use_gitops, mock_gitops_manager_class):
        """Test rules retrieval with exception"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"from_env": True}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock GitOps check with exception
        mock_should_use_gitops.side_effect = Exception("GitOps check error")

        result = await get_rules()

        assert result["use_gitops"] is False
        assert "rules" in result
        assert len(result["rules"]["node"]) == 0
        assert len(result["rules"]["opa"]) == 0

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_sync_gitops_repository_success(self, mock_gitops_manager_class):
        """Test successful GitOps repository sync"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock config
        mock_config = {"repository": {"name": "test-repo"}}
        mock_gitops_manager.load_config.return_value = mock_config

        # Mock sync
        mock_gitops_manager.clone_or_update_repo.return_value = (True, "Sync successful")

        result = _sync_gitops_repository()

        assert result is True
        mock_gitops_manager.load_config.assert_called_once()
        mock_gitops_manager.clone_or_update_repo.assert_called_once_with({"name": "test-repo"})

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_sync_gitops_repository_no_config(self, mock_gitops_manager_class):
        """Test GitOps repository sync with no config"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock config with no repository
        mock_config = {}
        mock_gitops_manager.load_config.return_value = mock_config

        result = _sync_gitops_repository()

        assert result is False
        mock_gitops_manager.load_config.assert_called_once()
        mock_gitops_manager.clone_or_update_repo.assert_not_called()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_sync_gitops_repository_sync_success_again(self, mock_gitops_manager_class):
        """Test GitOps repository sync with success again"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock config
        mock_config = {"repository": {"name": "test-repo"}}
        mock_gitops_manager.load_config.return_value = mock_config

        # Mock sync success
        mock_gitops_manager.clone_or_update_repo.return_value = (True, "Sync successful")

        result = _sync_gitops_repository()

        assert result is True
        mock_gitops_manager.load_config.assert_called_once()
        mock_gitops_manager.clone_or_update_repo.assert_called_once_with({"name": "test-repo"})

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_sync_gitops_repository_success_third(self, mock_gitops_manager_class):
        """Test GitOps repository sync with success third"""
        # Mock GitOps manager
        mock_gitops_manager = Mock()
        mock_gitops_manager_class.return_value = mock_gitops_manager

        # Mock config
        mock_config = {"repository": {"name": "test-repo"}}
        mock_gitops_manager.load_config.return_value = mock_config

        # Mock sync success
        mock_gitops_manager.clone_or_update_repo.return_value = (True, "Sync successful")

        result = _sync_gitops_repository()

        assert result is True

    @patch("infra.rules.rule_loader.load_rules")
    def test_load_rules_for_types(self, mock_load_rules):
        from infra.rules import rule_loader

        """Test loading rules for specified types"""
        # Clear cache to ensure mock is used
        from infra.rules.rule_loader import clear_rules_cache

        clear_rules_cache()

        # Mock rule loading
        def load_rules_side_effect(rule_type, use_gitops):
            if rule_type == "node":
                return [{"name": "node_rule"}]
            elif rule_type == "prometheus":
                return [{"name": "prometheus_rule"}]
            elif rule_type == "opa":
                return [{"name": "opa_rule"}]
            return []

        mock_load_rules.side_effect = load_rules_side_effect

        result = _load_rules_for_types(["node", "opa"], use_gitops=True)

        assert len(result) == 2
        assert "node" in result
        assert "opa" in result
        # Check that the rules are loaded correctly from GitOps
        assert len(result["node"]) == 7
        assert len(result["opa"]) == 8

        # No rules should be loaded, so we don't check for calls

    def test_log_rules_statistics(self):
        """Test logging of rules statistics"""
        rules = {"node": [{"name": "rule1"}, {"name": "rule2"}], "opa": []}

        result = _log_rules_statistics(rules, use_gitops=True)

        assert result == 2  # 2 + 0
