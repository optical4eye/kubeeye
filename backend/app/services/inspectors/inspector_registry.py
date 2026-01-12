#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspector registry for dynamic inspector management
"""

from typing import Dict, Any, List
from abc import ABC, abstractmethod

from services.inspectors.base_inspector import BaseInspector
from core.logging import get_logger

logger = get_logger(__name__)


class InspectorFactory(ABC):
    """Abstract factory for creating inspectors"""

    @abstractmethod
    def create_inspector(self, config: Dict[str, Any], use_gitops: bool = False) -> BaseInspector:
        """Create an inspector instance"""
        pass

    @abstractmethod
    def can_create(self, config: Dict[str, Any]) -> bool:
        """Check if this factory can create an inspector for the given config"""
        pass


class NodeInspectorFactory(InspectorFactory):
    """Factory for NodeInspector"""

    def can_create(self, config: Dict[str, Any]) -> bool:
        return "nodes" in config and config["nodes"]

    def create_inspector(self, config: Dict[str, Any], use_gitops: bool = False) -> BaseInspector:
        from services.inspectors.node.node_inspector import NodeInspector

        return NodeInspector(config["nodes"], use_gitops=use_gitops)


class OpaInspectorFactory(InspectorFactory):
    """Factory for OpaInspector"""

    def can_create(self, config: Dict[str, Any]) -> bool:
        return "opa" in config

    def create_inspector(self, config: Dict[str, Any], use_gitops: bool = False) -> BaseInspector:
        from services.inspectors.opa.opa_inspector import OpaInspector

        return OpaInspector(config["opa"], use_gitops=use_gitops)


class InspectorRegistry:
    """Registry for inspector factories"""

    def __init__(self):
        self._factories: Dict[str, InspectorFactory] = {}
        self._register_default_factories()

    def _register_default_factories(self):
        """Register default inspector factories"""
        self.register_factory("node", NodeInspectorFactory())
        self.register_factory("opa", OpaInspectorFactory())

    def register_factory(self, inspector_type: str, factory: InspectorFactory):
        """Register an inspector factory"""
        self._factories[inspector_type] = factory
        logger.info(f"Registered factory for inspector type: {inspector_type}")

    def get_available_types(self) -> List[str]:
        """Get list of available inspector types"""
        return list(self._factories.keys())

    def create_inspectors(self, config: Dict[str, Any], use_gitops: bool = False) -> Dict[str, BaseInspector]:
        """Create inspectors based on configuration"""
        inspectors = {}

        for inspector_type, factory in self._factories.items():
            if factory.can_create(config):
                try:
                    inspector = factory.create_inspector(config, use_gitops)
                    inspectors[inspector_type] = inspector
                    logger.info(f"Created inspector: {inspector_type}")
                except Exception as e:
                    logger.error(f"Failed to create inspector {inspector_type}: {e}")

        return inspectors


# Global registry instance
inspector_registry = InspectorRegistry()
