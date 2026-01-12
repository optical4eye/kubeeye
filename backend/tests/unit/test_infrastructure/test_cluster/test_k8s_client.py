#!/usr/bin/env python3
from core.logging import get_logger

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for K8sClient
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from kubernetes.client.rest import ApiException

from infra.cluster.k8s_client import K8sClient

logger = get_logger(__name__)


class TestK8sClient:
    """Test cases for K8sClient"""

    @pytest.fixture
    def mock_kubeconfig(self):
        return "mock-kubeconfig-content"

    @pytest.fixture
    def k8s_client(self, mock_kubeconfig):
        """Create K8sClient instance with mocked initialization"""
        from infra.cluster.k8s_base_client import K8sBaseClient

        with patch.object(K8sBaseClient, "init_client_base", return_value=True), patch(
            "infra.cluster.k8s_client.CoreV1Api"
        ) as mock_core, patch("infra.cluster.k8s_client.AppsV1Api") as mock_apps, patch(
            "infra.cluster.k8s_client.BatchV1Api"
        ) as mock_batch, patch(
            "infra.cluster.k8s_client.NetworkingV1Api"
        ) as mock_networking, patch(
            "infra.cluster.k8s_client.StorageV1Api"
        ) as mock_storage, patch(
            "infra.cluster.k8s_client.RbacAuthorizationV1Api"
        ) as mock_rbac, patch(
            "infra.cluster.k8s_client.CustomObjectsApi"
        ) as mock_custom:
            client = K8sClient(mock_kubeconfig)
            # Manually set attributes that would be set in init_client
            client.core_v1 = mock_core.return_value
            client.apps_v1 = mock_apps.return_value
            client.batch_v1 = mock_batch.return_value
            client.networking_v1 = mock_networking.return_value
            client.storage_v1 = mock_storage.return_value
            client.rbac_v1 = mock_rbac.return_value
            client.custom_objects = mock_custom.return_value
            client.initialized = True
            return client

    def test_init(self, mock_kubeconfig):
        """Test client initialization"""
        with patch.object(K8sClient, "init_client", return_value=True) as mock_init:
            client = K8sClient(mock_kubeconfig)
            assert client.kubeconfig_content == mock_kubeconfig
            mock_init.assert_called_once()

    def test_init_client_success(self, k8s_client):
        """Test successful client initialization"""
        with patch.object(k8s_client, "init_client_base", return_value=True):
            with patch("infra.cluster.k8s_client.CoreV1Api") as mock_core:
                with patch("infra.cluster.k8s_client.AppsV1Api") as mock_apps:
                    with patch("infra.cluster.k8s_client.BatchV1Api") as mock_batch:
                        with patch("infra.cluster.k8s_client.NetworkingV1Api") as mock_networking:
                            with patch("infra.cluster.k8s_client.StorageV1Api") as mock_storage:
                                with patch("infra.cluster.k8s_client.RbacAuthorizationV1Api") as mock_rbac:
                                    with patch("infra.cluster.k8s_client.CustomObjectsApi") as mock_custom:
                                        result = k8s_client.init_client()
                                        assert result is True
                                        assert k8s_client.core_v1 is not None
                                        assert k8s_client.apps_v1 is not None
                                        assert k8s_client.batch_v1 is not None
                                        assert k8s_client.networking_v1 is not None
                                        assert k8s_client.storage_v1 is not None
                                        assert k8s_client.rbac_v1 is not None
                                        assert k8s_client.custom_objects is not None

    def test_init_client_base_failure(self, mock_kubeconfig):
        """Test client initialization failure in base class"""
        with patch.object(K8sClient, "init_client_base", return_value=False):
            client = K8sClient(mock_kubeconfig)
            result = client.init_client()
            assert result is False
            assert client.initialized is False

    def test_init_client_exception(self, k8s_client):
        """Test client initialization with exception"""
        with patch.object(k8s_client, "init_client_base", return_value=True):
            with patch("infra.cluster.k8s_client.CoreV1Api", side_effect=Exception("Init error")):
                result = k8s_client.init_client()
                assert result is False
                assert k8s_client.initialized is False

    def test_get_nodes_not_initialized(self, k8s_client):
        """Test get_nodes when client not initialized"""
        k8s_client.initialized = False
        result = k8s_client.get_nodes()
        assert result == {"status": "error", "error": "Client not initialized"}

    def test_get_nodes_success(self, k8s_client):
        """Test successful get_nodes"""
        # Mock node object
        mock_node = Mock()
        mock_node.metadata.name = "node1"
        mock_node.metadata.creation_timestamp = None
        mock_node.metadata.labels = {"node-role.kubernetes.io/worker": ""}
        mock_node.status.addresses = [
            Mock(type="InternalIP", address="192.168.1.1"),
            Mock(type="ExternalIP", address="203.0.113.1"),
        ]
        mock_node.status.node_info.kubelet_version = "v1.24.0"
        mock_node.status.node_info.os_image = "Ubuntu 20.04"
        mock_node.status.node_info.kernel_version = "5.4.0"
        mock_node.status.node_info.container_runtime_version = "docker://20.10.0"
        mock_node.status.capacity = {"cpu": "4", "memory": "8Gi", "pods": "110"}
        mock_node.status.conditions = [
            Mock(
                type="Ready",
                status="True",
                reason="KubeletReady",
                message="kubelet is posting ready status",
                last_transition_time="2023-01-01T00:00:00Z",
            )
        ]
        mock_node.spec.taints = []

        # Mock API response
        mock_nodes_response = Mock()
        mock_nodes_response.items = [mock_node]

        with patch.object(k8s_client.core_v1, "list_node", return_value=mock_nodes_response):
            result = k8s_client.get_nodes()

        assert result["status"] == "success"
        assert len(result["nodes"]) == 1
        node = result["nodes"][0]
        assert node["name"] == "node1"
        assert node["status"] == "Ready"
        assert node["roles"] == ["worker"]
        assert node["internal_ip"] == "192.168.1.1"
        assert node["external_ip"] == "203.0.113.1"

    def test_get_nodes_api_exception(self, k8s_client):
        """Test get_nodes with API exception"""
        with patch.object(k8s_client.core_v1, "list_node", side_effect=ApiException(reason="API Error")):
            result = k8s_client.get_nodes()
        assert result["status"] == "error"
        assert "API error" in result["error"]

    def test_get_nodes_general_exception(self, k8s_client):
        """Test get_nodes with general exception"""
        with patch.object(k8s_client.core_v1, "list_node", side_effect=Exception("General error")):
            result = k8s_client.get_nodes()
        assert result["status"] == "error"
        assert "Failed to get nodes" in result["error"]

    def test_get_pods_not_initialized(self, k8s_client):
        """Test get_pods when client not initialized"""
        k8s_client.initialized = False
        result = k8s_client.get_pods()
        assert result == {"status": "error", "error": "Client not initialized"}

    def test_get_pods_all_namespaces(self, k8s_client):
        """Test get_pods for all namespaces"""
        mock_pod = Mock()
        mock_pod.metadata.name = "pod1"
        mock_pod.metadata.namespace = "default"
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node1"
        mock_pod.status.pod_ip = "192.168.1.10"
        mock_pod.metadata.creation_timestamp = None
        mock_pod.spec.containers = [Mock(name="container1")]
        mock_pod.status.container_statuses = [Mock(restart_count=1)]

        mock_pods_response = Mock()
        mock_pods_response.items = [mock_pod]

        with patch.object(k8s_client.core_v1, "list_pod_for_all_namespaces", return_value=mock_pods_response):
            result = k8s_client.get_pods()

        assert result["status"] == "success"
        assert len(result["pods"]) == 1
        pod = result["pods"][0]
        assert pod["name"] == "pod1"
        assert pod["namespace"] == "default"
        assert pod["status"] == "Running"

    def test_get_pods_namespace(self, k8s_client):
        """Test get_pods for specific namespace"""
        mock_pod = Mock()
        mock_pod.metadata.name = "pod1"
        mock_pod.metadata.namespace = "test-ns"
        mock_pod.status.phase = "Pending"
        mock_pod.spec.node_name = "node1"
        mock_pod.status.pod_ip = "192.168.1.10"
        mock_pod.metadata.creation_timestamp = None
        mock_pod.spec.containers = [Mock(name="container1")]
        mock_pod.status.container_statuses = [Mock(restart_count=1)]

        mock_pods_response = Mock()
        mock_pods_response.items = [mock_pod]

        k8s_client.core_v1.list_namespaced_pod.return_value = mock_pods_response
        result = k8s_client.get_pods("test-ns")

        assert result["status"] == "success"
        assert len(result["pods"]) == 1

    def test_list_pods_all_namespaces_success(self, k8s_client):
        """Test list_pods_all_namespaces success"""
        mock_pod = Mock()
        mock_pods_response = Mock()
        mock_pods_response.items = [mock_pod]

        with patch.object(k8s_client.core_v1, "list_pod_for_all_namespaces", return_value=mock_pods_response):
            with patch.object(k8s_client, "_convert_k8s_object_to_dict", return_value={"name": "pod1"}):
                result = k8s_client.list_pods_all_namespaces()
        assert result == [{"name": "pod1"}]

    def test_list_pods_all_namespaces_exception(self, k8s_client):
        """Test list_pods_all_namespaces with exception"""
        with patch.object(k8s_client.core_v1, "list_pod_for_all_namespaces", side_effect=Exception("API error")):
            result = k8s_client.list_pods_all_namespaces()
        assert result == []

    def test_list_deployments_all_namespaces_success(self, k8s_client):
        """Test list_deployments_all_namespaces success"""
        mock_deployment = Mock()
        mock_deployments_response = Mock()
        mock_deployments_response.items = [mock_deployment]

        with patch.object(
            k8s_client.apps_v1, "list_deployment_for_all_namespaces", return_value=mock_deployments_response
        ):
            with patch.object(k8s_client, "_convert_k8s_object_to_dict", return_value={"name": "deployment1"}):
                result = k8s_client.list_deployments_all_namespaces()
        assert result == [{"name": "deployment1"}]

    def test_list_resources_pods(self, k8s_client):
        """Test list_resources for pods"""
        mock_pod = Mock()
        mock_pods_response = Mock()
        mock_pods_response.items = [mock_pod]

        with patch.object(k8s_client.core_v1, "list_pod_for_all_namespaces", return_value=mock_pods_response):
            with patch.object(k8s_client, "_convert_k8s_object_to_dict", return_value={"name": "pod1"}):
                result = k8s_client.list_resources("pods")
        assert result == [{"name": "pod1"}]

    def test_list_resources_unknown_type(self, k8s_client):
        """Test list_resources for unknown resource type"""
        result = k8s_client.list_resources("unknown")
        assert result == []

    def test_list_resources_crd_fallback(self, k8s_client):
        """Test list_resources CRD fallback"""
        with patch.object(k8s_client, "_list_custom_resources", return_value=[{"name": "crd1"}]):
            result = k8s_client.list_resources("virtualservices")
        assert result == [{"name": "crd1"}]

    def test_list_cluster_resources_nodes(self, k8s_client):
        """Test list_cluster_resources for nodes"""
        mock_node = Mock()
        mock_nodes_response = Mock()
        mock_nodes_response.items = [mock_node]

        with patch.object(k8s_client.core_v1, "list_node", return_value=mock_nodes_response):
            with patch.object(k8s_client, "_convert_k8s_object_to_dict", return_value={"name": "node1"}):
                result = k8s_client.list_cluster_resources("nodes")
        assert result == [{"name": "node1"}]

    def test_list_namespaces_success(self, k8s_client):
        """Test list_namespaces success"""
        mock_ns = Mock()
        mock_namespaces_response = Mock()
        mock_namespaces_response.items = [mock_ns]

        with patch.object(k8s_client.core_v1, "list_namespace", return_value=mock_namespaces_response):
            with patch.object(k8s_client, "_convert_k8s_object_to_dict", return_value={"name": "default"}):
                result = k8s_client.list_namespaces()
        assert result == [{"name": "default"}]

    def test_convert_k8s_object_to_dict_with_to_dict(self, k8s_client):
        """Test _convert_k8s_object_to_dict with to_dict method"""
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"name": "test"}
        result = k8s_client._convert_k8s_object_to_dict(mock_obj)
        assert result == {"name": "test"}

    def test_convert_k8s_object_to_dict_serialization(self, k8s_client):
        """Test _convert_k8s_object_to_dict with serialization"""
        mock_obj = Mock()
        mock_obj.to_dict = None  # No to_dict method
        mock_obj.metadata = Mock()
        mock_obj.metadata.name = "test"
        mock_obj.metadata.namespace = None
        mock_api_client = Mock()
        mock_api_client.sanitize_for_serialization.return_value = {"metadata": {"name": "test", "namespace": None}}

        with patch("infra.cluster.k8s_client.ApiClient", return_value=mock_api_client):
            result = k8s_client._convert_k8s_object_to_dict(mock_obj)
        assert result == {"metadata": {"name": "test", "namespace": None}}

    def test_get_custom_resources_namespaced(self, k8s_client):
        """Test get_custom_resources for namespaced resources"""
        mock_response = {"items": [{"metadata": {"name": "cr1"}}]}

        with patch.object(k8s_client.custom_objects, "list_namespaced_custom_object", return_value=mock_response):
            with patch.object(k8s_client, "_convert_dict_to_k8s_format", return_value={"name": "cr1"}):
                result = k8s_client.get_custom_resources("group", "v1", "plural", "namespace")
        assert result == [{"name": "cr1"}]

    def test_get_custom_resources_cluster(self, k8s_client):
        """Test get_custom_resources for cluster resources"""
        mock_response = {"items": [{"metadata": {"name": "cr1"}}]}

        with patch.object(k8s_client.custom_objects, "list_cluster_custom_object", return_value=mock_response):
            with patch.object(k8s_client, "_convert_dict_to_k8s_format", return_value={"name": "cr1"}):
                result = k8s_client.get_custom_resources("group", "v1", "plural")
        assert result == [{"name": "cr1"}]

    def test_list_all_custom_resource_definitions_success(self, k8s_client):
        """Test list_all_custom_resource_definitions success"""
        mock_crd = Mock()
        mock_crd.metadata.name = "crd1.example.com"
        mock_crd.spec.group = "example.com"
        mock_crd.spec.versions = [Mock(name="v1")]
        mock_crd.spec.scope = "Namespaced"
        mock_crd.spec.names.kind = "Example"
        mock_crd.spec.names.plural = "examples"

        mock_crds_response = Mock()
        mock_crds_response.items = [mock_crd]

        with patch("infra.cluster.k8s_client.ApiextensionsV1Api") as mock_api_ext:
            mock_api_ext.return_value.list_custom_resource_definition.return_value = mock_crds_response
            result = k8s_client.list_all_custom_resource_definitions()

        assert len(result) == 1
        assert result[0]["name"] == "crd1.example.com"
        assert result[0]["group"] == "example.com"

    def test_format_age_seconds(self, k8s_client):
        """Test _format_age formatting"""
        assert k8s_client._format_age(30) == "30s"
        assert k8s_client._format_age(90) == "1m"
        assert k8s_client._format_age(3660) == "1h"
        assert k8s_client._format_age(86401) == "1d"

    def test_get_node_status_ready(self, k8s_client):
        """Test _get_node_status when ready"""
        mock_condition = Mock(type="Ready", status="True")
        mock_node = Mock(status=Mock(conditions=[mock_condition]))
        assert k8s_client._get_node_status(mock_node) == "Ready"

    def test_get_node_status_not_ready(self, k8s_client):
        """Test _get_node_status when not ready"""
        mock_condition = Mock(type="Ready", status="False")
        mock_node = Mock(status=Mock(conditions=[mock_condition]))
        assert k8s_client._get_node_status(mock_node) == "NotReady"

    def test_get_node_status_unknown(self, k8s_client):
        """Test _get_node_status unknown"""
        mock_node = Mock(status=Mock(conditions=[]))
        assert k8s_client._get_node_status(mock_node) == "Unknown"

    def test_get_node_roles_with_labels(self, k8s_client):
        """Test _get_node_roles with role labels"""
        mock_node = Mock(
            metadata=Mock(labels={"node-role.kubernetes.io/master": "", "node-role.kubernetes.io/worker": ""})
        )
        roles = k8s_client._get_node_roles(mock_node)
        assert "master" in roles
        assert "worker" in roles

    def test_get_node_roles_no_labels(self, k8s_client):
        """Test _get_node_roles without role labels"""
        mock_node = Mock(metadata=Mock(labels={}))
        roles = k8s_client._get_node_roles(mock_node)
        assert roles == ["worker"]
