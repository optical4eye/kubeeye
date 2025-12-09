#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reports management routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import os
import json
from utils.inspection_result import list_results, load_result, export_report

router = APIRouter()


@router.get("/reports")
async def get_reports(limit: int = 100):
    """Get list of reports"""
    try:
        reports = list_results(limit=limit, order_by="timestamp DESC")
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report by ID"""
    try:
        report = load_result(report_id)
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
        # Find and delete report file
        results_dir = Path("data/results")
        for file_path in results_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("result_id") == report_id:
                    os.remove(file_path)
                    return {"message": f"Report {report_id} deleted"}
            except:
                continue
        raise HTTPException(status_code=404, detail="Report not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def delete_exported_file_after_delay(file_path: str):
    """Delete exported file after short delay to allow download completion"""
    import asyncio

    # Wait 1 second to ensure download is complete
    await asyncio.sleep(1)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted exported file: {file_path}")
    except Exception as e:
        print(f"Error deleting exported file {file_path}: {e}")


@router.get("/reports/{report_id}/export/{format}")
async def export_report_endpoint(
    report_id: str, format: str, background_tasks: BackgroundTasks
):
    """Export report"""
    try:
        success, file_path = export_report(report_id, format)
        if not success:
            raise HTTPException(status_code=500, detail=file_path)

        # Add background task to delete the file after download
        background_tasks.add_task(delete_exported_file_after_delay, file_path)

        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
