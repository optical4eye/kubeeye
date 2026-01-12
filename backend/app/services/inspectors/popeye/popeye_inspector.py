#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Popeye inspector - runs Popeye Kubernetes cluster scanner
"""

import asyncio
import os
import tempfile
from typing import Dict, List, Any, Optional

from services.inspectors.base_inspector import BaseInspector
from infra.results.inspection_result import InspectionResult
from infra.rules.rule_loader import Rule
from core.logging import get_logger
from core.config.settings import settings
from core.common.exceptions import (
    PopeyeError,
    PopeyeBinaryNotFoundError,
    PopeyeBinaryNotExecutableError,
    PopeyeTimeoutError,
    PopeyeExecutionError,
    PopeyeParseError,
)
from infra.cluster.k8s_client import K8sClient

logger = get_logger("popeye_inspector")


class PopeyeInspector(BaseInspector):
    """Popeye inspector for Kubernetes cluster scanning"""

    def __init__(self, config: Optional[Dict[str, Any]] = None, use_gitops: bool = False):
        self.config = config or {}
        self.popeye_path = self.config.get("popeye_path") or settings.kubeeye_popeye_path
        self.timeout = int(self.config.get("timeout", settings.kubeeye_popeye_timeout))
        self.default_format = self.config.get("default_format", settings.kubeeye_popeye_default_format)
        super().__init__(self.config, use_gitops=use_gitops)

    @property
    def inspector_type(self) -> str:
        return "popeye"

    def _validate_popeye_binary(self) -> None:
        """Validate that Popeye binary is available and executable"""
        if not os.path.exists(self.popeye_path):
            raise PopeyeBinaryNotFoundError(f"Popeye binary not found at {self.popeye_path}")

        if not os.access(self.popeye_path, os.X_OK):
            raise PopeyeBinaryNotExecutableError(f"Popeye binary at {self.popeye_path} is not executable")

    def _validate_scan_parameters(
        self, cluster_name: str, kubeconfig: str, output_format: str, all_namespaces: bool, namespace: Optional[str]
    ) -> None:
        """Validate scan parameters"""
        if not cluster_name or not isinstance(cluster_name, str):
            raise ValueError("Cluster name must be a non-empty string")

        if not kubeconfig or not isinstance(kubeconfig, str):
            raise ValueError("Kubeconfig must be a non-empty string")

        if output_format != "html":
            raise ValueError(f"Invalid output format '{output_format}'. Popeye only supports HTML format.")

        if not all_namespaces and namespace and not isinstance(namespace, str):
            raise ValueError("Namespace must be a string when specified")

        if all_namespaces and namespace:
            raise ValueError("Cannot specify both all_namespaces=True and a specific namespace")

    async def _validate_namespace(self, cluster_name: str, kubeconfig: str, namespace: Optional[str]) -> None:
        """Validate that namespace exists in the cluster if specified"""
        if not namespace:
            return

        try:
            k8s_client = K8sClient(kubeconfig)
            namespaces_result = await k8s_client.get_namespaces()

            if namespaces_result.get("status") == "error":
                raise ValueError(f"Failed to get namespaces: {namespaces_result.get('error')}")

            available_namespaces = [ns["name"] for ns in namespaces_result.get("namespaces", [])]
            if namespace not in available_namespaces:
                raise ValueError(
                    f"Namespace '{namespace}' does not exist in cluster '{cluster_name}'. "
                    f"Available namespaces: {', '.join(available_namespaces)}"
                )

        except Exception as e:
            raise ValueError(f"Failed to validate namespace: {str(e)}")

    async def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """Apply Popeye inspection rule"""
        import time

        rule_start_time = time.time()

        try:
            cluster_name = context.get("cluster_name", "unknown")

            # Get kubeconfig from rule config or context
            kubeconfig = self.get_rule_config(rule, "kubeconfig") or context.get("kubeconfig")
            if not kubeconfig:
                return self.rule_processor.result_formatter.error_result(rule, "Missing kubeconfig configuration")

            # Get scan parameters from rule config
            output_format = self.get_rule_config(rule, "output_format", self.default_format)
            all_namespaces = self.get_rule_config(rule, "all_namespaces", True)
            namespace = self.get_rule_config(rule, "namespace")

            # Run Popeye scan
            scan_result = await self.run_popeye_scan(
                cluster_name=cluster_name,
                kubeconfig=kubeconfig,
                output_format=output_format,
                all_namespaces=all_namespaces,
                namespace=namespace,
            )

            # Create inspection result
            inspection_result = await self.create_inspection_result(cluster_name, scan_result)

            # Return the first item from the inspection result
            if inspection_result.items:
                result_item = inspection_result.items[0]
                rule_duration = time.time() - rule_start_time
                logger.info(f"Rule {rule.id} completed in {rule_duration:.2f}s")
                return result_item
            else:
                return self.rule_processor.result_formatter.error_result(rule, "No results generated from Popeye scan")

        except (PopeyeBinaryNotFoundError, PopeyeBinaryNotExecutableError) as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} failed with binary error after {rule_duration:.2f}s: {e}")
            return self.rule_processor.result_formatter.error_result(rule, f"Popeye binary issue: {str(e)}")
        except PopeyeTimeoutError as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} timed out after {rule_duration:.2f}s: {e}")
            return self.rule_processor.result_formatter.error_result(rule, f"Popeye scan timed out: {str(e)}")
        except (PopeyeExecutionError, PopeyeParseError) as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} failed with execution error after {rule_duration:.2f}s: {e}")
            return self.rule_processor.result_formatter.error_result(rule, f"Popeye execution failed: {str(e)}")
        except PopeyeError as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} failed with PopeyeError after {rule_duration:.2f}s: {e}")
            return self.rule_processor.result_formatter.error_result(rule, f"Popeye scan failed: {str(e)}")
        except Exception as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} execution failed after {rule_duration:.2f}s: {e}", exc_info=True)
            return self.rule_processor.result_formatter.error_result(rule, f"Execution failed: {str(e)}")

    async def run_popeye_scan(
        self,
        cluster_name: str,
        kubeconfig: str,
        output_format: Optional[str] = None,
        all_namespaces: bool = True,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Popeye scan on Kubernetes cluster

        Args:
            cluster_name: name of the cluster
            kubeconfig: kubeconfig content or path
            output_format: output format (html only), defaults to configured default
            all_namespaces: scan all namespaces
            namespace: specific namespace to scan

        Returns:
            Dictionary with scan results
        """
        logger.info(f"Starting Popeye scan for cluster: {cluster_name}")

        # Pre-flight validation
        self._validate_popeye_binary()

        # Set default format if not provided
        output_format = output_format or self.default_format

        # Validate all scan parameters
        self._validate_scan_parameters(cluster_name, kubeconfig, output_format, all_namespaces, namespace)

        # Validate namespace if specified
        await self._validate_namespace(cluster_name, kubeconfig, namespace)

        # Create temporary kubeconfig file
        kubeconfig_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(kubeconfig)
                kubeconfig_path = f.name

            # Build popeye command
            cmd = [self.popeye_path, f"--kubeconfig={kubeconfig_path}", f"--out={output_format}"]

            if all_namespaces:
                cmd.append("--all-namespaces")
            elif namespace:
                cmd.append(f"--namespace={namespace}")

            logger.info(f"Executing Popeye command: {' '.join(cmd)}")

            # Execute Popeye
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)

                if process.returncode != 0:
                    error_msg = f"Popeye execution failed: {stderr.decode()}"
                    logger.error(error_msg)
                    raise PopeyeExecutionError(error_msg)

                # Popeye only supports HTML format - return raw output
                scan_result = stdout.decode()

                logger.info(f"Popeye scan completed successfully for cluster: {cluster_name}")

                return {"cluster_name": cluster_name, "format": output_format, "result": scan_result, "success": True}

            except asyncio.TimeoutError:
                # Kill the process if it's still running
                if process and process.returncode is None:
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass

                error_msg = f"Popeye scan timed out after {self.timeout} seconds"
                logger.error(error_msg)
                raise PopeyeTimeoutError(error_msg)

        except (
            PopeyeBinaryNotFoundError,
            PopeyeBinaryNotExecutableError,
            PopeyeTimeoutError,
            PopeyeExecutionError,
            PopeyeParseError,
        ):
            # Re-raise specific Popeye exceptions
            raise
        except Exception as e:
            error_msg = f"Popeye scan failed: {str(e)}"
            logger.error(error_msg)
            raise PopeyeError(error_msg)
        finally:
            # Clean up temporary kubeconfig file
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                try:
                    os.unlink(kubeconfig_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary kubeconfig file {kubeconfig_path}: {e}")

    async def create_inspection_result(self, cluster_name: str, scan_result: Dict[str, Any]) -> InspectionResult:
        """
        Create inspection result from Popeye scan

        Args:
            cluster_name: cluster name
            scan_result: result from run_popeye_scan

        Returns:
            InspectionResult object

        Raises:
            PopeyeParseError: If JSON parsing fails
            ValueError: If unsupported format or invalid data
        """
        output_format = scan_result.get("format", "unknown")
        raw_result = scan_result.get("result")

        # Popeye only supports HTML format
        if output_format != "html":
            raise ValueError(f"Unsupported output format '{output_format}'. Popeye only supports HTML format.")

        # Create a single item with the HTML content
        result = InspectionResult(cluster_name, "popeye")
        result.add_item(
            {
                "name": "Popeye HTML Report",
                "status": "completed",
                "description": "Popeye cluster scan report in HTML format",
                "severity": "info",
                "details": "HTML report content",
                "solution": "View the HTML content for detailed Popeye analysis",
                "popeye_result": raw_result,  # Store HTML as string
                "scan_format": "html",
            }
        )
        return result
