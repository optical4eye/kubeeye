#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reports management routes
"""

import asyncio
from fastapi import APIRouter, HTTPException
from datetime import datetime
from infra.results.inspection_result import (
    list_results,
    load_result,
    clear_metadata_cache,
)
from core.common.streaming_response import StreamingExportResponse
from core.common.unified_validation import validate_task_id
import json
from services.inspectors.controller import InspectionController
from infra.dependency_injection.container import get_service
from db.database_context import with_db_session

from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/reports")
async def get_reports(limit: int = 100, offset: int = 0):
    """
    Get list of reports with pagination

    Args:
        limit: Maximum number of results to return (default 100)
        offset: Offset for pagination (default 0)

    Returns:
        Dict containing:
            - reports: List of inspection result summaries
            - total: Total count of results
            - limit: Limit used in query
            - offset: Offset used in query
    """
    try:
        # Validate limit parameter using centralized validation
        from core.common.unified_validation import validate_limit_param

        validated_limit = validate_limit_param(limit)

        # Validate offset parameter
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")

        # Clear cache to ensure fresh data
        clear_metadata_cache()

        result_data = await list_results(limit=validated_limit, offset=offset, order_by="timestamp DESC")

        return {
            "reports": result_data["results"],
            "total": result_data["total"],
            "limit": result_data["limit"],
            "offset": result_data["offset"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report by ID"""
    try:
        logger.info(f"Getting report with ID: {report_id}")
        # Validate report_id parameter using centralized validation
        validated_report_id = validate_task_id(report_id)
        logger.info(f"Validated report ID: {validated_report_id}")

        report = await load_result(validated_report_id)
        logger.info(f"Loaded report: {report is not None}")
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        logger.info(
            f"Report type: {type(report)}, keys: {list(report.keys()) if isinstance(report, dict) else 'not dict'}"
        )

        # Sort items by severity level within the report
        def sort_report_items_by_severity(report_data):
            """Sort all items in the report by severity level"""
            logger.info(f"Sorting report items, report_data type: {type(report_data)}")
            if not isinstance(report_data, dict):
                logger.error(f"report_data is not dict: {type(report_data)}")
                return report_data

            severity_order = {
                "critical": 0,
                "high": 1,
                "error": 2,
                "medium": 3,
                "warning": 4,
                "low": 5,
                "info": 6,
            }

            # Check if new format with inspection_results
            if "inspection_results" in report_data:
                logger.info(f"New format: inspection_results keys: {list(report_data['inspection_results'].keys())}")
                for inspector_type, inspector_result in report_data["inspection_results"].items():
                    logger.info(f"Processing inspector {inspector_type}, type: {type(inspector_result)}")
                    items = inspector_result.get("items", [])
                    logger.info(f"Items count: {len(items)}")
                    items.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 7))
            elif "items" in report_data:
                # Old format: sort items directly
                logger.info("Old format: sorting items directly")
                items = report_data["items"]
                if isinstance(items, list):
                    logger.info(f"Items count: {len(items)}")
                    items.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 7))
                else:
                    logger.warning(f"Items is not list: {type(items)}")
            else:
                logger.warning("No items or inspection_results found in report_data")

            return report_data

        # Sort the report items by severity
        sorted_report = sort_report_items_by_severity(report)
        logger.info("Report sorted successfully")

        # Determine inspection type based on results
        if "inspection_results" in sorted_report:
            if "popeye" in sorted_report["inspection_results"]:
                sorted_report["inspection_type"] = "popeye"
            elif "network" in sorted_report["inspection_results"]:
                sorted_report["inspection_type"] = "network"
            else:
                sorted_report["inspection_type"] = "cluster"
        elif "items" in sorted_report:
            # Determine type based on item categories
            categories = set()
            for item in sorted_report["items"]:
                if "category" in item:
                    categories.add(item["category"])
            if "popeye" in categories:
                sorted_report["inspection_type"] = "popeye"
            elif "network" in categories:
                sorted_report["inspection_type"] = "network"
            else:
                sorted_report["inspection_type"] = "cluster"

        return sorted_report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete report from database"""
    try:
        # Validate report_id parameter using centralized validation
        validated_report_id = validate_task_id(report_id)

        from db.repositories.inspection_result_repository import InspectionResultRepository

        async with with_db_session() as db:
            repo = InspectionResultRepository(db)
            if await repo.delete_by_result_id(validated_report_id):
                return {"message": f"Report {validated_report_id} deleted"}
            raise HTTPException(status_code=404, detail="Report not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}/export/{format}")
async def export_report_endpoint(report_id: str, format: str):
    """Export report using streaming (no temporary files)"""
    try:
        # Validate report_id parameter using centralized validation
        validated_report_id = validate_task_id(report_id)

        # Validate format parameter
        valid_formats = ["json", "pdf", "html"]
        if format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Format must be one of: {', '.join(valid_formats)}")

        # Load report data
        result_data = await load_result(validated_report_id)
        if not result_data:
            raise HTTPException(status_code=404, detail="Report not found")

        # Get cluster name from result_data
        cluster_name = result_data.get("cluster_name", "unknown")
        inspection_type = result_data.get("inspection_type", "unknown")

        # Determine filename based on inspection type
        if inspection_type == "popeye":
            filename = f"popeye_{validated_report_id}.{format}"
        else:
            filename = f"{validated_report_id}.{format}"

        if format == "json":
            # JSON streaming
            async def json_generator():
                """Асинхронный генератор JSON данных"""
                try:
                    yield json.dumps(result_data, ensure_ascii=False, indent=2).encode("utf-8")
                except Exception as e:
                    logger.error(f"Error generating JSON export: {e}")
                    raise

            streaming_response = StreamingExportResponse(
                content_generator=json_generator, filename=filename, media_type="application/json"
            )
            return streaming_response.to_response()

        elif format == "html":
            # HTML export (only for Popeye reports)
            if inspection_type != "popeye":
                raise HTTPException(status_code=400, detail="HTML export is only supported for Popeye reports")

            # Find Popeye result in the report data
            popeye_html = None
            if "items" in result_data:
                for item in result_data["items"]:
                    if "popeye_result" in item and item.get("scan_format") == "html":
                        popeye_html = item["popeye_result"]
                        break

            if not popeye_html:
                raise HTTPException(status_code=400, detail="No HTML Popeye result found in the report")

            async def html_generator():
                """Асинхронный генератор HTML данных"""
                try:
                    yield popeye_html.encode("utf-8")
                except Exception as e:
                    logger.error(f"Error generating HTML export: {e}")
                    raise

            streaming_response = StreamingExportResponse(
                content_generator=html_generator, filename=filename, media_type="text/html"
            )
            return streaming_response.to_response()

        elif format == "pdf":
            # PDF streaming (more complex, but possible)
            try:
                # Check if reportlab is available
                import reportlab
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Paragraph,
                    Spacer,
                    Table,
                    TableStyle,
                )
                from reportlab.lib import colors
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.lib.units import cm
                import io
                import re

                # Register DejaVu font for Cyrillic support
                try:
                    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/dejavu/DejaVuSans.ttf"))
                    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"))
                except Exception as e:
                    logger.warning(f"Failed to register DejaVu font: {e}")

                async def pdf_generator():
                    """Асинхронная генерация PDF отчета

                    Args:
                        result_data: Данные для генерации отчета (замыкание из внешней области видимости)

                    Yields:
                        bytes: PDF данные
                    """
                    pdf_bytes = await asyncio.to_thread(_generate_pdf_sync, result_data)
                    yield pdf_bytes

                def _generate_pdf_sync(result_data: dict) -> bytes:
                    """Синхронная генерация PDF отчета

                    Args:
                        result_data: Данные для генерации отчета

                    Returns:
                        bytes: PDF данные
                    """
                    try:
                        # Create PDF in memory
                        buffer = io.BytesIO()

                        # Create PDF document with landscape orientation
                        doc = SimpleDocTemplate(
                            buffer,
                            pagesize=landscape(A4),
                            topMargin=1 * cm,
                            bottomMargin=1 * cm,
                            leftMargin=1 * cm,
                            rightMargin=1 * cm,
                        )
                        styles = getSampleStyleSheet()

                        # Create styles with DejaVu font for Cyrillic support
                        title_style = ParagraphStyle(
                            "CustomTitle",
                            parent=styles["Heading1"],
                            fontName="DejaVuSans-Bold",
                            fontSize=14,
                            spaceAfter=20,
                            alignment=1,  # center
                        )

                        normal_style = ParagraphStyle(
                            "CustomNormal",
                            parent=styles["Normal"],
                            fontName="DejaVuSans",
                            fontSize=9,
                            spaceAfter=6,
                            leading=11,
                        )

                        cell_style = ParagraphStyle(
                            "CellStyle",
                            fontName="DejaVuSans",
                            fontSize=9,
                            leading=11,
                            alignment=0,  # left
                        )

                        header_cell_style = ParagraphStyle(
                            "HeaderCellStyle",
                            fontName="DejaVuSans-Bold",
                            fontSize=10,
                            leading=12,
                            alignment=1,  # center
                        )

                        # Function to clean text
                        def clean_text(text):
                            if not isinstance(text, str):
                                text = str(text)
                            # Remove emojis and special symbols
                            emoji_pattern = re.compile(
                                "["
                                "\U0001f600-\U0001f64f"  # emoticons
                                "\U0001f300-\U0001f5ff"  # symbols & pictographs
                                "\U0001f680-\U0001f6ff"  # transport & map symbols
                                "\U0001f1e0-\U0001f1ff"  # flags (iOS)
                                "\U00002700-\U000027bf"  # dingbats
                                "\U0001f926-\U0001f937"  # gestures
                                "\U00010000-\U0010ffff"  # other unicode
                                "\u2640-\u2642"  # gender symbols
                                "\u2600-\u2b55"  # misc symbols
                                "\u200d"  # zero width joiner
                                "\u23cf"  # eject symbol
                                "\u23e9"  # fast forward
                                "\u231a"  # watch
                                "\ufe0f"  # variation selector
                                "\u3030"  # wavy dash
                                "]+",
                                flags=re.UNICODE,
                            )
                            return emoji_pattern.sub("", text).strip()

                        # Function to wrap text for better display in cells
                        def wrap_text(text, field_type="general"):
                            """Clean and truncate text for table cells to prevent excessive height"""
                            if not isinstance(text, str):
                                text = str(text)

                            text = clean_text(text)

                            # Limit characters to prevent cells from becoming too tall
                            max_chars = 400
                            if len(text) > max_chars:
                                text = text[: max_chars - 3] + "..."

                            return text

                        # Assemble PDF content
                        story = []

                        # Title
                        cluster_name = clean_text(result_data.get("cluster_name", "Unknown"))
                        title = f"Kubernetes cluster inspection report for {cluster_name}"
                        story.append(Paragraph(title, title_style))
                        story.append(Spacer(1, 10))

                        # Cluster information
                        cluster_info = [
                            f"<b>Cluster name:</b> {clean_text(result_data.get('cluster_name', 'Unknown'))}",
                            f"<b>Inspection time:</b> {result_data.get('timestamp', 'Unknown')}",
                            f"<b>Report ID:</b> {clean_text(result_data.get('result_id', 'Unknown'))}",
                            f"<b>Inspection type:</b> {clean_text(result_data.get('inspection_type', 'Unknown'))}",
                        ]

                        for info in cluster_info:
                            story.append(Paragraph(info, normal_style))
                        story.append(Spacer(1, 15))

                        # Get all inspection items
                        logger.info(f"result_data keys: {list(result_data.keys())}")
                        logger.info(f"inspection_results present: {'inspection_results' in result_data}")

                        all_items = []
                        if "inspection_results" in result_data:
                            # New format
                            for inspector_type, inspector_result in result_data["inspection_results"].items():
                                items = inspector_result.get("items", [])
                                all_items.extend(items)
                        elif "items" in result_data:
                            # Old format
                            all_items = result_data["items"]
                        else:
                            logger.error("Neither inspection_results nor items key found in result_data")
                            raise KeyError("No items found in report data")

                        # Sort items by severity (critical/high first, then medium/warning, then low/info)
                        severity_order = {
                            "critical": 0,
                            "high": 1,
                            "error": 2,
                            "medium": 3,
                            "warning": 4,
                            "low": 5,
                            "info": 6,
                        }
                        all_items.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 7))

                        # Statistics
                        passed_count = sum(1 for item in all_items if item.get("status") in ["passed", "success"])
                        warning_count = sum(
                            1
                            for item in all_items
                            if item.get("severity") == "warning" and item.get("status") not in ["passed", "success"]
                        )
                        exception_count = len(all_items) - passed_count

                        stats_text = f"<b>Total checks:</b> {len(all_items)}, <b>Passed:</b> {passed_count}, <b>Warnings:</b> {warning_count}, <b>Errors:</b> {exception_count}"
                        story.append(Paragraph(stats_text, normal_style))
                        story.append(Spacer(1, 15))

                        # Results table (simplified for streaming)
                        if all_items:
                            # Create table data
                            table_data = []

                            # Table headers
                            header_row = [
                                "Check name",
                                "Status",
                                "Severity level",
                                "Description",
                                "Details",
                                "Solution",
                            ]
                            table_data.append(header_row)

                            # Add data (limit to first 50 items for performance)
                            severity_values = []
                            status_values = []
                            for item in all_items[:50]:
                                name = wrap_text(item.get("name", ""), field_type="general")
                                status = wrap_text(item.get("status", ""), field_type="general")
                                severity = wrap_text(item.get("severity", ""), field_type="general")
                                description = wrap_text(item.get("description", ""), field_type="description")
                                details = wrap_text(item.get("details", ""), field_type="details")
                                solution = wrap_text(item.get("solution", ""), field_type="solution")

                                row = [name, status, severity, description, details, solution]
                                table_data.append(row)
                                severity_values.append(severity)
                                status_values.append(status)

                            # Convert all cells to Paragraph objects for proper word wrapping
                            for row_idx, row in enumerate(table_data):
                                for col_idx, cell in enumerate(row):
                                    if row_idx == 0:
                                        table_data[row_idx][col_idx] = Paragraph(str(cell), header_cell_style)
                                    else:
                                        table_data[row_idx][col_idx] = Paragraph(str(cell), cell_style)

                            # Calculate available width for table
                            page_width, page_height = landscape(A4)
                            available_width = page_width - (doc.leftMargin + doc.rightMargin)

                            # Calculate optimal column widths based on content
                            def calculate_column_widths(table_data, available_width):
                                """Calculate column widths based on content and available width"""
                                num_columns = len(table_data[0]) if table_data else 0

                                # Calculate minimum and maximum widths for each column
                                min_widths = [30] * num_columns  # Minimum width for each column
                                max_widths = [150] * num_columns  # Maximum width for each column

                                # Special handling for different columns
                                if num_columns > 1:
                                    min_widths[1] = 30  # Status column (narrow)
                                    max_widths[1] = 50

                                    min_widths[2] = 40  # Severity column
                                    max_widths[2] = 60

                                    # Solution column (index 5) should have more space
                                    if num_columns > 5:
                                        min_widths[5] = 50  # Solution column
                                        max_widths[5] = 200  # More space for solutions

                                # Calculate content-based widths
                                content_widths = [min_widths[i] for i in range(num_columns)]

                                for row in table_data:
                                    for col_idx, cell_content in enumerate(row):
                                        # Calculate required width based on text length
                                        if isinstance(cell_content, str):
                                            # Approximate character width (adjust as needed)
                                            char_width = 5  # Average character width in points
                                            required_width = len(cell_content) * char_width

                                            # Update content width if needed
                                            if required_width > content_widths[col_idx]:
                                                content_widths[col_idx] = min(required_width, max_widths[col_idx])

                                # Distribute remaining width proportionally
                                total_content_width = sum(content_widths)
                                remaining_width = available_width - total_content_width

                                if remaining_width > 0:
                                    # Distribute remaining width proportionally
                                    total_weight = sum(max_widths)
                                    if total_weight > 0:
                                        for i in range(num_columns):
                                            weight = max_widths[i] / total_weight
                                            extra_width = remaining_width * weight
                                            content_widths[i] += extra_width
                                elif total_content_width > available_width:
                                    # Scale down if total width exceeds available width
                                    scale_factor = available_width / total_content_width
                                    content_widths = [w * scale_factor for w in content_widths]

                                return content_widths

                            # Calculate optimal column widths
                            column_widths = calculate_column_widths(table_data, available_width)

                            # Create table with calculated column widths
                            table = Table(table_data, repeatRows=1, colWidths=column_widths)

                            # Set table to stretch to full width
                            table.hAlign = "LEFT"

                            # Apply styles to table
                            table_style = TableStyle(
                                [
                                    # Table header
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                                    # Table borders
                                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                    # Content alignment
                                    ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                    # Word wrap for better text display
                                    ("WORDWRAP", (0, 0), (-1, -1), 1),
                                    # Special handling for solution column (column index 5) - more padding for better readability
                                    ("LEFTPADDING", (5, 0), (5, -1), 8),
                                    ("RIGHTPADDING", (5, 0), (5, -1), 8),
                                    ("TOPPADDING", (5, 0), (5, -1), 8),
                                    ("BOTTOMPADDING", (5, 0), (5, -1), 8),
                                    # Allow text to wrap in all columns
                                    ("WORDWRAP", (0, 0), (-1, -1), 1),
                                ]
                            )

                            # Add severity-based cell coloring
                            for row_idx, severity in enumerate(severity_values, start=1):
                                if severity == "info" or severity == "low":
                                    table_style.add(
                                        "BACKGROUND", (2, row_idx), (2, row_idx), colors.HexColor("#D5E8D4")
                                    )
                                elif severity == "warning" or severity == "medium":
                                    table_style.add(
                                        "BACKGROUND", (2, row_idx), (2, row_idx), colors.HexColor("#FFF2CC")
                                    )
                                elif severity == "error" or severity == "high" or severity == "critical":
                                    table_style.add(
                                        "BACKGROUND", (2, row_idx), (2, row_idx), colors.HexColor("#F8CECC")
                                    )

                            # Add status-based cell coloring
                            for row_idx, status in enumerate(status_values, start=1):
                                if status in ["passed", "success"]:
                                    table_style.add(
                                        "BACKGROUND", (1, row_idx), (1, row_idx), colors.HexColor("#D5E8D4")
                                    )
                                elif status in ["failed", "error"]:
                                    table_style.add(
                                        "BACKGROUND", (1, row_idx), (1, row_idx), colors.HexColor("#F8CECC")
                                    )
                                else:
                                    table_style.add(
                                        "BACKGROUND", (1, row_idx), (1, row_idx), colors.HexColor("#FFF2CC")
                                    )

                            table.setStyle(table_style)
                            story.append(table)

                        # Add final statistics
                        story.append(Spacer(1, 20))
                        summary_text = (
                            f"<b>Summary:</b> Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        story.append(Paragraph(summary_text, normal_style))

                        # Generate PDF
                        doc.build(story)

                        # Get PDF bytes
                        pdf_bytes = buffer.getvalue()
                        buffer.close()

                        return pdf_bytes

                    except Exception as e:
                        logger.error(f"Error generating PDF export: {e}")
                        raise

                streaming_response = StreamingExportResponse(
                    content_generator=pdf_generator, filename=filename, media_type="application/pdf"
                )
                return streaming_response.to_response()

            except ImportError:
                raise HTTPException(
                    status_code=500, detail="PDF export not available. Install reportlab: pip install reportlab"
                )
            except Exception as e:
                logger.error(f"Error in PDF export: {e}")
                raise HTTPException(status_code=500, detail=f"PDF export error: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/immediate")
async def create_immediate_report():
    """Create immediate inspection report"""
    try:
        # Get available clusters
        from services.cluster_service import ClusterService

        service = ClusterService()
        clusters_data = await service.get_clusters_list()
        if not clusters_data or "clusters" not in clusters_data:
            raise HTTPException(status_code=404, detail="No clusters found")

        clusters = clusters_data["clusters"]
        if not clusters:
            raise HTTPException(status_code=404, detail="No clusters found")

        # Use first available cluster for immediate inspection
        cluster = clusters[0]
        cluster_name = cluster.get("name", "unknown") if isinstance(cluster, dict) else str(cluster)

        # Get controller configuration from DI container
        config = await get_service("config")

        # Get cluster configuration to update nodes
        from infra.cluster.cluster_config import get_cluster

        cluster_config = await get_cluster(cluster_name)
        if cluster_config:
            nodes = await cluster_config.get_nodes()
            config["nodes"] = nodes
            logger.info(f"Updated config with {len(nodes)} nodes for cluster {cluster_name}")

        # Create inspection controller
        controller = InspectionController(config, use_gitops=False)

        # Run immediate inspection
        all_results = await controller.run_inspection(cluster_name)

        if not all_results:
            raise HTTPException(status_code=500, detail="Failed to create inspection report")

        # Save inspection results
        result_id = await controller.save_inspection_result(all_results, cluster_name, "immediate")

        # Calculate total items from tuple format results
        total_items = 0
        for result in all_results.values():
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "items"):
                    total_items += len(result_obj.items)
            elif not isinstance(result, tuple) and hasattr(result, "items"):
                total_items += len(result.items)

        return {
            "message": "Immediate inspection report created successfully",
            "result_id": result_id,
            "cluster_name": cluster_name,
            "timestamp": datetime.now().isoformat(),
            "total_items": total_items,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
