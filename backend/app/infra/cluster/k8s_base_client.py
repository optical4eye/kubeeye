#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from core.logging import get_logger

"""
Base Kubernetes client - providing common initialization and configuration logic
Reducing code duplication between k8s_client.py and k8s_dynamic_client.py
"""

import tempfile
import os
import datetime
from typing import Tuple, Dict, List, Any, Optional, Union
from abc import ABC

# Try to import kubernetes, but handle gracefully if not available
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    from kubernetes.client import ApiClient

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None
    ApiException = Exception
    ApiClient = None

logger = get_logger(__name__)


class K8sBaseClient(ABC):
    """Base Kubernetes client providing common initialization and configuration functionality"""

    def __init__(self, kubeconfig_content: Optional[str] = None):
        """
        Initialize the base client

        Args:
            kubeconfig_content: Content of the kubeconfig file
        """
        self.kubeconfig_content = kubeconfig_content
        self.temp_config = None
        self.initialized = False
        self._cluster_name = None
        self._api_clients = {}
        self._resource_cache = {}

    def init_client_base(self) -> bool:
        """
        Common client initialization logic

        Returns:
            Returns True on success, False on failure
        """
        if not KUBERNETES_AVAILABLE:
            logger.error("Kubernetes library not available")
            self.initialized = False
            return False

        try:
            if self.kubeconfig_content:
                import yaml

                if isinstance(self.kubeconfig_content, dict):
                    kubeconfig_dict = self.kubeconfig_content
                elif isinstance(self.kubeconfig_content, str):
                    try:
                        kubeconfig_dict = yaml.safe_load(self.kubeconfig_content)
                    except yaml.YAMLError as e:
                        logger.error(f"Invalid kubeconfig YAML: {e}")
                        self.initialized = False
                        return False
                else:
                    raise ValueError(f"kubeconfig_content must be str or dict, got {type(self.kubeconfig_content)}")

                # Load from dict
                config.load_kube_config_from_dict(kubeconfig_dict)
            else:
                # Try to load configuration using default method
                config.load_kube_config()

            # Configure SSL certificate verification
            client.Configuration.set_default(self._configure_no_verify_ssl())

            self.initialized = True
            logger.info("Base Kubernetes client initialization successful")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize base Kubernetes client: {e}")
            self.initialized = False
            return False

    def _configure_no_verify_ssl(self):
        """
        Configure Kubernetes client to skip SSL certificate verification, for environments with self-signed certificates

        Returns:
            Configured client configuration
        """
        if not KUBERNETES_AVAILABLE:
            return None

        # Get current client configuration
        configuration = client.Configuration.get_default_copy()

        # Disable SSL certificate verification
        configuration.verify_ssl = False
        configuration.ssl_ca_cert = None

        # Set warning
        logger.warning("SSL certificate verification disabled, this may pose a security threat")

        return configuration

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Kubernetes cluster

        Returns:
            (Whether successful, Message)
        """
        if not KUBERNETES_AVAILABLE:
            return False, "Kubernetes library not available"

        try:
            if not self.initialized:
                return False, "Client not initialized"

            # Try to get cluster version information
            version_api = client.VersionApi()
            version = version_api.get_code().git_version
            return True, f"Connection successful, cluster version: {version}"

        except ApiException as e:
            logger.error(f"Connection test failed: {e}")
            return False, f"API error: {e.reason}"
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"

    async def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get basic cluster information

        Returns:
            Dict containing cluster info like version, nodes count, etc.
        """
        try:
            if not self.initialized:
                return {"error": "Client not initialized"}

            version_api = client.VersionApi()
            version_info = version_api.get_code()

            core_v1 = client.CoreV1Api()
            nodes = core_v1.list_node()

            return {
                "version": version_info.git_version,
                "major": version_info.major,
                "minor": version_info.minor,
                "platform": version_info.platform,
                "nodes_count": len(nodes.items),
                "build_date": version_info.build_date,
                "compiler": version_info.compiler,
                "git_commit": version_info.git_commit,
                "git_tree_state": version_info.git_tree_state,
                "go_version": version_info.go_version,
            }
        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}

    def is_connected(self) -> bool:
        """
        Check if client is connected to cluster

        Returns:
            bool: True if connected, False otherwise
        """
        return self.initialized

    def get_cluster_name(self) -> str:
        """
        Get cluster name or identifier

        Returns:
            str: Cluster name
        """
        if self._cluster_name:
            return self._cluster_name

        # Try to extract cluster name from kubeconfig
        if self.kubeconfig_content:
            try:
                import yaml

                kubeconfig = yaml.safe_load(self.kubeconfig_content)
                contexts = kubeconfig.get("contexts", [])
                if contexts:
                    current_context = kubeconfig.get("current-context")
                    if current_context:
                        for ctx in contexts:
                            if ctx.get("name") == current_context:
                                self._cluster_name = ctx.get("name", "unknown")
                                return self._cluster_name
                    elif contexts:
                        self._cluster_name = contexts[0].get("name", "unknown")
                        return self._cluster_name
            except Exception:
                pass

        self._cluster_name = "unknown"
        return self._cluster_name

    def get_api_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available API resources

        Returns:
            Dict mapping API versions to list of resources
        """
        if not KUBERNETES_AVAILABLE:
            return {"error": "Kubernetes library not available"}

        try:
            if not self.initialized:
                return {"error": "Client not initialized"}

            discovery_api = client.DiscoveryApi()
            api_resources = discovery_api.get_server_group_api_resources()

            result = {}
            for api_group in api_resources:
                group_version = api_group.group_version
                resources = []

                for resource in api_group.resources:
                    resources.append(
                        {
                            "name": resource.name,
                            "singular_name": resource.singular_name,
                            "namespaced": resource.namespaced,
                            "kind": resource.kind,
                            "verbs": resource.verbs,
                        }
                    )

                result[group_version] = resources

            return result
        except Exception as e:
            logger.error(f"Failed to get API resources: {e}")
            return {"error": str(e)}

    def _get_api_client(self, api_class):
        """
        Get or create API client instance with caching

        Args:
            api_class: Kubernetes API class

        Returns:
            API client instance
        """
        if not KUBERNETES_AVAILABLE:
            raise ImportError("Kubernetes library not available")

        class_name = api_class.__name__
        if class_name not in self._api_clients:
            self._api_clients[class_name] = api_class()
        return self._api_clients[class_name]

    def _convert_datetime_in_dict(self, data: Any) -> None:
        """
        Recursively convert datetime objects in dictionary to strings

        Args:
            data: dictionary or list to convert
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, datetime.datetime):
                    data[key] = value.isoformat()
                elif isinstance(value, datetime.date):
                    data[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    self._convert_datetime_in_dict(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._convert_datetime_in_dict(item)

    def _convert_k8s_object_to_dict(self, obj) -> Dict:
        """
        Convert Kubernetes object to dictionary format

        Args:
            obj: Kubernetes object

        Returns:
            Dictionary representation of the object
        """
        try:
            # Use to_dict() method if object supports it
            if hasattr(obj, "to_dict"):
                result = obj.to_dict()
            else:
                # Use kubernetes client serialization method to ensure datetime objects are handled
                if ApiClient:
                    json_str = ApiClient().sanitize_for_serialization(obj)
                else:
                    # Fallback conversion
                    if hasattr(obj, "__dict__"):
                        json_str = dict(obj.__dict__)
                    else:
                        json_str = dict(obj)

                # Ensure all datetime are converted to strings
                if isinstance(json_str, dict):
                    self._convert_datetime_in_dict(json_str)

                return json_str if isinstance(json_str, dict) else {}

            # Filter out callable objects to avoid serialization issues
            def filter_callable(data):
                if isinstance(data, dict):
                    return {k: filter_callable(v) for k, v in data.items() if not callable(v)}
                elif isinstance(data, list):
                    return [filter_callable(item) for item in data if not callable(item)]
                else:
                    return data if not callable(data) else None

            result = filter_callable(result)
            return result

        except Exception as e:
            logger.warning(f"Failed to convert Kubernetes object: {e}")
            # Return minimal object
            if hasattr(obj, "metadata") and hasattr(obj.metadata, "name"):
                return {
                    "metadata": {
                        "name": obj.metadata.name,
                        "namespace": (obj.metadata.namespace if hasattr(obj.metadata, "namespace") else None),
                    }
                }
            return {}

    def _format_age(self, seconds: float) -> str:
        """
        Format age in seconds to human readable format

        Args:
            seconds: Age in seconds

        Returns:
            Human readable age string
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h"
        else:
            days = int(seconds / 86400)
            return f"{days}d"

    def _get_node_status(self, node) -> str:
        """
        Get node status

        Args:
            node: Kubernetes node object

        Returns:
            Node status string
        """
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return "Ready" if condition.status == "True" else "NotReady"
        return "Unknown"

    def _get_node_roles(self, node) -> List[str]:
        """
        Get node roles from labels

        Args:
            node: Kubernetes node object

        Returns:
            List of node roles
        """
        roles = []
        labels = node.metadata.labels or {}

        for label in labels:
            if label.startswith("node-role.kubernetes.io/"):
                role = label.split("/")[-1]
                roles.append(role)

        if not roles:
            roles.append("worker")

        return roles

    def _get_node_conditions(self, node) -> List[Dict]:
        """
        Get node status conditions

        Args:
            node: Kubernetes node object

        Returns:
            List of node conditions
        """
        conditions = []

        for condition in node.status.conditions:
            conditions.append(
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_transition_time": condition.last_transition_time,
                }
            )

        return conditions

    def _get_node_taints(self, node) -> List[Dict]:
        """
        Get node taints

        Args:
            node: Kubernetes node object

        Returns:
            List of node taints
        """
        taints = []

        if node.spec.taints:
            for taint in node.spec.taints:
                taints.append({"key": taint.key, "value": taint.value, "effect": taint.effect})

        return taints

    def _kind_to_plural(self, kind: str) -> str:
        """
        Convert Kind to plural resource name

        Args:
            kind: Kubernetes resource Kind

        Returns:
            Plural resource name
        """
        # Common singular to plural rules
        kind_lower = kind.lower()

        # Special cases
        special_cases = {
            "networkpolicy": "networkpolicies",
            "ingress": "ingresses",
            "horizontalpodautoscaler": "horizontalpodautoscalers",
            "poddisruptionbudget": "poddisruptionbudgets",
            "priorityclass": "priorityclasses",
            "storageclass": "storageclasses",
            "volumeattachment": "volumeattachments",
            "customresourcedefinition": "customresourcedefinitions",
        }

        if kind_lower in special_cases:
            return special_cases[kind_lower]

        # General rules
        if kind_lower.endswith("y"):
            return kind_lower[:-1] + "ies"
        elif kind_lower.endswith(("s", "sh", "ch", "x", "z")):
            return kind_lower + "es"
        else:
            return kind_lower + "s"

    def _handle_api_exception(self, e: ApiException, operation: str, resource_type: str = "") -> Dict:
        """
        Handle Kubernetes API exceptions consistently

        Args:
            e: ApiException instance
            operation: Operation being performed
            resource_type: Type of resource being operated on

        Returns:
            Error dictionary
        """
        error_msg = f"API error during {operation}"
        if resource_type:
            error_msg += f" for {resource_type}"

        if hasattr(e, "reason"):
            error_msg += f": {e.reason}"
        else:
            error_msg += f": {str(e)}"

        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    def _handle_general_exception(self, e: Exception, operation: str, resource_type: str = "") -> Dict:
        """
        Handle general exceptions consistently

        Args:
            e: Exception instance
            operation: Operation being performed
            resource_type: Type of resource being operated on

        Returns:
            Error dictionary
        """
        error_msg = f"Failed to {operation}"
        if resource_type:
            error_msg += f" {resource_type}"
        error_msg += f": {str(e)}"

        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    def validate_kubeconfig_auth(self, kubeconfig_path: str) -> bool:
        """
        Validate kubeconfig authentication

        Args:
            kubeconfig_path: Path to kubeconfig file

        Returns:
            True if authentication is valid, False otherwise
        """
        if not KUBERNETES_AVAILABLE:
            logger.error("Kubernetes library not available, cannot validate kubeconfig")
            return False

        try:
            # Temporarily save current configuration
            original_config = None
            try:
                original_config = config.KUBE_CONFIG_DEFAULT_LOCATION
            except Exception:
                pass

            try:
                # Load specified kubeconfig
                config.load_kube_config(config_file=kubeconfig_path)

                # Create API client and test connection
                v1 = client.CoreV1Api()

                # Try to list namespaces, this is a basic permission test
                # Set short timeout to avoid long waiting
                api_client = v1.api_client
                api_client.rest_timeout = 10  # 10 second timeout

                namespaces = v1.list_namespace(_request_timeout=5)

                logger.info(f"kubeconfig authentication verification passed: {kubeconfig_path}")
                logger.debug(f"Successfully connected to cluster, discovered {len(namespaces.items)} namespaces")
                return True

            except ApiException as e:
                if e.status == 401:
                    logger.error(f"kubeconfig authentication failed - unauthorized: {kubeconfig_path}")
                elif e.status == 403:
                    logger.error(f"kubeconfig authentication failed - insufficient permissions: {kubeconfig_path}")
                else:
                    logger.error(f"kubeconfig API call failed (status code {e.status}): {e.reason}")
                return False

            except Exception as e:
                logger.error(f"kubeconfig connection test failed: {str(e)}")
                return False

            finally:
                # Restore original configuration (if exists)
                if original_config:
                    try:
                        config.load_kube_config(config_file=original_config)
                    except Exception:
                        pass

        except ImportError:
            logger.error("kubernetes client library not installed, cannot verify kubeconfig")
            return False
        except Exception as e:
            logger.error(f"kubeconfig authentication verification exception: {str(e)}")
            return False

    def get_common_resource_mappings(self) -> Dict[str, Dict]:
        """
        Get common resource mappings for standard Kubernetes resources

        Returns:
            Dictionary of resource mappings
        """
        return {
            "pods": {"group": "", "version": "v1", "plural": "pods", "namespaced": True, "kind": "Pod"},
            "services": {"group": "", "version": "v1", "plural": "services", "namespaced": True, "kind": "Service"},
            "deployments": {
                "group": "apps",
                "version": "v1",
                "plural": "deployments",
                "namespaced": True,
                "kind": "Deployment",
            },
            "replicasets": {
                "group": "apps",
                "version": "v1",
                "plural": "replicasets",
                "namespaced": True,
                "kind": "ReplicaSet",
            },
            "statefulsets": {
                "group": "apps",
                "version": "v1",
                "plural": "statefulsets",
                "namespaced": True,
                "kind": "StatefulSet",
            },
            "daemonsets": {
                "group": "apps",
                "version": "v1",
                "plural": "daemonsets",
                "namespaced": True,
                "kind": "DaemonSet",
            },
            "jobs": {"group": "batch", "version": "v1", "plural": "jobs", "namespaced": True, "kind": "Job"},
            "cronjobs": {
                "group": "batch",
                "version": "v1",
                "plural": "cronjobs",
                "namespaced": True,
                "kind": "CronJob",
            },
            "configmaps": {
                "group": "",
                "version": "v1",
                "plural": "configmaps",
                "namespaced": True,
                "kind": "ConfigMap",
            },
            "secrets": {"group": "", "version": "v1", "plural": "secrets", "namespaced": True, "kind": "Secret"},
            "persistentvolumeclaims": {
                "group": "",
                "version": "v1",
                "plural": "persistentvolumeclaims",
                "namespaced": True,
                "kind": "PersistentVolumeClaim",
            },
            "persistentvolumes": {
                "group": "",
                "version": "v1",
                "plural": "persistentvolumes",
                "namespaced": False,
                "kind": "PersistentVolume",
            },
            "namespaces": {
                "group": "",
                "version": "v1",
                "plural": "namespaces",
                "namespaced": False,
                "kind": "Namespace",
            },
            "nodes": {"group": "", "version": "v1", "plural": "nodes", "namespaced": False, "kind": "Node"},
            "ingresses": {
                "group": "networking.k8s.io",
                "version": "v1",
                "plural": "ingresses",
                "namespaced": True,
                "kind": "Ingress",
            },
            "networkpolicies": {
                "group": "networking.k8s.io",
                "version": "v1",
                "plural": "networkpolicies",
                "namespaced": True,
                "kind": "NetworkPolicy",
            },
            "serviceaccounts": {
                "group": "",
                "version": "v1",
                "plural": "serviceaccounts",
                "namespaced": True,
                "kind": "ServiceAccount",
            },
            "roles": {
                "group": "rbac.authorization.k8s.io",
                "version": "v1",
                "plural": "roles",
                "namespaced": True,
                "kind": "Role",
            },
            "rolebindings": {
                "group": "rbac.authorization.k8s.io",
                "version": "v1",
                "plural": "rolebindings",
                "namespaced": True,
                "kind": "RoleBinding",
            },
            "clusterroles": {
                "group": "rbac.authorization.k8s.io",
                "version": "v1",
                "plural": "clusterroles",
                "namespaced": False,
                "kind": "ClusterRole",
            },
            "clusterrolebindings": {
                "group": "rbac.authorization.k8s.io",
                "version": "v1",
                "plural": "clusterrolebindings",
                "namespaced": False,
                "kind": "ClusterRoleBinding",
            },
            "storageclasses": {
                "group": "storage.k8s.io",
                "version": "v1",
                "plural": "storageclasses",
                "namespaced": False,
                "kind": "StorageClass",
            },
            "customresourcedefinitions": {
                "group": "apiextensions.k8s.io",
                "version": "v1",
                "plural": "customresourcedefinitions",
                "namespaced": False,
                "kind": "CustomResourceDefinition",
            },
        }

    def close(self):
        """
        Close client connections and cleanup resources
        """
        # Clear API clients cache
        self._api_clients.clear()
        self._resource_cache.clear()

        # Call parent close method
        if self.temp_config:
            try:
                self.temp_config.close()
                os.unlink(self.temp_config.name)
                self.temp_config = None
            except Exception:
                pass
        self.initialized = False

    def __del__(self):
        """Destructor, delete temporary files"""
        self.close()
