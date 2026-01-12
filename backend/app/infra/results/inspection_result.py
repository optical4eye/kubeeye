#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection result management module for saving and loading inspection results
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from core.logging import get_logger
from core.common.cache_utils import CacheManager
from db.database_context import with_db_session

logger = get_logger(__name__)

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

# Results are now stored in PostgreSQL - no local file storage needed

# Cache for result metadata using CacheManager
_cache_manager = CacheManager()
_result_metadata_cache = _cache_manager.get_or_create_cache("result_metadata", maxsize=128, ttl=300)  # 5 minutes TTL


class InspectionResult:
    """Inspection result class"""

    def __init__(self, cluster_name: str, inspection_type: str):
        """
        Initialize inspection results

        Args:
            cluster_name: cluster name
            inspection_type: inspection type
        """
        self.cluster_name: str = cluster_name
        self.inspection_type: str = inspection_type
        self.timestamp: datetime = datetime.now()
        # Use different prefix based on inspection type
        prefix = "popeye" if inspection_type == "popeye" else "cluster"
        self.result_id: str = f"{prefix}_{cluster_name}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.items: List[Dict[str, Any]] = []

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
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "result_id": self.result_id,
            "total": len(self.items),
            "passed": passed,
            "total_exceptions": total_exceptions,
            "exception_critical": exception_critical,
            "exception_warning": exception_warning,
            "exception_info": exception_info,
        }

    async def save(self) -> Optional[str]:
        """
        Save inspection results to database

        Returns:
            result_id of saved inspection result
        """
        from db.database import get_db
        from db.repositories.inspection_result_repository import InspectionResultRepository

        # Calculate summary
        summary = self.get_summary()

        result_data = {
            "result_id": self.result_id,
            "cluster_name": self.cluster_name,
            "inspection_type": self.inspection_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,  # Convert datetime to ISO string
            "items": self.items,
            "execution_info": {
                "triggered_by": "user",
                "inspectors_used": [self.inspection_type],
                "execution_duration": None,
            },
            "summary": {
                "total_items": summary["total"],
                "passed": summary["passed"],
                "failed": summary["exception_critical"],
                "warning": summary["exception_warning"],
                "error": summary["exception_info"],
            },
            "critical": summary["exception_critical"],
            "warning": summary["exception_warning"],
            "passed": summary["passed"],
        }

        async with with_db_session() as db:
            repo = InspectionResultRepository(db)
            result_id = await repo.save_result(result_data)
            return result_id


async def load_result(result_id: str) -> Optional[Dict]:
    """
    Load inspection results from database

    Args:
        result_id: inspection results ID

    Returns:
        inspection results dictionary, return None if not exists
    """
    from db.database import get_db
    from db.repositories.inspection_result_repository import InspectionResultRepository

    async with with_db_session() as db:
        repo = InspectionResultRepository(db)
        result = await repo.get_by_result_id(result_id)
        if result:
            result_data = result.result_data
        else:
            result_data = None
        return result_data


def _calculate_result_summary(result_data: Dict) -> Dict:
    """Calculation of result summary for one file"""
    # New format: inspection_results with nested items
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
                # Count by severity
                if severity == "critical":
                    critical += 1
                elif severity == "warning":
                    warning += 1
                else:
                    info += 1
            else:
                # Unknown status - count as info
                info += 1

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


def clear_metadata_cache() -> None:
    """Clear the metadata cache force refresh"""
    global _result_metadata_cache, _cache_timestamp
    _result_metadata_cache = {}
    _cache_timestamp = 0


async def list_results(
    cluster_name: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by: Optional[str] = None,
    exclude_inspection_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    List inspection results with pagination and sorting support

    Args:
        cluster_name: Optional filtering by cluster name
        limit: Maximum number of results to return (None for all, default 100)
        offset: Offset for pagination (default 0)
        order_by: Field for sorting ('timestamp DESC' for sorting by time)
        exclude_inspection_types: List of inspection types to exclude

    Returns:
        Dict containing:
            - results: List of inspection result summaries
            - total: Total count of results matching filters
            - limit: Limit used in query
            - offset: Offset used in query
    """
    from db.database import get_db
    from db.repositories.inspection_result_repository import InspectionResultRepository

    async with with_db_session() as db:
        repo = InspectionResultRepository(db)
        result = await repo.list_results(
            cluster_name=cluster_name,
            limit=limit,
            offset=offset,
            order_by=order_by,
            exclude_inspection_types=exclude_inspection_types,
        )
        return result


async def get_latest_result_by_cluster(
    cluster_name: str, exclude_inspection_types: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Get latest inspection results for specified cluster

    Args:
        cluster_name (str): cluster name
        exclude_inspection_types: list of inspection types to exclude

    Returns:
        Optional[Dict[str, Any]]: latest inspection results, return None if none
    """
    result_data = await list_results(
        cluster_name=cluster_name, limit=1, exclude_inspection_types=exclude_inspection_types
    )

    results = result_data.get("results", [])
    return results[0] if results else None
