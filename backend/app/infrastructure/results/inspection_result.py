#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection result management module for saving and loading inspection results
"""

import json
import os
import re
import logging
import time
from functools import lru_cache

# openpyxl not used
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Attempt import for PDF generation
try:
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

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Data directory definition
DATA_DIR = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
RESULTS_DIR = DATA_DIR / "results"

# Ensure directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

# Cache for result metadata to avoid repeated file reads
_result_metadata_cache = {}
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes cache TTL


class InspectionResult:
    """Inspection result class"""

    def __init__(self, cluster_name: str, inspection_type: str):
        """
        Initialize inspection results

        Args:
            cluster_name: cluster name
            inspection_type: inspection type
        """
        self.cluster_name = cluster_name
        self.inspection_type = inspection_type
        self.timestamp = datetime.now()
        self.result_id = f"{cluster_name}_{inspection_type}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.items = []

    def add_item(self, item: Dict) -> None:
        """
        Add inspection item

        Args:
            item: inspection item dictionary, must contain:
                - name: inspection item name
                - status: 'passed' or 'exception' (simplified status system)
                - description: description
                - severity: severity level ('critical', 'warning', 'info') - only for exception item details
                - details: detailed content
                - solution: solution (optional)
        """
        if "solution" not in item:
            item["solution"] = ""

        # Status normalization: uniformly convert failed, warning, error to exception, success to passed
        if item.get("status") in ["failed", "warning", "error"]:
            item["status"] = "exception"
        elif item.get("status") in ["success"]:
            item["status"] = "passed"

        self.items.append(item)

    def get_items(self) -> List[Dict]:
        """Get all inspection items"""
        return self.items

    def get_summary(self) -> Dict:
        """Get inspection summary"""
        passed = 0
        exception_critical = 0
        exception_warning = 0
        exception_info = 0

        for item in self.items:
            # Safely get status and severity, handle different item types
            if isinstance(item, dict):
                status = item.get("status", "unknown")
                severity = item.get("severity", "unknown")
            elif hasattr(item, "status"):
                status = getattr(item, "status", "unknown")
                severity = getattr(item, "severity", "unknown")
            else:
                status = "unknown"
                severity = "unknown"

            # Simplified status system: only passed and exception
            if status in ["passed", "success"]:
                passed += 1
            else:
                # All non-passing statuses are considered exceptions, detailed by severity
                if severity == "critical":
                    exception_critical += 1
                elif severity == "warning":
                    exception_warning += 1
                else:
                    exception_info += 1

        total_exceptions = exception_critical + exception_warning + exception_info

        return {
            "cluster_name": self.cluster_name,
            "inspection_type": self.inspection_type,
            "timestamp": self.timestamp,
            "result_id": self.result_id,
            "total": len(self.items),
            "passed": passed,
            "total_exceptions": total_exceptions,
            "exception_critical": exception_critical,
            "exception_warning": exception_warning,
            "exception_info": exception_info,
            # Keep old fields for compatibility
            "critical": exception_critical,
            "warning": exception_warning,
            "info": exception_info,
        }

    def save(self) -> str:
        """
        Save inspection results

        Returns:
            path to results file
        """
        # Create cluster results directory
        cluster_dir = RESULTS_DIR / self.cluster_name
        os.makedirs(cluster_dir, exist_ok=True)

        result_data = {
            "cluster_name": self.cluster_name,
            "inspection_type": self.inspection_type,
            "timestamp": self.timestamp.isoformat(),
            "result_id": self.result_id,
            "items": self.items,
        }

        result_file = cluster_dir / f"{self.result_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return str(result_file)


def load_result(result_id: str) -> Optional[Dict]:
    """
    Load inspection results

    Args:
        result_id: inspection results ID

    Returns:
        inspection results dictionary, return None if not exists
    """
    # Search all json files in results directory, find matching result_id
    for file_path in RESULTS_DIR.rglob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Check if result_id matches
            if result_data.get("result_id") == result_id:
                return result_data
        except Exception as e:
            # Log file that failed to read, but continue search
            logger.warning(f"Failed to read {file_path}: {e}")
            continue

    # If not found by result_id, try by filename pattern
    # Handle different filename formats
    possible_patterns = [
        f"inspection_result_{result_id}.json",
        f"{result_id}.json",
        # Try to extract cluster name and timestamp from result_id
    ]

    # If result_id contains timestamp, try to build standard filename
    if "_" in result_id:
        parts = result_id.split("_")
        if len(parts) >= 3:
            # Assume format type_date_time, try to find corresponding file
            for file_path in RESULTS_DIR.glob(f"inspection_result_*_{parts[-2]}_{parts[-1]}.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                    # If file content matches, return result
                    if result_data.get("result_id") == result_id:
                        return result_data
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
                    continue

    # Try direct filename match
    for pattern in possible_patterns:
        result_file = RESULTS_DIR / pattern
        if result_file.exists():
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read {result_file}: {e}")
                continue

    return None


def export_report(result_id: str, format_type: str = "json") -> Tuple[bool, str]:
    """
    Export inspection report in different formats

    Args:
        result_id: inspection results ID
        format_type: export format, supports "json", "pdf"

    Returns:
        tuple (success, file path), return exported file path on success
    """
    # Load inspection results
    result_data = load_result(result_id)
    if not result_data:
        return False, "Specified inspection results not found"

    # Get cluster name from result_data
    cluster_name = result_data.get("cluster_name", "unknown")
    export_dir = (
        Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))
        / "exports"
        / cluster_name
        / "inspect_reports"
    )

    os.makedirs(export_dir, exist_ok=True)

    # Export by format type
    if format_type == "json":
        # Find original results file
        source_path = None
        for file_path in RESULTS_DIR.rglob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("result_id") == result_id:
                    source_path = file_path
                    break
            except Exception:
                continue

        if source_path and source_path.exists():
            export_path = export_dir / f"{result_id}.json"
            import shutil

            shutil.copy(source_path, export_path)
            return True, str(export_path)
        else:
            return False, "Original file not found"

    elif format_type == "pdf":
        if not PDF_SUPPORT:
            return (
                False,
                "PDF export not available. Install reportlab: pip install reportlab",
            )

        export_path = export_dir / f"{result_id}.pdf"

        try:
            # Enhanced font search for Cyrillic
            font_name = "DejaVuSans"  # Use DejaVuSans by default

            # Check available system fonts (in priority order)
            possible_fonts = [
                # DejaVu Sans (often available in Linux)
                ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "DejaVuSans"),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
                ("/usr/share/fonts/TTF/DejaVuSans.ttf", "DejaVuSans"),
                # Liberation Sans (Linux alternative)
                (
                    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
                    "LiberationSans",
                ),
                # Arial (Windows/Linux)
                ("/usr/share/fonts/arial.ttf", "Arial"),
                ("/usr/share/fonts/Arial.ttf", "Arial"),
                ("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf", "Arial"),
                ("C:/Windows/Fonts/arial.ttf", "Arial"),
                ("C:/Windows/Fonts/arial.ttf", "Arial"),
                # Times New Roman
                ("/usr/share/fonts/TTF/Times.ttf", "TimesNewRoman"),
                ("C:/Windows/Fonts/times.ttf", "TimesNewRoman"),
                # FreeSans (may be in systems with ghostscript)
                ("/usr/share/fonts/type1/gsfonts/FreeSans.pfb", "FreeSans"),
            ]

            font_found = False
            for font_path, font_alias in possible_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_alias, font_path))
                        font_name = font_alias
                        font_found = True
                        logger.info(f"Using font: {font_alias} from {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load font {font_path}: {e}")
                        continue

            # If no suitable font found, use Times-Roman (better Unicode support)
            if not font_found:
                font_name = "Times-Roman"
                logger.info(f"Using built-in font: {font_name}")

            # Create PDF document with landscape orientation
            doc = SimpleDocTemplate(
                str(export_path),
                pagesize=landscape(A4),
                topMargin=1 * cm,
                bottomMargin=1 * cm,
                leftMargin=1 * cm,
                rightMargin=1 * cm,
            )
            styles = getSampleStyleSheet()

            # Create styles for Cyrillic
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=14,
                spaceAfter=20,
                alignment=1,  # center
                fontName=font_name,
            )

            header_style = ParagraphStyle(
                "CustomHeader",
                parent=styles["Heading2"],
                fontSize=11,
                spaceAfter=10,
                alignment=0,  # left
                fontName=font_name,
                textColor=colors.white,
            )

            normal_style = ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontSize=9,
                spaceAfter=6,
                fontName=font_name,
                leading=11,  # line spacing
            )

            # Style for table cells with text wrapping
            cell_style = ParagraphStyle(
                "TableCell",
                parent=styles["Normal"],
                fontSize=8,
                fontName=font_name,
                leading=10,
                wordWrap="CJK",  # Enable text wrapping
            )

            # Function to clean text from emojis
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

            # Function to create Paragraph with text wrapping
            def create_cell_paragraph(text, max_length=400):
                """Creates Paragraph with truncated text if necessary"""
                clean = clean_text(text)
                if len(clean) > max_length:
                    clean = clean[:max_length] + "..."
                return Paragraph(clean, cell_style)

            # Assemble PDF content
            story = []

            # Title
            title = clean_text("Kubernetes cluster inspection report")
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
            all_items = []
            if "inspection_results" in result_data:
                for inspector_type, inspector_result in result_data["inspection_results"].items():
                    items = inspector_result.get("items", [])
                    all_items.extend(items)
            else:
                all_items = result_data.get("items", [])

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

            # Results table
            if all_items:
                # Define maximum rows per page
                max_rows_per_page = 30  # Limit for readability

                # Split data into chunks for pagination
                for page_num, start_idx in enumerate(range(0, len(all_items), max_rows_per_page)):
                    end_idx = min(start_idx + max_rows_per_page, len(all_items))
                    page_items = all_items[start_idx:end_idx]

                    if page_num > 0:
                        story.append(Paragraph("<i>Table continuation...</i>", normal_style))
                        story.append(Spacer(1, 10))

                    # Create table data
                    table_data = []

                    # Table headers
                    header_row = [
                        create_cell_paragraph("Check name"),
                        create_cell_paragraph("Status"),
                        create_cell_paragraph("Severity level"),
                        create_cell_paragraph("Description"),
                        create_cell_paragraph("Details"),
                        create_cell_paragraph("Solution"),
                    ]
                    table_data.append(header_row)

                    # Add data
                    for item in page_items:
                        name = create_cell_paragraph(item.get("name", ""))
                        status = create_cell_paragraph(item.get("status", ""))

                        # Determine color for status
                        status_color = colors.green
                        if item.get("status") != "passed":
                            status_color = colors.red

                        severity = create_cell_paragraph(item.get("severity", ""))
                        description = create_cell_paragraph(item.get("description", ""))
                        details = create_cell_paragraph(item.get("details", ""))
                        solution = create_cell_paragraph(item.get("solution", ""))

                        row = [name, status, severity, description, details, solution]
                        table_data.append(row)

                    # Automatic column width determination
                    # Use proportional distribution based on content
                    page_width = landscape(A4)[0] - 2 * cm  # Page width minus margins

                    # Define approximate column proportions based on content
                    col_proportions = [
                        3.0,
                        1.0,
                        1.5,
                        3.0,
                        3.0,
                        3.0,
                    ]  # Approximate proportions
                    total_proportion = sum(col_proportions)

                    # Calculate width of each column
                    col_widths = [(page_width / total_proportion) * prop for prop in col_proportions]

                    # Create table
                    table = Table(table_data, colWidths=col_widths, repeatRows=1)

                    # Apply styles to table
                    table_style = TableStyle(
                        [
                            # Table header
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), font_name),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                            ("TOPPADDING", (0, 0), (-1, 0), 8),
                            # Alternating row colors for readability
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#F2F2F2")],
                            ),
                            # Table borders
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            # Content alignment
                            (
                                "ALIGN",
                                (0, 1),
                                (1, -1),
                                "CENTER",
                            ),  # Status and severity centered
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            # Automatic text wrapping
                            ("WORDWRAP", (0, 0), (-1, -1), True),
                        ]
                    )

                    # Dynamic status cell coloring
                    for i in range(1, len(table_data)):
                        status_text = all_items[start_idx + i - 1].get("status", "")
                        if status_text == "passed":
                            table_style.add("BACKGROUND", (1, i), (1, i), colors.lightgreen)
                        elif status_text in ["failed", "error", "exception"]:
                            table_style.add("BACKGROUND", (1, i), (1, i), colors.lightcoral)
                        elif status_text == "warning":
                            table_style.add("BACKGROUND", (1, i), (1, i), colors.lightyellow)

                    table.setStyle(table_style)

                    # Add table to story
                    story.append(table)

                    # Add page break if this is not the last part
                    if end_idx < len(all_items):
                        story.append(Spacer(1, 10))
                        story.append(Paragraph(f"Page {page_num + 1}", normal_style))
                        story.append(Spacer(1, 20))

            # Add final statistics
            story.append(Spacer(1, 20))
            summary_text = f"<b>Summary:</b> Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            story.append(Paragraph(summary_text, normal_style))

            # Generate PDF
            doc.build(story)
            return True, str(export_path)

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            return False, f"PDF export error: {str(e)}\nDetails: {error_details}"

    else:
        return False, f"Unsupported export format: {format_type}"


# Caching disabled


def _calculate_result_summary(result_data: Dict) -> Dict:
    """Calculation of result summary for one file"""
    # Always recalculate for accuracy, ignoring old summary fields
    # Handle new data structure
    if "inspection_results" in result_data:
        # New format: but no summary, need to calculate
        critical = 0
        warning = 0
        info = 0
        passed = 0
        total = 0

        for inspector_type, inspector_result in result_data.get("inspection_results", {}).items():
            items = inspector_result.get("items", [])
            total += len(items)

            for item in items:
                # Safely get status and severity, handle different item types
                if isinstance(item, dict):
                    status = item.get("status", "unknown")
                    severity = item.get("severity", "unknown")
                elif hasattr(item, "status"):
                    status = getattr(item, "status", "unknown")
                    severity = getattr(item, "severity", "unknown")
                else:
                    status = "unknown"
                    severity = "unknown"

                if status in ["passed", "success"]:
                    passed += 1
                elif status == "exception":
                    # Count by severity as in old format
                    if severity == "critical":
                        critical += 1
                    elif severity == "warning":
                        warning += 1
                    else:
                        info += 1
                else:
                    # Unknown status - count as info
                    info += 1
    else:
        # Old format: direct items field
        critical = 0
        warning = 0
        info = 0
        passed = 0

        for item in result_data.get("items", []):
            # Safely get status and severity, handle different item types
            if isinstance(item, dict):
                status = item.get("status", "unknown")
                severity = item.get("severity", "unknown")
            elif hasattr(item, "status"):
                status = getattr(item, "status", "unknown")
                severity = getattr(item, "severity", "unknown")
            else:
                status = "unknown"
                severity = "unknown"

            if status in ["passed", "success"]:
                passed += 1
            elif status == "exception":
                if severity == "critical":
                    critical += 1
                elif severity == "warning":
                    warning += 1
                else:
                    info += 1
            else:
                # Unknown status - count as info
                info += 1

        total = len(result_data.get("items", []))

    # Determine overall status
    if critical > 0:
        status = "failed"
    elif warning > 0:
        status = "warning"
    else:
        status = "passed"

    return {
        "cluster_name": result_data.get("cluster_name", ""),
        "inspection_type": result_data.get("inspection_type", "unknown"),
        "timestamp": result_data.get("timestamp", ""),
        "result_id": result_data.get("result_id", ""),
        "total": total,
        "passed": passed,
        "critical": critical,
        "warning": warning,
        "info": info,
        "status": status,
    }


def _refresh_metadata_cache() -> None:
    """Refresh the metadata cache by scanning files and updating only necessary information"""
    global _result_metadata_cache, _cache_timestamp

    current_time = time.time()

    # Check if cache is still valid
    if current_time - _cache_timestamp < CACHE_TTL and _result_metadata_cache:
        return

    # Build new cache
    new_cache = {}

    for file_path in RESULTS_DIR.rglob("*.json"):
        try:
            # Get file modification time
            file_mtime = file_path.stat().st_mtime

            # Check if we need to read this file (either not in cache or file changed)
            cache_key = str(file_path)
            if cache_key in _result_metadata_cache and _result_metadata_cache[cache_key].get("mtime") == file_mtime:
                # Use cached metadata
                new_cache[cache_key] = _result_metadata_cache[cache_key]
                continue

            # Read only essential metadata from file
            with open(file_path, "r", encoding="utf-8") as f:
                # Use json.load with object_hook to extract only needed fields
                data = json.load(f)

                # Extract only essential fields for caching
                metadata = {
                    "result_id": data.get("result_id"),
                    "cluster_name": data.get("cluster_name"),
                    "timestamp": data.get("timestamp"),
                    "inspection_type": data.get("inspection_type"),
                    "mtime": file_mtime,
                    "file_path": str(file_path),
                }

                # Calculate summary statistics without loading full items
                if "critical" in data and "warning" in data and "passed" in data:
                    # Use pre-calculated summary if available
                    metadata.update(
                        {
                            "critical": data.get("critical", 0),
                            "warning": data.get("warning", 0),
                            "passed": data.get("passed", 0),
                            "total": data.get("total", 0),
                        }
                    )
                else:
                    # Calculate from items if needed (but limit the number of items processed)
                    items = data.get("items", [])
                    if len(items) > 100:  # Limit processing for large files
                        # For large files, only count first 100 items to estimate
                        sample_items = items[:100]
                        critical = sum(
                            1
                            for item in sample_items
                            if item.get("status") == "exception" and item.get("severity") == "critical"
                        )
                        warning = sum(
                            1
                            for item in sample_items
                            if item.get("status") == "exception" and item.get("severity") == "warning"
                        )
                        passed = sum(1 for item in sample_items if item.get("status") in ["passed", "success"])

                        # Estimate totals based on sample
                        factor = len(items) / 100
                        metadata.update(
                            {
                                "critical": int(critical * factor),
                                "warning": int(warning * factor),
                                "passed": int(passed * factor),
                                "total": len(items),
                            }
                        )
                    else:
                        # For smaller files, process all items
                        critical = sum(
                            1
                            for item in items
                            if item.get("status") == "exception" and item.get("severity") == "critical"
                        )
                        warning = sum(
                            1
                            for item in items
                            if item.get("status") == "exception" and item.get("severity") == "warning"
                        )
                        passed = sum(1 for item in items if item.get("status") in ["passed", "success"])

                        metadata.update(
                            {"critical": critical, "warning": warning, "passed": passed, "total": len(items)}
                        )

                new_cache[cache_key] = metadata

        except (json.JSONDecodeError, IOError, UnicodeDecodeError):
            # Skip corrupted files
            continue
        except Exception:
            # Skip files with other errors
            continue

    # Update cache
    _result_metadata_cache = new_cache
    _cache_timestamp = current_time


def clear_metadata_cache() -> None:
    """Clear the metadata cache force refresh"""
    global _result_metadata_cache, _cache_timestamp
    _result_metadata_cache = {}
    _cache_timestamp = 0


def list_results_cached(cluster_name: Optional[str] = None) -> List[Dict]:
    """
    Loading results with efficient caching and lazy loading

    Args:
        cluster_name: optional filtering by cluster name

    Returns:
        list of inspection result summaries
    """
    _refresh_metadata_cache()

    results = []

    # Process cached metadata
    for metadata in _result_metadata_cache.values():
        # Filtering by cluster name
        if cluster_name and metadata.get("cluster_name") != cluster_name:
            continue

        # Determine status from cached data
        critical = metadata.get("critical", 0)
        warning = metadata.get("warning", 0)
        if critical > 0:
            status = "failed"
        elif warning > 0:
            status = "warning"
        else:
            status = "passed"

        # Create summary from cached metadata
        total = metadata.get("total", 0)
        passed = metadata.get("passed", 0)
        critical = metadata.get("critical", 0)
        warning = metadata.get("warning", 0)
        info = metadata.get("info", 0)

        # If info not in metadata, calculate it
        if info == 0 and total > 0:
            info = total - passed - critical - warning

        summary = {
            "cluster_name": metadata.get("cluster_name", ""),
            "inspection_type": metadata.get("inspection_type", "unknown"),
            "timestamp": metadata.get("timestamp", ""),
            "result_id": metadata.get("result_id", ""),
            "total": total,
            "passed": passed,
            "critical": critical,
            "warning": warning,
            "info": info,
            "status": status,
        }

        results.append(summary)

    # Sorting by time (newest first)
    results.sort(key=lambda x: x["timestamp"], reverse=True)

    return results


def list_results(
    cluster_name: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: Optional[str] = None,
) -> List[Dict]:
    """
    List inspection results with pagination and sorting support

    Args:
        cluster_name: optional filtering by cluster name
        limit: maximum number of results (None for all)
        offset: offset for pagination
        order_by: field for sorting ('timestamp DESC' for sorting by time)

    Returns:
        list of inspection result summaries
    """
    results = list_results_cached(cluster_name)

    # Apply sorting
    if order_by == "timestamp DESC":
        results.sort(key=lambda x: x["timestamp"], reverse=True)

    # Apply pagination
    if limit is not None:
        start_idx = offset
        end_idx = offset + limit
        results = results[start_idx:end_idx]

    return results


def load_result_minimal(file_path: Path) -> Optional[Dict]:
    """Loading only necessary fields of result for lists"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Calculate status
        critical = data.get("critical", 0)
        warning = data.get("warning", 0)
        if critical > 0:
            status = "failed"
        elif warning > 0:
            status = "warning"
        else:
            status = "passed"

        # Return only necessary fields for list
        return {
            "result_id": data.get("result_id"),
            "cluster_name": data.get("cluster_name"),
            "timestamp": data.get("timestamp"),
            "inspection_type": data.get("inspection_type"),
            "critical": critical,
            "warning": warning,
            "passed": data.get("passed", 0),
            "status": status,
        }
    except Exception:
        return None


def get_latest_result_by_cluster(cluster_name: str) -> Optional[Dict[str, Any]]:
    """
    Get latest inspection results for specified cluster

    Args:
        cluster_name (str): cluster name

    Returns:
        Optional[Dict[str, Any]]: latest inspection results, return None if none
    """
    results = list_results(cluster_name=cluster_name, limit=1)

    return results[0] if results else None
