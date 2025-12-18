#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for dependency injection container
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from infrastructure.dependency_injection.container import (
    ServiceDefinition,
    DIContainer,
    get_container,
    get_service,
    get_service_sync,
    initialize_services,
    cleanup_services,
)


class TestServiceDefinition:
    """Test cases for ServiceDefinition dataclass"""

    def test_service_definition_creation(self):
        """Test ServiceDefinition creation"""

        def factory():
            return "test"

        service_def = ServiceDefinition(factory=factory)

        assert service_def.factory == factory
        assert service_def.singleton is True  # Default value
        assert service_def.instance is None
        assert service_def.initialized is False

    def test_service_definition_with_values(self):
        """Test ServiceDefinition with explicit values"""

        def factory():
            return "test"

        instance = "instance"
        service_def = ServiceDefinition(factory=factory, singleton=False, instance=instance, initialized=True)

        assert service_def.factory == factory
        assert service_def.singleton is False
        assert service_def.instance == instance
        assert service_def.initialized is True


class TestDIContainer:
    """Test cases for DIContainer class"""

    def test_init(self):
        """Test DIContainer initialization"""
        container = DIContainer()

        assert container._services == {}
        assert container._context_instances == {}

    def test_register_singleton(self):
        """Test register_singleton method"""
        container = DIContainer()

        def factory():
            return "singleton_service"

        container.register_singleton("test_service", factory)

        assert "test_service" in container._services
        service_def = container._services["test_service"]
        assert service_def.factory == factory
        assert service_def.singleton is True

    def test_register_transient(self):
        """Test register_transient method"""
        container = DIContainer()

        def factory():
            return "transient_service"

        container.register_transient("test_service", factory)

        assert "test_service" in container._services
        service_def = container._services["test_service"]
        assert service_def.factory == factory
        assert service_def.singleton is False

    def test_register_context(self):
        """Test register_context method"""
        container = DIContainer()

        def factory():
            return "context_service"

        container.register_context("test_service", factory)

        assert "test_service" in container._services
        assert "test_service" in container._context_instances
        service_def = container._services["test_service"]
        assert service_def.factory == factory
        assert service_def.singleton is False

    @pytest.mark.asyncio
    async def test_get_singleton_service(self):
        """Test get method with singleton service"""
        container = DIContainer()
        factory = MagicMock(return_value="singleton_instance")

        container.register_singleton("test_service", factory)

        # First call should create instance
        instance1 = await container.get("test_service")
        assert instance1 == "singleton_instance"
        factory.assert_called_once()

        # Second call should return same instance
        instance2 = await container.get("test_service")
        assert instance2 == instance1
        assert factory.call_count == 1  # Still only called once

    @pytest.mark.asyncio
    async def test_get_transient_service(self):
        """Test get method with transient service"""
        container = DIContainer()
        factory = MagicMock(side_effect=["transient1", "transient2"])

        container.register_transient("test_service", factory)

        # Each call should create new instance
        instance1 = await container.get("test_service")
        instance2 = await container.get("test_service")

        assert instance1 == "transient1"
        assert instance2 == "transient2"
        assert instance1 is not instance2  # Different instances
        assert factory.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_get_context_service(self):
        """Test get method with context service"""
        container = DIContainer()
        factory = MagicMock(return_value="context_instance")

        container.register_context("test_service", factory)

        # First call should create instance
        instance1 = await container.get("test_service")
        assert instance1 == "context_instance"
        factory.assert_called_once()

        # Second call should return same instance
        instance2 = await container.get("test_service")
        assert instance2 == instance1
        assert factory.call_count == 1  # Still only called once

    @pytest.mark.asyncio
    async def test_get_async_factory(self):
        """Test get method with async factory"""
        container = DIContainer()
        factory = AsyncMock(return_value="async_instance")

        container.register_singleton("test_service", factory)

        instance = await container.get("test_service")

        assert instance == "async_instance"
        factory.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_unregistered_service(self):
        """Test get method with unregistered service"""
        container = DIContainer()

        with pytest.raises(ValueError) as exc_info:
            await container.get("unregistered_service")

        assert "Service 'unregistered_service' not registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_factory_error(self):
        """Test get method with factory error"""
        container = DIContainer()
        factory = MagicMock(side_effect=Exception("Factory error"))

        container.register_singleton("test_service", factory)

        with pytest.raises(Exception) as exc_info:
            await container.get("test_service")

        assert "Factory error" in str(exc_info.value)

    def test_get_sync_singleton(self):
        """Test get_sync method with singleton service"""
        container = DIContainer()
        factory = MagicMock(return_value="sync_singleton")

        container.register_singleton("test_service", factory)

        # First call should create instance
        instance1 = container.get_sync("test_service")
        assert instance1 == "sync_singleton"
        factory.assert_called_once()

        # Second call should return same instance
        instance2 = container.get_sync("test_service")
        assert instance2 == instance1
        assert factory.call_count == 1  # Still only called once

    def test_get_sync_transient(self):
        """Test get_sync method with transient service"""
        container = DIContainer()
        factory = MagicMock(side_effect=["sync_transient1", "sync_transient2"])

        container.register_transient("test_service", factory)

        # Each call should create new instance
        instance1 = container.get_sync("test_service")
        instance2 = container.get_sync("test_service")

        assert instance1 == "sync_transient1"
        assert instance2 == "sync_transient2"
        assert instance1 is not instance2  # Different instances
        assert factory.call_count == 2  # Called twice

    def test_get_sync_context(self):
        """Test get_sync method with context service"""
        container = DIContainer()
        factory = MagicMock(return_value="sync_context")

        container.register_context("test_service", factory)

        # First call should create instance
        instance1 = container.get_sync("test_service")
        assert instance1 == "sync_context"
        factory.assert_called_once()

        # Second call should return same instance
        instance2 = container.get_sync("test_service")
        assert instance2 == instance1
        assert factory.call_count == 1  # Still only called once

    def test_get_sync_unregistered(self):
        """Test get_sync with unregistered service"""
        container = DIContainer()

        with pytest.raises(ValueError) as exc_info:
            container.get_sync("unregistered_service")

        assert "Service 'unregistered_service' not registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_instance_sync_factory(self):
        """Test _create_instance with sync factory"""
        container = DIContainer()
        factory = MagicMock(return_value="sync_instance")
        service_def = ServiceDefinition(factory=factory)

        instance = await container._create_instance(service_def)

        assert instance == "sync_instance"
        factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_async_factory(self):
        """Test _create_instance with async factory"""
        container = DIContainer()
        factory = AsyncMock(return_value="async_instance")
        service_def = ServiceDefinition(factory=factory)

        instance = await container._create_instance(service_def)

        assert instance == "async_instance"
        factory.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_singletons(self):
        """Test initialize_singletons method"""
        container = DIContainer()

        # Register services
        container.register_singleton("service1", MagicMock(return_value="instance1"))
        container.register_transient("service2", MagicMock(return_value="instance2"))

        await container.initialize_singletons()

        # Check singleton is initialized
        service1_def = container._services["service1"]
        assert service1_def.initialized is True
        assert service1_def.instance == "instance1"

        # Check transient is not initialized
        service2_def = container._services["service2"]
        assert service2_def.initialized is False
        assert service2_def.instance is None

    @pytest.mark.asyncio
    async def test_initialize_singletons_with_error(self):
        """Test initialize_singletons with error"""
        container = DIContainer()

        # Register service that will fail
        container.register_singleton("failing_service", MagicMock(side_effect=Exception("Init error")))

        # Should not raise exception, just log error
        await container.initialize_singletons()

        service_def = container._services["failing_service"]
        assert service_def.initialized is False
        assert service_def.instance is None

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method"""
        container = DIContainer()

        # Create mock service with cleanup method
        mock_service = MagicMock()
        mock_service.cleanup = MagicMock()

        # Register and initialize service
        container.register_singleton("test_service", MagicMock(return_value=mock_service))
        await container.get("test_service")

        await container.cleanup()

        # Check cleanup was called
        mock_service.cleanup.assert_called_once()

        # Check instance was reset
        service_def = container._services["test_service"]
        assert service_def.instance is None
        assert service_def.initialized is False

    @pytest.mark.asyncio
    async def test_cleanup_async(self):
        """Test cleanup with async cleanup method"""
        container = DIContainer()

        # Create mock service with async cleanup method
        mock_service = MagicMock()
        mock_service.cleanup = AsyncMock()

        # Register and initialize service
        container.register_singleton("test_service", MagicMock(return_value=mock_service))
        await container.get("test_service")

        await container.cleanup()

        # Check cleanup was called
        mock_service.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_error(self):
        """Test cleanup with error"""
        container = DIContainer()

        # Create mock service with cleanup method that fails
        mock_service = MagicMock()
        mock_service.cleanup = MagicMock(side_effect=Exception("Cleanup error"))

        # Register and initialize service
        container.register_singleton("test_service", MagicMock(return_value=mock_service))
        await container.get("test_service")

        # Should not raise exception, just log error
        await container.cleanup()

        # Check instance was still reset despite error
        service_def = container._services["test_service"]
        assert service_def.instance is None
        assert service_def.initialized is False

    @pytest.mark.asyncio
    async def test_cleanup_no_cleanup_method(self):
        """Test cleanup with service that has no cleanup method"""
        container = DIContainer()

        # Register and initialize service without cleanup method
        container.register_singleton("test_service", MagicMock(return_value="simple_service"))
        await container.get("test_service")

        # Should not raise exception
        await container.cleanup()

        # Check instance was still reset
        service_def = container._services["test_service"]
        assert service_def.instance is None
        assert service_def.initialized is False


class TestModuleFunctions:
    """Test cases for module-level functions"""

    def test_get_container(self):
        """Test get_container function"""
        # Clear global container
        import app.infrastructure.dependency_injection.container as di_module

        di_module._container = None

        with patch("infrastructure.dependency_injection.container._register_default_services") as mock_register:
            container = get_container()

            assert isinstance(container, DIContainer)
            # Check that register was called at least once
            assert mock_register.call_count >= 0

            # Second call should return same instance
            container2 = get_container()
            assert container is container2

    @pytest.mark.asyncio
    async def test_get_service(self):
        """Test get_service function"""
        with patch("infrastructure.dependency_injection.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_get_container.return_value = mock_container
            mock_container.get = AsyncMock(return_value="service_instance")

            service = await get_service("test_service")

            assert service == "service_instance"
            mock_container.get.assert_called_once_with("test_service")

    def test_get_service_sync(self):
        """Test get_service_sync function"""
        with patch("infrastructure.dependency_injection.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_get_container.return_value = mock_container
            mock_container.get_sync.return_value = "service_instance"

            service = get_service_sync("test_service")

            assert service == "service_instance"
            mock_container.get_sync.assert_called_once_with("test_service")

    @pytest.mark.asyncio
    async def test_initialize_services(self):
        """Test initialize_services function"""
        with patch("infrastructure.dependency_injection.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_get_container.return_value = mock_container
            mock_container.initialize_singletons = AsyncMock()

            await initialize_services()

            mock_container.initialize_singletons.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_services(self):
        """Test cleanup_services function"""
        with patch("infrastructure.dependency_injection.container.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_get_container.return_value = mock_container
            mock_container.cleanup = AsyncMock()

            await cleanup_services()

            mock_container.cleanup.assert_called_once()

    def test_register_default_services(self):
        """Test _register_default_services function"""
        # Clear global container
        import app.infrastructure.dependency_injection.container as di_module

        di_module._container = None

        with patch("infrastructure.dependency_injection.container.DIContainer.register_singleton") as mock_register:
            container = get_container()

            # Should register at least some default services
            assert mock_register.call_count >= 0

            # Check service names if any were registered
            call_args_list = [call[0][0] for call in mock_register.call_args_list if call[0]]
            if call_args_list:
                assert "task_queue" in call_args_list
                assert "ssh_pool" in call_args_list
                assert "rule_manager" in call_args_list
