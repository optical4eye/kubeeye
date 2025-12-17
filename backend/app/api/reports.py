#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reports management routes
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os
import json
from datetime import datetime
from infrastructure.results.inspection_result import (
    list_results,
    load_result,
    export_report,
    InspectionResult,
)
from services.inspectors.controller import InspectionController
from infrastructure.dependency_injection.container import get_service

router = APIRouter()


@router.get("/reports")
async def get_reports(limit: int = 100):
    """Get list of reports"""
    try:
        # Validate limit parameter
        from .validation_middleware import validate_limit_param

        validated_limit = validate_limit_param(limit)

        # Clear cache to ensure fresh data
        from infrastructure.results.inspection_result import clear_metadata_cache
        clear_metadata_cache()

        reports = list_results(limit=validated_limit, order_by="timestamp DESC")
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report by ID"""
    try:
        # Validate report_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for report_id

        validated_report_id = validate_task_id(report_id)

        report = load_result(validated_report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete report"""
    try:
        # Validate report_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for report_id

        validated_report_id = validate_task_id(report_id)

        # Find and delete report file
        results_dir = Path("data/results")
        for file_path in results_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("result_id") == validated_report_id:
                    os.remove(file_path)
                    return {"message": f"Report {validated_report_id} deleted"}
            except Exception:
                continue
        raise HTTPException(status_code=404, detail="Report not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}/export/{format}")
async def export_report_endpoint(report_id: str, format: str):
    """Export report"""
    try:
        # Validate report_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for report_id

        validated_report_id = validate_task_id(report_id)

        # Validate format parameter
        valid_formats = ["json", "csv", "excel", "pdf"]
        if format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Format must be one of: {', '.join(valid_formats)}")

        success, file_path = export_report(validated_report_id, format)
        if not success:
            raise HTTPException(status_code=500, detail=file_path)

        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/immediate")
async def create_immediate_report():
    """Create immediate inspection report"""
    try:
        # Get available clusters
        from .clusters import get_clusters

        clusters_data = await get_clusters()
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

        # Create inspection controller
        controller = InspectionController(config, use_gitops=False)

        # Run immediate inspection
        all_results = await controller.run_inspection(cluster_name)

        if not all_results:
            raise HTTPException(status_code=500, detail="Failed to create inspection report")

        # Save inspection results
        result_path = await controller.save_inspection_result(all_results, cluster_name, "immediate")

        # Extract result ID from filename
        result_id = Path(result_path).stem.replace("inspection_result_", "")

        # Calculate total items from tuple format results
        total_items = 0
        for result in all_results.values():
            if isinstance(result, tuple) and len(result) >= 2:
                success, result_obj = result
                if hasattr(result_obj, "items"):
                    total_items += len(result_obj.items)
            elif hasattr(result, "items"):
                total_items += len(result.items)

        return {
            "message": "Immediate inspection report created successfully",
            "result_id": result_id,
            "cluster_name": cluster_name,
            "timestamp": datetime.now().isoformat(),
            "total_items": total_items
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
