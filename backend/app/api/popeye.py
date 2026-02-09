#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Popeye API routes - handles Popeye cluster scanning
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from infra.tasks.task_queue import submit_popeye_task, get_task_queue
from infra.cluster.cluster_config import get_cluster
from infra.cluster.k8s_client import K8sClient
from core.logging import get_logger
from core.common.unified_validation import validate_task_id, validate_cluster_name
from api.dependencies import get_current_user, require_operator
from db.models.user import User

from core.logging import get_logger

logger = get_logger("popeye_api")

router = APIRouter()


class PopeyeScanRequest(BaseModel):
    """Request model for Popeye scan"""

    cluster_name: str
    output_format: str = "html"  # Popeye only supports HTML format
    all_namespaces: Optional[bool] = True
    namespace: Optional[str] = None


@router.post("/popeye/scan")
async def start_popeye_scan(
    request: PopeyeScanRequest,
    current_user: User = Depends(require_operator)
):
    """Start Popeye scan for specified cluster"""
    try:
        logger.info(f"Starting Popeye scan for cluster: {request.cluster_name}")

        # Validate output format - Popeye only supports HTML
        valid_formats = ["html"]
        if request.output_format not in valid_formats:
            raise HTTPException(status_code=400, detail="Invalid output format. Popeye only supports HTML format.")

        # Submit task to queue
        task_id = await submit_popeye_task(
            cluster_name=request.cluster_name,
            output_format=request.output_format,
            all_namespaces=request.all_namespaces,
            namespace=request.namespace,
        )

        logger.info(f"Popeye scan task submitted: {task_id}")

        return {
            "task_id": task_id,
            "message": "Popeye scan task submitted successfully",
            "status": "pending",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Popeye scan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


@router.get("/popeye/task/{task_id}")
async def get_popeye_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of Popeye scan task"""
    try:
        # Validate task_id using centralized validation
        validated_task_id = validate_task_id(task_id)

        logger.info(f"Getting status for Popeye task: {validated_task_id}")

        task_queue = await get_task_queue()
        task_status = await task_queue.get_task_status(validated_task_id)

        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")

        return task_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Popeye task status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete("/popeye/task/{task_id}")
async def cancel_popeye_task(
    task_id: str,
    current_user: User = Depends(require_operator)
):
    """Cancel Popeye scan task"""
    try:
        # Validate task_id using centralized validation
        validated_task_id = validate_task_id(task_id)

        logger.info(f"Cancelling Popeye task: {validated_task_id}")

        task_queue = await get_task_queue()
        cancelled = await task_queue.cancel_task(validated_task_id)

        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail="Task cannot be cancelled (may be running or completed)",
            )

        logger.info(f"Popeye task cancelled successfully: {validated_task_id}")
        return {"message": "Popeye task cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel Popeye task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.get("/popeye/namespaces/{cluster_name}")
async def get_popeye_namespaces(cluster_name: str):
    """Get available namespaces for Popeye scan in specified cluster"""
    try:
        logger.info(f"Getting namespaces for Popeye scan in cluster: {cluster_name}")

        # Validate cluster name
        validated_cluster_name = validate_cluster_name(cluster_name)

        cluster_config = await get_cluster(validated_cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail=f"Cluster '{validated_cluster_name}' not found")

        kubeconfig = await cluster_config.get_kubeconfig(parse_secrets=True)
        if not kubeconfig:
            raise HTTPException(
                status_code=400, detail=f"Kubeconfig not configured for cluster '{validated_cluster_name}'"
            )

        k8s_client = K8sClient(kubeconfig)
        namespaces_result = await k8s_client.get_namespaces()

        if namespaces_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=f"Failed to get namespaces: {namespaces_result.get('error')}")

        # Return only namespace names for UI selection
        namespaces = [ns["name"] for ns in namespaces_result.get("namespaces", [])]

        logger.info(f"Successfully retrieved {len(namespaces)} namespaces for cluster {validated_cluster_name}")
        return {"cluster_name": validated_cluster_name, "namespaces": namespaces}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get namespaces for Popeye: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get namespaces: {str(e)}")
