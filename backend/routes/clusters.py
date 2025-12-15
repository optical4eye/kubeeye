#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster management routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

from utils.cluster_config import list_clusters, get_cluster, delete_cluster
from utils.cert_checker import get_cluster_cert_status
from utils.node_connection import test_node_connection
from utils.k8s_client import K8sClient
from .main import ClusterCreate, TestNodesRequest, TestKubeconfigRequest

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard data"""
    try:
        from utils.dashboard import get_dashboard_data_api

        return get_dashboard_data_api()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def get_clusters():
    """Get list of clusters"""
    try:
        clusters = list_clusters()
        cluster_data = []
        for cluster_name in clusters:
            cluster_config = get_cluster(cluster_name)
            if cluster_config:
                kubeconfig = cluster_config.get_kubeconfig()
                cert_status = None
                if kubeconfig:
                    cert_status = get_cluster_cert_status(cluster_name, kubeconfig)

                cluster_data.append(
                    {
                        "name": cluster_name,
                        "nodes": cluster_config.get_nodes(),
                        "prometheus_config": cluster_config.get_prometheus_config(),
                        "kubeconfig": kubeconfig is not None,
                        "cert_expiry_days": (
                            cert_status.get("days_remaining") if cert_status else None
                        ),
                    }
                )
        return {"clusters": cluster_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clusters")
async def create_cluster(cluster: ClusterCreate):
    """Create new cluster"""
    try:
        cluster_config = get_cluster(cluster.name)
        # Add nodes
        for node in cluster.nodes:
            cluster_config.update_node(node)

        # Prometheus config
        if cluster.prometheus_config:
            cluster_config.update_prometheus(cluster.prometheus_config)

        # Kubeconfig
        if cluster.kubeconfig:
            cluster_config.update_kubeconfig(cluster.kubeconfig)

        return {"message": f"Cluster {cluster.name} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clusters/{cluster_name}")
async def update_cluster(cluster_name: str, cluster: ClusterCreate):
    """Update cluster"""
    try:
        cluster_config = get_cluster(cluster_name)

        # Clear existing nodes
        cluster_config.config["nodes"] = []

        # Add new nodes
        for node in cluster.nodes:
            cluster_config.update_node(node)

        # Prometheus config
        if cluster.prometheus_config:
            cluster_config.update_prometheus(cluster.prometheus_config)
        else:
            # Disable Prometheus if not specified
            cluster_config.update_prometheus({"enabled": False})

        # Kubeconfig
        cluster_config.update_kubeconfig(cluster.kubeconfig or "")

        return {"message": f"Cluster {cluster_name} updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clusters/{cluster_name}")
async def remove_cluster(cluster_name: str):
    """Delete cluster"""
    try:
        delete_cluster(cluster_name)
        return {"message": f"Cluster {cluster_name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_name}")
async def get_cluster_details(cluster_name: str):
    """Get cluster details"""
    try:
        cluster_config = get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        return {
            "name": cluster_name,
            "nodes": cluster_config.get_nodes(),
            "prometheus_config": cluster_config.get_prometheus_config(),
            "kubeconfig": cluster_config.get_kubeconfig(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_name}/nodes")
async def get_cluster_nodes(cluster_name: str):
    """Get cluster nodes information"""
    try:
        cluster_config = get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        kubeconfig = cluster_config.get_kubeconfig()
        if not kubeconfig:
            raise HTTPException(status_code=400, detail="Kubeconfig not configured for this cluster")

        k8s_client = K8sClient(kubeconfig)
        nodes_result = k8s_client.get_nodes()

        if nodes_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=nodes_result.get("error", "Failed to get nodes"))

        return nodes_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster nodes: {str(e)}")


def _get_nodes_for_testing(
    cluster_name: str, request: Optional[TestNodesRequest] = None
) -> List[Dict]:
    """Get list of nodes for testing"""
    if request and request.nodes:
        return request.nodes

    cluster_config = get_cluster(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster_config.get_nodes()


async def _test_single_node_async(node: Dict) -> Dict:
    """Test connection to single node asynchronously"""
    from utils.node_connection import async_test_node_connection

    node_name = node.get("name", node["ip"])
    node_address = f"{node['ip']}:{node['port']}"

    try:
        success, message = await async_test_node_connection(node)
        return {
            "node": node_address,
            "node_name": node_name,
            "success": success,
            "message": message,
        }
    except Exception as e:
        return {
            "node": node_address,
            "node_name": node_name,
            "success": False,
            "message": f"Test failed for {node_name}: {str(e)}",
        }


def _test_single_node(node: Dict) -> Dict:
    """Test connection to single node (synchronous)"""
    try:
        success, message = test_node_connection(node)
        return {
            "node": f"{node['ip']}:{node['port']}",
            "success": success,
            "message": message,
        }
    except Exception as e:
        return {
            "node": f"{node['ip']}:{node['port']}",
            "success": False,
            "message": f"Test failed: {str(e)}",
        }


@router.post("/clusters/{cluster_name}/test-nodes")
async def test_cluster_nodes(
    cluster_name: str, request: Optional[TestNodesRequest] = None
):
    """Test connection to all cluster nodes"""
    try:
        nodes = _get_nodes_for_testing(cluster_name, request)

        # Test nodes asynchronously in parallel with individual timeouts
        async def test_with_timeout(node):
            try:
                result = await asyncio.wait_for(
                    _test_single_node_async(node), timeout=10.0
                )
                return result
            except asyncio.TimeoutError:
                node_name = node.get("name", node["ip"])
                return {
                    "node": f"{node['ip']}:{node['port']}",
                    "node_name": node_name,
                    "success": False,
                    "message": f"Connection timeout (15s) for node {node_name}",
                }
            except Exception as e:
                node_name = node.get("name", node["ip"])
                return {
                    "node": f"{node['ip']}:{node['port']}",
                    "node_name": node_name,
                    "success": False,
                    "message": f"Test failed for node {node_name}: {str(e)}",
                }

        # Create tasks for all nodes with mapping
        task_to_node = {}
        tasks = []
        for node in nodes:
            task = asyncio.create_task(test_with_timeout(node))
            tasks.append(task)
            task_to_node[task] = node

        # Wait for all tasks to complete with overall timeout
        try:
            done, pending = await asyncio.wait(tasks, timeout=10.0)  # Reduced timeout
            results = []
            failed_nodes = []

            for task in done:
                try:
                    result = task.result()
                    results.append(result)
                    if not result["success"]:
                        failed_nodes.append(result["node_name"])
                except Exception as e:
                    # Find the node for this task
                    node = task_to_node[task]
                    node_name = node.get("name", node["ip"])
                    failed_result = {
                        "node": f"{node['ip']}:{node['port']}",
                        "node_name": node_name,
                        "success": False,
                        "message": f"Test failed: {str(e)}",
                    }
                    results.append(failed_result)
                    failed_nodes.append(node_name)

            # Cancel remaining tasks and mark them as failed
            for task in pending:
                task.cancel()
                node = task_to_node[task]
                node_name = node.get("name", node["ip"])
                failed_result = {
                    "node": f"{node['ip']}:{node['port']}",
                    "node_name": node_name,
                    "success": False,
                    "message": f"Connection timeout (10s) for node {node_name}",
                }
                results.append(failed_result)
                failed_nodes.append(node_name)

            # If there are failed nodes, include error message
            response = {"results": results}
            if failed_nodes:
                response["error"] = f"Нет соединения с {', '.join(failed_nodes)}"

            return response

        except Exception as e:
            return {
                "results": [],
                "error": f"Test execution error: {str(e)}",
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Node testing error: {str(e)}")


@router.post("/clusters/{cluster_name}/test-kubeconfig")
async def test_cluster_kubeconfig(
    cluster_name: str, request: Optional[TestKubeconfigRequest] = None
):
    """Test cluster kubeconfig validity"""
    try:
        # If kubeconfig passed in request, use it, otherwise get from config
        if request and request.kubeconfig:
            kubeconfig = request.kubeconfig
        else:
            cluster_config = get_cluster(cluster_name)
            if not cluster_config:
                raise HTTPException(status_code=404, detail="Cluster not found")
            kubeconfig = cluster_config.get_kubeconfig()

        if not kubeconfig:
            return {"success": False, "message": "Kubeconfig not configured"}

        k8s_client = K8sClient(kubeconfig)
        success, message = k8s_client.test_connection()

        return {"success": success, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
