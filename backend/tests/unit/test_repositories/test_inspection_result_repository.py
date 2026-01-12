# -*- coding: utf-8 -*-
"""
Unit tests for InspectionResultRepository
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.inspection_result_repository import InspectionResultRepository
from db.models.inspection_result import InspectionResult


class TestInspectionResultRepository:
    """Test cases for InspectionResultRepository"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def repo(self, mock_session):
        """InspectionResultRepository instance"""
        return InspectionResultRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_result_id_success(self, repo, mock_session):
        """Test successful result retrieval by result_id"""
        mock_result = Mock(spec=InspectionResult)
        mock_result.result_id = "result-123"

        with patch.object(repo, "get_by_field", new_callable=AsyncMock) as mock_get_by_field:
            mock_get_by_field.return_value = mock_result

            result = await repo.get_by_result_id("result-123")

            assert result == mock_result
            mock_get_by_field.assert_called_once_with("result_id", "result-123")

    @pytest.mark.asyncio
    async def test_get_by_cluster_success(self, repo, mock_session):
        """Test successful results retrieval by cluster"""
        mock_results = [Mock(spec=InspectionResult), Mock(spec=InspectionResult)]

        with patch.object(repo, "get_many_by_field", new_callable=AsyncMock) as mock_get_many:
            mock_get_many.return_value = mock_results

            result = await repo.get_by_cluster("test-cluster")

            assert result == mock_results
            mock_get_many.assert_called_once_with("cluster_name", "test-cluster")

    @pytest.mark.asyncio
    async def test_get_by_type_success(self, repo, mock_session):
        """Test successful results retrieval by type"""
        mock_results = [Mock(spec=InspectionResult)]

        with patch.object(repo, "get_many_by_field", new_callable=AsyncMock) as mock_get_many:
            mock_get_many.return_value = mock_results

            result = await repo.get_by_type("node")

            assert result == mock_results
            mock_get_many.assert_called_once_with("inspection_type", "node")

    @pytest.mark.asyncio
    async def test_list_results_basic(self, repo, mock_session):
        """Test basic results listing"""
        mock_result = Mock(spec=InspectionResult)
        mock_result.cluster_name = "test-cluster"
        mock_result.inspection_type = "node"
        mock_result.timestamp = datetime(2024, 1, 1)
        mock_result.result_id = "result-123"
        mock_result.total_items = 10
        mock_result.passed_count = 8
        mock_result.critical_count = 1
        mock_result.warning_count = 1
        mock_result.info_count = 0

        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = [mock_result]
        mock_query_result.scalar.return_value = 1  # Mock total count
        mock_session.execute.return_value = mock_query_result

        result = await repo.list_results()

        assert "results" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["cluster_name"] == "test-cluster"
        assert result["results"][0]["inspection_type"] == "node"
        assert result["results"][0]["status"] == "failed"  # critical_count > 0
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_results_with_filters(self, repo, mock_session):
        """Test results listing with filters"""
        mock_result = Mock(spec=InspectionResult)
        mock_result.cluster_name = "test-cluster"
        mock_result.inspection_type = "node"
        mock_result.timestamp = datetime(2024, 1, 1)
        mock_result.result_id = "result-123"
        mock_result.total_items = 10
        mock_result.passed_count = 9
        mock_result.critical_count = 0
        mock_result.warning_count = 1
        mock_result.info_count = 0

        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = [mock_result]
        mock_query_result.scalar.return_value = 1  # Mock total count
        mock_session.execute.return_value = mock_query_result

        result = await repo.list_results(
            cluster_name="test-cluster", inspection_type="node", limit=10, offset=0, exclude_inspection_types=["opa"]
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "warning"  # warning_count > 0
        assert result["limit"] == 10
        assert result["offset"] == 0
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_results_ordering(self, repo, mock_session):
        """Test results listing with custom ordering"""
        mock_result = Mock(spec=InspectionResult)
        mock_result.cluster_name = "test-cluster"
        mock_result.inspection_type = "node"
        mock_result.timestamp = datetime(2024, 1, 1)
        mock_result.result_id = "result-123"
        mock_result.total_items = 10
        mock_result.passed_count = 10
        mock_result.critical_count = 0
        mock_result.warning_count = 0
        mock_result.info_count = 0

        mock_query_result = Mock()
        mock_query_result.scalars.return_value.all.return_value = [mock_result]
        mock_query_result.scalar.return_value = 1  # Mock total count
        mock_session.execute.return_value = mock_query_result

        result = await repo.list_results(order_by="timestamp DESC")

        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "passed"
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_results_exception(self, repo, mock_session):
        """Test list_results with exception"""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await repo.list_results()

    @pytest.mark.asyncio
    async def test_save_result_with_summary(self, repo, mock_session):
        """Test saving result with summary data"""
        result_data = {
            "result_id": "result-123",
            "cluster_name": "test-cluster",
            "inspection_type": "node",
            "summary": {
                "total_items": 10,
                "passed": 8,
                "failed": 1,
                "warning": 1,
                "error": 0,
            },
            "execution_info": {
                "execution_duration": 5.5,
                "triggered_by": "user",
                "inspectors_used": ["node"],
            },
        }

        mock_created_result = Mock(spec=InspectionResult)
        mock_created_result.result_id = "result-123"
        mock_created_result.cluster_name = "test-cluster"

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_created_result

            result_id = await repo.save_result(result_data)

            assert result_id == "result-123"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_result_with_inspection_results(self, repo, mock_session):
        """Test saving result with inspection_results format"""
        result_data = {
            "result_id": "result-123",
            "cluster_name": "test-cluster",
            "inspection_type": "node",
            "inspection_results": {
                "node": {
                    "items": [
                        {"status": "passed", "severity": "info"},
                        {"status": "exception", "severity": "warning"},
                        {"status": "exception", "severity": "critical"},
                    ]
                }
            },
            "summary": {
                "total_items": 3,
                "passed": 1,
                "failed": 1,
                "warning": 1,
                "error": 0,
            },
            "execution_info": {
                "execution_duration": 3.2,
                "triggered_by": "scheduled",
                "inspectors_used": ["node"],
            },
        }

        mock_created_result = Mock(spec=InspectionResult)
        mock_created_result.result_id = "result-123"
        mock_created_result.cluster_name = "test-cluster"

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_created_result

            result_id = await repo.save_result(result_data)

            assert result_id == "result-123"

    @pytest.mark.asyncio
    async def test_save_result_exception(self, repo, mock_session):
        """Test save_result with exception"""
        result_data = {
            "result_id": "result-123",
            "cluster_name": "test-cluster",
            "inspection_type": "node",
            "summary": {
                "total_items": 0,
                "passed": 0,
                "failed": 0,
                "warning": 0,
                "error": 0,
            },
        }

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.save_result(result_data)

    @pytest.mark.asyncio
    async def test_delete_by_result_id_success(self, repo, mock_session):
        """Test successful result deletion by result_id"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = True

            result = await repo.delete_by_result_id("result-123")

            assert result is True
            mock_get_by_field_and_delete.assert_called_once_with("result_id", "result-123")

    @pytest.mark.asyncio
    async def test_delete_by_result_id_not_found(self, repo, mock_session):
        """Test result deletion when result doesn't exist"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.return_value = False

            result = await repo.delete_by_result_id("nonexistent-result")

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_by_result_id_exception(self, repo, mock_session):
        """Test delete_by_result_id with exception"""
        with patch.object(repo, "get_by_field_and_delete", new_callable=AsyncMock) as mock_get_by_field_and_delete:
            mock_get_by_field_and_delete.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await repo.delete_by_result_id("result-123")

    @pytest.mark.asyncio
    async def test_get_latest_by_cluster_exception(self, repo, mock_session):
        """Test get_latest_by_cluster with exception"""
        mock_session.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await repo.get_latest_by_cluster("test-cluster")

    @pytest.mark.asyncio
    async def test_save_result_db_error(self, repo, mock_session):
        """Test save_result with database error"""
        result_data = {
            "result_id": "result-123",
            "cluster_name": "test-cluster",
            "inspection_type": "node",
            "summary": {
                "total_items": 0,
                "passed": 0,
                "failed": 0,
                "warning": 0,
                "error": 0,
            },
        }

        with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await repo.save_result(result_data)
