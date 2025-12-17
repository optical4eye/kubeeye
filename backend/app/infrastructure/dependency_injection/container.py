#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency Injection Container for managing application instances
"""

import logging
from typing import Dict, Any, Optional, TypeVar, Type, Callable
from dataclasses import dataclass
from contextvars import ContextVar
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ServiceDefinition:
    """Service definition for DI container"""

    factory: Callable
    singleton: bool = True
    instance: Optional[Any] = None
    initialized: bool = False


class DIContainer:
    """
    Dependency Injection Container

    Manages service instances and their lifecycle.
    Supports singleton and transient services.
    """

    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._context_instances: Dict[str, ContextVar] = {}

    def register_singleton(self, name: str, factory: Callable) -> None:
        """Register a singleton service"""
        self._services[name] = ServiceDefinition(factory=factory, singleton=True)
        logger.debug(f"Registered singleton service: {name}")

    def register_transient(self, name: str, factory: Callable) -> None:
        """Register a transient service (new instance each time)"""
        self._services[name] = ServiceDefinition(factory=factory, singleton=False)
        logger.debug(f"Registered transient service: {name}")

    def register_context(self, name: str, factory: Callable) -> None:
        """Register a context-scoped service"""
        self._services[name] = ServiceDefinition(factory=factory, singleton=False)
        self._context_instances[name] = ContextVar(f"di_{name}")
        logger.debug(f"Registered context service: {name}")

    async def get(self, name: str) -> Any:
        """Get service instance"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")

        service_def = self._services[name]

        # Context-scoped service
        if name in self._context_instances:
            context_var = self._context_instances[name]
            instance = context_var.get(None)
            if instance is None:
                instance = await self._create_instance(service_def)
                context_var.set(instance)
            return instance

        # Singleton service
        if service_def.singleton:
            if not service_def.initialized:
                service_def.instance = await self._create_instance(service_def)
                service_def.initialized = True
            return service_def.instance

        # Transient service
        return await self._create_instance(service_def)

    def get_sync(self, name: str) -> Any:
        """Get service instance synchronously (for non-async factories)"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")

        service_def = self._services[name]

        # Context-scoped service
        if name in self._context_instances:
            context_var = self._context_instances[name]
            instance = context_var.get(None)
            if instance is None:
                instance = service_def.factory()
                context_var.set(instance)
            return instance

        # Singleton service
        if service_def.singleton:
            if not service_def.initialized:
                service_def.instance = service_def.factory()
                service_def.initialized = True
            return service_def.instance

        # Transient service
        return service_def.factory()

    async def _create_instance(self, service_def: ServiceDefinition) -> Any:
        """Create service instance"""
        try:
            if asyncio.iscoroutinefunction(service_def.factory):
                return await service_def.factory()
            else:
                return service_def.factory()
        except Exception as e:
            logger.error(f"Failed to create service instance: {e}")
            raise

    async def initialize_singletons(self) -> None:
        """Initialize all singleton services"""
        for name, service_def in self._services.items():
            if service_def.singleton and not service_def.initialized:
                try:
                    service_def.instance = await self._create_instance(service_def)
                    service_def.initialized = True
                    logger.info(f"Initialized singleton service: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize singleton service {name}: {e}")

    async def cleanup(self) -> None:
        """Cleanup all services"""
        for name, service_def in self._services.items():
            if service_def.instance and hasattr(service_def.instance, "cleanup"):
                try:
                    if asyncio.iscoroutinefunction(service_def.instance.cleanup):
                        await service_def.instance.cleanup()
                    else:
                        service_def.instance.cleanup()
                    logger.info(f"Cleaned up service: {name}")
                except Exception as e:
                    logger.error(f"Failed to cleanup service {name}: {e}")

        # Reset instances
        for service_def in self._services.values():
            service_def.instance = None
            service_def.initialized = False


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container"""
    global _container
    if _container is None:
        _container = DIContainer()
        _register_default_services()
    return _container


def _register_default_services() -> None:
    """Register default services"""
    container = get_container()

    # Register task queue as singleton service
    async def task_queue_factory():
        from infrastructure.tasks.task_queue import AsyncTaskQueue

        return AsyncTaskQueue(max_workers=3, queue_size=50)

    container.register_singleton("task_queue", task_queue_factory)

    # Register SSH connection pool as singleton
    async def ssh_pool_factory():
        from infrastructure.security.ssh_connection_pool import SSHConnectionPool

        return SSHConnectionPool()

    container.register_singleton("ssh_pool", ssh_pool_factory)

    # Register rule manager as singleton
    def rule_manager_factory():
        from infrastructure.rules.rule_manager import RuleManager

        return RuleManager()

    container.register_singleton("rule_manager", rule_manager_factory)


# Convenience functions
async def get_service(name: str) -> Any:
    """Get service from container"""
    return await get_container().get(name)


def get_service_sync(name: str) -> Any:
    """Get service from container synchronously"""
    return get_container().get_sync(name)


async def initialize_services() -> None:
    """Initialize all singleton services"""
    await get_container().initialize_singletons()


async def cleanup_services() -> None:
    """Cleanup all services"""
    await get_container().cleanup()
