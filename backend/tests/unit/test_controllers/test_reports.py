#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for reports API controller
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from fastapi import HTTPException
from pathlib import Path

from api.reports import get_reports, get_report, delete_report, export_report_endpoint, create_immediate_report


@pytest.fixture
def mock_pdf_dependencies():
    """Fixture for mocking PDF generation dependencies"""
    with patch("reportlab.lib.pagesizes.A4", (595.27, 841.89)) as mock_a4, patch(
        "reportlab.lib.pagesizes.landscape", side_effect=lambda x: x
    ) as mock_landscape, patch("reportlab.lib.styles.getSampleStyleSheet") as mock_styles, patch(
        "reportlab.platypus.SimpleDocTemplate"
    ) as mock_doc, patch(
        "reportlab.pdfbase.pdfmetrics.registerFont"
    ) as mock_register_font, patch(
        "reportlab.pdfbase.ttfonts.TTFont"
    ) as mock_ttfont, patch(
        "io.BytesIO"
    ) as mock_buffer:

        mock_style_sheet = Mock()
        mock_style_sheet.Heading1 = Mock()
        mock_style_sheet.Normal = Mock()
        mock_styles.return_value = mock_style_sheet

        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance

        mock_buf_instance = Mock()
        mock_buf_instance.getvalue.return_value = b"pdf_content"
        mock_buffer.return_value = mock_buf_instance

        yield {
            "a4": mock_a4,
            "landscape": mock_landscape,
            "styles": mock_styles,
            "doc": mock_doc,
            "register_font": mock_register_font,
            "ttfont": mock_ttfont,
            "buffer": mock_buffer,
        }


class TestReportsAPI:
    """Test cases for reports API endpoints"""

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_success(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test successful retrieval of reports"""
        # Mock validation
        mock_validate_limit.return_value = 100

        # Mock results with pagination metadata
        mock_list_results.return_value = {
            "results": [
                {"result_id": "report1", "cluster_name": "cluster1", "timestamp": "2023-01-01T00:00:00"},
                {"result_id": "report2", "cluster_name": "cluster2", "timestamp": "2023-01-02T00:00:00"},
            ],
            "total": 2,
            "limit": 100,
            "offset": 0,
        }

        result = await get_reports(limit=100)

        assert "reports" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert len(result["reports"]) == 2
        assert result["total"] == 2
        mock_validate_limit.assert_called_once_with(100)
        mock_clear_cache.assert_called_once()
        mock_list_results.assert_called_once_with(limit=100, offset=0, order_by="timestamp DESC")

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_exception(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test retrieval of reports with exception"""
        # Mock validation
        mock_validate_limit.return_value = 100

        # Mock exception
        mock_list_results.side_effect = Exception("List error")

        # The function should raise HTTPException with status 500
        with pytest.raises(HTTPException) as exc_info:
            await get_reports(limit=100)

        assert exc_info.value.status_code == 500
        assert "List error" in str(exc_info.value.detail)
        mock_validate_limit.assert_called_once_with(100)
        mock_clear_cache.assert_called_once()
        mock_list_results.assert_called_once_with(limit=100, offset=0, order_by="timestamp DESC")

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_success(self, mock_validate_id, mock_load_result):
        """Test successful retrieval of specific report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock report - return a valid report that exists
        mock_load_result.return_value = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        result = await get_report("report-123")

        assert result["result_id"] == "validated-report-123"
        assert result["cluster_name"] == "test-cluster"
        mock_validate_id.assert_called_once_with("report-123")
        mock_load_result.assert_called_once_with("validated-report-123")

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_not_found(self, mock_validate_id, mock_load_result):
        """Test retrieval of non-existent report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock report not found
        mock_load_result.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_report("report-123")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_success(self, mock_validate_id, mock_get_db, mock_delete):
        """Test successful deletion of report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock db session
        mock_db = AsyncMock()

        # Mock get_db as an async generator that yields the mock db
        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock delete
        mock_delete.return_value = True

        result = await delete_report("report-123")

        assert result["message"] == "Report validated-report-123 deleted"
        mock_validate_id.assert_called_once_with("report-123")
        mock_delete.assert_called_once_with("validated-report-123")

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_not_found(self, mock_validate_id, mock_get_db, mock_delete):
        """Test deletion of non-existent report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock db session
        mock_db = AsyncMock()

        # Mock get_db as an async generator that yields the mock db
        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock delete not found
        mock_delete.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_report("report-123")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_success(self, mock_validate_id):
        """Test successful export of report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        with patch(
            "api.reports.load_result", return_value={"result_id": "validated-report-123", "cluster_name": "test"}
        ):
            result = await export_report_endpoint("report-123", "json")

        mock_validate_id.assert_called_once_with("report-123")
        # Check that result is a response object
        assert hasattr(result, "headers") or hasattr(result, "body")

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_invalid_format(self, mock_validate_id):
        """Test export with invalid format"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        with pytest.raises(HTTPException) as exc_info:
            await export_report_endpoint("report-123", "invalid")

        assert exc_info.value.status_code == 400
        assert "Format must be one of" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_export_failure(self, mock_validate_id):
        """Test export with failure"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock load_result to return None (report not found)
        with patch("api.reports.load_result", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await export_report_endpoint("report-123", "json")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

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

        with pytest.raises(HTTPException) as exc_info:
            await create_immediate_report()

        assert exc_info.value.status_code == 404
        assert "No clusters found" in str(exc_info.value.detail)

    @patch("services.cluster_service.ClusterService.get_clusters_list")
    @pytest.mark.asyncio
    async def test_create_immediate_report_clusters_data_missing(self, mock_get_clusters):
        """Test creation of immediate report with missing clusters data"""
        # Mock missing clusters data
        mock_get_clusters.return_value = {}

        with pytest.raises(HTTPException) as exc_info:
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

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_success(self, mock_validate_id):
        """Test successful PDF export of report"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Mock report data with inspection results
        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_type": "full",
            "inspection_results": {
                "node": {
                    "items": [
                        {
                            "name": "Check SSH access",
                            "status": "passed",
                            "severity": "high",
                            "description": "SSH access check",
                            "details": "SSH connection successful",
                            "solution": "No action needed",
                        }
                    ]
                }
            },
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            with patch("reportlab.lib.pagesizes.A4", (595.27, 841.89)):
                with patch("reportlab.lib.pagesizes.landscape", side_effect=lambda x: x):
                    with patch("reportlab.lib.styles.getSampleStyleSheet") as mock_styles:
                        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
                            with patch("reportlab.pdfbase.pdfmetrics.registerFont"):
                                with patch("reportlab.pdfbase.ttfonts.TTFont"):
                                    with patch("io.BytesIO") as mock_buffer:
                                        # Mock styles
                                        mock_style_sheet = Mock()
                                        mock_style_sheet.Heading1 = Mock()
                                        mock_style_sheet.Normal = Mock()
                                        mock_styles.return_value = mock_style_sheet

                                        # Mock document
                                        mock_doc_instance = Mock()
                                        mock_doc.return_value = mock_doc_instance

                                        # Mock buffer
                                        mock_buf_instance = Mock()
                                        mock_buf_instance.getvalue.return_value = b"pdf_content"
                                        mock_buffer.return_value = mock_buf_instance

                                        result = await export_report_endpoint("report-123", "pdf")

                                        assert result is not None
                                        mock_validate_id.assert_called_once_with("report-123")

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_missing_reportlab(self, mock_validate_id):
        """Test PDF export when reportlab is not installed"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        mock_report_data = {"result_id": "validated-report-123", "cluster_name": "test-cluster"}

        with patch("api.reports.load_result", return_value=mock_report_data):
            # Mock ImportError for reportlab by patching sys.modules
            import sys

            with patch.dict(sys.modules, {"reportlab": None}):
                with pytest.raises(HTTPException) as exc_info:
                    await export_report_endpoint("report-123", "pdf")

                assert exc_info.value.status_code == 500
                assert "PDF export not available. Install reportlab: pip install reportlab" in str(
                    exc_info.value.detail
                )

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_json_with_complex_data(self, mock_validate_id):
        """Test JSON export with complex inspection data"""
        # Mock validation
        mock_validate_id.return_value = "validated-report-123"

        # Complex report data
        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_type": "full",
            "inspection_results": {
                "node": {
                    "items": [
                        {
                            "name": "Check SSH access",
                            "status": "passed",
                            "severity": "high",
                            "description": "SSH access check with unicode: тест",
                            "details": "SSH connection successful ✓",
                            "solution": "No action needed 🚀",
                        }
                    ]
                },
                "opa": {
                    "items": [
                        {
                            "name": "Check OPA policies",
                            "status": "failed",
                            "severity": "critical",
                            "description": "OPA policy validation",
                            "details": "Policy violation detected",
                            "solution": "Update policy configuration",
                        }
                    ]
                },
            },
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            result = await export_report_endpoint("report-123", "json")

            assert result is not None
            # Check that result is a StreamingResponse with correct media type
            from fastapi.responses import StreamingResponse

            assert isinstance(result, StreamingResponse)
            assert result.media_type == "application/json"

    @patch("api.reports.list_results")
    @patch("api.reports.clear_metadata_cache")
    @patch("core.common.unified_validation.validate_limit_param")
    @pytest.mark.asyncio
    async def test_get_reports_with_different_limits(self, mock_validate_limit, mock_clear_cache, mock_list_results):
        """Test get_reports with different limit values"""
        # Test with limit 0
        mock_validate_limit.return_value = 0
        mock_list_results.return_value = {
            "results": [],
            "total": 0,
            "limit": 0,
            "offset": 0,
        }

        result = await get_reports(limit=0)
        assert "reports" in result
        mock_list_results.assert_called_with(limit=0, offset=0, order_by="timestamp DESC")

        # Test with large limit
        mock_validate_limit.return_value = 1000
        mock_list_results.return_value = {
            "results": [{"result_id": "report1"}],
            "total": 1,
            "limit": 1000,
            "offset": 0,
        }

        result = await get_reports(limit=1000)
        assert len(result["reports"]) == 1
        assert result["total"] == 1

    @patch("api.reports.load_result")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_get_report_with_minimal_data(self, mock_validate_id, mock_load_result):
        """Test get_report with minimal valid data"""
        mock_validate_id.return_value = "validated-report-123"

        # Minimal valid report
        mock_load_result.return_value = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        result = await get_report("report-123")

        assert result["result_id"] == "validated-report-123"
        assert result["cluster_name"] == "test-cluster"

    @patch("db.repositories.inspection_result_repository.InspectionResultRepository.delete_by_result_id")
    @patch("db.database.get_db")
    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_delete_report_with_db_error(self, mock_validate_id, mock_get_db, mock_delete):
        """Test delete_report with database error"""
        mock_validate_id.return_value = "validated-report-123"

        mock_db = AsyncMock()

        async def mock_get_db_gen():
            yield mock_db

        mock_get_db.return_value = mock_get_db_gen()

        # Mock database error
        mock_delete.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await delete_report("report-123")

        assert exc_info.value.status_code == 500
        assert "Database connection failed" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_not_found(self, mock_validate_id):
        """Test export when report not found"""
        mock_validate_id.return_value = "validated-report-123"

        with patch("api.reports.load_result", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await export_report_endpoint("report-123", "json")

            assert exc_info.value.status_code == 404
            assert "Report not found" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_with_empty_data(self, mock_validate_id):
        """Test PDF export with empty inspection results"""
        mock_validate_id.return_value = "validated-report-123"

        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            with patch("reportlab.lib.pagesizes.A4", (595.27, 841.89)):
                with patch("reportlab.lib.pagesizes.landscape", side_effect=lambda x: x):
                    with patch("reportlab.lib.styles.getSampleStyleSheet") as mock_styles:
                        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
                            with patch("reportlab.pdfbase.pdfmetrics.registerFont"):
                                with patch("reportlab.pdfbase.ttfonts.TTFont"):
                                    with patch("io.BytesIO") as mock_buffer:
                                        # Mock styles
                                        mock_style_sheet = Mock()
                                        mock_style_sheet.Heading1 = Mock()
                                        mock_style_sheet.Normal = Mock()
                                        mock_styles.return_value = mock_style_sheet

                                        # Mock document
                                        mock_doc_instance = Mock()
                                        mock_doc.return_value = mock_doc_instance

                                        # Mock buffer
                                        mock_buf_instance = Mock()
                                        mock_buf_instance.getvalue.return_value = b"pdf_content"
                                        mock_buffer.return_value = mock_buf_instance

                                        result = await export_report_endpoint("report-123", "pdf")

                                        assert result is not None
                                        mock_validate_id.assert_called_once_with("report-123")

    @pytest.mark.asyncio
    async def test_get_reports_validation_error(self):
        """Test get_reports with validation error"""
        with patch(
            "core.common.unified_validation.validate_limit_param", side_effect=ValueError("Limit must be at least 1")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_reports(limit=-1)

            assert exc_info.value.status_code == 500
            assert "Limit must be at least 1" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_report_validation_error(self):
        """Test get_report with validation error"""
        with patch("api.reports.validate_task_id", side_effect=ValueError("Invalid ID")):
            with pytest.raises(HTTPException) as exc_info:
                await get_report("invalid-id")

            assert exc_info.value.status_code == 500
            assert "Invalid ID" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_report_validation_error(self):
        """Test delete_report with validation error"""
        with patch("api.reports.validate_task_id", side_effect=ValueError("Invalid ID")):
            with pytest.raises(HTTPException) as exc_info:
                await delete_report("invalid-id")

            assert exc_info.value.status_code == 500
            assert "Invalid ID" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_export_report_validation_error(self):
        """Test export_report with validation error"""
        with patch("api.reports.validate_task_id", side_effect=ValueError("Invalid ID")):
            with pytest.raises(HTTPException) as exc_info:
                await export_report_endpoint("invalid-id", "json")

            assert exc_info.value.status_code == 500
            assert "Invalid ID" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_with_empty_inspection_results(self, mock_validate_id, mock_pdf_dependencies):
        """Test PDF export with empty inspection results"""
        mock_validate_id.return_value = "validated-report-123"

        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {},
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            result = await export_report_endpoint("report-123", "pdf")

            assert result is not None
            mock_validate_id.assert_called_once_with("report-123")

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_font_registration_failure(self, mock_validate_id, mock_pdf_dependencies):
        """Test PDF export when font registration fails but export succeeds"""
        mock_validate_id.return_value = "validated-report-123"

        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {"node": {"items": []}},
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            with patch("reportlab.pdfbase.pdfmetrics.registerFont", side_effect=Exception("Font error")):
                result = await export_report_endpoint("report-123", "pdf")

                # Should still succeed despite font error
                assert result is not None


# Helper function for mocking file operations
def mock_open(read_data=""):
    """Mock open function for file operations"""
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=read_data)
