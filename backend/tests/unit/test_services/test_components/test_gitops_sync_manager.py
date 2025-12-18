#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for GitOps sync manager component
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path


class TestGitOpsSyncManager:
    """Test cases for GitOps sync manager"""

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_success(self, mock_rule_manager, mock_gitops_manager):
        """Test successful sync from GitOps"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.return_value = True
        mock_gitops_instance.sync_rules.return_value = True
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = True
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import sync_rules_from_gitops

        result = await sync_rules_from_gitops()

        assert result is True
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.sync_rules.assert_called_once()

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_not_configured(self, mock_rule_manager, mock_gitops_manager):
        """Test sync when GitOps is not configured"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.return_value = False
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = False
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import sync_rules_from_gitops

        result = await sync_rules_from_gitops()

        assert result is False
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.sync_rules.assert_not_called()

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_sync_failure(self, mock_rule_manager, mock_gitops_manager):
        """Test sync when GitOps sync fails"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.return_value = True
        mock_gitops_instance.sync_rules.return_value = False
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = True
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import sync_rules_from_gitops

        result = await sync_rules_from_gitops()

        assert result is False
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.sync_rules.assert_called_once()

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_sync_rules_from_gitops_exception(self, mock_rule_manager, mock_gitops_manager):
        """Test sync when exception occurs"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.side_effect = Exception("GitOps error")
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = True
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import sync_rules_from_gitops

        result = await sync_rules_from_gitops()

        assert result is False
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.sync_rules.assert_not_called()

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_configured(self, mock_rule_manager, mock_gitops_manager):
        """Test getting GitOps status when configured"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.return_value = True
        mock_gitops_instance.get_repository_info.return_value = {
            "url": "https://github.com/example/rules.git",
            "branch": "main",
            "last_sync": "2023-01-01T00:00:00",
        }
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = True
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import get_gitops_status

        result = await get_gitops_status()

        assert result["configured"] is True
        assert result["repository"]["url"] == "https://github.com/example/rules.git"
        assert result["repository"]["branch"] == "main"
        assert result["repository"]["last_sync"] == "2023-01-01T00:00:00"
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.get_repository_info.assert_called_once()

    @patch("services.components.gitops_sync_manager.GitOpsRuleManager")
    @patch("services.components.gitops_sync_manager.RuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_not_configured(self, mock_rule_manager, mock_gitops_manager):
        """Test getting GitOps status when not configured"""
        # Mock GitOps manager
        mock_gitops_instance = Mock()
        mock_gitops_instance.is_configured.return_value = False
        mock_gitops_manager.return_value = mock_gitops_instance

        # Mock rule manager
        mock_rule_instance = Mock()
        mock_rule_instance.should_use_gitops.return_value = False
        mock_rule_manager.return_value = mock_rule_instance

        from services.components.gitops_sync_manager import get_gitops_status

        result = await get_gitops_status()

        assert result["configured"] is False
        assert result["repository"] is None
        mock_gitops_instance.is_configured.assert_called_once()
        mock_gitops_instance.get_repository_info.assert_not_called()
