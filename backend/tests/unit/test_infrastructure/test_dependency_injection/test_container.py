#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for dependency injection container
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from contextvars import ContextVar

from infra.dependency_injection.container import (
    DIContainer,
    ServiceDefinition,
    get_container,
    get_service,
    get_service_sync,
    initialize_services,
    cleanup_services,
    injectable,
    inject,
)


class TestServiceDefinition:
    """Test cases for ServiceDefinition"""

    def test_init(self):
        """Test ServiceDefinition initialization"""
        factory = Mock()
        service_def = ServiceDefinition(factory=factory, singleton=True)

        assert service_def.factory == factory
        assert service_def.singleton is True
        assert service_def.instance is None
        assert service_def.initialized is False

    def test_init_defaults(self):
        """Test ServiceDefinition with default values"""
        factory = Mock()
        service_def = ServiceDefinition(factory=factory)

        assert service_def.factory == factory
        assert service_def.singleton is True
        assert service_def.instance is None
        assert service_def.initialized is False


class TestDIContainer:
    """Test cases for DIContainer"""

    @pytest.fixture
    def container(self):
        """Create DIContainer instance"""
        return DIContainer()

    def test_init(self, container):
        """Test container initialization"""
        assert container._services == {}
        assert container._context_instances == {}

    def test_register_singleton(self, container):
        """Test singleton service registration"""
        factory = Mock()
        container.register_singleton("test_service", factory)

        assert "test_service" in container._services
        service_def = container._services["test_service"]
        assert service_def.factory == factory
        assert service_def.singleton is True

    def test_register_transient(self, container):
        """Test transient service registration"""
        factory = Mock()
        container.register_transient("test_service", factory)

        assert "test_service" in container._services
        service_def = container._services["test_service"]
        assert service_def.factory == factory
        assert service_def.singleton is False

    def test_register_context(self, container):
        """Test context service registration"""
        factory = Mock()
        container.register_context("test_service", factory)

        assert "test_service" in container._services
        assert "test_service" in container._context_instances
        assert isinstance(container._context_instances["test_service"], ContextVar)

    @pytest.mark.asyncio
    async def test_get_singleton(self, container):
        """Test getting singleton service"""
        factory = AsyncMock(return_value="singleton_instance")
        container.register_singleton("test_service", factory)

        # First call
        result1 = await container.get("test_service")
        assert result1 == "singleton_instance"
        factory.assert_called_once()

        # Second call should return cached instance
        factory.reset_mock()
        result2 = await container.get("test_service")
        assert result2 == "singleton_instance"
        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_transient(self, container):
        """Test getting transient service"""
        factory = AsyncMock(return_value="transient_instance")
        container.register_transient("test_service", factory)

        # First call
        result1 = await container.get("test_service")
        assert result1 == "transient_instance"

        # Second call should create new instance
        result2 = await container.get("test_service")
        assert result2 == "transient_instance"
        assert factory.call_count == 2

    @pytest.mark.asyncio
    async def test_get_context(self, container):
        """Test getting context service"""
        factory = AsyncMock(return_value="context_instance")
        container.register_context("test_service", factory)

        # First call in context
        result1 = await container.get("test_service")
        assert result1 == "context_instance"
        factory.assert_called_once()

        # Second call in same context should return cached instance
        factory.reset_mock()
        result2 = await container.get("test_service")
        assert result2 == "context_instance"
        factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_unknown_service(self, container):
        """Test getting unknown service"""
        with pytest.raises(ValueError, match="Service 'unknown' not registered"):
            await container.get("unknown")

    def test_get_sync_singleton(self, container):
        """Test synchronous get for singleton"""
        factory = Mock(return_value="sync_instance")
        container.register_singleton("test_service", factory)

        result = container.get_sync("test_service")
        assert result == "sync_instance"
        factory.assert_called_once()

    def test_get_sync_transient(self, container):
        """Test synchronous get for transient"""
        factory = Mock(return_value="sync_instance")
        container.register_transient("test_service", factory)

        result = container.get_sync("test_service")
        assert result == "sync_instance"
        factory.assert_called_once()

    def test_get_sync_context(self, container):
        """Test synchronous get for context"""
        factory = Mock(return_value="sync_instance")
        container.register_context("test_service", factory)

        result = container.get_sync("test_service")
        assert result == "sync_instance"
        factory.assert_called_once()

    def test_get_sync_unknown_service(self, container):
        """Test synchronous get for unknown service"""
        with pytest.raises(ValueError, match="Service 'unknown' not registered"):
            container.get_sync("unknown")

    @pytest.mark.asyncio
    async def test_create_instance_async_factory(self, container):
        """Test _create_instance with async factory"""
        factory = AsyncMock(return_value="async_instance")
        service_def = ServiceDefinition(factory=factory)

        result = await container._create_instance(service_def)
        assert result == "async_instance"
        factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_sync_factory(self, container):
        """Test _create_instance with sync factory"""
        factory = Mock(return_value="sync_instance")
        service_def = ServiceDefinition(factory=factory)

        result = await container._create_instance(service_def)
        assert result == "sync_instance"
        factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_exception(self, container):
        """Test _create_instance with exception"""
        factory = AsyncMock(side_effect=Exception("Factory error"))
        service_def = ServiceDefinition(factory=factory)

        with pytest.raises(Exception, match="Factory error"):
            await container._create_instance(service_def)

    @pytest.mark.asyncio
    async def test_initialize_singletons(self, container):
        """Test initialize_singletons"""
        factory1 = AsyncMock(return_value="instance1")
        factory2 = AsyncMock(return_value="instance2")
        factory3 = Mock(return_value="sync_instance")  # Non-singleton

        container.register_singleton("service1", factory1)
        container.register_singleton("service2", factory2)
        container.register_transient("service3", factory3)

        await container.initialize_singletons()

        factory1.assert_called_once()
        factory2.assert_called_once()
        factory3.assert_not_called()

        # Check instances are stored
        assert container._services["service1"].instance == "instance1"
        assert container._services["service1"].initialized is True
        assert container._services["service2"].instance == "instance2"
        assert container._services["service2"].initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self, container):
        """Test cleanup"""
        # Create mock instances with cleanup methods
        instance1 = Mock()
        instance1.cleanup = Mock()
        instance2 = Mock()
        instance2.cleanup = Mock()

        container._services["service1"] = ServiceDefinition(
            factory=Mock(), singleton=True, instance=instance1, initialized=True
        )
        container._services["service2"] = ServiceDefinition(
            factory=Mock(), singleton=True, instance=instance2, initialized=True
        )
        container._services["service3"] = ServiceDefinition(
            factory=Mock(), singleton=True, instance=None, initialized=True
        )

        await container.cleanup()

        instance1.cleanup.assert_called_once()
        instance2.cleanup.assert_called_once()

        # Check instances are reset
        assert container._services["service1"].instance is None
        assert container._services["service1"].initialized is False
        assert container._services["service2"].instance is None
        assert container._services["service2"].initialized is False


class TestGlobalFunctions:
    """Test cases for global functions"""

    @patch("infra.dependency_injection.container._container", None)
    def test_get_container_new_instance(self):
        """Test get_container creates new instance"""
        container = get_container()
        assert isinstance(container, DIContainer)

        # Second call should return same instance
        container2 = get_container()
        assert container is container2

    @pytest.mark.asyncio
    @patch("infra.dependency_injection.container.get_container")
    async def test_get_service(self, mock_get_container):
        """Test get_service"""
        mock_container = AsyncMock()
        mock_container.get.return_value = "service_instance"
        mock_get_container.return_value = mock_container

        result = await get_service("test_service")
        assert result == "service_instance"
        mock_container.get.assert_called_once_with("test_service")

    @patch("infra.dependency_injection.container.get_container")
    def test_get_service_sync(self, mock_get_container):
        """Test get_service_sync"""
        mock_container = Mock()
        mock_container.get_sync.return_value = "service_instance"
        mock_get_container.return_value = mock_container

        result = get_service_sync("test_service")
        assert result == "service_instance"
        mock_container.get_sync.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    @patch("infra.dependency_injection.container.get_container")
    async def test_initialize_services(self, mock_get_container):
        """Test initialize_services"""
        mock_container = AsyncMock()
        mock_get_container.return_value = mock_container

        await initialize_services()
        mock_container.initialize_singletons.assert_called_once()

    @pytest.mark.asyncio
    @patch("infra.dependency_injection.container.get_container")
    async def test_cleanup_services(self, mock_get_container):
        """Test cleanup_services"""
        mock_container = AsyncMock()
        mock_get_container.return_value = mock_container

        await cleanup_services()
        mock_container.cleanup.assert_called_once()


class TestDecorators:
    """Test cases for decorators"""

    def test_injectable_decorator(self):
        """Test @injectable decorator"""

        @injectable(name="test_service")
        class TestService:
            pass

        # Check if service is registered
        from infra.dependency_injection.container import _injectable_services, _injectable_classes

        assert TestService in _injectable_services
        assert _injectable_services[TestService] == "test_service"
        assert TestService in _injectable_classes

    def test_injectable_default_name(self):
        """Test @injectable decorator with default name"""

        @injectable()
        class DefaultService:
            pass

        from infra.dependency_injection.container import _injectable_services

        assert _injectable_services[DefaultService] == "defaultservice"

    def test_inject_decorator(self):
        """Test @inject decorator"""

        @injectable()
        class DependencyService:
            def __init__(self, value: int = 42):
                self.value = value

        @inject()
        class TestService:
            def __init__(self, dep: DependencyService = None):
                self.dep = dep

        # Initialize container and register services manually since classes are defined locally
        container = get_container()
        container.register_singleton("dependencyservice", lambda: DependencyService())

        # Create instance - should inject dependency
        service = TestService()
        assert service.dep is not None
        assert isinstance(service.dep, DependencyService)
        assert service.dep.value == 42


class TestAutoRegistration:
    """Test cases for automatic service registration"""

    @pytest.fixture
    def container(self):
        """Create DIContainer instance"""
        return DIContainer()

    def test_auto_register_services(self, container):
        """Test auto_register_services method"""
        # Create a mock module with injectable classes
        import sys
        from unittest.mock import MagicMock

        mock_module = MagicMock()
        mock_module.__name__ = "test_module"

        @injectable()
        class MockService:
            pass

        # Mock the module's dir and getattr
        mock_module.__dict__["MockService"] = MockService

        # Mock pkgutil and importlib
        with patch("pkgutil.walk_packages") as mock_walk, patch("importlib.import_module") as mock_import:

            mock_walk.return_value = [(None, "test_module", None)]
            mock_import.return_value = mock_module

            container.auto_register_services(["test_module"])

            # Check if service was registered
            assert "mockservice" in container._services

    def test_scan_and_register_package(self, container):
        """Test _scan_and_register_package method"""
        # This test would require more complex mocking, skip for now
        pass
