# Unit tests for reports immediate creation functionality
import pytest
from unittest.mock import patch, AsyncMock, Mock

from api.reports import create_immediate_report


class TestReportsImmediate:
    """Test cases for create_immediate_report functionality"""

    @patch("services.inspectors.controller.InspectionController.run_inspection", new_callable=AsyncMock)
    @patch("services.inspectors.controller.InspectionController.save_inspection_result", new_callable=AsyncMock)
    @patch("infra.dependency_injection.container.get_service", new_callable=AsyncMock)
    @patch("services.cluster_service.ClusterService.get_clusters_list", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_create_immediate_report_success(
        self, mock_get_clusters, mock_get_service, mock_save_result, mock_run_inspection
    ):
        """Test successful creation of immediate report"""
        # Mock clusters
        mock_get_clusters.return_value = {"clusters": [{"name": "test-cluster", "nodes": []}]}

        # Mock config
        mock_config = AsyncMock()
        mock_get_service.return_value = mock_config

        # Mock results
        mock_result = Mock()
        mock_result.items = [1, 2, 3]
        mock_run_inspection.return_value = {"node": (True, mock_result)}

        # Mock save result
        mock_save_result.return_value = "report123"

        result = await create_immediate_report()

        assert result["message"] == "Immediate inspection report created successfully"
        assert result["result_id"] == "report123"
        assert result["cluster_name"] == "test-cluster"
        assert result["total_items"] == 3

    @patch("services.cluster_service.ClusterService.get_clusters_list")
    @pytest.mark.asyncio
    async def test_create_immediate_report_no_clusters(self, mock_get_clusters):
        """Test creation of immediate report with no clusters"""
        # Mock no clusters
        mock_get_clusters.return_value = {"clusters": []}

        with pytest.raises(Exception) as exc_info:
            await create_immediate_report()

        assert exc_info.value.status_code == 404
        assert "No clusters found" in str(exc_info.value.detail)

    @patch("services.cluster_service.ClusterService.get_clusters_list")
    @pytest.mark.asyncio
    async def test_create_immediate_report_clusters_data_missing(self, mock_get_clusters):
        """Test creation of immediate report with missing clusters data"""
        # Mock missing clusters data
        mock_get_clusters.return_value = {}

        with pytest.raises(Exception) as exc_info:
            await create_immediate_report()

        assert exc_info.value.status_code == 404
        assert "No clusters found" in str(exc_info.value.detail)

    @patch("services.inspectors.controller.InspectionController.run_inspection", new_callable=AsyncMock)
    @patch("services.inspectors.controller.InspectionController.save_inspection_result", new_callable=AsyncMock)
    @patch("infra.dependency_injection.container.get_service", new_callable=AsyncMock)
    @patch("services.cluster_service.ClusterService.get_clusters_list", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_create_immediate_report_inspection_success(
        self, mock_get_clusters, mock_get_service, mock_save_result, mock_run_inspection
    ):
        """Test creation of immediate report with inspection success"""
        # Mock clusters
        mock_get_clusters.return_value = {"clusters": [{"name": "test-cluster", "nodes": []}]}

        # Mock config
        mock_config = AsyncMock()
        mock_get_service.return_value = mock_config

        # Mock results with success
        mock_result = Mock()
        mock_result.items = [1, 2, 3]
        mock_run_inspection.return_value = {"node": (True, mock_result)}

        # Mock save result
        mock_save_result.return_value = "report123"

        result = await create_immediate_report()

        assert result["message"] == "Immediate inspection report created successfully"
        assert result["result_id"] == "report123"
        assert result["cluster_name"] == "test-cluster"
        assert result["total_items"] == 3

    @patch("services.inspectors.controller.InspectionController.run_inspection", new_callable=AsyncMock)
    @patch("services.inspectors.controller.InspectionController.save_inspection_result", new_callable=AsyncMock)
    @patch("infra.dependency_injection.container.get_service", new_callable=AsyncMock)
    @patch("services.cluster_service.ClusterService.get_clusters_list", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_create_immediate_report_with_string_cluster(
        self, mock_get_clusters, mock_get_service, mock_save_result, mock_run_inspection
    ):
        """Test creation of immediate report with string cluster"""
        # Mock clusters with string
        mock_get_clusters.return_value = {"clusters": ["test-cluster"]}

        # Mock config
        mock_config = AsyncMock()
        mock_get_service.return_value = mock_config

        # Mock results
        mock_result = Mock()
        mock_result.items = [1, 2, 3]
        mock_run_inspection.return_value = {"node": (True, mock_result)}

        # Mock save result
        mock_save_result.return_value = "report123"

        result = await create_immediate_report()

        assert result["cluster_name"] == "test-cluster"
        assert result["total_items"] == 3

    @patch("services.inspectors.controller.InspectionController.run_inspection", new_callable=AsyncMock)
    @patch("services.inspectors.controller.InspectionController.save_inspection_result", new_callable=AsyncMock)
    @patch("infra.dependency_injection.container.get_service", new_callable=AsyncMock)
    @patch("services.cluster_service.ClusterService.get_clusters_list", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_create_immediate_report_with_results(
        self, mock_get_clusters, mock_get_service, mock_save_result, mock_run_inspection
    ):
        """Test creation of immediate report with results"""
        # Mock clusters
        mock_get_clusters.return_value = {"clusters": [{"name": "test-cluster", "nodes": []}]}

        # Mock config
        mock_config = AsyncMock()
        mock_get_service.return_value = mock_config

        # Mock results
        mock_result = Mock()
        mock_result.items = [1, 2, 3]
        mock_run_inspection.return_value = {"node": (True, mock_result)}

        # Mock save result
        mock_save_result.return_value = "report123"

        result = await create_immediate_report()

        assert result["message"] == "Immediate inspection report created successfully"
        assert result["result_id"] == "report123"
        assert result["cluster_name"] == "test-cluster"
        assert result["total_items"] == 3

    @patch("services.inspectors.controller.InspectionController.run_inspection", new_callable=AsyncMock)
    @patch("services.inspectors.controller.InspectionController.save_inspection_result", new_callable=AsyncMock)
    @patch("infra.dependency_injection.container.get_service", new_callable=AsyncMock)
    @patch("services.cluster_service.ClusterService.get_clusters_list", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_create_immediate_report_mixed_result_formats(
        self, mock_get_clusters, mock_get_service, mock_save_result, mock_run_inspection
    ):
        """Test creation of immediate report with mixed result formats"""
        # Mock clusters
        mock_get_clusters.return_value = {"clusters": [{"name": "test-cluster", "nodes": []}]}

        # Mock config
        mock_config = AsyncMock()
        mock_get_service.return_value = mock_config

        # Mock results with mixed formats
        mock_result1 = Mock()
        mock_result1.items = [1, 2, 3]
        mock_result2 = Mock()
        mock_result2.items = [4, 5]
        mock_run_inspection.return_value = {"node": (True, mock_result1), "opa": mock_result2}

        # Mock save result
        mock_save_result.return_value = "report123"

        result = await create_immediate_report()

        assert result["total_items"] == 5  # 3 + 2
