# Unit tests for reports export functionality
import pytest
from unittest.mock import patch, Mock
from fastapi import HTTPException

from api.reports import export_report_endpoint


class TestReportsExport:
    """Test cases for export_report_endpoint functionality"""

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
        mock_validate_id.return_value = "validated-report-123"

        with pytest.raises(Exception) as exc_info:
            await export_report_endpoint("report-123", "invalid")

        assert exc_info.value.status_code == 400
        assert "Format must be one of" in str(exc_info.value.detail)

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_not_found(self, mock_validate_id):
        """Test export when report not found"""
        mock_validate_id.return_value = "validated-report-123"

        with patch("api.reports.load_result", return_value=None):
            with pytest.raises(Exception) as exc_info:
                await export_report_endpoint("report-123", "json")

        assert exc_info.value.status_code == 404
        assert "Report not found" in str(exc_info.value.detail)

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

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_pdf_font_registration_failure(self, mock_validate_id):
        """Test PDF export when font registration fails"""
        mock_validate_id.return_value = "validated-report-123"

        mock_report_data = {
            "result_id": "validated-report-123",
            "cluster_name": "test-cluster",
            "timestamp": "2023-01-01T00:00:00",
            "inspection_results": {"node": {"items": []}},
        }

        with patch("api.reports.load_result", return_value=mock_report_data):
            with patch("reportlab.pdfbase.pdfmetrics.registerFont", side_effect=Exception("Font error")):
                with patch("reportlab.lib.pagesizes.A4", (595.27, 841.89)):
                    with patch("reportlab.lib.pagesizes.landscape", side_effect=lambda x: x):
                        with patch("reportlab.lib.styles.getSampleStyleSheet") as mock_styles:
                            with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
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

                                    # Should still succeed despite font registration failure
                                    assert result is not None

    @patch("api.reports.validate_task_id")
    @pytest.mark.asyncio
    async def test_export_report_validation_error(self, mock_validate_id):
        """Test export_report with validation error"""
        mock_validate_id.side_effect = ValueError("Invalid ID")

        with pytest.raises(Exception) as exc_info:
            await export_report_endpoint("invalid-id", "json")

        assert "Invalid ID" in str(exc_info.value)
