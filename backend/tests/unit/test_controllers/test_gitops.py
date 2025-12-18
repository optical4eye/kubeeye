#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for GitOps API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException

from api.gitops import get_gitops_status, get_gitops_config, sync_gitops_repository


class TestGitOpsAPI:
    """Test cases for GitOps API endpoints"""

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_configured(self, mock_gitops_manager_class):
        """Test getting GitOps status when repository is configured"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"},
            "last_sync": "2023-01-01T12:00:00Z",
        }

        result = await get_gitops_status()

        assert result["enabled"] is True
        assert result["repository"] == "test-repo"
        assert result["last_sync"] == "2023-01-01T12:00:00Z"
        assert result["status"] == "configured"

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_not_configured(self, mock_gitops_manager_class):
        """Test getting GitOps status when repository is not configured"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {}

        result = await get_gitops_status()

        assert result["enabled"] is False
        assert result["repository"] is None
        assert result["last_sync"] is None
        assert result["status"] == "not_configured"

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_exception(self, mock_gitops_manager_class):
        """Test getting GitOps status when exception occurs"""
        mock_gitops_manager_class.side_effect = Exception("GitOps error")

        with pytest.raises(HTTPException) as exc_info:
            await get_gitops_status()

        assert exc_info.value.status_code == 500
        assert "GitOps error" in str(exc_info.value.detail)

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_config_with_repository(self, mock_gitops_manager_class):
        """Test getting GitOps config with repository configured"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {
                "name": "test-repo",
                "url": "https://github.com/test/repo.git",
                "token": "secret-token",
                "username": "test-user",
            },
            "last_sync": "2023-01-01T12:00:00Z",
        }

        result = await get_gitops_config()

        assert result["repository"]["name"] == "test-repo"
        assert result["repository"]["url"] == "https://github.com/test/repo.git"
        assert "token" not in result["repository"]  # Should be removed
        assert "username" not in result["repository"]  # Should be removed
        assert result["last_sync"] == "2023-01-01T12:00:00Z"

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_config_no_repository(self, mock_gitops_manager_class):
        """Test getting GitOps config without repository"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {"last_sync": "2023-01-01T12:00:00Z"}

        result = await get_gitops_config()

        assert result["last_sync"] == "2023-01-01T12:00:00Z"
        assert "repository" not in result

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_config_exception(self, mock_gitops_manager_class):
        """Test getting GitOps config when exception occurs"""
        mock_gitops_manager_class.side_effect = Exception("Config error")

        with pytest.raises(HTTPException) as exc_info:
            await get_gitops_config()

        assert exc_info.value.status_code == 500
        assert "Config error" in str(exc_info.value.detail)

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_gitops_repository_success(self, mock_gitops_manager_class):
        """Test successful GitOps repository synchronization"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        }
        mock_manager.clone_or_update_repo.return_value = (True, "Repository synchronized")

        result = await sync_gitops_repository()

        assert result["message"] == "GitOps repository synchronized successfully"
        mock_manager.clone_or_update_repo.assert_called_once_with(
            {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        )

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_gitops_repository_not_configured(self, mock_gitops_manager_class):
        """Test GitOps repository sync when not configured"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {}

        result = await sync_gitops_repository()

        assert result["success"] is False
        assert "not configured" in result["message"]
        mock_manager.clone_or_update_repo.assert_not_called()

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_gitops_repository_sync_failure(self, mock_gitops_manager_class):
        """Test GitOps repository sync when sync fails"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git"}
        }
        mock_manager.clone_or_update_repo.return_value = (False, "Authentication failed")

        with pytest.raises(HTTPException) as exc_info:
            await sync_gitops_repository()

        assert exc_info.value.status_code == 500
        assert "Failed to sync GitOps repository" in str(exc_info.value.detail)

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_gitops_repository_exception(self, mock_gitops_manager_class):
        """Test GitOps repository sync when exception occurs"""
        mock_gitops_manager_class.side_effect = Exception("Sync error")

        with pytest.raises(HTTPException) as exc_info:
            await sync_gitops_repository()

        assert exc_info.value.status_code == 500
        assert "Sync error" in str(exc_info.value.detail)

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_status_empty_repository(self, mock_gitops_manager_class):
        """Test getting GitOps status with empty repository config"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {"repository": {}}

        result = await get_gitops_status()

        assert result["enabled"] is False
        assert result["repository"] is None
        assert result["status"] == "not_configured"

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_get_gitops_config_repository_without_sensitive_fields(self, mock_gitops_manager_class):
        """Test getting GitOps config when repository has no sensitive fields"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git", "branch": "main"}
        }

        result = await get_gitops_config()

        assert result["repository"]["name"] == "test-repo"
        assert result["repository"]["url"] == "https://github.com/test/repo.git"
        assert result["repository"]["branch"] == "main"

    @patch("infrastructure.gitops.gitops_manager.GitOpsRuleManager")
    @pytest.mark.asyncio
    async def test_sync_gitops_repository_with_branch(self, mock_gitops_manager_class):
        """Test GitOps repository sync with branch specified"""
        mock_manager = Mock()
        mock_gitops_manager_class.return_value = mock_manager
        mock_manager.load_config.return_value = {
            "repository": {"name": "test-repo", "url": "https://github.com/test/repo.git", "branch": "develop"}
        }
        mock_manager.clone_or_update_repo.return_value = (True, "Repository synchronized")

        result = await sync_gitops_repository()

        assert result["message"] == "GitOps repository synchronized successfully"
        mock_manager.clone_or_update_repo.assert_called_once_with(
            {"name": "test-repo", "url": "https://github.com/test/repo.git", "branch": "develop"}
        )
