#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster controller - API endpoints для работы с кластерами
"""

from fastapi import APIRouter, Depends
from typing import Optional, Dict, Any

from api.models import ClusterCreate, NodesTestRequest, KubeconfigTestRequest, GetNodesFromKubeconfigRequest
from api.unified_middleware import (
    api_error_handler,
    validate_cluster_name_decorator,
    set_resource_context,
    audit_resource,
)
from api.dependencies import get_current_user
from db.models.user import User
from db.database import get_db
from services.cluster_service import ClusterService
from core.common.unified_validation import validate_cluster_name
from core.rbac import Permission, require_permission
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def get_cluster_service() -> ClusterService:
    """
    Dependency injection для ClusterService

    Returns:
        Экземпляр ClusterService
    """
    return ClusterService()


@router.get(
    "/dashboard",
    summary="Get dashboard data",
    description="""
    Retrieve aggregated data for dashboard including:
    - Total number of clusters
    - Cluster health status
    - Recent inspection results
    - Scheduled tasks summary
    """,
    response_description="Dashboard data with cluster statistics and recent activity",
)
@api_error_handler
@require_permission(Permission.CLUSTER_READ)
async def get_dashboard(
    current_user: User = Depends(get_current_user), service: ClusterService = Depends(get_cluster_service)
) -> Dict[str, Any]:
    """
    Get dashboard data with cluster statistics and recent activity.

    Returns:
        Dict containing dashboard metrics and summaries
    """
    return await service.get_dashboard_data()


@router.get(
    "/clusters",
    summary="List all clusters",
    description="Retrieve a list of all configured Kubernetes clusters with their basic information and status.",
    response_description="List of clusters with metadata",
)
@api_error_handler
@require_permission(Permission.CLUSTER_READ)
async def get_clusters(
    current_user: User = Depends(get_current_user), service: ClusterService = Depends(get_cluster_service)
) -> Dict[str, Any]:
    """
    Get list of all configured clusters.

    Returns:
        Dict containing list of clusters with their details
    """
    return await service.get_clusters_list()


@router.post(
    "/clusters",
    summary="Create new cluster",
    description="""
    Create a new Kubernetes cluster configuration.

    The cluster can be configured with either:
    - Node-based connection (SSH to individual nodes)
    - Kubeconfig-based connection (standard Kubernetes config)

    All node connections will be validated for security.
    """,
    response_description="Success message with cluster creation confirmation",
    status_code=201,
)
@api_error_handler
@require_permission(Permission.CLUSTER_CREATE)
@audit_resource(
    res_type="cluster",
    resource_name_param="cluster_name",
    resource_id_param="cluster_name",
)
async def create_cluster(
    cluster: ClusterCreate,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create a new cluster configuration.

    Args:
        cluster: Cluster creation data including nodes and kubeconfig

    Returns:
        Dict with success message and cluster details
    """
    # Set resource context for middleware logging
    set_resource_context(name=cluster.name, type="cluster", id=cluster.name)

    result = await service.create_cluster(cluster.model_dump())

    return result


@router.put(
    "/clusters/{cluster_name}",
    summary="Update cluster configuration",
    description="Update an existing cluster's configuration including nodes and kubeconfig.",
    response_description="Success message with update confirmation",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_UPDATE)
@audit_resource(
    res_type="cluster",
    resource_id_param="cluster_name",
    resource_name_param="cluster_name",
)
async def update_cluster(
    cluster_name: str,
    cluster: ClusterCreate,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Update cluster configuration.

    Args:
        cluster_name: Name of cluster to update
        cluster: Updated cluster data

    Returns:
        Dict with success message
    """
    result = await service.update_cluster(cluster_name, cluster.model_dump())

    return result


@router.delete(
    "/clusters/{cluster_name}",
    summary="Delete cluster",
    description="Remove a cluster configuration and all associated data.",
    response_description="Success message with deletion confirmation",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_DELETE)
@audit_resource(
    res_type="cluster",
    resource_id_param="cluster_name",
    resource_name_param="cluster_name",
)
async def remove_cluster(
    cluster_name: str,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete a cluster configuration.

    Args:
        cluster_name: Name of cluster to delete

    Returns:
        Dict with success message
    """
    result = await service.delete_cluster(cluster_name)

    return result


@router.get(
    "/clusters/{cluster_name}",
    summary="Get cluster details",
    description="Retrieve detailed information about a specific cluster including nodes, status, and configuration.",
    response_description="Detailed cluster information",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_READ)
async def get_cluster_details(
    cluster_name: str,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Get detailed cluster information.

    Args:
        cluster_name: Name of the cluster

    Returns:
        Dict with comprehensive cluster details
    """
    return await service.get_cluster_details(cluster_name)


@router.get(
    "/clusters/{cluster_name}/nodes",
    summary="Get cluster nodes",
    description="Retrieve information about all nodes in the Kubernetes cluster.",
    response_description="List of cluster nodes with their status and specifications",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_READ)
async def get_cluster_nodes(
    cluster_name: str,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Get nodes information from Kubernetes cluster.

    Args:
        cluster_name: Name of the cluster

    Returns:
        Dict with nodes information
    """
    return await service.get_cluster_nodes(cluster_name)


@router.get(
    "/clusters/{cluster_name}/namespaces",
    summary="Get cluster namespaces",
    description="Retrieve all namespaces in the Kubernetes cluster.",
    response_description="List of namespaces in the cluster",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_READ)
async def get_cluster_namespaces(
    cluster_name: str,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Get namespaces from Kubernetes cluster.

    Args:
        cluster_name: Name of the cluster

    Returns:
        Dict with namespaces information
    """
    return await service.get_cluster_namespaces(cluster_name)


@router.post(
    "/clusters/{cluster_name}/test-nodes",
    summary="Test node connectivity",
    description="Test SSH connectivity to all nodes in the cluster or specific nodes provided in the request.",
    response_description="Connectivity test results for each node",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_UPDATE)
async def test_cluster_nodes(
    cluster_name: str,
    request: Optional[NodesTestRequest] = None,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Test connectivity to cluster nodes.

    Args:
        cluster_name: Name of the cluster
        request: Optional request with specific nodes to test

    Returns:
        Dict with test results for each node
    """
    validated_cluster_name = validate_cluster_name(cluster_name)
    request_nodes = request.nodes if request else None
    return await service.test_cluster_nodes(validated_cluster_name, request_nodes)


@router.post(
    "/clusters/{cluster_name}/test-kubeconfig",
    summary="Test kubeconfig validity",
    description="Validate kubeconfig for the cluster and test connectivity to the Kubernetes API.",
    response_description="Kubeconfig validation results",
)
@api_error_handler
@validate_cluster_name_decorator
@require_permission(Permission.CLUSTER_UPDATE)
async def test_cluster_kubeconfig(
    cluster_name: str,
    request: Optional[KubeconfigTestRequest] = None,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Test kubeconfig validity for the cluster.

    Args:
        cluster_name: Name of the cluster
        request: Optional request with kubeconfig to test

    Returns:
        Dict with validation results
    """
    validated_cluster_name = validate_cluster_name(cluster_name)
    request_kubeconfig = request.kubeconfig if request else None
    return await service.test_cluster_kubeconfig(validated_cluster_name, request_kubeconfig)


@router.post(
    "/clusters/get-nodes-from-kubeconfig",
    summary="Extract nodes from kubeconfig",
    description="Parse kubeconfig and extract node information for cluster setup.",
    response_description="List of nodes extracted from kubeconfig",
)
@api_error_handler
@require_permission(Permission.CLUSTER_CREATE)
async def get_nodes_from_kubeconfig(
    request: GetNodesFromKubeconfigRequest,
    current_user: User = Depends(get_current_user),
    service: ClusterService = Depends(get_cluster_service),
) -> Dict[str, Any]:
    """
    Get nodes information from kubeconfig.

    Args:
        request: Request containing kubeconfig

    Returns:
        Dict with extracted nodes information
    """
    return await service.get_nodes_from_kubeconfig(request.kubeconfig)
