#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster management routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import asyncio
import time
import yaml
import base64

from infrastructure.cluster.cluster_config import (
    list_clusters,
    get_cluster,
    delete_cluster,
)
from infrastructure.security.cert_checker import get_cluster_cert_status
from infrastructure.cluster.node_connection import test_node_connection
from infrastructure.cluster.k8s_client import K8sClient
from .models import ClusterCreate, TestNodesRequest, TestKubeconfigRequest

router = APIRouter()

# Simple in-memory cache for clusters data
_clusters_cache = {}
_CACHE_TTL = 300  # 5 minutes


def validate_kubeconfig(kubeconfig: str) -> bool:
    """Validate kubeconfig format"""
    print(f"[DEBUG] Validating kubeconfig (first 50 chars): {kubeconfig[:50]}...")
    print(f"[DEBUG] Kubeconfig length: {len(kubeconfig)}")
    print(f"[DEBUG] Kubeconfig type: {type(kubeconfig)}")

    if not kubeconfig or not isinstance(kubeconfig, str):
        print("[DEBUG] kubeconfig is empty or not str")
        return False

    # Check if the string looks like YAML (not base64)
    # If it starts with typical YAML keywords, treat it as YAML directly
    if kubeconfig.strip().startswith(("apiVersion:", "kind:", "clusters:", "users:", "contexts:")):
        print("[DEBUG] Detected YAML format, treating as direct YAML")
        try:
            config = yaml.safe_load(kubeconfig)
            print(f"[DEBUG] YAML loaded directly: {type(config)}")
        except Exception as yaml_err:
            print(f"[DEBUG] Direct YAML parsing error: {yaml_err}")
            return False
    else:
        # Check if the string looks like base64 (basic validation)
        # Base64 strings should have length divisible by 4 (after padding)
        # and only contain valid base64 characters
        import re

        if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", kubeconfig):
            print("[DEBUG] kubeconfig contains invalid base64 characters and doesn't look like YAML")
            return False

        try:
            # Add padding if needed (base64 strings should have length divisible by 4)
            padded_kubeconfig = kubeconfig
            padding_needed = (4 - len(kubeconfig) % 4) % 4
            if padding_needed:
                padded_kubeconfig = kubeconfig + ("=" * padding_needed)
                print(f"[DEBUG] Added {padding_needed} padding characters")

            # Decode base64
            decoded = base64.b64decode(padded_kubeconfig).decode("utf-8")
            print(f"[DEBUG] Decoded successfully (first 50 chars): {decoded[:50]}...")
            config = yaml.safe_load(decoded)
            print(f"[DEBUG] YAML loaded: {type(config)}")
        except Exception as decode_err:
            print(f"[DEBUG] Decode/YAML error: {decode_err}")
            return False

    if not isinstance(config, dict):
        print("[DEBUG] Not a dict after YAML load")
        return False
    # Check for required fields
    missing_fields = []
    if "apiVersion" not in config:
        missing_fields.append("apiVersion")
    if "clusters" not in config:
        missing_fields.append("clusters")
    if "users" not in config:
        missing_fields.append("users")
    if missing_fields:
        print(f"[DEBUG] Missing fields: {missing_fields}")
        return False
    print("[DEBUG] kubeconfig VALID")
    return True


def validate_ssh_key(ssh_key: str) -> bool:
    """Validate SSH key format"""
    if not ssh_key or not isinstance(ssh_key, str):
        return False
    # Basic check for SSH key format
    lines = ssh_key.strip().split("\n")
    if not lines:
        return False
    first_line = lines[0].strip()
    # Should start with ssh-rsa, ssh-ed25519, etc.
    if not first_line.startswith("ssh-") or " " not in first_line:
        return False
    return True


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard data"""
    try:
        from infrastructure.common.dashboard import get_dashboard_data_api

        return get_dashboard_data_api()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def get_clusters():
    """Get list of clusters"""
    try:
        # Check cache
        current_time = time.time()
        if "clusters" in _clusters_cache and current_time - _clusters_cache["clusters"]["timestamp"] < _CACHE_TTL:
            return _clusters_cache["clusters"]["data"]

        clusters = await asyncio.to_thread(list_clusters)
        cluster_data = []
        for cluster_name in clusters:
            cluster_config = await asyncio.to_thread(get_cluster, cluster_name)
            if cluster_config:
                kubeconfig = cluster_config.get_kubeconfig()
                cert_status = None
                if kubeconfig:
                    cert_status = await asyncio.to_thread(get_cluster_cert_status, cluster_name, kubeconfig)

                cluster_data.append(
                    {
                        "name": cluster_name,
                        "nodes": cluster_config.get_nodes(),
                        "prometheus_config": cluster_config.get_prometheus_config(),
                        "kubeconfig": kubeconfig is not None,
                        "cert_expiry_days": (cert_status.get("days_remaining") if cert_status else None),
                    }
                )

        result = {"clusters": cluster_data}
        # Cache the result only on success
        _clusters_cache["clusters"] = {"data": result, "timestamp": current_time}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clusters")
async def create_cluster(cluster: ClusterCreate):
    """Create new cluster"""
    try:
        cluster_config = await asyncio.to_thread(get_cluster, cluster.name)
        # Add nodes
        for node in cluster.nodes:
            ssh_key = getattr(node, "ssh_key", node.get("ssh_key"))
            if ssh_key and not validate_ssh_key(ssh_key):
                node_name = getattr(node, "name", node.get("name", "unknown"))
                raise HTTPException(status_code=400, detail=f"Invalid SSH key format for node {node_name}")
            cluster_config.update_node(node)

        # Prometheus config
        if cluster.prometheus_config:
            cluster_config.update_prometheus(cluster.prometheus_config)

        # Kubeconfig
        if cluster.kubeconfig:
            if not validate_kubeconfig(cluster.kubeconfig):
                raise HTTPException(status_code=400, detail="Invalid kubeconfig format")
            cluster_config.update_kubeconfig(cluster.kubeconfig)

        # Invalidate cache
        _clusters_cache.pop("clusters", None)
        return {"message": f"Cluster {cluster.name} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clusters/{cluster_name}")
async def update_cluster(cluster_name: str, cluster: ClusterCreate):
    """Update cluster"""
    try:
        cluster_config = await asyncio.to_thread(get_cluster, cluster_name)

        # Clear existing nodes
        cluster_config.config["nodes"] = []

        # Add new nodes
        for node in cluster.nodes:
            ssh_key = getattr(node, "ssh_key", node.get("ssh_key"))
            if ssh_key and not validate_ssh_key(ssh_key):
                node_name = getattr(node, "name", node.get("name", "unknown"))
                raise HTTPException(status_code=400, detail=f"Invalid SSH key format for node {node_name}")
            cluster_config.update_node(node)

        # Prometheus config
        if cluster.prometheus_config:
            cluster_config.update_prometheus(cluster.prometheus_config)
        else:
            # Disable Prometheus if not specified
            cluster_config.update_prometheus({"enabled": False})

        # Kubeconfig
        if cluster.kubeconfig:
            if not validate_kubeconfig(cluster.kubeconfig):
                raise HTTPException(status_code=400, detail="Invalid kubeconfig format")
        cluster_config.update_kubeconfig(cluster.kubeconfig or "")

        # Invalidate cache
        _clusters_cache.pop("clusters", None)
        return {"message": f"Cluster {cluster_name} updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clusters/{cluster_name}")
async def remove_cluster(cluster_name: str):
    """Delete cluster"""
    try:
        # Validate cluster_name using our validation function
        from .validation_middleware import validate_cluster_name

        validated_cluster_name = validate_cluster_name(cluster_name)

        await asyncio.to_thread(delete_cluster, validated_cluster_name)
        # Invalidate cache
        _clusters_cache.pop("clusters", None)
        return {"message": f"Cluster {validated_cluster_name} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_name}")
async def get_cluster_details(cluster_name: str):
    """Get cluster details"""
    try:
        # Validate cluster_name using our validation function
        from .validation_middleware import validate_cluster_name

        validated_cluster_name = validate_cluster_name(cluster_name)

        cluster_config = await asyncio.to_thread(get_cluster, validated_cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        return {
            "name": validated_cluster_name,
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
        # Validate cluster_name using our validation function
        from .validation_middleware import validate_cluster_name

        validated_cluster_name = validate_cluster_name(cluster_name)

        cluster_config = await asyncio.to_thread(get_cluster, validated_cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        kubeconfig = cluster_config.get_kubeconfig()
        if not kubeconfig:
            raise HTTPException(status_code=400, detail="Kubeconfig not configured for this cluster")

        k8s_client = K8sClient(kubeconfig)
        nodes_result = await asyncio.to_thread(k8s_client.get_nodes)

        if nodes_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=nodes_result.get("error", "Failed to get nodes"))

        return nodes_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster nodes: {str(e)}")


async def _get_nodes_for_testing(cluster_name: str, request: Optional[TestNodesRequest] = None) -> List[Dict]:
    """Get list of nodes for testing"""
    if request and request.nodes:
        return request.nodes

    cluster_config = await asyncio.to_thread(get_cluster, cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster_config.get_nodes()


async def _test_single_node_async(node: Dict) -> Dict:
    """Test connection to single node asynchronously"""
    from infrastructure.cluster.node_connection import async_test_node_connection

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
async def test_cluster_nodes(cluster_name: str, request: Optional[TestNodesRequest] = None):
    """Test connection to all cluster nodes"""
    try:
        # Validate cluster_name using our validation function
        from .validation_middleware import validate_cluster_name

        validated_cluster_name = validate_cluster_name(cluster_name)

        nodes = await _get_nodes_for_testing(validated_cluster_name, request)

        # Test nodes asynchronously in parallel with individual timeouts
        async def test_with_timeout(node):
            try:
                result = await asyncio.wait_for(_test_single_node_async(node), timeout=10.0)
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
async def test_cluster_kubeconfig(cluster_name: str, request: Optional[TestKubeconfigRequest] = None):
    """Test cluster kubeconfig validity"""
    try:
        # Validate cluster_name using our validation function
        from .validation_middleware import validate_cluster_name

        validated_cluster_name = validate_cluster_name(cluster_name)

        # If kubeconfig passed in request, use it, otherwise get from infrastructure.config
        if request and request.kubeconfig:
            kubeconfig = request.kubeconfig
        else:
            cluster_config = await asyncio.to_thread(get_cluster, validated_cluster_name)
            if not cluster_config:
                raise HTTPException(status_code=404, detail="Cluster not found")
            kubeconfig = cluster_config.get_kubeconfig()

        if not kubeconfig:
            return {"success": False, "message": "Kubeconfig not configured"}

        k8s_client = K8sClient(kubeconfig)
        success, message = await asyncio.to_thread(k8s_client.test_connection)

        return {"success": success, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
