#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster service - бизнес-логика для работы с кластерами
"""

from typing import Dict, List, Optional, Tuple
import asyncio
import time

from fastapi import HTTPException
from core.common.cache_utils import CacheManager
from infra.cluster.cluster_config import (
    list_clusters,
    get_cluster,
    delete_cluster,
    get_cluster_quick_status,
    get_cluster_status_counts_fast,
)
from infra.security.cert_checker import get_cluster_cert_status
from infra.cluster.node_connection import async_test_node_connection
from infra.cluster.k8s_client import K8sClient
from infra.security.secret_variable_parser import SecretVariableParser
from db.database_context import with_db_session
from core.logging import get_logger

logger = get_logger(__name__)


class ClusterService:
    """
    Сервис для бизнес-логики работы с кластерами.

    Отвечает за:
    - Создание, обновление, удаление кластеров
    - Тестирование соединений с кластерами и узлами
    - Получение информации о кластерах
    - Валидацию секретных переменных
    """

    def __init__(self):
        self.logger = logger
        # Use CacheManager for clusters data
        self.cache_manager = CacheManager()
        self._CACHE_TTL = 300  # 5 minutes

    def _invalidate_cache(self) -> None:
        """Инвалидация кэша кластеров"""
        self.cache_manager.invalidate_namespace("clusters")

    async def get_dashboard_data(self) -> Dict:
        """
        Получить данные для дашборда

        Returns:
            Dict с данными дашборда
        """
        try:
            from infra.results.inspection_result import list_results
            from infra.rules.rule_loader import load_rules
            from infra.gitops.gitops_manager import GitOpsRuleManager
            from db.database import get_session_local
            from db.repositories.cluster_repository import ClusterRepository
            from db.repositories.inspection_result_repository import InspectionResultRepository
            from datetime import datetime

            # Load all clusters with details in a single query (optimized)
            session_local = get_session_local()
            async with session_local() as db:
                cluster_repo = ClusterRepository(db)
                result_repo = InspectionResultRepository(db)

                # Get all clusters with their details (nodes, secrets) in one query
                clusters = await cluster_repo.get_all_clusters_with_details()
                cluster_names = [c.name for c in clusters]
                total_clusters = len(clusters)

                # Get latest results for all clusters in a single query (optimized)
                latest_results_map = await result_repo.get_latest_results_for_all_clusters(
                    cluster_names, exclude_inspection_types=["network", "popeye"]
                )

            # Load rules
            node_rules = load_rules("node")
            opa_rules = load_rules("opa")
            total_rules = len(node_rules) + len(opa_rules)

            # Check if GitOps is configured and add GitOps rules
            gitops_manager = GitOpsRuleManager()
            gitops_config = gitops_manager.load_config()
            if gitops_config.get("mode") == "gitops" and gitops_config.get("repository"):
                try:
                    gitops_rules = gitops_manager.get_repo_rules(gitops_config["repository"]["name"])
                    total_rules += len(gitops_rules)
                except Exception as e:
                    logger.warning(f"Failed to load GitOps rules: {e}")

            # Fast status counting without loading all results
            status_counts = await get_cluster_status_counts_fast(exclude_inspection_types=["network", "popeye"])

            # Load results for dashboard (increased for trends), exclude network and popeye reports
            recent_results_data = await list_results(
                limit=100, order_by="timestamp DESC", exclude_inspection_types=["network", "popeye"]
            )
            recent_results = recent_results_data.get("results", [])

            # Recent scans statistics (24 hours)
            now = datetime.now()
            cutoff_time = now.timestamp() - (24 * 3600)

            recent_scans = 0
            recent_issues = 0

            for result in recent_results:
                timestamp = datetime.fromisoformat(result["timestamp"]).timestamp()
                if timestamp > cutoff_time:
                    recent_scans += 1
                    recent_issues += result.get("critical", 0) + result.get("warning", 0)

            # Last inspection time
            latest_scan_time = "No data"
            if recent_results:
                latest_time = datetime.fromisoformat(recent_results[0]["timestamp"])
                latest_scan_time = latest_time.strftime("%m-%d %H:%M")

            # Create simplified cluster statuses (only necessary fields)
            cluster_statuses = []
            for cluster in clusters:
                cluster_name = cluster.name
                try:
                    # Get latest result from pre-loaded map (no additional query)
                    latest_result = latest_results_map.get(cluster_name)

                    # Determine status from latest result
                    if latest_result:
                        critical = latest_result.get("critical", 0)
                        warning = latest_result.get("warning", 0)
                        if critical > 0:
                            status = "critical"
                        elif warning > 0:
                            status = "warning"
                        else:
                            status = "healthy"
                    else:
                        status = "healthy"

                    # Get node count from cluster data (already loaded)
                    node_count = len(cluster.nodes) if cluster.nodes else 0

                    # Get certificate information
                    cert_status = "unknown"
                    cert_days_remaining = None
                    try:
                        kubeconfig_content = cluster.kubeconfig
                        if kubeconfig_content:
                            # Parse secret variables in kubeconfig for cert check
                            async with with_db_session() as db:
                                parser = SecretVariableParser(db)
                                processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig_content)
                                if parse_errors:
                                    logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
                                kubeconfig_content = processed_kubeconfig

                            cert_info = await asyncio.to_thread(
                                get_cluster_cert_status, cluster_name, kubeconfig_content
                            )
                            cert_status = cert_info.get("status", "unknown")
                            cert_days_remaining = cert_info.get("days_remaining")
                    except Exception as e:
                        logger.warning(f"Failed to get certificate info for cluster {cluster_name}: {e}")
                        cert_status = "unknown"
                        cert_days_remaining = None

                    cluster_status_dict = {
                        "name": cluster_name,
                        "status": status,
                        "last_scan": latest_result["timestamp"] if latest_result else None,
                        "critical_count": (latest_result.get("critical", 0) if latest_result else 0),
                        "warning_count": (latest_result.get("warning", 0) if latest_result else 0),
                        "passed_count": latest_result.get("passed", 0) if latest_result else 0,
                        "node_count": node_count,
                        "cert_status": cert_status,
                        "cert_days_remaining": cert_days_remaining,
                    }

                    cluster_statuses.append(cluster_status_dict)
                except Exception as e:
                    # In case of error - minimal information
                    logger.warning(f"Error processing cluster {cluster_name}: {e}")
                    cluster_statuses.append(
                        {
                            "name": cluster_name,
                            "status": "unknown",
                            "last_scan": None,
                            "critical_count": 0,
                            "warning_count": 0,
                            "passed_count": 0,
                            "node_count": 0,
                            "cert_status": "unknown",
                            "cert_days_remaining": None,
                        }
                    )

            return {
                "clusters": cluster_names,
                "cluster_statuses": cluster_statuses,
                "total_clusters": total_clusters,
                "recent_scans": recent_scans,
                "recent_issues": recent_issues,
                "latest_scan_time": latest_scan_time,
                "total_rules": total_rules,
                "status_counts": status_counts,
                "recent_results": recent_results,
            }
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def get_clusters_list(self) -> Dict:
        """
        Получить список кластеров с информацией о них

        Returns:
            Dict со списком кластеров
        """
        # Check cache using CacheManager
        cache = self.cache_manager.get_or_create_cache("clusters", maxsize=1, ttl=self._CACHE_TTL)
        if "clusters" in cache:
            return cache["clusters"]

        clusters = await list_clusters()
        cluster_data = []
        for cluster_name in clusters:
            cluster_config = await get_cluster(cluster_name)
            if cluster_config:
                kubeconfig = await cluster_config.get_kubeconfig()
                cert_status = None
                cert_expiry_days = None
                if kubeconfig:
                    # Parse secret variables in kubeconfig for cert check
                    async with with_db_session() as db:
                        parser = SecretVariableParser(db)
                        processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
                        if parse_errors:
                            logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
                        kubeconfig = processed_kubeconfig

                    cert_status = await asyncio.to_thread(get_cluster_cert_status, cluster_name, kubeconfig)
                    if cert_status:
                        cert_expiry_days = cert_status.get("days_remaining")

                nodes = await cluster_config.get_nodes()

                cluster_data.append(
                    {
                        "name": cluster_name,
                        "nodes": nodes,
                        "kubeconfig": kubeconfig is not None,
                        "cert_expiry_days": cert_expiry_days,
                    }
                )

        result = {"clusters": cluster_data}
        # Cache the result only on success using CacheManager
        cache = self.cache_manager.get_or_create_cache("clusters", maxsize=1, ttl=self._CACHE_TTL)
        cache["clusters"] = result
        return result

    async def create_cluster(self, cluster_data: Dict) -> Dict:
        """
        Создать новый кластер

        Args:
            cluster_data: Dict с данными кластера (name, nodes, kubeconfig)

        Returns:
            Dict с сообщением об успехе

        Raises:
            HTTPException: если валидация не прошла
        """
        try:
            cluster_name = cluster_data["name"]
            nodes = cluster_data["nodes"]
            kubeconfig = cluster_data.get("kubeconfig")

            # Get database session for secret validation
            async with with_db_session() as db:
                cluster_config = await get_cluster(cluster_name)

            # Validate secret variables in nodes
            parser = SecretVariableParser(db)
            processed_nodes = []

            for node in nodes:
                processed_node = node.copy()

                # Validate password if present
                if "password" in processed_node and processed_node["password"]:
                    password_text = processed_node["password"]
                    # Validate secret variables
                    is_valid, errors = await parser.validate_variables(password_text)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid secret variables in password: {', '.join(errors)}"
                        )
                    processed_node["password"] = password_text

                # Validate ssh_key if present
                if "ssh_key" in processed_node and processed_node["ssh_key"]:
                    ssh_key_text = processed_node["ssh_key"]
                    # Validate secret variables
                    is_valid, errors = await parser.validate_variables(ssh_key_text)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid secret variables in SSH key: {', '.join(errors)}"
                        )
                    processed_node["ssh_key"] = ssh_key_text

                processed_nodes.append(processed_node)

            # Add processed nodes
            for node in processed_nodes:
                await cluster_config.update_node(node)

            # Validate secret variables in kubeconfig
            processed_kubeconfig = kubeconfig
            if kubeconfig:
                # Validate secret variables
                is_valid, errors = await parser.validate_variables(kubeconfig)
                if not is_valid:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid secret variables in kubeconfig: {', '.join(errors)}"
                    )
                processed_kubeconfig = kubeconfig
                await cluster_config.update_kubeconfig(processed_kubeconfig or "")

                # Invalidate cache
                self._invalidate_cache()
                return {"message": f"Cluster {cluster_name} created successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating cluster: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def update_cluster(self, cluster_name: str, cluster_data: Dict) -> Dict:
        """
        Обновить кластер

        Args:
            cluster_name: Имя кластера
            cluster_data: Dict с данными кластера (nodes, kubeconfig)

        Returns:
            Dict с сообщением об успехе

        Raises:
            HTTPException: если валидация не прошла
        """
        nodes = cluster_data["nodes"]
        kubeconfig = cluster_data.get("kubeconfig")

        cluster_config = await get_cluster(cluster_name)

        # Get database session for secret validation
        async with with_db_session() as db:
            # Clear existing nodes
            if cluster_config.config is None:
                cluster_config.config = await cluster_config._load_config()
            cluster_config.config["nodes"] = []

            # Validate secret variables in nodes
            parser = SecretVariableParser(db)
            processed_nodes = []

            for node in nodes:
                processed_node = node.copy()

                # Validate password if present
                if "password" in processed_node and processed_node["password"]:
                    password_text = processed_node["password"]
                    # Validate secret variables
                    is_valid, errors = await parser.validate_variables(password_text)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid secret variables in password: {', '.join(errors)}"
                        )
                    processed_node["password"] = password_text

                # Validate ssh_key if present
                if "ssh_key" in processed_node and processed_node["ssh_key"]:
                    ssh_key_text = processed_node["ssh_key"]
                    # Validate secret variables
                    is_valid, errors = await parser.validate_variables(ssh_key_text)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid secret variables in SSH key: {', '.join(errors)}"
                        )
                    processed_node["ssh_key"] = ssh_key_text

                processed_nodes.append(processed_node)

            # Add processed nodes
            for node in processed_nodes:
                await cluster_config.update_node(node)

            # Validate secret variables in kubeconfig
            processed_kubeconfig = kubeconfig
            if kubeconfig:
                # Validate secret variables
                is_valid, errors = await parser.validate_variables(kubeconfig)
                if not is_valid:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid secret variables in kubeconfig: {', '.join(errors)}"
                    )
                processed_kubeconfig = kubeconfig
                await cluster_config.update_kubeconfig(processed_kubeconfig or "")

            # Invalidate cache
            self._invalidate_cache()
            return {"message": f"Cluster {cluster_name} updated successfully"}

    async def delete_cluster(self, cluster_name: str) -> Dict:
        """
        Удалить кластер

        Args:
            cluster_name: Имя кластера

        Returns:
            Dict с сообщением об успехе

        Raises:
            HTTPException: если кластер не найден
        """
        try:
            await delete_cluster(cluster_name)
            # Invalidate cache
            self._invalidate_cache()
            return {"message": f"Cluster {cluster_name} deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting cluster: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def get_cluster_details(self, cluster_name: str) -> Dict:
        """
        Получить детали кластера

        Args:
            cluster_name: Имя кластера

        Returns:
            Dict с деталями кластера

        Raises:
            HTTPException: если кластер не найден
        """
        cluster_config = await get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        return {
            "name": cluster_name,
            "nodes": await cluster_config.get_nodes(),
            "kubeconfig": await cluster_config.get_kubeconfig(),
        }

    async def get_cluster_nodes(self, cluster_name: str) -> Dict:
        """
        Получить узлы кластера из Kubernetes

        Args:
            cluster_name: Имя кластера

        Returns:
            Dict с информацией об узлах

        Raises:
            HTTPException: если кластер не найден или kubeconfig не настроен
        """
        cluster_config = await get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        kubeconfig = await cluster_config.get_kubeconfig()
        if not kubeconfig:
            raise HTTPException(status_code=400, detail="Kubeconfig not configured for this cluster")

        # Parse secret variables in kubeconfig for K8sClient
        async with with_db_session() as db:
            parser = SecretVariableParser(db)
            processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
            if parse_errors:
                logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
            kubeconfig = processed_kubeconfig

        k8s_client = K8sClient(kubeconfig)
        nodes_result = await asyncio.to_thread(k8s_client.get_nodes)

        if nodes_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=nodes_result.get("error", "Failed to get nodes"))

        return nodes_result

    async def get_cluster_namespaces(self, cluster_name: str) -> Dict:
        """
        Получить пространства имен кластера из Kubernetes

        Args:
            cluster_name: Имя кластера

        Returns:
            Dict с информацией о пространствах имен

        Raises:
            HTTPException: если кластер не найден или kubeconfig не настроен
        """
        cluster_config = await get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        kubeconfig = await cluster_config.get_kubeconfig()
        if not kubeconfig:
            raise HTTPException(status_code=400, detail="Kubeconfig not configured for this cluster")

        # Parse secret variables in kubeconfig for K8sClient
        async with with_db_session() as db:
            parser = SecretVariableParser(db)
            processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
            if parse_errors:
                logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
            kubeconfig = processed_kubeconfig

        k8s_client = K8sClient(kubeconfig)
        namespaces_result = await k8s_client.get_namespaces()

        if namespaces_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=namespaces_result.get("error", "Failed to get namespaces"))

        return namespaces_result

    async def _get_nodes_for_testing(self, cluster_name: str, request_nodes: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Получить список узлов для тестирования с парсингом секретных переменных

        Args:
            cluster_name: Имя кластера
            request_nodes: Опциональный список узлов из запроса

        Returns:
            List[Dict] с обработанными узлами
        """
        # Always get full node data from cluster config to include secrets
        cluster_config = await get_cluster(cluster_name)
        if not cluster_config:
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Get all nodes from cluster config with secrets
        config_nodes = await cluster_config.get_nodes()

        # If request_nodes provided, merge them with config nodes
        if request_nodes:
            # Create a map of config nodes by IP and port for quick lookup
            config_nodes_map = {}
            for node in config_nodes:
                key = f"{node['ip']}:{node['port']}"
                config_nodes_map[key] = node

            # Merge request nodes with config nodes (request nodes override config)
            nodes = []
            for request_node in request_nodes:
                key = f"{request_node['ip']}:{request_node['port']}"
                if key in config_nodes_map:
                    # Merge config node with request node (request takes precedence)
                    merged_node = config_nodes_map[key].copy()
                    merged_node.update(request_node)
                    nodes.append(merged_node)
                else:
                    # Node not in config, use request node as-is
                    nodes.append(request_node)
        else:
            nodes = config_nodes

        # Parse secret variables in nodes
        async with with_db_session() as db:
            parser = SecretVariableParser(db)
            processed_nodes = []

            for node in nodes:
                processed_node = node.copy()

                # Parse password if present
                if "password" in processed_node and processed_node["password"]:
                    password_text = processed_node["password"]
                    # Replace secret variables with decrypted values
                    processed_password, parse_errors = await parser.replace_variables(password_text)
                    if parse_errors:
                        logger.warning(f"Secret parsing errors: {parse_errors}")
                    processed_node["password"] = processed_password

                # Parse ssh_key if present
                if "ssh_key" in processed_node and processed_node["ssh_key"]:
                    ssh_key_text = processed_node["ssh_key"]
                    # Replace secret variables with decrypted values
                    processed_ssh_key, parse_errors = await parser.replace_variables(ssh_key_text)
                    if parse_errors:
                        logger.warning(f"Secret parsing errors: {parse_errors}")
                    processed_node["ssh_key"] = processed_ssh_key

                processed_nodes.append(processed_node)

            return processed_nodes

    def _create_node_test_result(
        self, node: Dict, success: bool, message: str, error_msg: Optional[str] = None
    ) -> Dict:
        """
        Создать стандартизированный результат теста узла

        Args:
            node: Dict с информацией об узле
            success: Успешность теста
            message: Сообщение
            error_msg: Опциональное сообщение об ошибке

        Returns:
            Dict с результатом теста
        """
        node_name = node.get("name", node["ip"])
        node_address = f"{node['ip']}:{node['port']}"

        return {
            "node": node_address,
            "node_name": node_name,
            "success": success,
            "message": error_msg if error_msg else message,
        }

    async def _test_single_node_async(self, node: Dict) -> Dict:
        """
        Тестировать соединение с одним узлом асинхронно

        Args:
            node: Dict с информацией об узле

        Returns:
            Dict с результатом теста
        """
        try:
            success, message = await async_test_node_connection(node)
            return self._create_node_test_result(node, success, message)
        except Exception as e:
            node_name = node.get("name", node["ip"])
            return self._create_node_test_result(node, False, "", f"Test failed for {node_name}: {str(e)}")

    async def test_cluster_nodes(self, cluster_name: str, request_nodes: Optional[List[Dict]] = None) -> Dict:
        """
        Тестировать соединение со всеми узлами кластера

        Args:
            cluster_name: Имя кластера
            request_nodes: Опциональный список узлов из запроса

        Returns:
            Dict с результатами тестирования
        """
        nodes = await self._get_nodes_for_testing(cluster_name, request_nodes)

        # Test nodes asynchronously in parallel with individual timeouts
        async def test_with_timeout(node):
            try:
                result = await asyncio.wait_for(self._test_single_node_async(node), timeout=10.0)
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
                failed_nodes_str = ", ".join(failed_nodes)
                response["error"] = ["Нет соединения с {}".format(failed_nodes_str)]

            return response

        except Exception as e:
            return {
                "results": [],
                "error": f"Test execution error: {str(e)}",
            }

    async def test_cluster_kubeconfig(self, cluster_name: str, request_kubeconfig: Optional[str] = None) -> Dict:
        """
        Тестировать валидность kubeconfig кластера

        Args:
            cluster_name: Имя кластера
            request_kubeconfig: Опциональный kubeconfig из запроса

        Returns:
            Dict с результатом теста
        """
        # If kubeconfig passed in request, use it, otherwise get from core.config
        if request_kubeconfig:
            kubeconfig = request_kubeconfig
        else:
            cluster_config = await get_cluster(cluster_name)
            if not cluster_config:
                raise HTTPException(status_code=404, detail="Cluster not found")
            kubeconfig = await cluster_config.get_kubeconfig()

        if not kubeconfig:
            return {"success": False, "message": "Kubeconfig not configured"}

        # Parse secret variables in kubeconfig
        async with with_db_session() as db:
            parser = SecretVariableParser(db)
            processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
            if parse_errors:
                logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
            kubeconfig = processed_kubeconfig

        k8s_client = K8sClient(kubeconfig)
        success, message = await k8s_client.test_connection()

        return {"success": success, "message": message}

    async def get_nodes_from_kubeconfig(self, kubeconfig: str) -> Dict:
        """
        Получить список узлов из kubeconfig

        Args:
            kubeconfig: Base64 encoded kubeconfig content

        Returns:
            Dict с информацией об узлах

        Raises:
            HTTPException: если kubeconfig невалиден
        """
        if not kubeconfig:
            raise HTTPException(status_code=400, detail="Kubeconfig is required")

        # Parse secret variables in kubeconfig
        async with with_db_session() as db:
            parser = SecretVariableParser(db)
            processed_kubeconfig, parse_errors = await parser.replace_variables(kubeconfig)
            if parse_errors:
                logger.warning(f"Secret parsing errors in kubeconfig: {parse_errors}")
            kubeconfig = processed_kubeconfig

        k8s_client = K8sClient(kubeconfig)
        nodes_result = await asyncio.to_thread(k8s_client.get_nodes)

        if nodes_result.get("status") == "error":
            raise HTTPException(status_code=500, detail=nodes_result.get("error", "Failed to get nodes"))

        return nodes_result
