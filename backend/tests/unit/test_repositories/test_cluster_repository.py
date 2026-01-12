# -*- coding: utf-8 -*-
"""
Unit tests for ClusterRepository
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.cluster_repository import ClusterRepository
from db.models.cluster import Cluster


class TestClusterRepository:
    """Test cases for ClusterRepository"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def repo(self, mock_session):
        """ClusterRepository instance"""
        return ClusterRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_name_success(self, repo, mock_session):
        """Test successful cluster retrieval by name"""
        mock_cluster = Mock(spec=Cluster)
        mock_cluster.name = "test-cluster"

        with patch.object(repo, "get_by_field", new_callable=AsyncMock) as mock_get_by_field:
            mock_get_by_field.return_value = mock_cluster

            result = await repo.get_by_name("test-cluster")

            assert result == mock_cluster
            mock_get_by_field.assert_called_once_with("name", "test-cluster")

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_session):
        """Test cluster retrieval when cluster doesn't exist"""
        with patch.object(repo, "get_by_field", new_callable=AsyncMock) as mock_get_by_field:
            mock_get_by_field.return_value = None

            result = await repo.get_by_name("nonexistent-cluster")

            assert result is None
            mock_get_by_field.assert_called_once_with("name", "nonexistent-cluster")

    @pytest.mark.asyncio
    async def test_get_all_names_success(self, repo, mock_session):
        """Test successful retrieval of all cluster names"""
        mock_result = Mock()
        mock_result.all.return_value = [("cluster1",), ("cluster2",)]
        mock_session.execute.return_value = mock_result

        result = await repo.get_all_names()

        assert result == ["cluster1", "cluster2"]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_names_exception(self, repo, mock_session):
        """Test get_all_names with database exception"""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await repo.get_all_names()

    @pytest.mark.asyncio
    async def test_create_cluster_success(self, repo, mock_session):
        """Test successful cluster creation"""
        mock_created_cluster = Mock(spec=Cluster)
        mock_created_cluster.name = "new-cluster"

        nodes = [{"ip": "192.168.1.1", "port": 22}]
        kubeconfig = "test-kubeconfig"

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_created_cluster

            result = await repo.create_cluster("new-cluster", nodes, kubeconfig)

            assert result == mock_created_cluster
            expected_data = {
                "name": "new-cluster",
                "nodes": nodes,
                "kubeconfig": kubeconfig,
            }
            mock_create.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_create_cluster_default_values(self, repo, mock_session):
        """Test cluster creation with default values"""
        mock_created_cluster = Mock(spec=Cluster)

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_created_cluster

            result = await repo.create_cluster("new-cluster")

            expected_data = {
                "name": "new-cluster",
                "nodes": [],
                "kubeconfig": "",
            }
            mock_create.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_update_cluster_success(self, repo, mock_session):
        """Test successful cluster update"""
        mock_updated_cluster = Mock(spec=Cluster)

        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = mock_updated_cluster

            result = await repo.update_cluster("test-cluster", nodes=[{"ip": "192.168.1.1"}], kubeconfig="new-config")

            assert result == mock_updated_cluster
            mock_get_by_field_and_update.assert_called_once_with(
                "name", "test-cluster", {"nodes": [{"ip": "192.168.1.1"}], "kubeconfig": "new-config"}
            )

    @pytest.mark.asyncio
    async def test_update_cluster_kubeconfig_dict(self, repo, mock_session):
        """Test cluster update with kubeconfig as dict"""
        mock_updated_cluster = Mock(spec=Cluster)

        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = mock_updated_cluster

            kubeconfig_dict = {"kubeconfig": "config-content"}
            result = await repo.update_cluster("test-cluster", kubeconfig=kubeconfig_dict)

            mock_get_by_field_and_update.assert_called_once_with(
                "name", "test-cluster", {"kubeconfig": "config-content"}
            )

    @pytest.mark.asyncio
    async def test_update_cluster_not_found(self, repo, mock_session):
        """Test cluster update when cluster doesn't exist"""
        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = None

            result = await repo.update_cluster("nonexistent-cluster", nodes=[])

            assert result is None

    @pytest.mark.asyncio
    async def test_update_cluster_exception(self, repo, mock_session):
        """Test cluster update with exception"""
        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.update_cluster("test-cluster", nodes=[])

    @pytest.mark.asyncio
    async def test_delete_cluster_success(self, repo, mock_session):
        """Test successful cluster deletion"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = True

            result = await repo.delete_cluster("test-cluster")

            assert result is True
            mock_get_by_field_and_delete.assert_called_once_with("name", "test-cluster")

    @pytest.mark.asyncio
    async def test_delete_cluster_not_found(self, repo, mock_session):
        """Test cluster deletion when cluster doesn't exist"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = False

            result = await repo.delete_cluster("nonexistent-cluster")

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_cluster_exception(self, repo, mock_session):
        """Test cluster deletion with exception"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.delete_cluster("test-cluster")

    @pytest.mark.asyncio
    async def test_get_cluster_config_success(self, repo, mock_session):
        """Test successful cluster config retrieval"""
        from datetime import datetime

        mock_cluster = Mock(spec=Cluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.nodes = [{"ip": "192.168.1.1"}]
        mock_cluster.kubeconfig = "test-config"
        mock_cluster.created_at = datetime(2024, 1, 1)
        mock_cluster.updated_at = datetime(2024, 1, 2)

        with patch.object(repo, "get_by_name", new_callable=AsyncMock) as mock_get_by_name:
            mock_get_by_name.return_value = mock_cluster

            result = await repo.get_cluster_config("test-cluster")

            assert result["name"] == "test-cluster"
            assert result["nodes"] == [{"ip": "192.168.1.1"}]
            assert result["created_at"] == "2024-01-01T00:00:00"
            assert result["updated_at"] == "2024-01-02T00:00:00"
            assert result["kubeconfig"]["kubeconfig"] == "test-config"
            assert result["opa"]["kubeconfig"] == "test-config"

    @pytest.mark.asyncio
    async def test_get_cluster_config_not_found(self, repo, mock_session):
        """Test cluster config retrieval when cluster doesn't exist"""
        with patch.object(repo, "get_by_name", new_callable=AsyncMock) as mock_get_by_name:
            mock_get_by_name.return_value = None

            result = await repo.get_cluster_config("nonexistent-cluster")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_cluster_config_exception(self, repo, mock_session):
        """Test cluster config retrieval with exception"""
        with patch.object(repo, "get_by_name", new_callable=AsyncMock) as mock_get_by_name:
            mock_get_by_name.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.get_cluster_config("test-cluster")

    @pytest.mark.asyncio
    async def test_update_last_inspection_success(self, repo, mock_session):
        """Test successful last inspection update"""
        mock_cluster = Mock(spec=Cluster)

        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = mock_cluster

            result = await repo.update_last_inspection("test-cluster", "result-123", "success")

            assert result is True
            mock_get_by_field_and_update.assert_called_once_with(
                "name", "test-cluster", {"last_inspection": "result-123", "status": "success"}
            )

    @pytest.mark.asyncio
    async def test_update_last_inspection_not_found(self, repo, mock_session):
        """Test last inspection update when cluster doesn't exist"""
        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.return_value = None

            result = await repo.update_last_inspection("nonexistent-cluster", "result-123", "success")

            assert result is False

    @pytest.mark.asyncio
    async def test_update_last_inspection_exception(self, repo, mock_session):
        """Test last inspection update with exception"""
        with patch.object(repo, "get_by_field_and_update", new_callable=AsyncMock) as mock_get_by_field_and_update:
            mock_get_by_field_and_update.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.update_last_inspection("test-cluster", "result-123", "success")
