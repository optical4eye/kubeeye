#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for GitOps sync manager component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from services.components.gitops_sync_manager import (
    GitOpsSyncManager,
    sync_rules_from_gitops,
    sync_rules,
    get_gitops_status,
    get_repository_info,
)


class TestGitOpsSyncManager:
    """Test cases for GitOps sync manager"""

    @pytest.fixture
    def gitops_sync_manager(self):
        """Create GitOpsSyncManager instance"""
        return GitOpsSyncManager()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_init(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test GitOpsSyncManager initialization"""
        mock_gitops_manager_class.return_value = Mock()

        manager = GitOpsSyncManager()

        assert manager._gitops_manager is None

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_get_gitops_manager_lazy_init(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test lazy initialization of GitOps manager"""
        mock_gitops_manager = Mock()
        mock_gitops_manager_class.return_value = mock_gitops_manager

        manager = gitops_sync_manager._get_gitops_manager()

        assert manager is mock_gitops_manager
        mock_gitops_manager_class.assert_called_once()

        # Second call should return cached instance
        manager2 = gitops_sync_manager._get_gitops_manager()
        assert manager2 is mock_gitops_manager
        mock_gitops_manager_class.assert_called_once()  # Still only called once

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_if_needed_disabled(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test sync_if_needed when GitOps is disabled"""
        success, message = await gitops_sync_manager.sync_if_needed(use_gitops=False)

        assert success is True
        assert message == "GitOps not enabled"
        mock_gitops_manager_class.assert_not_called()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_if_needed_not_configured(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test sync_if_needed when GitOps is not configured"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"repository": None}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        success, message = await gitops_sync_manager.sync_if_needed(use_gitops=True)

        assert success is True
        assert message == "No GitOps repository configured"
        mock_gitops_manager.load_config.assert_called_once()
        mock_gitops_manager.clone_or_update_repo.assert_not_called()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_if_needed_success(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test successful sync_if_needed"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        }
        mock_gitops_manager.clone_or_update_repo.return_value = (True, "Repository synchronized")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        success, message = await gitops_sync_manager.sync_if_needed(use_gitops=True, show_progress=True)

        assert success is True
        assert message == "Repository synchronized"
        mock_gitops_manager.load_config.assert_called_once()
        mock_gitops_manager.clone_or_update_repo.assert_called_once_with(
            {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        )

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_if_needed_sync_failure(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test sync_if_needed when sync fails but continues"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        }
        mock_gitops_manager.clone_or_update_repo.return_value = (False, "Sync failed")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        success, message = await gitops_sync_manager.sync_if_needed(use_gitops=True)

        assert success is True
        assert message == "GitOps sync failed but continuing: Sync failed"

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_if_needed_exception(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test sync_if_needed when exception occurs"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.side_effect = Exception("Config error")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        success, message = await gitops_sync_manager.sync_if_needed(use_gitops=True)

        assert success is True
        assert message == "GitOps sync error but continuing: GitOps synchronization error: Config error"

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_is_configured_true(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test is_configured when GitOps is configured"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        }
        mock_gitops_manager_class.return_value = mock_gitops_manager

        result = gitops_sync_manager.is_configured()

        assert result is True
        mock_gitops_manager.load_config.assert_called_once()

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_is_configured_false(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test is_configured when GitOps is not configured"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"repository": None}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        result = gitops_sync_manager.is_configured()

        assert result is False

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_is_configured_exception(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test is_configured when exception occurs"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.side_effect = Exception("Config error")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        result = gitops_sync_manager.is_configured()

        assert result is False

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_get_gitops_status_enabled(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test get_gitops_status when enabled"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git", "branch": "main"}
        }
        mock_gitops_manager_class.return_value = mock_gitops_manager

        status = gitops_sync_manager.get_gitops_status()

        expected = {
            "enabled": True,
            "repository": "test-repo",
            "url": "https://github.com/test/repo.git",
            "branch": "main",
        }
        assert status == expected

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_get_gitops_status_disabled(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test get_gitops_status when disabled"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.return_value = {"repository": None}
        mock_gitops_manager_class.return_value = mock_gitops_manager

        status = gitops_sync_manager.get_gitops_status()

        expected = {"enabled": False, "repository": None, "url": None, "branch": None}
        assert status == expected

    @patch("infra.gitops.gitops_manager.GitOpsRuleManager")
    def test_get_gitops_status_exception(self, mock_gitops_manager_class, gitops_sync_manager):
        """Test get_gitops_status when exception occurs"""
        mock_gitops_manager = Mock()
        mock_gitops_manager.load_config.side_effect = Exception("Status error")
        mock_gitops_manager_class.return_value = mock_gitops_manager

        status = gitops_sync_manager.get_gitops_status()

        expected = {"enabled": False, "error": "Status error"}
        assert status == expected

    @patch("infra.rules.rule_manager.RuleManager")
    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_success(self, mock_sync_manager_class, mock_rule_manager_class):
        """Test successful sync_rules_from_gitops"""
        mock_rule_manager = Mock()
        mock_rule_manager.should_use_gitops.return_value = True
        mock_rule_manager_class.return_value = mock_rule_manager

        mock_sync_manager = Mock()
        mock_sync_manager.sync_if_needed = AsyncMock(return_value=(True, "Synced"))
        mock_sync_manager_class.return_value = mock_sync_manager

        result = await sync_rules_from_gitops()

        assert result is True
        mock_rule_manager.should_use_gitops.assert_called_once()
        mock_sync_manager.sync_if_needed.assert_called_once_with(use_gitops=True)

    @patch("infra.rules.rule_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_disabled(self, mock_rule_manager_class):
        """Test sync_rules_from_gitops when GitOps is disabled"""
        mock_rule_manager = Mock()
        mock_rule_manager.should_use_gitops.return_value = False
        mock_rule_manager_class.return_value = mock_rule_manager

        result = await sync_rules_from_gitops()

        assert result is False
        mock_rule_manager.should_use_gitops.assert_called_once()

    @patch("infra.rules.rule_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_exception(self, mock_rule_manager_class):
        """Test sync_rules_from_gitops when exception occurs"""
        mock_rule_manager = Mock()
        mock_rule_manager.should_use_gitops.side_effect = Exception("Rule manager error")
        mock_rule_manager_class.return_value = mock_rule_manager

        result = await sync_rules_from_gitops()

        assert result is False

    @patch("infra.rules.rule_manager.RuleManager")
    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    def test_sync_rules_success(self, mock_sync_manager_class, mock_rule_manager_class):
        """Test successful sync_rules"""
        mock_rule_manager = Mock()
        mock_rule_manager.should_use_gitops.return_value = True
        mock_rule_manager_class.return_value = mock_rule_manager

        mock_sync_manager = Mock()
        mock_sync_manager.is_configured.return_value = True
        mock_sync_manager_class.return_value = mock_sync_manager

        result = sync_rules()

        assert result is True

    @patch("infra.rules.rule_manager.RuleManager")
    def test_sync_rules_disabled(self, mock_rule_manager_class):
        """Test sync_rules when GitOps is disabled"""
        mock_rule_manager = Mock()
        mock_rule_manager.should_use_gitops.return_value = False
        mock_rule_manager_class.return_value = mock_rule_manager

        result = sync_rules()

        assert result is False

    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_function(self, mock_sync_manager_class):
        """Test get_gitops_status function"""
        mock_sync_manager = Mock()
        mock_sync_manager.get_gitops_status.return_value = {"enabled": True, "repository": "test"}
        mock_sync_manager_class.return_value = mock_sync_manager

        result = await get_gitops_status()

        assert result == {"enabled": True, "repository": "test"}
        mock_sync_manager.get_gitops_status.assert_called_once()

    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_function_exception(self, mock_sync_manager_class):
        """Test get_gitops_status function with exception"""
        mock_sync_manager = Mock()
        mock_sync_manager.get_gitops_status.side_effect = Exception("Status error")
        mock_sync_manager_class.return_value = mock_sync_manager

        result = await get_gitops_status()

        assert result == {"enabled": False, "error": "Status error"}

    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    def test_get_repository_info_enabled(self, mock_sync_manager_class):
        """Test get_repository_info when enabled"""
        mock_sync_manager = Mock()
        mock_sync_manager.get_gitops_status.return_value = {
            "enabled": True,
            "repository": "test-repo",
            "url": "https://github.com/test/repo.git",
            "branch": "develop",
        }
        mock_sync_manager_class.return_value = mock_sync_manager

        result = get_repository_info()

        expected = {"url": "https://github.com/test/repo.git", "branch": "develop", "last_sync": "Unknown"}
        assert result == expected

    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    def test_get_repository_info_disabled(self, mock_sync_manager_class):
        """Test get_repository_info when disabled"""
        mock_sync_manager = Mock()
        mock_sync_manager.get_gitops_status.return_value = {"enabled": False}
        mock_sync_manager_class.return_value = mock_sync_manager

        result = get_repository_info()

        assert result == {}

    @patch("services.components.gitops_sync_manager.GitOpsSyncManager")
    def test_get_repository_info_exception(self, mock_sync_manager_class):
        """Test get_repository_info with exception"""
        mock_sync_manager = Mock()
        mock_sync_manager.get_gitops_status.side_effect = Exception("Info error")
        mock_sync_manager_class.return_value = mock_sync_manager

        result = get_repository_info()

        assert result == {}
