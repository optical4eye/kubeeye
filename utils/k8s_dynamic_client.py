#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes dynamic client tool - similar to Go's Dynamic Client
Uses kubernetes.dynamic module and resource mapping table to simplify resource operations
"""

import yaml
import json
import base64
import datetime
from typing import Dict, List, Any, Optional, Tuple
from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.dynamic import DynamicClient
from kubernetes.dynamic.exceptions import ResourceNotFoundError
import logging
import tempfile
import os
import subprocess

from .k8s_base_client import K8sBaseClient

logger = logging.getLogger(__name__)

class K8sDynamicClient(K8sBaseClient):
    """
    Kubernetes dynamic client class - imitating Go's Dynamic Client
    Supports dynamic resource discovery and operations, reduces duplicate code
    """

    def __init__(self, kubeconfig_content: str = None):
        """
        Initialize Kubernetes dynamic client

        Args:
            kubeconfig_content: kubeconfig file content
        """
        super().__init__(kubeconfig_content)
        self.dynamic_client = None
        self.api_client = None
        self.resource_cache = {}  # Resource definition cache
        self.resource_mappings = {}  # Dynamic resource mapping table, built from rule configuration

        self.init_client()

    def init_client(self) -> bool:
        """
        Initialize Kubernetes dynamic client, supports custom kubeconfig_content

        Returns:
            Returns True on success, False on failure
        """
        try:
            # Use base class common initialization logic
            if not self.init_client_base():
                self.initialized = False
                return False

            # Prefer custom kubeconfig_content initialization
            if self.kubeconfig_content:
                import tempfile
                from kubernetes import config
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml', mode='w', encoding='utf-8')
                tmp.write(self.kubeconfig_content)
                tmp.close()
                kubeconfig_path = tmp.name
                try:
                    config.load_kube_config(config_file=kubeconfig_path)
                finally:
                    os.unlink(kubeconfig_path)
            else:
                from kubernetes import config
                config.load_kube_config()

            self.api_client = client.ApiClient()
            self.dynamic_client = DynamicClient(self.api_client)

            # Authentication verification (optional, initialization fails if failed)
            if self.kubeconfig_content:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml', mode='w', encoding='utf-8')
                tmp.write(self.kubeconfig_content)
                tmp.close()
                kubeconfig_path = tmp.name
                try:
                    if not K8sDynamicClient.validate_kubeconfig_auth(kubeconfig_path):
                        logger.error("kubeconfig authentication verification failed, initialization terminated")
                        self.initialized = False
                        return False
                finally:
                    os.unlink(kubeconfig_path)
            self.initialized = True
            logger.info("Kubernetes dynamic client initialization successful")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes dynamic client: {e}")
            self.initialized = False
            return False

    def __del__(self):
        """Moved to base class K8sBaseClient"""
        super().__del__()

    def get_resource_definition(self, resource_type: str) -> Optional[Any]:
        """
        Get resource definition - similar to Go Dynamic Client's Resource() method

        Args:
            resource_type: resource type, such as 'pods', 'deployments', etc.

        Returns:
            resource definition object or None
        """
        if not self.initialized:
            logger.warning(f"Dynamic client not initialized, unable to get resource definition: {resource_type}")
            return None

        # Check cache
        if resource_type in self.resource_cache:
            return self.resource_cache[resource_type]

        try:
            # Get resource information from mapping table
            if resource_type in self.resource_mappings:
                mapping = self.resource_mappings[resource_type]
                api_version = f"{mapping['group']}/{mapping['version']}" if mapping['group'] else mapping['version']

                # Use dynamic client to get resource definition
                resource = self.dynamic_client.resources.get(
                    api_version=api_version,
                    kind=mapping['kind']
                )

                self.resource_cache[resource_type] = resource
                return resource

            else:
                # Try automatic discovery
                resource = self._discover_resource(resource_type)
                if resource:
                    self.resource_cache[resource_type] = resource
                return resource

        except Exception as e:
            logger.error(f"Failed to get resource definition {resource_type}: {str(e)}")
            return None

    def _discover_resource(self, resource_type: str) -> Optional[Any]:
        """
        Automatic resource definition discovery
        """
        try:
            # Try to find resource in all API groups
            for resource in self.dynamic_client.resources.search(name=resource_type):
                return resource
            return None
        except Exception as e:
            logger.debug(f"Automatic resource discovery failed {resource_type}: {str(e)}")
            return None

    def list_resources(self, resource_type: str, namespace: str = None) -> List[Dict]:
        """
        Unified resource list method - similar to Go Dynamic Client's List() method

        Args:
            resource_type: resource type
            namespace: namespace (optional)

        Returns:
            resource object list
        """
        if not self.initialized:
            logger.error(f"Client not initialized, unable to list resources: {resource_type}")
            return []

        try:
            # Get resource definition
            resource = self.get_resource_definition(resource_type)
            if not resource:
                logger.warning(f"Unable to get resource definition: {resource_type}")
                return []

            # Check if resource is namespace-level
            mapping = self.resource_mappings.get(resource_type, {})
            is_namespaced = mapping.get('namespaced', True)

            # List resources
            if is_namespaced and namespace:
                result = resource.get(namespace=namespace)
            elif is_namespaced:
                result = resource.get()
            else:
                result = resource.get()

            # Convert to dictionary format
            items = result.items if hasattr(result, 'items') else [result]
            converted_items = []
            for item in items:
                try:
                    converted = self._convert_dynamic_object_to_dict(item)
                    converted_items.append(converted)
                except Exception as convert_e:
                    logger.error(f"Failed to convert resource object: {str(convert_e)}")

            logger.info(f"Successfully listed resources {resource_type}: {len(converted_items)} items")
            return converted_items

        except ResourceNotFoundError as e:
            logger.warning(f"Resource type does not exist: {resource_type}, error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"[list_resources] Failed to list resources {resource_type}: {str(e)}")
            logger.error(f"[list_resources] Exception type: {type(e).__name__}")
            logger.error(f"[list_resources] Detailed error information: {repr(e)}")
            logger.error(f"[list_resources] Current mapping table keys: {list(self.resource_mappings.keys())}")
            logger.error(f"[list_resources] Current cache keys: {list(self.resource_cache.keys())}")
            return []

    def get_resource(self, resource_type: str, name: str, namespace: str = None) -> Optional[Dict]:
        """
        Get single resource - similar to Go Dynamic Client's Get() method

        Args:
            resource_type: resource type
            name: resource name
            namespace: namespace (optional)

        Returns:
            resource object or None
        """
        if not self.initialized:
            return None

        try:
            resource = self.get_resource_definition(resource_type)
            if not resource:
                return None

            # Get resource
            if namespace:
                result = resource.get(name=name, namespace=namespace)
            else:
                result = resource.get(name=name)

            return self._convert_dynamic_object_to_dict(result)

        except Exception as e:
            logger.debug(f"Failed to get resource {resource_type}/{name}: {str(e)}")
            return None

    def list_all_resources(self, resource_types: List[str]) -> Dict[str, List[Dict]]:
        """
        Batch get multiple resource types - optimized version

        Args:
            resource_types: resource type list

        Returns:
            resource dictionary grouped by type
        """
        results = {}

        for resource_type in resource_types:
            try:
                resources = self.list_resources(resource_type)
                results[resource_type] = resources
                logger.debug(f"Got {resource_type}: {len(resources)} resources")
            except Exception as e:
                logger.warning(f"Failed to get resource type {resource_type}: {str(e)}")
                results[resource_type] = []

        return results

    def discover_all_crds(self) -> List[Dict]:
        """
        Discover all CRDs in cluster - dynamic discovery

        Returns:
            CRD definition list
        """
        try:
            # Get CRD resource definition
            crd_resource = self.get_resource_definition('customresourcedefinitions')
            if not crd_resource:
                logger.warning("Unable to get CRD resource definition")
                return []

            crds = crd_resource.get()
            crd_list = []

            for crd in crds.items:
                crd_info = {
                    'name': crd.metadata.name,
                    'group': crd.spec.group,
                    'versions': [v.name for v in crd.spec.versions],
                    'scope': crd.spec.scope,
                    'kind': crd.spec.names.kind,
                    'plural': crd.spec.names.plural,
                }
                crd_list.append(crd_info)

                # Dynamically add to resource mapping table
                latest_version = crd.spec.versions[0].name if crd.spec.versions else 'v1'
                self.resource_mappings[crd.spec.names.plural] = {
                    'group': crd.spec.group,
                    'version': latest_version,
                    'plural': crd.spec.names.plural,
                    'namespaced': crd.spec.scope == 'Namespaced'
                }

            logger.info(f"Discovered {len(crd_list)} CRDs, added to resource mapping table")
            return crd_list

        except Exception as e:
            logger.error(f"Failed to discover CRDs: {str(e)}")
            return []

    def list_all_crd_resources(self) -> Dict[str, List[Dict]]:
        """
        Get all CRD resource instances

        Returns:
            resource dictionary grouped by CRD type
        """
        crd_resources = {}

        # First discover all CRDs
        crds = self.discover_all_crds()

        for crd in crds:
            try:
                plural = crd['plural']
                resources = self.list_resources(plural)
                crd_resources[plural] = resources
                logger.debug(f"Got CRD {plural}: {len(resources)} instances")
            except Exception as e:
                logger.warning(f"Failed to get CRD resource {crd['plural']}: {str(e)}")
                crd_resources[crd['plural']] = []

        return crd_resources

    def _convert_dynamic_object_to_dict(self, obj) -> Dict:
        """
        Convert dynamic object to dictionary format

        Args:
            obj: dynamic object

        Returns:
            dictionary format object
        """
        try:
            if hasattr(obj, 'to_dict'):
                result = obj.to_dict()
            elif hasattr(obj, '__dict__'):
                result = dict(obj.__dict__)
            else:
                result = dict(obj)

            # Handle datetime objects
            self._convert_datetime_in_dict(result)
            return result

        except Exception as e:
            logger.warning(f"Failed to convert dynamic object: {str(e)}")
            return {}

    def _convert_datetime_in_dict(self, data: Any) -> None:
        """
        Recursively convert datetime objects in dictionary to strings
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

    def get_supported_resource_types(self) -> List[str]:
        """
        Get supported resource type list

        Returns:
            supported resource type list
        """
        return list(self.resource_mappings.keys())

    def is_namespaced_resource(self, resource_type: str) -> bool:
        """
        Check if resource is namespace-level

        Args:
            resource_type: resource type

        Returns:
            whether it is namespace-level resource
        """
        mapping = self.resource_mappings.get(resource_type, {})
        return mapping.get('namespaced', True)

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to cluster

        Returns:
            (success, message) tuple
        """
        if not self.initialized:
            return False, "Dynamic client not initialized"

        try:
            # Try to list namespaces to test connection
            namespaces = self.list_resources('namespaces')
            return True, f"Connection successful, discovered {len(namespaces)} namespaces"
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"

    def build_resource_mappings_from_config(self, rule_config: Dict) -> None:
        """
        Build resource mapping table from rule configuration

        Args:
            rule_config: rule configuration dictionary, contains resources and scope information
        """
        # Support two configuration structures:
        # 1. rule_config directly contains resources: rule_config.get('resources', [])
        # 2. rule_config contains config field: rule_config.get('config', {}).get('resources', [])
        resources_config = rule_config.get('resources', [])

        if not resources_config:
            # Try to get from nested config field
            config_data = rule_config.get('config', {})
            resources_config = config_data.get('resources', [])

        # Clear existing mappings (avoid accumulation)
        self.resource_mappings.clear()

        for resource in resources_config:

            kind = resource.get('kind', '')
            api_version = resource.get('apiVersion', '')
            namespaced = resource.get('namespaced', True)

            if not kind or not api_version:
                logger.warning(f"Resource information incomplete, skipping: Kind={kind}, API version={api_version}")
                continue

            # Parse apiVersion to get group and version
            if '/' in api_version:
                group, version = api_version.split('/', 1)
            else:
                group = ''
                version = api_version

            # Generate plural resource name
            plural = self._kind_to_plural(kind)

            # Add to resource mapping table
            mapping_key = plural.lower()
            mapping_value = {
                'group': group,
                'version': version,
                'plural': plural.lower(),
                'namespaced': namespaced,
                'kind': kind
            }

            self.resource_mappings[mapping_key] = mapping_value

        logger.info(f"Built {len(self.resource_mappings)} resource mappings from rule configuration")

    def _kind_to_plural(self, kind: str) -> str:
        """
        Convert Kind to plural resource name

        Args:
            kind: Kubernetes resource Kind

        Returns:
            plural resource name
        """
        # Common singular to plural rules
        kind_lower = kind.lower()

        # Special cases
        special_cases = {
            'networkpolicy': 'networkpolicies',
            'ingress': 'ingresses',
            'horizontalpodautoscaler': 'horizontalpodautoscalers',
            'poddisruptionbudget': 'poddisruptionbudgets',
            'priorityclass': 'priorityclasses',
            'storageclass': 'storageclasses',
            'volumeattachment': 'volumeattachments',
            'customresourcedefinition': 'customresourcedefinitions',
        }

        if kind_lower in special_cases:
            return special_cases[kind_lower]

        # General rules
        if kind_lower.endswith('y'):
            return kind_lower[:-1] + 'ies'
        elif kind_lower.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return kind_lower + 'es'
        else:
            return kind_lower + 's'

    def list_resources_from_config(self, rule_config: Dict) -> Dict[str, List[Dict]]:
        """
        Get required resources based on rule configuration

        Args:
            rule_config: rule configuration dictionary

        Returns:
            resource dictionary grouped by resource type
        """
        # Build resource mapping
        self.build_resource_mappings_from_config(rule_config)

        # Get namespace configuration
        scope_config = rule_config.get('scope', {})
        namespace_config = scope_config.get('namespaces', {})
        include_namespaces = namespace_config.get('include', [])
        exclude_namespaces = namespace_config.get('exclude', [])

        resources = {}

        # Get all configured resource types
        for resource_type in self.resource_mappings.keys():
            try:
                mapping = self.resource_mappings[resource_type]
                is_namespaced = mapping.get('namespaced', True)

                if is_namespaced:
                    # Handle namespace-level resources
                    if include_namespaces:
                        # Only get resources for specified namespaces
                        all_resources = []
                        for namespace in include_namespaces:
                            if namespace not in exclude_namespaces:
                                ns_resources = self.list_resources(resource_type, namespace=namespace)
                                all_resources.extend(ns_resources)
                        resources[resource_type] = all_resources
                    else:
                        # Get resources for all namespaces, then filter
                        all_resources = self.list_resources(resource_type)
                        if exclude_namespaces:
                            filtered_resources = [
                                res for res in all_resources
                                if res.get('metadata', {}).get('namespace') not in exclude_namespaces
                            ]
                            resources[resource_type] = filtered_resources
                        else:
                            resources[resource_type] = all_resources
                else:
                    # Cluster-level resources, get directly
                    resources[resource_type] = self.list_resources(resource_type)

                logger.debug(f"Got {resource_type}: {len(resources[resource_type])} resources")

            except Exception as e:
                logger.warning(f"Failed to get resource type {resource_type}: {str(e)}")
                resources[resource_type] = []

        return resources

    def _analyze_resource_strategy(self, resource_config: List[Dict]) -> Dict[str, Any]:
        """
        Analyze resource configuration, select optimal acquisition strategy

        Args:
            resource_config: resource configuration list

        Returns:
            strategy analysis result
        """
        logger.debug(f"[_analyze_resource_strategy] Starting resource strategy analysis")
        logger.debug(f"[_analyze_resource_strategy] Input configuration count: {len(resource_config)}")
        logger.debug(f"[_analyze_resource_strategy] Input resource types: {[r.get('kind', 'unknown') for r in resource_config]}")

        configured_kinds = {res['kind'] for res in resource_config}
        logger.debug(f"[_analyze_resource_strategy] Configured resource type set: {configured_kinds}")

        # Define controller types
        workload_controllers = {'Deployment', 'StatefulSet', 'DaemonSet'}
        job_controllers = {'Job', 'CronJob'}
        all_controllers = workload_controllers | job_controllers

        logger.debug(f"[_analyze_resource_strategy] Workload controller definitions: {workload_controllers}")
        logger.debug(f"[_analyze_resource_strategy] Job controller definitions: {job_controllers}")
        logger.debug(f"[_analyze_resource_strategy] All controller definitions: {all_controllers}")

        # Analyze configuration
        has_pods = 'Pod' in configured_kinds
        has_controllers = bool(configured_kinds & all_controllers)
        configured_controllers = configured_kinds & all_controllers

        logger.debug(f"[_analyze_resource_strategy] Configuration analysis results:")
        logger.debug(f"    - Contains Pod: {has_pods}")
        logger.debug(f"    - Contains controllers: {has_controllers}")
        logger.debug(f"    - Configured controllers: {configured_controllers}")
        logger.debug(f"    - Controller count: {len(configured_controllers)}")

        strategy = {
            'mode': 'default',
            'get_pods_directly': has_pods,
            'get_controllers': list(configured_controllers),
            'filter_controlled_pods': False,
            'optimization_applied': False,
            'reasoning': 'Default strategy - get all configured resources'
        }

        logger.debug(f"[_analyze_resource_strategy] Initial strategy: {json.dumps(strategy, indent=2)}")

        # If both controllers and Pod are configured, apply optimization strategy
        if has_pods and has_controllers:
            logger.debug(f"[_analyze_resource_strategy] Both Pod and controllers included, entering optimization strategy analysis")
            logger.debug(f"[_analyze_resource_strategy] Controller count: {len(configured_controllers)}")

            if len(configured_controllers) >= 2:
                # Multiple controllers + Pod: recommend controller-only strategy
                logger.debug("[_analyze_resource_strategy] Triggered controller-only strategy (multiple controllers+Pod)")
                strategy.update({
                    'mode': 'controller_only',
                    'get_pods_directly': False,
                    'filter_controlled_pods': False,
                    'optimization_applied': True,
                    'reasoning': 'Multiple controllers+Pod configuration, use controller-only strategy to avoid duplication'
                })
                logger.debug("[_analyze_resource_strategy] Applied controller-only strategy, disabled direct Pod acquisition")
            else:
                # Single controller + Pod: recommend smart hybrid strategy
                logger.debug("[_analyze_resource_strategy] Triggered smart hybrid strategy (single controller+Pod)")
                strategy.update({
                    'mode': 'hybrid_smart',
                    'get_pods_directly': True,
                    'filter_controlled_pods': True,
                    'optimization_applied': True,
                    'reasoning': 'Controller+Pod configuration, use smart hybrid strategy to filter controlled Pods'
                })
                logger.debug("[_analyze_resource_strategy] Applied smart hybrid strategy, enabled Pod filtering")
        else:
            logger.debug("[_analyze_resource_strategy] Use default strategy (no Pod+controller combination, or only single type)")
            logger.debug(f"[_analyze_resource_strategy] Reason: has_pods={has_pods}, has_controllers={has_controllers}")

        logger.debug(f" [_analyze_resource_strategy] Final strategy analysis completed:")
        logger.debug(f"    - Mode: {strategy['mode']}")
        logger.debug(f"    - Get Pods directly: {strategy['get_pods_directly']}")
        logger.debug(f"    - Get controllers: {strategy['get_controllers']}")
        logger.debug(f"    - Filter controlled Pods: {strategy['filter_controlled_pods']}")
        logger.debug(f"    - Optimization applied: {strategy['optimization_applied']}")
        logger.debug(f"    - Reason: {strategy['reasoning']}")

        return strategy

    def _filter_controlled_pods(self, pods: List[Dict], controllers: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Filter out Pods controlled by controllers, keep only independent Pods

        Args:
            pods: Pod resource list
            controllers: controller resource dictionary

        Returns:
            filtered independent Pod list
        """
        if not pods:
            return []

        # Collect all controller UIDs
        controller_uids = set()

        for controller_type, controller_list in controllers.items():
            for controller in controller_list:
                uid = controller.get('metadata', {}).get('uid')
                if uid:
                    controller_uids.add(uid)

        # Filter Pods
        independent_pods = []
        controlled_pods = []

        for pod in pods:
            owner_refs = pod.get('metadata', {}).get('ownerReferences', [])
            is_controlled = False

            for owner_ref in owner_refs:
                if owner_ref.get('uid') in controller_uids:
                    is_controlled = True
                    controlled_pods.append(pod)
                    break

            if not is_controlled:
                independent_pods.append(pod)

        logger.info(f"Pod filtering results: Total={len(pods)}, Controlled={len(controlled_pods)}, Independent={len(independent_pods)}")
        return independent_pods

    def list_resources_from_config_optimized(self, rule_config: Dict) -> Dict[str, List[Dict]]:
        """
        Get resources based on rule configuration - optimized version, avoid duplicate acquisition

        Args:
            rule_config: rule configuration dictionary

        Returns:
            resource dictionary grouped by resource type
        """
        logger.info(" [list_resources_from_config_optimized] ==== Starting optimized resource acquisition ====")
        logger.debug(f" [list_resources_from_config_optimized] Input configuration structure: {list(rule_config.keys())}")
        logger.debug(f" [list_resources_from_config_optimized] Input configuration type: {type(rule_config)}")

        # Build resource mapping
        logger.debug(" [list_resources_from_config_optimized] Step 1: Build resource mapping")
        logger.debug(f" [list_resources_from_config_optimized] Mapping table keys before build: {list(self.resource_mappings.keys())}")
        self.build_resource_mappings_from_config(rule_config)
        logger.debug(f" [list_resources_from_config_optimized] Mapping table keys after build: {list(self.resource_mappings.keys())}")

        # Analyze resource acquisition strategy
        logger.debug(" [list_resources_from_config_optimized] Step 2: Analyze resource acquisition strategy")
        resource_config = rule_config.get('config', {}).get('resources', [])
        logger.debug(f" [list_resources_from_config_optimized] Resources extracted from config.resources: {[r.get('kind', 'unknown') for r in resource_config]}")

        if not resource_config:
            # Try to get from root level
            resource_config = rule_config.get('resources', [])
            logger.debug(f" [list_resources_from_config_optimized] Resources extracted from root level resources: {[r.get('kind', 'unknown') for r in resource_config]}")

        strategy = self._analyze_resource_strategy(resource_config)

        logger.info(f" [list_resources_from_config_optimized] Selected resource acquisition strategy: {strategy['mode']} - {strategy['reasoning']}")
        logger.debug(f" [list_resources_from_config_optimized] Complete strategy information: {json.dumps(strategy, indent=2)}")

        # Get namespace configuration
        logger.debug(" [list_resources_from_config_optimized] Step 3: Parse namespace configuration")
        scope_config = rule_config.get('scope', {})
        logger.debug(f" [list_resources_from_config_optimized] scope configuration: {scope_config}")
        namespace_config = scope_config.get('namespaces', {})
        logger.debug(f" [list_resources_from_config_optimized] namespace configuration: {namespace_config}")
        include_namespaces = namespace_config.get('include', [])
        exclude_namespaces = namespace_config.get('exclude', [])

        logger.debug(f" [list_resources_from_config_optimized] Namespace filtering:")
        logger.debug(f"    - Include namespaces: {include_namespaces}")
        logger.debug(f"    - Exclude namespaces: {exclude_namespaces}")

        resources = {}

        # Get resources according to strategy
        logger.debug(f" [list_resources_from_config_optimized] Step 4: Get resources according to strategy '{strategy['mode']}'")

        if strategy['mode'] == 'controller_only':
            logger.info(" [list_resources_from_config_optimized] Executing controller-only strategy")
            controllers_to_get = strategy['get_controllers']
            logger.debug(f" [list_resources_from_config_optimized] Controllers to get: {controllers_to_get}")

            # Only get controller resources
            for i, resource_type in enumerate(controllers_to_get):
                resource_type_lower = resource_type.lower() + 's'
                logger.debug(f" [list_resources_from_config_optimized] Processing controller {i+1}/{len(controllers_to_get)}: {resource_type} -> {resource_type_lower}")

                if resource_type_lower in self.resource_mappings:
                    logger.debug(f" [list_resources_from_config_optimized] Found in resource mapping: {resource_type_lower}")
                    logger.debug(f" [list_resources_from_config_optimized] Calling _get_namespaced_resources...")
                    controller_resources = self._get_namespaced_resources(
                        resource_type_lower, include_namespaces, exclude_namespaces
                    )
                    resources[resource_type_lower] = controller_resources
                    logger.info(f" [list_resources_from_config_optimized] Got {resource_type_lower}: {len(controller_resources)} items")
                else:
                    logger.warning(f" [list_resources_from_config_optimized] Not found in resource mapping: {resource_type_lower}")
                    logger.debug(f" [list_resources_from_config_optimized] Available mappings: {list(self.resource_mappings.keys())}")

        elif strategy['mode'] == 'hybrid_smart':
            logger.info(" [list_resources_from_config_optimized] Executing smart hybrid strategy")
            # Smart hybrid mode: get controllers + filter independent Pods
            controllers = {}
            controllers_to_get = strategy['get_controllers']
            logger.debug(f" [list_resources_from_config_optimized] Controllers to get: {controllers_to_get}")

            # Get controllers
            logger.debug(" [list_resources_from_config_optimized] Phase 1: Get controller resources")
            for i, resource_type in enumerate(controllers_to_get):
                resource_type_lower = resource_type.lower() + 's'
                logger.debug(f" [list_resources_from_config_optimized] Processing controller {i+1}/{len(controllers_to_get)}: {resource_type} -> {resource_type_lower}")

                if resource_type_lower in self.resource_mappings:
                    logger.debug(f" [list_resources_from_config_optimized] Found controller in resource mapping: {resource_type_lower}")
                    controller_resources = self._get_namespaced_resources(
                        resource_type_lower, include_namespaces, exclude_namespaces
                    )
                    resources[resource_type_lower] = controller_resources
                    controllers[resource_type_lower] = controller_resources
                    logger.info(f" [list_resources_from_config_optimized] Got controller {resource_type_lower}: {len(controller_resources)} items")
                else:
                    logger.warning(f" [list_resources_from_config_optimized] Controller resource mapping missing: {resource_type_lower}")
                    logger.debug(f" [list_resources_from_config_optimized] Available mappings: {list(self.resource_mappings.keys())}")

            # Get and filter Pods
            logger.debug(" [list_resources_from_config_optimized] Phase 2: Get and filter Pod resources")
            logger.debug(f" [list_resources_from_config_optimized] Whether to get Pods directly: {strategy['get_pods_directly']}")
            logger.debug(f" [list_resources_from_config_optimized] pods whether in mapping: {'pods' in self.resource_mappings}")

            if strategy['get_pods_directly'] and 'pods' in self.resource_mappings:
                logger.debug(" [list_resources_from_config_optimized] Getting all Pods...")
                all_pods = self._get_namespaced_resources(
                    'pods', include_namespaces, exclude_namespaces
                )
                logger.debug(f" [list_resources_from_config_optimized] Got {len(all_pods)} Pods")

                if strategy['filter_controlled_pods']:
                    logger.debug(" [list_resources_from_config_optimized] Filtering Pods controlled by controllers...")
                    logger.debug(f" [list_resources_from_config_optimized] Available controller data: {list(controllers.keys())}")
                    # Filter out Pods controlled by controllers
                    independent_pods = self._filter_controlled_pods(all_pods, controllers)
                    resources['pods'] = independent_pods
                    logger.info(f" [list_resources_from_config_optimized] Independent Pods after filtering: {len(independent_pods)} items")
                else:
                    resources['pods'] = all_pods
                    logger.info(f" [list_resources_from_config_optimized] Unfiltered Pods: {len(all_pods)} items")
            else:
                logger.debug(" [list_resources_from_config_optimized] Skip Pod acquisition (strategy does not require or mapping missing)")

        else:
            logger.info(" [list_resources_from_config_optimized] Executing default strategy")
            # Default strategy: get all configured resources (do not rebuild resource mapping)
            logger.debug(" [list_resources_from_config_optimized] Use built resource mapping to get all configured resources")
            logger.debug(f" [list_resources_from_config_optimized] Built mapping table: {list(self.resource_mappings.keys())}")

            # Get all configured resource types
            total_types = len(self.resource_mappings)
            logger.debug(f" [list_resources_from_config_optimized] Need to process {total_types} resource types")

            for i, resource_type in enumerate(self.resource_mappings.keys()):
                logger.debug(f" [list_resources_from_config_optimized] Processing resource type {i+1}/{total_types}: {resource_type}")

                try:
                    mapping = self.resource_mappings[resource_type]
                    is_namespaced = mapping.get('namespaced', True)
                    logger.debug(f" [list_resources_from_config_optimized] Resource {resource_type} mapping information: {json.dumps(mapping, indent=2)}")
                    logger.debug(f" [list_resources_from_config_optimized] Whether namespace-level: {is_namespaced}")

                    if is_namespaced:
                        logger.debug(f" [list_resources_from_config_optimized] Processing namespace-level resource: {resource_type}")
                        # Handle namespace-level resources
                        if include_namespaces:
                            logger.debug(f" [list_resources_from_config_optimized] Getting resources for specified namespaces {include_namespaces}")
                            # Only get resources for specified namespaces
                            all_resources = []
                            for j, namespace in enumerate(include_namespaces):
                                if namespace not in exclude_namespaces:
                                    logger.debug(f" [list_resources_from_config_optimized] Processing namespace {j+1}/{len(include_namespaces)}: {namespace}")
                                    ns_resources = self.list_resources(resource_type, namespace=namespace)
                                    all_resources.extend(ns_resources)
                                    logger.debug(f" [list_resources_from_config_optimized] Namespace {namespace} got: {len(ns_resources)} items")
                                else:
                                    logger.debug(f" [list_resources_from_config_optimized] Skip excluded namespace: {namespace}")
                            resources[resource_type] = all_resources
                            logger.debug(f" [list_resources_from_config_optimized] Specified namespaces total: {len(all_resources)} items")
                        else:
                            logger.debug(" [list_resources_from_config_optimized] Getting resources for all namespaces")
                            # Get resources for all namespaces, then filter
                            all_resources = self.list_resources(resource_type)
                            logger.debug(f" [list_resources_from_config_optimized] All namespaces got: {len(all_resources)} items")
                            if exclude_namespaces:
                                logger.debug(f" [list_resources_from_config_optimized] Filtering excluded namespaces: {exclude_namespaces}")
                                filtered_resources = [
                                    res for res in all_resources
                                    if res.get('metadata', {}).get('namespace') not in exclude_namespaces
                                ]
                                resources[resource_type] = filtered_resources
                                logger.debug(f" [list_resources_from_config_optimized] After filtering: {len(filtered_resources)} items (original: {len(all_resources)} items)")
                            else:
                                resources[resource_type] = all_resources
                                logger.debug(f" [list_resources_from_config_optimized] No filtering needed: {len(all_resources)} items")
                    else:
                        logger.debug(f" [list_resources_from_config_optimized] Processing cluster-level resource: {resource_type}")
                        # Cluster-level resources, get directly
                        cluster_resources = self.list_resources(resource_type)
                        resources[resource_type] = cluster_resources
                        logger.debug(f" [list_resources_from_config_optimized] Cluster-level got: {len(cluster_resources)} items")

                    logger.info(f" [list_resources_from_config_optimized] Got {resource_type}: {len(resources[resource_type])} resources")

                except Exception as e:
                    logger.error(f"[list_resources_from_config_optimized] Failed to get resource {resource_type}: {str(e)}")
                    logger.error(f"[list_resources_from_config_optimized] Exception type: {type(e).__name__}")
                    logger.error(f"[list_resources_from_config_optimized] Detailed error: {repr(e)}")
                    resources[resource_type] = []

                except Exception as e:
                    logger.error(f"Failed to get resource type {resource_type}: {str(e)}")
                    logger.debug(f"Detailed error: {repr(e)}")
                    resources[resource_type] = []

        # Record results
        total_resources = sum(len(res_list) for res_list in resources.values())
        logger.info(f"Optimized acquisition got {len(resources)} resource types, total {total_resources} resources")
        logger.debug(f"Resource distribution: {[(k, len(v)) for k, v in resources.items()]}")

        if strategy['optimization_applied']:
            logger.info(" Resource acquisition optimization applied, avoided duplicate acquisition")

        logger.info("==== Optimized resource acquisition completed ====")
        return resources

    def _get_namespaced_resources(self, resource_type: str, include_namespaces: List[str],
                                  exclude_namespaces: List[str]) -> List[Dict]:
        """
        Get namespace-level resources (helper method)

        Args:
            resource_type: resource type
            include_namespaces: included namespaces
            exclude_namespaces: excluded namespaces

        Returns:
            resource list
        """
        logger.debug(f" [_get_namespaced_resources] Starting to get namespace resources")
        logger.debug(f" [_get_namespaced_resources] Input parameters:")
        logger.debug(f"    - resource_type: {resource_type}")
        logger.debug(f"    - include_namespaces: {include_namespaces}")
        logger.debug(f"    - exclude_namespaces: {exclude_namespaces}")

        try:
            # Check resource mapping
            if resource_type not in self.resource_mappings:
                logger.error(f"[_get_namespaced_resources] Resource type {resource_type} not in mapping table")
                logger.debug(f"[_get_namespaced_resources] Current mapping table keys: {list(self.resource_mappings.keys())}")
                return []

            mapping = self.resource_mappings[resource_type]
            is_namespaced = mapping.get('namespaced', True)

            logger.debug(f" [_get_namespaced_resources] Resource mapping information:")
            logger.debug(f"    - Mapping: {json.dumps(mapping, indent=2)}")
            logger.debug(f"    - Whether namespace-level: {is_namespaced}")

            if not is_namespaced:
                # Cluster-level resources
                logger.debug(f" [_get_namespaced_resources] Resource is cluster-level, get directly")
                logger.debug(f" [_get_namespaced_resources] Calling list_resources({resource_type})...")
                cluster_resources = self.list_resources(resource_type)
                logger.debug(f" [_get_namespaced_resources] Cluster-level resources got: {len(cluster_resources)} items")
                return cluster_resources

            # Namespace-level resource processing
            if include_namespaces:
                # Only get resources for specified namespaces
                logger.debug(f" [_get_namespaced_resources] Strategy: Get resources for specified namespaces")
                logger.debug(f" [_get_namespaced_resources] Namespaces to process: {include_namespaces}")
                all_resources = []

                for i, namespace in enumerate(include_namespaces):
                    logger.debug(f" [_get_namespaced_resources] Processing namespace {i+1}/{len(include_namespaces)}: {namespace}")

                    if namespace not in exclude_namespaces:
                        logger.debug(f" [_get_namespaced_resources] Namespace {namespace} not excluded, starting acquisition")
                        logger.debug(f" [_get_namespaced_resources] Calling list_resources({resource_type}, {namespace})...")
                        namespace_resources = self.list_resources(resource_type, namespace)
                        all_resources.extend(namespace_resources)
                        logger.debug(f" [_get_namespaced_resources] Namespace {namespace} got: {len(namespace_resources)} items")
                    else:
                        logger.debug(f" [_get_namespaced_resources] Skip excluded namespace: {namespace}")

                logger.debug(f" [_get_namespaced_resources] Specified namespaces total resources: {len(all_resources)}")
                return all_resources
            else:
                # Get resources for all namespaces, then filter
                logger.debug(f" [_get_namespaced_resources] Strategy: Get resources for all namespaces")
                logger.debug(f" [_get_namespaced_resources] Calling list_resources({resource_type})...")
                all_resources = self.list_resources(resource_type)
                logger.debug(f" [_get_namespaced_resources] All namespaces resources got: {len(all_resources)} items")

                if exclude_namespaces:
                    logger.debug(f" [_get_namespaced_resources] Need to filter excluded namespaces: {exclude_namespaces}")
                    logger.debug(f" [_get_namespaced_resources] Starting filtering...")

                    # Count resources per namespace before filtering
                    ns_count_before = {}
                    for res in all_resources:
                        ns = res.get('metadata', {}).get('namespace', '<cluster-scoped>')
                        ns_count_before[ns] = ns_count_before.get(ns, 0) + 1
                    logger.debug(f" [_get_namespaced_resources] Resources per namespace before filtering: {ns_count_before}")

                    filtered_resources = [
                        resource for resource in all_resources
                        if resource.get('metadata', {}).get('namespace') not in exclude_namespaces
                    ]

                    # Count resources per namespace after filtering
                    ns_count_after = {}
                    for res in filtered_resources:
                        ns = res.get('metadata', {}).get('namespace', '<cluster-scoped>')
                        ns_count_after[ns] = ns_count_after.get(ns, 0) + 1
                    logger.debug(f" [_get_namespaced_resources] Resources per namespace after filtering: {ns_count_after}")

                    logger.debug(f" [_get_namespaced_resources] Filtering completed: {len(filtered_resources)} items (original: {len(all_resources)} items)")
                    return filtered_resources
                else:
                    logger.debug(f" [_get_namespaced_resources] No filtering needed, return all resources: {len(all_resources)} items")
                    return all_resources

        except Exception as e:
            logger.error(f"[_get_namespaced_resources] Failed to get resource {resource_type}: {str(e)}")
            logger.error(f"[_get_namespaced_resources] Exception type: {type(e).__name__}")
            logger.error(f"[_get_namespaced_resources] Detailed error: {repr(e)}")
            logger.error(f"[_get_namespaced_resources] Current resource mappings: {list(self.resource_mappings.keys())}")
            return []

    # New: Extract kubeconfig from cluster json file and write to temporary file
    def get_kubeconfig_file_from_cluster_json(cluster_json_path: str) -> str:
        """
        Read kubeconfig string from data/clusters/<cluster_name>.json, write to temporary file and return path.
        Args:
            cluster_json_path: cluster json file path
        Returns:
            kubeconfig temporary file path
        Raises:
            Exception: kubeconfig field does not exist or write failed
        """
        with open(cluster_json_path, 'r', encoding='utf-8') as f:
            cluster_data = json.load(f)
        kubeconfig_str = cluster_data.get('kubeconfig')
        if not kubeconfig_str:
            raise Exception(f"kubeconfig field does not exist in {cluster_json_path}")
        # Write to temporary file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml', mode='w', encoding='utf-8')
        tmp.write(kubeconfig_str)
        tmp.close()
        return tmp.name

    @staticmethod
    def validate_kubeconfig_auth(kubeconfig_path: str) -> bool:
        """
        Use pure Python kubernetes client to verify kubeconfig can authenticate and access API normally.
        Args:
            kubeconfig_path: kubeconfig file path
        Returns:
            True means authentication passed, False means failed
        """
        try:
            from kubernetes import config, client
            from kubernetes.client.rest import ApiException

            # Temporarily save current configuration
            original_config = None
            try:
                original_config = config.KUBE_CONFIG_DEFAULT_LOCATION
            except:
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
                    except:
                        pass

        except ImportError:
            logger.error("kubernetes client library not installed, cannot verify kubeconfig")
            return False
        except Exception as e:
            logger.error(f"kubeconfig authentication verification exception: {str(e)}")
            return False

# Usage example:
# kubeconfig_path = get_kubeconfig_file_from_cluster_json('data/clusters/demo.json')
# k8s_client = config.new_client_from_config(config_file=kubeconfig_path)
# dyn_client = DynamicClient(k8s_client)
