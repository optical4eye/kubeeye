#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified inspection orchestrator with clear separation of concerns
"""

from typing import Dict, List, Any, Optional
import asyncio
from core.logging import get_logger
from services.inspectors.base_inspector import BaseInspector

logger = get_logger(__name__)


class InspectionOrchestrator:
    """Simplified inspection orchestrator with clear separation of concerns"""

    def __init__(self, inspectors: Dict[str, BaseInspector]):
        """
        Initialize orchestrator with available inspectors

        Args:
            inspectors: Dictionary of inspector name to inspector instance
        """
        self.inspectors = inspectors
        self._results: Dict[str, Any] = {}

    async def orchestrate(self, cluster_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate inspection execution

        Args:
            cluster_name: Name of the cluster
            config: Inspection configuration

        Returns:
            Dictionary with inspection results
        """
        logger.info(f"Starting inspection orchestration for cluster: {cluster_name}")

        # Determine which inspectors to run
        active_inspectors = self._get_active_inspectors(config)

        if not active_inspectors:
            logger.warning("No active inspectors found for configuration")
            return {"status": "skipped", "message": "No active inspectors"}

        # Execute inspections in parallel
        tasks = [
            self._run_inspector(inspector_name, inspector, cluster_name, config)
            for inspector_name, inspector in active_inspectors.items()
        ]

        # Wait for all inspections to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        self._results = {}
        for i, (inspector_name, _) in enumerate(active_inspectors.items()):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Inspector {inspector_name} failed: {result}")
                self._results[inspector_name] = {"status": "failed", "error": str(result)}
            else:
                self._results[inspector_name] = result

        logger.info(f"Inspection orchestration completed for cluster: {cluster_name}")
        return self._results

    def _get_active_inspectors(self, config: Dict[str, Any]) -> Dict[str, BaseInspector]:
        """
        Get active inspectors based on configuration

        Args:
            config: Inspection configuration

        Returns:
            Dictionary of active inspectors
        """
        active = {}

        for name, inspector in self.inspectors.items():
            if self._should_run_inspector(name, config):
                active[name] = inspector
                logger.debug(f"Inspector {name} is active")

        return active

    def _should_run_inspector(self, inspector_name: str, config: Dict[str, Any]) -> bool:
        """
        Determine if inspector should run

        Args:
            inspector_name: Name of the inspector
            config: Inspection configuration

        Returns:
            True if inspector should run, False otherwise
        """
        # Simple logic: run if enabled in config
        return config.get(f"enable_{inspector_name}", True)

    async def _run_inspector(
        self, inspector_name: str, inspector: BaseInspector, cluster_name: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a single inspector

        Args:
            inspector_name: Name of the inspector
            inspector: Inspector instance
            cluster_name: Name of the cluster
            config: Inspection configuration

        Returns:
            Inspection result
        """
        try:
            logger.info(f"Running {inspector_name} inspector for cluster: {cluster_name}")
            result = await inspector.run_inspection(cluster_name)
            logger.info(f"{inspector_name} inspector completed for cluster: {cluster_name}")
            return {"status": "completed", "result": result}
        except Exception as e:
            logger.error(f"{inspector_name} inspector failed for cluster {cluster_name}: {e}")
            raise

    def get_results(self) -> Dict[str, Any]:
        """
        Get inspection results

        Returns:
            Dictionary with inspection results
        """
        return self._results

    def get_inspector_status(self, inspector_name: str) -> Optional[str]:
        """
        Get status of a specific inspector

        Args:
            inspector_name: Name of the inspector

        Returns:
            Status string or None if inspector not found
        """
        if inspector_name not in self._results:
            return None

        result = self._results[inspector_name]
        return result.get("status", "unknown")

    def get_failed_inspectors(self) -> List[str]:
        """
        Get list of failed inspectors

        Returns:
            List of inspector names that failed
        """
        failed = []
        for name, result in self._results.items():
            if result.get("status") == "failed":
                failed.append(name)
        return failed

    def get_successful_inspectors(self) -> List[str]:
        """
        Get list of successful inspectors

        Returns:
            List of inspector names that succeeded
        """
        successful = []
        for name, result in self._results.items():
            if result.get("status") == "completed":
                successful.append(name)
        return successful

    def reset_results(self):
        """Reset inspection results"""
        self._results = {}
        logger.debug("Inspection results reset")
