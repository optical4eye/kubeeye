#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependency Injection Container for managing application instances

This module provides a sophisticated DI container with automatic service registration
and dependency injection capabilities.

Features:
- Automatic service registration using @injectable decorator
- Dependency injection using @inject decorator or type hints
- Support for singleton, transient, and context-scoped services
- Automatic scanning of packages for injectable services

Usage:

1. Mark services as injectable:
   @injectable()
   class MyService:
       def __init__(self, config: ConfigService = None):
           self.config = config

2. Use dependency injection:
   @inject()
   class MyController:
       def __init__(self, service: MyService = None):
           self.service = service

3. Services are automatically registered and dependencies injected at runtime.
"""

from typing import Dict, Any, Optional, TypeVar, Type, Callable, List
from dataclasses import dataclass
from contextvars import ContextVar
import asyncio
import inspect
import importlib
import pkgutil

from core.logging import get_logger
from core.config.settings import settings

logger = get_logger(__name__)

T = TypeVar("T")

# Global registry for injectable services
_injectable_services: Dict[Type, str] = {}
_injectable_classes: List[Type] = []


def injectable(name: Optional[str] = None, singleton: bool = True):
    """Decorator to mark a class as injectable service"""

    def decorator(cls: Type[T]) -> Type[T]:
        service_name = name or cls.__name__.lower()
        _injectable_services[cls] = service_name
        _injectable_classes.append(cls)

        # Store metadata on the class
        cls._di_name = service_name
        cls._di_singleton = singleton
        return cls

    return decorator


def inject(service_name: Optional[str] = None):
    """Decorator to inject dependencies into class constructor"""

    def decorator(cls: Type[T]) -> Type[T]:
        original_init = cls.__init__

        def injected_init(self, *args, **kwargs):
            # Get container
            container = get_container()

            # Inject dependencies based on type hints
            init_signature = inspect.signature(original_init)
            for param_name, param in init_signature.parameters.items():
                if param_name == "self":
                    continue

                # Skip if already provided
                if param_name in kwargs or len(args) > 0:
                    continue

                # Try to inject by service name or type
                if service_name:
                    try:
                        kwargs[param_name] = container.get_sync(service_name)
                        continue
                    except ValueError:
                        pass

                # Try to inject by parameter name
                try:
                    kwargs[param_name] = container.get_sync(param_name)
                    continue
                except ValueError:
                    pass

                # Try to inject by type annotation
                if param.annotation != inspect.Parameter.empty:
                    for service_type, svc_name in _injectable_services.items():
                        if param.annotation == service_type or issubclass(param.annotation, service_type):
                            try:
                                kwargs[param_name] = container.get_sync(svc_name)
                                break
                            except ValueError:
                                continue

            return original_init(self, *args, **kwargs)

        cls.__init__ = injected_init
        return cls

    return decorator


@dataclass
class ServiceDefinition:
    """Service definition for DI container"""

    factory: Callable
    singleton: bool = True
    instance: Optional[Any] = None
    initialized: bool = False
    injectable: bool = False
    service_type: Optional[Type] = None


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

    def auto_register_services(self, package_names: List[str]) -> None:
        """Automatically register services from specified packages"""
        for package_name in package_names:
            self._scan_and_register_package(package_name)

    def _scan_and_register_package(self, package_name: str) -> None:
        """Scan package and register injectable services"""
        try:
            package = importlib.import_module(package_name)
            if hasattr(package, "__path__"):
                # It's a package, scan all modules
                for importer, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                    try:
                        module = importlib.import_module(modname)
                        self._register_injectable_classes_from_module(module)
                    except ImportError as e:
                        logger.warning(f"Failed to import module {modname}: {e}")
            else:
                # It's a module
                self._register_injectable_classes_from_module(package)
        except ImportError as e:
            logger.warning(f"Failed to import package {package_name}: {e}")

    def _register_injectable_classes_from_module(self, module) -> None:
        """Register injectable classes from a module"""
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isclass(obj) and hasattr(obj, "_di_name") and obj in _injectable_classes:
                service_name = getattr(obj, "_di_name")
                singleton = getattr(obj, "_di_singleton", True)

                # Create factory function that uses dependency injection
                def create_instance(cls):
                    return cls()

                if singleton:
                    self.register_singleton(service_name, lambda cls=obj: create_instance(cls))
                else:
                    self.register_transient(service_name, lambda cls=obj: create_instance(cls))

                logger.debug(f"Auto-registered service: {service_name} ({obj.__name__})")

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
            if inspect.iscoroutinefunction(service_def.factory):
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
                    if inspect.iscoroutinefunction(service_def.instance.cleanup):
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
        from infra.tasks.task_queue import AsyncTaskQueue

        return AsyncTaskQueue(max_workers=3, queue_size=50)

    container.register_singleton("task_queue", task_queue_factory)

    # Register rule manager as singleton
    def rule_manager_factory():
        from infra.rules.rule_manager import RuleManager

        return RuleManager()

    container.register_singleton("rule_manager", rule_manager_factory)

    # Register config as singleton service
    def config_factory():
        """Factory for application configuration"""

        # Basic configuration from settings
        config = {
            "log_level": settings.kubeeye_log_level,
            "gitops_repo_name": settings.kubeeye_gitops_repo_name,
            "gitops_repo_url": settings.kubeeye_gitops_repo_url,
            "gitops_repo_branch": settings.kubeeye_gitops_repo_branch,
            "gitops_repo_username": settings.kubeeye_gitops_repo_username,
            "gitops_repo_token": settings.kubeeye_gitops_repo_token,
            "gitops_repo_description": settings.kubeeye_gitops_repo_description,
            "report_retention_days": settings.kubeeye_report_retention_days,
            "ssh_connection_timeout": settings.kubeeye_ssh_connection_timeout,
            "ssh_max_concurrent_checks": settings.kubeeye_ssh_max_concurrent_checks,
            # Add empty structures for inspectors
            "nodes": [],
            "opa": {"kubeconfig": ""},
        }

        return config

    container.register_singleton("config", config_factory)

    # Register scheduler as singleton service
    async def scheduler_factory():
        from infra.tasks.apscheduler_adapter import APSchedulerAdapter

        return APSchedulerAdapter()

    container.register_singleton("scheduler", scheduler_factory)

    # Register task executor as singleton service
    async def task_executor_factory():
        from infra.tasks.async_task_executor import AsyncTaskExecutor

        return AsyncTaskExecutor()

    container.register_singleton("task_executor", task_executor_factory)

    # Register task repository as singleton service
    async def task_repository_factory():
        from infra.tasks.database_task_repository import DatabaseTaskRepository

        return DatabaseTaskRepository()

    container.register_singleton("task_repository", task_repository_factory)

    # Register task manager as singleton service
    async def task_manager_factory():
        from infra.tasks.task_manager import TaskManager

        scheduler = await get_container().get("scheduler")
        task_executor = await get_container().get("task_executor")
        task_repository = await get_container().get("task_repository")

        return TaskManager(scheduler, task_executor, task_repository)

    container.register_singleton("task_manager", task_manager_factory)

    # Auto-register injectable services from specified packages
    packages_to_scan = [
        "infra.tasks",
        "infra.security",
        "infra.rules",
        "services.components",
        "services.inspectors",
        "db.repositories",
    ]
    container.auto_register_services(packages_to_scan)


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
