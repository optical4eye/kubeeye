#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network connectivity check routes
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import logging
import os

from infrastructure.cluster.cluster_config import get_cluster
from infrastructure.network.network_check import (
    check_connectivity_from_nodes,
    validate_port,
    NetworkConnectivityResult,
    load_network_check_result,
    list_network_check_results,
    export_network_report,
)
from infrastructure.logging.enhanced_logging import log_api_request

logger = logging.getLogger(__name__)

router = APIRouter()


class NetworkCheckRequest(BaseModel):
    """Model for network connectivity check request"""

    cluster_name: str = Field(..., description="Name of the cluster")
    selected_nodes: List[str] = Field(..., description="List of selected node IPs to check from")
    target_ip: str = Field(..., description="Target IP address to connect to")
    target_port: int = Field(..., description="Target port to connect to")
    timeout: Optional[int] = Field(5, description="Connection timeout in seconds", ge=1, le=30)

    @field_validator("target_ip")
    @classmethod
    def validate_target_ip(cls, v):
        import socket

        try:
            socket.gethostbyname(v)
            return v
        except socket.gaierror:
            raise ValueError("Invalid IP address or hostname")
        return v

    @field_validator("target_port")
    @classmethod
    def validate_target_port(cls, v):
        if not validate_port(v):
            raise ValueError("Port must be between 1 and 65535")
        return v


class NetworkCheckResult(BaseModel):
    """Model for network check result"""

    status: str = Field(..., description="Check status: success or failed")
    response_time: float = Field(..., description="Response time in seconds")
    node_ip: str = Field(..., description="Node IP that performed the check")
    target_ip: str = Field(..., description="Target IP address")
    target_port: int = Field(..., description="Target port")
    error: Optional[str] = Field(None, description="Error message if failed")


class NetworkCheckResponse(BaseModel):
    """Model for network check response"""

    result_id: str = Field(..., description="Result ID for saved check")
    results: List[NetworkCheckResult] = Field(..., description="List of check results")


@router.post("/network-check", response_model=NetworkCheckResponse)
@log_api_request
async def check_network_connectivity(request: NetworkCheckRequest):
    """
    Check network connectivity from selected cluster nodes to a target IP and port

    This endpoint performs parallel connectivity checks from multiple nodes
    to verify network reachability and measure response times.
    """
    try:
        # Get cluster configuration
        cluster_config = get_cluster(request.cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail=f"Cluster '{request.cluster_name}' not found")

        # Get all nodes from cluster
        all_nodes = cluster_config.get_nodes()
        if not all_nodes:
            raise HTTPException(status_code=400, detail="No nodes configured in the cluster")

        # Filter selected nodes
        selected_nodes = []
        node_ips = set(request.selected_nodes)

        for node in all_nodes:
            if node.get("ip") in node_ips:
                selected_nodes.append(node)

        if not selected_nodes:
            raise HTTPException(status_code=400, detail="No valid nodes selected for checking")

        logger.info(
            f"Starting network connectivity check from {len(selected_nodes)} nodes to {request.target_ip}:{request.target_port}"
        )

        # Perform connectivity checks
        results = check_connectivity_from_nodes(
            nodes=selected_nodes,
            target_ip=request.target_ip,
            target_port=request.target_port,
            timeout=request.timeout or 5,
        )

        logger.info(
            f"Network connectivity check completed. Results: {len([r for r in results if r['status'] == 'success'])} successful, {len([r for r in results if r['status'] == 'failed'])} failed"
        )

        # Save results
        result_id = None
        try:
            result_obj = NetworkConnectivityResult(
                cluster_name=request.cluster_name,
                target_ip=request.target_ip,
                target_port=request.target_port,
            )

            for check_result in results:
                result_obj.add_check(check_result)

            saved_path = result_obj.save()
            result_id = result_obj.result_id
            logger.info(f"Network check results saved to: {saved_path}")

        except Exception as save_error:
            logger.error(f"Failed to save network check results: {str(save_error)}")
            # Don't fail the request if saving fails

        return {"result_id": result_id, "results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Network connectivity check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Network check failed: {str(e)}")


@router.get("/network-check/clusters")
@log_api_request
async def get_clusters_for_network_check():
    """
    Get list of clusters available for network connectivity checks

    Returns cluster names and their nodes for selection in the UI.
    """
    try:
        from infrastructure.cluster.cluster_config import list_clusters

        clusters = list_clusters()
        cluster_data = []

        for cluster_name in clusters:
            cluster_config = get_cluster(cluster_name)
            if cluster_config:
                nodes = cluster_config.get_nodes()
                cluster_data.append(
                    {
                        "name": cluster_name,
                        "nodes": [
                            {
                                "ip": node.get("ip"),
                                "name": node.get("name", node.get("ip")),
                                "port": node.get("port", 22),
                            }
                            for node in nodes
                        ],
                    }
                )

        return {"clusters": cluster_data}

    except Exception as e:
        logger.error(f"Failed to get clusters for network check: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get clusters: {str(e)}")


@router.get("/network-check/results")
@log_api_request
async def get_network_check_results(cluster_name: Optional[str] = None, limit: int = 50):
    """
    Get list of saved network connectivity check results

    Args:
        cluster_name: optional filtering by cluster name
        limit: maximum number of results to return
    """
    try:
        # Validate limit parameter
        from .validation_middleware import validate_limit_param

        validated_limit = validate_limit_param(limit)

        # Validate cluster_name if provided
        if cluster_name:
            from .validation_middleware import validate_cluster_name

            validated_cluster_name = validate_cluster_name(cluster_name)
        else:
            validated_cluster_name = None

        results = list_network_check_results(cluster_name=validated_cluster_name, limit=validated_limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to get network check results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/network-check/results/{result_id}")
@log_api_request
async def get_network_check_result(result_id: str):
    """
    Get specific network connectivity check result by ID
    """
    try:
        # Validate result_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for result_id

        validated_result_id = validate_task_id(result_id)

        result = load_network_check_result(validated_result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Network check result not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get network check result {result_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")


@router.delete("/network-check/results/{result_id}")
@log_api_request
async def delete_network_check_result(result_id: str):
    """
    Delete network connectivity check result
    """
    try:
        # Validate result_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for result_id

        validated_result_id = validate_task_id(result_id)

        from pathlib import Path
        import os

        # Find and delete result file
        data_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent)))

        for file_path in data_dir.rglob("exports/*/network_reports/*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = load_network_check_result(validated_result_id)
                    if data and data.get("result_id") == validated_result_id:
                        os.remove(file_path)
                        return {"message": f"Network check result {validated_result_id} deleted"}
            except Exception:
                continue

        raise HTTPException(status_code=404, detail="Network check result not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to delete network check result {result_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete result: {str(e)}")


@router.get("/network-check/results/{result_id}/export/{format}")
@log_api_request
async def export_network_check_result(result_id: str, format: str):
    """Export network connectivity check result"""
    try:
        # Validate result_id parameter
        from .validation_middleware import validate_task_id  # Reuse task_id validation for result_id

        validated_result_id = validate_task_id(result_id)

        # Validate format parameter
        valid_formats = ["json", "csv", "excel", "pdf"]
        if format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Format must be one of: {', '.join(valid_formats)}")

        success, file_path = export_network_report(validated_result_id, format)
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
        logger.error(
            f"Failed to export network check result {result_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
