#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core.logging import get_logger

"""
Kubernetes client tool for interacting with Kubernetes clusters
"""

# Standard library imports
import asyncio
import datetime
from typing import Dict, List, Tuple

# Third-party imports
from kubernetes.client import (
    CoreV1Api,
    AppsV1Api,
    BatchV1Api,
    NetworkingV1Api,
    StorageV1Api,
    RbacAuthorizationV1Api,
    CustomObjectsApi,
    ApiClient,
)
from kubernetes.client.rest import ApiException
from kubernetes.client import ApiextensionsV1Api

# Local imports
from .k8s_base_client import K8sBaseClient
from core.common.cache_utils import cached

logger = get_logger(__name__)


class K8sClient(K8sBaseClient):
    """Kubernetes client class"""

    def __init__(self, kubeconfig_content: str = None):
        """
        Initialize Kubernetes client

        Args:
            kubeconfig_content: kubeconfig file content
        """
        super().__init__(kubeconfig_content)
        self.init_client()

    def init_client(self) -> bool:
        """
        Initialize Kubernetes client configuration

        Returns:
            Returns True on success, False on failure
        """
        try:
            logger.info("Starting Kubernetes client initialization")
            # Use base class common initialization logic
            if not self.init_client_base():
                logger.error("Base client initialization failed")
                return False

            logger.info("Initializing specific API clients")
            # Initialize specific API clients
            self.core_v1 = CoreV1Api()
            self.apps_v1 = AppsV1Api()
            self.batch_v1 = BatchV1Api()
            self.networking_v1 = NetworkingV1Api()
            self.storage_v1 = StorageV1Api()
            self.rbac_v1 = RbacAuthorizationV1Api()
            self.custom_objects = CustomObjectsApi()

            logger.info("Kubernetes client API initialization successful")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self.initialized = False
            return False

    def _configure_no_verify_ssl(self):
        """Moved to base class K8sBaseClient"""
        return super()._configure_no_verify_ssl()

    def __del__(self):
        """Moved to base class K8sBaseClient"""
        super().__del__()

    async def test_connection(self) -> Tuple[bool, str]:
        """Moved to base class K8sBaseClient"""
        return await super().test_connection()

    @cached("k8s_nodes", ttl=60)
    def get_nodes(self) -> Dict:
        """
        Get cluster node list (cached for 60 seconds)

        Returns:
            Node information dictionary
        """
        logger.info("Starting get_nodes()")
        if not self.initialized:
            logger.error("Client not initialized")
            return {"status": "error", "error": "Client not initialized"}

        try:
            logger.info("Calling core_v1.list_node()")
            logger.debug("Executing Kubernetes API call: list_node")
            nodes = self.core_v1.list_node()
            logger.info(f"Retrieved {len(nodes.items)} nodes")
            logger.debug(f"Node items sample: {nodes.items[0].metadata.name if nodes.items else 'None'}")
            result = []

            for node in nodes.items:
                logger.debug(f"Processing node: {node.metadata.name}")
                # Calculate AGE
                creation_time = node.metadata.creation_timestamp
                if creation_time:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    age_seconds = (now - creation_time).total_seconds()
                    age = self._format_age(age_seconds)
                else:
                    age = "N/A"

                # Get IP addresses
                internal_ip = "N/A"
                external_ip = "N/A"
                if node.status.addresses:
                    for addr in node.status.addresses:
                        if addr.type == "InternalIP":
                            internal_ip = addr.address
                        elif addr.type == "ExternalIP":
                            external_ip = addr.address

                node_info = {
                    "name": node.metadata.name,
                    "status": self._get_node_status(node),
                    "roles": self._get_node_roles(node),
                    "age": age,
                    "version": node.status.node_info.kubelet_version,
                    "internal_ip": internal_ip,
                    "external_ip": external_ip,
                    "os_image": node.status.node_info.os_image,
                    "kernel_version": node.status.node_info.kernel_version,
                    "container_runtime": node.status.node_info.container_runtime_version,
                    "cpu": node.status.capacity.get("cpu", "N/A"),
                    "memory": node.status.capacity.get("memory", "N/A"),
                    "pods": node.status.capacity.get("pods", "N/A"),
                    "conditions": self._get_node_conditions(node),
                    "taints": self._get_node_taints(node),
                    "creation_timestamp": node.metadata.creation_timestamp,
                    "labels": node.metadata.labels,
                }
                result.append(node_info)

            logger.info(f"Successfully processed {len(result)} nodes")
            return {"status": "success", "nodes": result}
        except ApiException as e:
            logger.error(f"API error in get_nodes: {e.reason}")
            return {"status": "error", "error": f"API error: {e.reason}"}
        except Exception as e:
            logger.error(f"Exception in get_nodes: {str(e)}")
            return {"status": "error", "error": f"Failed to get nodes: {str(e)}"}

    @cached("k8s_pods", ttl=30)
    def get_pods(self, namespace: str = None) -> Dict:
        """
        Get Pod list (cached for 30 seconds)

        Args:
            namespace: namespace

        Returns:
            Pod list dictionary
        """
        if not self.initialized:
            return {"status": "error", "error": "Client not initialized"}

        try:
            if namespace:
                pods = self.core_v1.list_namespaced_pod(namespace)
            else:
                pods = self.core_v1.list_pod_for_all_namespaces()

            result = []

            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "creation_timestamp": pod.metadata.creation_timestamp,
                    "containers": [c.name for c in pod.spec.containers],
                    "restart_count": (
                        sum(c.restart_count for c in pod.status.container_statuses if c.restart_count)
                        if pod.status.container_statuses
                        else 0
                    ),
                }
                result.append(pod_info)

            return {"status": "success", "pods": result}
        except ApiException as e:
            return {"status": "error", "error": f"API error: {e.reason}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to get Pods: {str(e)}"}

    @cached("k8s_pods_all", ttl=60)
    def list_pods_all_namespaces(self):
        """Get Pod list for all namespaces (cached for 60 seconds)"""
        try:
            pods = self.core_v1.list_pod_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(pod) for pod in pods.items]
        except Exception as e:
            logger.error(f"Failed to get all Pods: {e}")
            return []

    @cached("k8s_deployments_all", ttl=60)
    def list_deployments_all_namespaces(self):
        """Get Deployment list for all namespaces (cached for 60 seconds)"""
        try:
            deployments = self.apps_v1.list_deployment_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(d) for d in deployments.items]
        except Exception as e:
            logger.error(f"Failed to get all Deployments: {e}")
            return []

    @cached("k8s_statefulsets_all", ttl=60)
    def list_statefulsets_all_namespaces(self):
        """Get StatefulSet list for all namespaces (cached for 60 seconds)"""
        try:
            statefulsets = self.apps_v1.list_stateful_set_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(s) for s in statefulsets.items]
        except Exception as e:
            logger.error(f"Failed to get all StatefulSets: {e}")
            return []

    @cached("k8s_daemonsets_all", ttl=60)
    def list_daemonsets_all_namespaces(self):
        """Get DaemonSet list for all namespaces (cached for 60 seconds)"""
        try:
            daemonsets = self.apps_v1.list_daemon_set_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(d) for d in daemonsets.items]
        except Exception as e:
            logger.error(f"Failed to get all DaemonSets: {e}")
            return []

    @cached("k8s_services_all", ttl=60)
    def list_services_all_namespaces(self):
        """Get Service list for all namespaces (cached for 60 seconds)"""
        try:
            services = self.core_v1.list_service_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(s) for s in services.items]
        except Exception as e:
            logger.error(f"Failed to get all Services: {e}")
            return []

    @cached("k8s_ingresses_all", ttl=60)
    def list_ingresses_all_namespaces(self):
        """Get Ingress list for all namespaces (cached for 60 seconds)"""
        try:
            ingresses = self.networking_v1.list_ingress_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(i) for i in ingresses.items]
        except Exception as e:
            logger.error(f"Failed to get all Ingresses: {e}")
            return []

    @cached("k8s_serviceaccounts_all", ttl=60)
    def list_serviceaccounts_all_namespaces(self):
        """Get ServiceAccount list for all namespaces (cached for 60 seconds)"""
        try:
            serviceaccounts = self.core_v1.list_service_account_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(sa) for sa in serviceaccounts.items]
        except Exception as e:
            logger.error(f"Failed to get all ServiceAccounts: {e}")
            return []

    @cached("k8s_configmaps_all", ttl=60)
    def list_configmaps_all_namespaces(self):
        """Get ConfigMap list for all namespaces (cached for 60 seconds)"""
        try:
            configmaps = self.core_v1.list_config_map_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(cm) for cm in configmaps.items]
        except Exception as e:
            logger.error(f"Failed to get all ConfigMaps: {e}")
            return []

    @cached("k8s_secrets_all", ttl=60)
    def list_secrets_all_namespaces(self):
        """Get Secret list for all namespaces (cached for 60 seconds)"""
        try:
            secrets = self.core_v1.list_secret_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(s) for s in secrets.items]
        except Exception as e:
            logger.error(f"Failed to get all Secrets: {e}")
            return []

    @cached("k8s_pvcs_all", ttl=60)
    def list_persistent_volume_claims_all_namespaces(self):
        """Get PVC list for all namespaces (cached for 60 seconds)"""
        try:
            pvcs = self.core_v1.list_persistent_volume_claim_for_all_namespaces()
            return [self._convert_k8s_object_to_dict(pvc) for pvc in pvcs.items]
        except Exception as e:
            logger.error(f"Failed to get all PVCs: {e}")
            return []

    def list_resources(self, resource_type: str):
        """
        Get resource list of specified type for all namespaces - enhanced version, supports more resource types

        Args:
            resource_type: resource type, such as 'pods', 'deployments', 'services', etc.

        Returns:
            resource object list
        """
        try:
            if resource_type == "pods":
                items = self.core_v1.list_pod_for_all_namespaces().items
            elif resource_type == "deployments":
                items = self.apps_v1.list_deployment_for_all_namespaces().items
            elif resource_type == "services":
                items = self.core_v1.list_service_for_all_namespaces().items
            elif resource_type == "statefulsets":
                items = self.apps_v1.list_stateful_set_for_all_namespaces().items
            elif resource_type == "daemonsets":
                items = self.apps_v1.list_daemon_set_for_all_namespaces().items
            elif resource_type == "replicasets":
                items = self.apps_v1.list_replica_set_for_all_namespaces().items
            elif resource_type == "configmaps":
                items = self.core_v1.list_config_map_for_all_namespaces().items
            elif resource_type == "secrets":
                items = self.core_v1.list_secret_for_all_namespaces().items
            elif resource_type == "persistentvolumeclaims":
                items = self.core_v1.list_persistent_volume_claim_for_all_namespaces().items
            elif resource_type == "serviceaccounts":
                items = self.core_v1.list_service_account_for_all_namespaces().items
            elif resource_type == "networkpolicies":
                items = self.networking_v1.list_network_policy_for_all_namespaces().items
            elif resource_type == "roles":
                items = self.rbac_v1.list_role_for_all_namespaces().items
            elif resource_type == "rolebindings":
                items = self.rbac_v1.list_role_binding_for_all_namespaces().items
            elif resource_type == "ingresses":
                items = self.networking_v1.list_ingress_for_all_namespaces().items
            else:
                # Try to handle as CRD resource
                items = self._list_custom_resources(resource_type)
                if items is None:
                    logger.warning(f"Unsupported resource type: {resource_type}")
                    return []

            return [self._convert_k8s_object_to_dict(item) for item in items]
        except Exception as e:
            logger.error(f"Failed to get resource {resource_type}: {e}")
            return []

    def list_cluster_resources(self, resource_type: str):
        """
        Get cluster-level resource list - enhanced version, supports more resource types

        Args:
            resource_type: resource type, such as 'nodes', 'persistentvolumes', etc.

        Returns:
            resource object list
        """
        try:
            if resource_type == "nodes":
                items = self.core_v1.list_node().items
            elif resource_type == "persistentvolumes":
                items = self.core_v1.list_persistent_volume().items
            elif resource_type == "clusterroles":
                items = self.rbac_v1.list_cluster_role().items
            elif resource_type == "clusterrolebindings":
                items = self.rbac_v1.list_cluster_role_binding().items
            elif resource_type == "storageclasses":
                items = self.storage_v1.list_storage_class().items
            else:
                # Try to handle as CRD cluster resource
                items = self._list_custom_cluster_resources(resource_type)
                if items is None:
                    logger.warning(f"Unsupported cluster resource type: {resource_type}")
                    return []

            return [self._convert_k8s_object_to_dict(item) for item in items]
        except Exception as e:
            logger.error(f"Failed to get cluster resource {resource_type}: {e}")
            return []

    @cached("k8s_namespaces", ttl=60)
    def list_namespaces(self):
        """Get all namespace list (cached for 60 seconds)"""
        try:
            namespaces = self.core_v1.list_namespace()
            return [self._convert_k8s_object_to_dict(ns) for ns in namespaces.items]
        except Exception as e:
            logger.error(f"Failed to get all namespaces: {e}")
            return []

    @cached("k8s_namespaces_async", ttl=60)
    async def get_namespaces(self) -> Dict:
        """
        Get all namespaces asynchronously (cached for 60 seconds)

        Returns:
            Dictionary with namespace information
        """
        logger.info("Starting get_namespaces()")
        if not self.initialized:
            logger.error("Client not initialized")
            return {"status": "error", "error": "Client not initialized"}

        try:
            logger.info("Calling core_v1.list_namespace() asynchronously")
            namespaces = await asyncio.to_thread(self.core_v1.list_namespace)
            logger.info(f"Retrieved {len(namespaces.items)} namespaces")

            result = []
            for ns in namespaces.items:
                ns_info = {
                    "name": ns.metadata.name,
                    "status": ns.status.phase,
                    "creation_timestamp": ns.metadata.creation_timestamp,
                    "labels": ns.metadata.labels or {},
                }
                result.append(ns_info)

            logger.info(f"Successfully processed {len(result)} namespaces")
            return {"status": "success", "namespaces": result}
        except ApiException as e:
            logger.error(f"API error in get_namespaces: {e.reason}")
            return {"status": "error", "error": f"API error: {e.reason}"}
        except Exception as e:
            logger.error(f"Exception in get_namespaces: {str(e)}")
            return {"status": "error", "error": f"Failed to get namespaces: {str(e)}"}

    def get_custom_resources(self, group: str, version: str, plural: str, namespace: str = None) -> List[Dict]:
        """
        Get custom resource (CRD) list

        Args:
            group: API group, such as 'networking.istio.io'
            version: API version, such as 'v1beta1'
            plural: resource plural name, such as 'virtualservices'
            namespace: namespace, if None then get cluster-level resources

        Returns:
            CRD resource object list
        """
        try:
            if namespace:
                # Get namespace-level CRD resources
                response = self.custom_objects.list_namespaced_custom_object(
                    group=group, version=version, namespace=namespace, plural=plural
                )
            else:
                # Get CRD resources for all namespaces
                response = self.custom_objects.list_cluster_custom_object(group=group, version=version, plural=plural)

            items = response.get("items", [])
            return [self._convert_dict_to_k8s_format(item) for item in items]

        except Exception as e:
            logger.debug(f"Failed to get CRD resource {group}/{version}/{plural}: {str(e)}")
            return []

    def _list_custom_resources(self, resource_type: str) -> List:
        """
        Try to list custom resources

        Args:
            resource_type: resource type

        Returns:
            resource list or None (if not supported)
        """
        # Common CRD resource mappings
        crd_mappings = {
            "virtualservices": ("networking.istio.io", "v1beta1"),
            "destinationrules": ("networking.istio.io", "v1beta1"),
            "gateways": ("networking.istio.io", "v1beta1"),
            "serviceentries": ("networking.istio.io", "v1beta1"),
            "certificates": ("cert-manager.io", "v1"),
            "certificaterequests": ("cert-manager.io", "v1"),
            "issuers": ("cert-manager.io", "v1"),
        }

        if resource_type in crd_mappings:
            group, version = crd_mappings[resource_type]
            try:
                response = self.custom_objects.list_cluster_custom_object(
                    group=group, version=version, plural=resource_type
                )
                return [self._convert_dict_to_k8s_format(item) for item in response.get("items", [])]
            except Exception as e:
                logger.debug(f"Failed to get CRD resource {resource_type}: {str(e)}")
                return []

        return None

    def _list_custom_cluster_resources(self, resource_type: str) -> List:
        """
        Try to list cluster-level custom resources

        Args:
            resource_type: resource type

        Returns:
            resource list or None (if not supported)
        """
        # Cluster-level CRD resource mappings
        cluster_crd_mappings = {
            "clusterissuers": ("cert-manager.io", "v1"),
            "clusterpolicies": ("kyverno.io", "v1"),
            "customresourcedefinitions": ("apiextensions.k8s.io", "v1"),
        }

        if resource_type in cluster_crd_mappings:
            group, version = cluster_crd_mappings[resource_type]
            try:
                response = self.custom_objects.list_cluster_custom_object(
                    group=group, version=version, plural=resource_type
                )
                return [self._convert_dict_to_k8s_format(item) for item in response.get("items", [])]
            except Exception as e:
                logger.debug(f"Failed to get cluster-level CRD resource {resource_type}: {str(e)}")
                return []

        return None

    def _convert_dict_to_k8s_format(self, item: Dict) -> Dict:
        """
        Convert dictionary format CRD resource to standard K8s format

        Args:
            item: CRD resource dictionary

        Returns:
            standard format resource dictionary
        """
        # CRD resources are already in dictionary format, just ensure format consistency
        return item

    @cached("k8s_crds", ttl=120)
    def list_all_custom_resource_definitions(self) -> List[Dict]:
        """
        Get all CRD definitions in cluster (cached for 120 seconds)

        Returns:
            CRD definition list
        """
        try:
            # Get all CRDs in cluster
            extensions_v1 = ApiextensionsV1Api()
            crds = extensions_v1.list_custom_resource_definition()

            crd_list = []
            for crd in crds.items:
                crd_info = {
                    "name": crd.metadata.name,
                    "group": crd.spec.group,
                    "versions": [v.name for v in crd.spec.versions],
                    "scope": crd.spec.scope,  # Cluster or Namespaced
                    "kind": crd.spec.names.kind,
                    "plural": crd.spec.names.plural,
                }
                crd_list.append(crd_info)

            return crd_list
        except Exception as e:
            logger.debug(f"Failed to get CRD list: {str(e)}")
            return []

    def get_custom_resource_by_crd(self, crd_info: Dict, namespace: str = None) -> List[Dict]:
        """
        Get custom resources based on CRD definition

        Args:
            crd_info: CRD definition information
            namespace: namespace (if it's a namespaced resource)

        Returns:
            custom resource list
        """
        try:
            group = crd_info["group"]
            # Use latest version
            version = crd_info["versions"][0] if crd_info["versions"] else "v1"
            plural = crd_info["plural"]
            scope = crd_info.get("scope", "Namespaced")

            if scope == "Namespaced" and namespace:
                response = self.custom_objects.list_namespaced_custom_object(
                    group=group, version=version, namespace=namespace, plural=plural
                )
            elif scope == "Cluster":
                response = self.custom_objects.list_cluster_custom_object(group=group, version=version, plural=plural)
            else:
                # Get resources for all namespaces
                response = self.custom_objects.list_cluster_custom_object(group=group, version=version, plural=plural)

            items = response.get("items", [])
            return [self._convert_dict_to_k8s_format(item) for item in items]

        except Exception as e:
            logger.debug(f"Failed to get CRD resource: {str(e)}")
            return []

    def discover_and_list_all_crd_resources(self) -> Dict[str, List[Dict]]:
        """
        Discover and list all CRD resources

        Returns:
            CRD resource dictionary grouped by type
        """
        crd_resources = {}

        # Get all CRD definitions
        crds = self.list_all_custom_resource_definitions()

        for crd in crds:
            try:
                resource_key = f"{crd['plural']}.{crd['group']}"
                crd_resources[resource_key] = self.get_custom_resource_by_crd(crd)

                # If it's a namespaced resource, also get resources for each namespace
                if crd.get("scope") == "Namespaced":
                    namespaces = self.list_namespaces()
                    all_resources = []
                    for ns in namespaces:
                        ns_name = ns.get("metadata", {}).get("name", "")
                        if ns_name:
                            ns_resources = self.get_custom_resource_by_crd(crd, ns_name)
                            all_resources.extend(ns_resources)
                    crd_resources[resource_key] = all_resources

            except Exception as e:
                logger.debug(f"Failed to get CRD resource {crd['plural']}: {str(e)}")
                continue

        return crd_resources
