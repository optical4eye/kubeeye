#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster controller - API endpoints для работы с кластерами
"""

from fastapi import APIRouter, Depends
from typing import Optional

from api.models import ClusterCreate, NodesTestRequest, KubeconfigTestRequest, GetNodesFromKubeconfigRequest
from api.unified_middleware import api_error_handler, validate_cluster_name_decorator
from services.cluster_service import ClusterService
from core.common.unified_validation import validate_cluster_name

router = APIRouter()


def get_cluster_service() -> ClusterService:
    """
    Dependency injection для ClusterService

    Returns:
        Экземпляр ClusterService
    """
    return ClusterService()


@router.get("/dashboard")
@api_error_handler
async def get_dashboard(service: ClusterService = Depends(get_cluster_service)):
    """
    Получить данные для дашборда

    Returns:
        Dict с данными дашборда
    """
    return await service.get_dashboard_data()


@router.get("/clusters")
@api_error_handler
async def get_clusters(service: ClusterService = Depends(get_cluster_service)):
    """
    Получить список кластеров

    Returns:
        Dict со списком кластеров
    """
    return await service.get_clusters_list()


@router.post("/clusters")
@api_error_handler
async def create_cluster(
    cluster: ClusterCreate,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Создать новый кластер

    Args:
        cluster: Данные для создания кластера

    Returns:
        Dict с сообщением об успехе
    """
    return await service.create_cluster(cluster.model_dump())


@router.put("/clusters/{cluster_name}")
@api_error_handler
@validate_cluster_name_decorator
async def update_cluster(
    cluster_name: str,
    cluster: ClusterCreate,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Обновить кластер

    Args:
        cluster_name: Имя кластера
        cluster: Данные для обновления кластера

    Returns:
        Dict с сообщением об успехе
    """
    return await service.update_cluster(cluster_name, cluster.model_dump())


@router.delete("/clusters/{cluster_name}")
@api_error_handler
@validate_cluster_name_decorator
async def remove_cluster(
    cluster_name: str,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Удалить кластер

    Args:
        cluster_name: Имя кластера

    Returns:
        Dict с сообщением об успехе
    """
    return await service.delete_cluster(cluster_name)


@router.get("/clusters/{cluster_name}")
@api_error_handler
@validate_cluster_name_decorator
async def get_cluster_details(
    cluster_name: str,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Получить детали кластера

    Args:
        cluster_name: Имя кластера

    Returns:
        Dict с деталями кластера
    """
    return await service.get_cluster_details(cluster_name)


@router.get("/clusters/{cluster_name}/nodes")
@api_error_handler
@validate_cluster_name_decorator
async def get_cluster_nodes(
    cluster_name: str,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Получить узлы кластера из Kubernetes

    Args:
        cluster_name: Имя кластера

    Returns:
        Dict с информацией об узлах
    """
    return await service.get_cluster_nodes(cluster_name)


@router.get("/clusters/{cluster_name}/namespaces")
@api_error_handler
@validate_cluster_name_decorator
async def get_cluster_namespaces(
    cluster_name: str,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Получить пространства имен кластера из Kubernetes

    Args:
        cluster_name: Имя кластера

    Returns:
        Dict с информацией о пространствах имен
    """
    return await service.get_cluster_namespaces(cluster_name)


@router.post("/clusters/{cluster_name}/test-nodes")
@api_error_handler
@validate_cluster_name_decorator
async def test_cluster_nodes(
    cluster_name: str,
    request: Optional[NodesTestRequest] = None,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Тестировать соединение со всеми узлами кластера

    Args:
        cluster_name: Имя кластера
        request: Опциональный запрос с узлами для тестирования

    Returns:
        Dict с результатами тестирования
    """
    validated_cluster_name = validate_cluster_name(cluster_name)
    request_nodes = request.nodes if request else None
    return await service.test_cluster_nodes(validated_cluster_name, request_nodes)


@router.post("/clusters/{cluster_name}/test-kubeconfig")
@api_error_handler
@validate_cluster_name_decorator
async def test_cluster_kubeconfig(
    cluster_name: str,
    request: Optional[KubeconfigTestRequest] = None,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Тестировать валидность kubeconfig кластера

    Args:
        cluster_name: Имя кластера
        request: Опциональный запрос с kubeconfig для тестирования

    Returns:
        Dict с результатом теста
    """
    validated_cluster_name = validate_cluster_name(cluster_name)
    request_kubeconfig = request.kubeconfig if request else None
    return await service.test_cluster_kubeconfig(validated_cluster_name, request_kubeconfig)


@router.post("/clusters/get-nodes-from-kubeconfig")
@api_error_handler
async def get_nodes_from_kubeconfig(
    request: GetNodesFromKubeconfigRequest,
    service: ClusterService = Depends(get_cluster_service),
):
    """
    Получить список узлов из kubeconfig

    Args:
        request: Запрос с kubeconfig

    Returns:
        Dict с информацией об узлах
    """
    return await service.get_nodes_from_kubeconfig(request.kubeconfig)
