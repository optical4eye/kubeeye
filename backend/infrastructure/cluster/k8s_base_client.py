#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Kubernetes client - providing common initialization and configuration logic
Reducing code duplication between k8s_client.py and k8s_dynamic_client.py
"""

import tempfile
import os
import logging
from typing import Tuple
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class K8sBaseClient:
    """Base Kubernetes client providing common initialization and configuration functionality"""

    def __init__(self, kubeconfig_content: str = None):
        """
        Initialize the base client

        Args:
            kubeconfig_content: Content of the kubeconfig file
        """
        self.kubeconfig_content = kubeconfig_content
        self.temp_config = None
        self.initialized = False

    def init_client_base(self) -> bool:
        """
        Common client initialization logic

        Returns:
            Returns True on success, False on failure
        """
        try:
            if self.kubeconfig_content:
                # Create temporary file to store kubeconfig
                self.temp_config = tempfile.NamedTemporaryFile(delete=False)
                self.temp_config.write(self.kubeconfig_content.encode())
                self.temp_config.flush()
                config.load_kube_config(self.temp_config.name)
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
        # Get current client configuration
        configuration = client.Configuration.get_default_copy()

        # Disable SSL certificate verification
        configuration.verify_ssl = False
        configuration.ssl_ca_cert = None

        # Set warning
        logger.warning(
            "SSL certificate verification disabled, this may pose a security threat"
        )

        return configuration

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Kubernetes cluster

        Returns:
            (Whether successful, Message)
        """
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

    def __del__(self):
        """Destructor, delete temporary files"""
        if self.temp_config:
            try:
                self.temp_config.close()
                os.unlink(self.temp_config.name)
            except:
                pass
