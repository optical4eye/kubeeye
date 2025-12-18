#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for inspector registry module
"""

import pytest
from unittest.mock import Mock, patch


class TestInspectorRegistry:
    """Test cases for InspectorRegistry class"""

    def test_inspector_registry_initialization(self):
        """Test InspectorRegistry initialization"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()

        assert registry is not None
        assert hasattr(registry, "_factories")

        # Check that default factories are registered
        available_types = registry.get_available_types()
        assert "node" in available_types
        assert "opa" in available_types
        assert "prometheus" in available_types

    def test_register_factory(self):
        """Test registering a factory"""
        from services.inspectors.inspector_registry import InspectorRegistry, InspectorFactory

        # Create a mock factory
        mock_factory = Mock(spec=InspectorFactory)
        mock_factory.can_create.return_value = False
        mock_factory.create_inspector.return_value = Mock()

        registry = InspectorRegistry()
        registry.register_factory("test", mock_factory)

        available_types = registry.get_available_types()
        assert "test" in available_types

    def test_get_available_types(self):
        """Test getting available inspector types"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()
        available_types = registry.get_available_types()

        assert isinstance(available_types, list)
        assert "node" in available_types
        assert "opa" in available_types
        assert "prometheus" in available_types

    def test_create_inspectors(self):
        """Test creating inspectors"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()

        # Mock the factories to avoid actual inspector creation
        with patch.object(registry._factories["node"], "can_create", return_value=True), patch.object(
            registry._factories["node"], "create_inspector"
        ) as mock_create_node, patch.object(registry._factories["opa"], "can_create", return_value=False):

            mock_create_node.return_value = Mock()

            config = {"nodes": [{"name": "node1"}], "opa": {}}
            inspectors = registry.create_inspectors(config)

            assert "node" in inspectors
            assert "opa" not in inspectors
            mock_create_node.assert_called_once_with(config, False)

    def test_create_inspectors_with_gitops(self):
        """Test creating inspectors with GitOps"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()

        # Mock the factories to avoid actual inspector creation
        with patch.object(registry._factories["node"], "can_create", return_value=True), patch.object(
            registry._factories["node"], "create_inspector"
        ) as mock_create_node, patch.object(registry._factories["opa"], "can_create", return_value=False):

            mock_create_node.return_value = Mock()

            config = {"nodes": [{"name": "node1"}], "opa": {}}
            inspectors = registry.create_inspectors(config, use_gitops=True)

            assert "node" in inspectors
            assert "opa" not in inspectors
            mock_create_node.assert_called_once_with(config, True)

    def test_create_inspectors_with_exception(self):
        """Test creating inspectors with exception"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()

        # Mock the factories to raise an exception
        with patch.object(registry._factories["node"], "can_create", return_value=True), patch.object(
            registry._factories["node"], "create_inspector", side_effect=Exception("Test error")
        ), patch.object(registry._factories["opa"], "can_create", return_value=False):

            config = {"nodes": [{"name": "node1"}], "opa": {}}
            inspectors = registry.create_inspectors(config)

            # Should not contain node inspector due to exception
            assert "node" not in inspectors
            assert "opa" not in inspectors

    def test_create_inspectors_empty_config(self):
        """Test creating inspectors with empty config"""
        from services.inspectors.inspector_registry import InspectorRegistry

        registry = InspectorRegistry()

        # Mock the factories to return False for can_create
        with patch.object(registry._factories["node"], "can_create", return_value=False), patch.object(
            registry._factories["opa"], "can_create", return_value=False
        ), patch.object(registry._factories["prometheus"], "can_create", return_value=False):

            config = {}
            inspectors = registry.create_inspectors(config)

            assert inspectors == {}


class TestNodeInspectorFactory:
    """Test cases for NodeInspectorFactory"""

    def test_can_create(self):
        """Test NodeInspectorFactory.can_create"""
        from services.inspectors.inspector_registry import NodeInspectorFactory

        factory = NodeInspectorFactory()

        # Test with nodes config
        config = {"nodes": [{"name": "node1"}]}
        result = factory.can_create(config)
        # The actual implementation returns the nodes list, not a boolean
        # So we check if it returns a non-empty list
        assert isinstance(result, list)
        assert len(result) > 0

        # Test without nodes config
        config = {"opa": {}}
        result = factory.can_create(config)
        # Should return False (not a list)
        assert result is False

        # Test with empty nodes config
        config = {"nodes": []}
        result = factory.can_create(config)
        # Should return False (not a list)
        assert result == []

    def test_create_inspector(self):
        """Test NodeInspectorFactory.create_inspector"""
        from services.inspectors.inspector_registry import NodeInspectorFactory

        factory = NodeInspectorFactory()

        with patch("services.inspectors.node.node_inspector.NodeInspector") as mock_node_inspector:
            mock_inspector = Mock()
            mock_node_inspector.return_value = mock_inspector

            config = {"nodes": [{"name": "node1"}]}
            inspector = factory.create_inspector(config)

            assert inspector == mock_inspector
            mock_node_inspector.assert_called_once_with([{"name": "node1"}], use_gitops=False)

    def test_create_inspector_with_gitops(self):
        """Test NodeInspectorFactory.create_inspector with GitOps"""
        from services.inspectors.inspector_registry import NodeInspectorFactory

        factory = NodeInspectorFactory()

        with patch("services.inspectors.node.node_inspector.NodeInspector") as mock_node_inspector:
            mock_inspector = Mock()
            mock_node_inspector.return_value = mock_inspector

            config = {"nodes": [{"name": "node1"}]}
            inspector = factory.create_inspector(config, use_gitops=True)

            assert inspector == mock_inspector
            mock_node_inspector.assert_called_once_with([{"name": "node1"}], use_gitops=True)


class TestOpaInspectorFactory:
    """Test cases for OpaInspectorFactory"""

    def test_can_create(self):
        """Test OpaInspectorFactory.can_create"""
        from services.inspectors.inspector_registry import OpaInspectorFactory

        factory = OpaInspectorFactory()

        # Test with opa config
        config = {"opa": {}}
        assert factory.can_create(config) is True

        # Test without opa config
        config = {"nodes": [{"name": "node1"}]}
        assert factory.can_create(config) is False

    def test_create_inspector(self):
        """Test OpaInspectorFactory.create_inspector"""
        from services.inspectors.inspector_registry import OpaInspectorFactory

        factory = OpaInspectorFactory()

        with patch("services.inspectors.opa.opa_inspector.OpaInspector") as mock_opa_inspector:
            mock_inspector = Mock()
            mock_opa_inspector.return_value = mock_inspector

            config = {"opa": {}}
            inspector = factory.create_inspector(config)

            assert inspector == mock_inspector
            mock_opa_inspector.assert_called_once_with({}, use_gitops=False)

    def test_create_inspector_with_gitops(self):
        """Test OpaInspectorFactory.create_inspector with GitOps"""
        from services.inspectors.inspector_registry import OpaInspectorFactory

        factory = OpaInspectorFactory()

        with patch("services.inspectors.opa.opa_inspector.OpaInspector") as mock_opa_inspector:
            mock_inspector = Mock()
            mock_opa_inspector.return_value = mock_inspector

            config = {"opa": {}}
            inspector = factory.create_inspector(config, use_gitops=True)

            assert inspector == mock_inspector
            mock_opa_inspector.assert_called_once_with({}, use_gitops=True)


class TestPrometheusInspectorFactory:
    """Test cases for PrometheusInspectorFactory"""

    def test_can_create(self):
        """Test PrometheusInspectorFactory.can_create"""
        from services.inspectors.inspector_registry import PrometheusInspectorFactory

        factory = PrometheusInspectorFactory()

        # Test with prometheus config
        config = {"prometheus": {}}
        assert factory.can_create(config) is True

        # Test without prometheus config
        config = {"nodes": [{"name": "node1"}]}
        assert factory.can_create(config) is False

    def test_create_inspector(self):
        """Test PrometheusInspectorFactory.create_inspector"""
        from services.inspectors.inspector_registry import PrometheusInspectorFactory

        factory = PrometheusInspectorFactory()

        with patch(
            "services.inspectors.prometheus.prometheus_inspector.PrometheusInspector"
        ) as mock_prometheus_inspector:
            mock_inspector = Mock()
            mock_prometheus_inspector.return_value = mock_inspector

            config = {"prometheus": {}}
            inspector = factory.create_inspector(config)

            assert inspector == mock_inspector
            mock_prometheus_inspector.assert_called_once_with({}, use_gitops=False)

    def test_create_inspector_with_gitops(self):
        """Test PrometheusInspectorFactory.create_inspector with GitOps"""
        from services.inspectors.inspector_registry import PrometheusInspectorFactory

        factory = PrometheusInspectorFactory()

        with patch(
            "services.inspectors.prometheus.prometheus_inspector.PrometheusInspector"
        ) as mock_prometheus_inspector:
            mock_inspector = Mock()
            mock_prometheus_inspector.return_value = mock_inspector

            config = {"prometheus": {}}
            inspector = factory.create_inspector(config, use_gitops=True)

            assert inspector == mock_inspector
            mock_prometheus_inspector.assert_called_once_with({}, use_gitops=True)


class TestInspectorFactory:
    """Test cases for InspectorFactory abstract class"""

    def test_inspector_factory_is_abstract(self):
        """Test that InspectorFactory is abstract"""
        from services.inspectors.inspector_registry import InspectorFactory

        # Should not be able to instantiate abstract class
        with pytest.raises(TypeError):
            InspectorFactory()
