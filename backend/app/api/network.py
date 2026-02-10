#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network connectivity check routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from core.common.streaming_response import StreamingExportResponse
from db.database_context import with_db_session
from api.dependencies import get_current_user
from db.models.user import User
from core.rbac import Permission, require_permission

from infra.cluster.cluster_config import get_cluster, list_clusters
from infra.network.network_check import (
    check_connectivity_from_nodes,
    NetworkConnectivityResult,
    load_network_check_result,
    list_network_check_results,
    export_network_stream,
)
from core.common.unified_validation import validate_port, validate_cluster_name, validate_task_id
from core.logging import log_api_request

from core.logging import get_logger

logger = get_logger(__name__)

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
            # Synchronous DNS resolution - fast enough for validation
            socket.gethostbyname(v)
            return v
        except socket.gaierror:
            raise ValueError("Invalid IP address or hostname")

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
@require_permission(Permission.NETWORK_CHECK)
async def check_network_connectivity(request: NetworkCheckRequest, current_user: User = Depends(get_current_user)):
    """
    Check network connectivity from selected cluster nodes to a target IP and port

    This endpoint performs parallel connectivity checks from multiple nodes
    to verify network reachability and measure response times.
    """
    try:
        logger.info(f"Starting check_network_connectivity for cluster {request.cluster_name}")
        # Get cluster configuration
        cluster_config = await get_cluster(request.cluster_name)
        if not cluster_config:
            logger.error(f"Cluster '{request.cluster_name}' not found")
            raise HTTPException(status_code=404, detail=f"Cluster '{request.cluster_name}' not found")

        # Get all nodes from cluster with secrets parsed for connectivity checks
        all_nodes = await cluster_config.get_nodes(parse_secrets=True)
        logger.info(f"Retrieved {len(all_nodes)} nodes from cluster {request.cluster_name}")
        if not all_nodes:
            logger.error(f"No nodes configured in cluster {request.cluster_name}")
            raise HTTPException(status_code=400, detail="No nodes configured in the cluster")

        # Filter selected nodes
        selected_nodes = []
        node_ips = set(request.selected_nodes)

        for node in all_nodes:
            if node.get("ip") in node_ips:
                selected_nodes.append(node)

        logger.info(f"Selected {len(selected_nodes)} nodes for checking")
        if not selected_nodes:
            logger.error("No valid nodes selected for checking")
            raise HTTPException(status_code=400, detail="No valid nodes selected for checking")

        logger.info(
            f"Starting network connectivity check from {len(selected_nodes)} nodes to {request.target_ip}:{request.target_port}"
        )

        # Perform connectivity checks
        results = await check_connectivity_from_nodes(
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
            logger.info("Saving network check results")
            result_obj = NetworkConnectivityResult(
                cluster_name=request.cluster_name,
                target_ip=request.target_ip,
                target_port=request.target_port,
            )

            for check_result in results:
                result_obj.add_check(check_result)

            result_id = await result_obj.save()
            logger.info(f"Network check results saved with result_id: {result_id}")

        except Exception as save_error:
            logger.error(f"Failed to save network check results: {str(save_error)}")
            # Don't fail the request if saving fails

        logger.info(f"Successfully completed check_network_connectivity for {request.cluster_name}")
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
        logger.info("Starting get_clusters_for_network_check")

        clusters = await list_clusters()
        logger.info(f"Found {len(clusters)} clusters for network check")
        cluster_data = []

        for cluster_name in clusters:
            logger.debug(f"Processing cluster {cluster_name}")
            cluster_config = await get_cluster(cluster_name)
            if cluster_config:
                nodes = await cluster_config.get_nodes()
                logger.debug(f"Cluster {cluster_name} has {len(nodes)} nodes")
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
            else:
                logger.warning(f"No config found for cluster {cluster_name}")

        logger.info(f"Successfully processed {len(cluster_data)} clusters")
        return {"clusters": cluster_data}

    except Exception as e:
        logger.error(f"Failed to get clusters for network check: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get clusters: {str(e)}")


@router.get("/network-check/results")
@log_api_request
async def get_network_check_results(
    cluster_name: Optional[str] = None, limit: int = 50, current_user: User = Depends(get_current_user)
):
    """
    Get list of saved network connectivity check results

    Args:
        cluster_name: optional filtering by cluster name
        limit: maximum number of results to return
    """
    try:
        # Validate limit parameter using centralized validation
        from core.common.unified_validation import validate_limit_param

        validated_limit = validate_limit_param(limit)

        # Validate cluster_name if provided using centralized validation
        if cluster_name:
            validated_cluster_name = validate_cluster_name(cluster_name)
        else:
            validated_cluster_name = None

        results = await list_network_check_results(cluster_name=validated_cluster_name, limit=validated_limit)
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to get network check results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/network-check/results/{result_id}")
@log_api_request
async def get_network_check_result(result_id: str, current_user: User = Depends(get_current_user)):
    """
    Get specific network connectivity check result by ID
    """
    try:
        # Validate result_id parameter using centralized validation
        validated_result_id = validate_task_id(result_id)

        result = await load_network_check_result(validated_result_id)
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
@require_permission(Permission.TASK_DELETE)
async def delete_network_check_result(result_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete network connectivity check result
    """
    try:
        # Validate result_id parameter using centralized validation
        validated_result_id = validate_task_id(result_id)

        # Try to delete from database first
        try:
            from db.repositories.inspection_result_repository import InspectionResultRepository

            async with with_db_session() as db:
                repo = InspectionResultRepository(db)
                if await repo.delete_by_result_id(validated_result_id):
                    return {"message": f"Network check result {validated_result_id} deleted"}
                raise HTTPException(status_code=404, detail="Network check result not found")
        except Exception as e:
            logger.warning(f"Failed to delete from database, trying files: {e}")

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
async def export_network_check_result(result_id: str, format: str, current_user: User = Depends(get_current_user)):
    """Export network connectivity check result"""
    try:
        # Validate result_id parameter using centralized validation
        validated_result_id = validate_task_id(result_id)

        # Validate format parameter
        valid_formats = ["json"]
        if format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Format must be one of: {', '.join(valid_formats)}")

        # Get media type for the format
        def get_media_type(fmt: str) -> str:
            media_types = {
                "json": "application/json",
                "pdf": "application/pdf",
            }
            return media_types.get(fmt, "application/octet-stream")

        async def content_generator():
            async for chunk in export_network_stream(validated_result_id, format):
                yield chunk

        return StreamingExportResponse(
            content_generator=content_generator,
            filename=f"{validated_result_id}.{format}",
            media_type=get_media_type(format),
        ).to_response()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to export network check result {result_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
