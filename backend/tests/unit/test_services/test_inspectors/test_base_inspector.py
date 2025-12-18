#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for base inspector module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict


class TestBaseInspector:
    """Test cases for BaseInspector class"""

    def test_base_inspector_initialization(self):
        """Test BaseInspector initialization"""
        config = {"test_param": "test_value"}

        # Create a mock inspector class
        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            # Import inside test to avoid import errors
            from services.inspectors.base_inspector import BaseInspector

            # Create a test implementation
            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            assert inspector.config == config
            assert inspector.use_gitops is False
            assert inspector.rules == []
            assert hasattr(inspector, "rule_processor")

    def test_base_inspector_with_gitops(self):
        """Test BaseInspector initialization with GitOps"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config, use_gitops=True)

            assert inspector.use_gitops is True
            mock_load_rules.assert_called_once_with(rule_type="test", use_gitops=True, include_disabled=True)

    def test_load_rules(self):
        """Test rule loading"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = True

        mock_rule2 = Mock()
        mock_rule2.id = "rule2"
        mock_rule2.name = "Test Rule 2"
        mock_rule2.type = "test"
        mock_rule2.enabled = False

        rules = [mock_rule1, mock_rule2]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            assert inspector.rules == rules
            mock_load_rules.assert_called_once_with(rule_type="test", use_gitops=False, include_disabled=True)

    def test_get_rule_by_id(self):
        """Test getting rule by ID"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = True

        mock_rule2 = Mock()
        mock_rule2.id = "rule2"
        mock_rule2.name = "Test Rule 2"
        mock_rule2.type = "test"
        mock_rule2.enabled = False

        rules = [mock_rule1, mock_rule2]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Test existing rule
            rule = inspector.get_rule_by_id("rule1")
            assert rule is not None
            assert rule.id == "rule1"

            # Test non-existing rule
            rule = inspector.get_rule_by_id("nonexistent")
            assert rule is None

    @pytest.mark.asyncio
    async def test_run_inspection_success(self):
        """Test successful inspection run"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = True

        mock_rule2 = Mock()
        mock_rule2.id = "rule2"
        mock_rule2.name = "Test Rule 2"
        mock_rule2.type = "test"
        mock_rule2.enabled = True

        rules = [mock_rule1, mock_rule2]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            result = await inspector.run_inspection("test_cluster")

            assert result.cluster_name == "test_cluster"
            assert result.inspection_type == "test"

    @pytest.mark.asyncio
    async def test_run_inspection_with_rule_ids(self):
        """Test inspection run with specific rule IDs"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = True

        mock_rule2 = Mock()
        mock_rule2.id = "rule2"
        mock_rule2.name = "Test Rule 2"
        mock_rule2.type = "test"
        mock_rule2.enabled = True

        rules = [mock_rule1, mock_rule2]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            result = await inspector.run_inspection("test_cluster", rule_ids=["rule1"])

            assert result.cluster_name == "test_cluster"
            assert result.inspection_type == "test"

    @pytest.mark.asyncio
    async def test_run_inspection_no_enabled_rules(self):
        """Test inspection run with no enabled rules"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = False

        mock_rule2 = Mock()
        mock_rule2.id = "rule2"
        mock_rule2.name = "Test Rule 2"
        mock_rule2.type = "test"
        mock_rule2.enabled = False

        rules = [mock_rule1, mock_rule2]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            result = await inspector.run_inspection("test_cluster")

            assert result.cluster_name == "test_cluster"
            assert result.inspection_type == "test"
            assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_run_inspection_with_exception(self):
        """Test inspection run with exception"""
        config = {"test_param": "test_value"}

        # Create mock rules
        mock_rule1 = Mock()
        mock_rule1.id = "rule1"
        mock_rule1.name = "Test Rule 1"
        mock_rule1.type = "test"
        mock_rule1.enabled = True

        rules = [mock_rule1]

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = rules

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    raise Exception("Test error")

            inspector = TestInspector(config)

            result = await inspector.run_inspection("test_cluster")

            assert result.cluster_name == "test_cluster"
            assert result.inspection_type == "test"

    def test_prepare_context(self):
        """Test context preparation"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            context = inspector._prepare_context("test_cluster")

            assert context == {"cluster_name": "test_cluster"}

    def test_should_apply_rule(self):
        """Test rule applicability check"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            context = {"cluster_name": "test_cluster"}

            # Default implementation always returns True
            should_apply = inspector._should_apply_rule(mock_rule, context)

            assert should_apply is True

    def test_validate_rule_config(self):
        """Test rule configuration validation"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            # Default implementation returns empty list
            issues = inspector._validate_rule_config(mock_rule)

            assert issues == []

    def test_get_rule_config(self):
        """Test getting rule configuration"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.config = {"execution": {"command": "ls -la"}}

            with patch.object(inspector.rule_processor, "get_rule_config") as mock_get_config:
                mock_get_config.return_value = "ls -la"

                result = inspector.get_rule_config(mock_rule, "execution.command")

                assert result == "ls -la"
                mock_get_config.assert_called_once_with(mock_rule, "execution.command", None)

    def test_format_invalid_result(self):
        """Test formatting invalid result"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            with patch.object(inspector.rule_processor.result_formatter, "invalid_result") as mock_format:
                mock_format.return_value = {"status": "invalid", "description": "Test"}

                result = inspector._format_invalid_result(mock_rule, "Test description", "Test details")

                assert result["status"] == "invalid"
                mock_format.assert_called_once_with(mock_rule, "Test description", "Test details")

    def test_format_not_applicable_result(self):
        """Test formatting not applicable result"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            with patch.object(inspector.rule_processor.result_formatter, "not_applicable_result") as mock_format:
                mock_format.return_value = {"status": "not_applicable", "reason": "Test"}

                result = inspector._format_not_applicable_result(mock_rule, "Test reason")

                assert result["status"] == "not_applicable"
                mock_format.assert_called_once_with(mock_rule, "Test reason")

    def test_format_skipped_result(self):
        """Test formatting skipped result"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            with patch.object(inspector.rule_processor.result_formatter, "skipped_result") as mock_format:
                mock_format.return_value = {"status": "skipped", "reason": "Test"}

                result = inspector._format_skipped_result(mock_rule, "Test reason")

                assert result["status"] == "skipped"
                mock_format.assert_called_once_with(mock_rule, "Test reason")

    def test_format_error_result(self):
        """Test formatting error result"""
        config = {"test_param": "test_value"}

        with patch("services.inspectors.base_inspector.load_rules") as mock_load_rules:
            mock_load_rules.return_value = []

            from services.inspectors.base_inspector import BaseInspector

            class TestInspector(BaseInspector):
                @property
                def inspector_type(self) -> str:
                    return "test"

                async def _apply_rule(self, rule, context: Dict) -> Dict:
                    return {"rule_id": rule.id, "status": "passed"}

            inspector = TestInspector(config)

            # Create mock rule
            mock_rule = Mock()
            mock_rule.id = "rule1"
            mock_rule.name = "Test Rule 1"
            mock_rule.type = "test"
            mock_rule.enabled = True

            with patch.object(inspector.rule_processor.result_formatter, "error_result") as mock_format:
                mock_format.return_value = {"status": "error", "description": "Test"}

                result = inspector._format_error_result(mock_rule, "Test description", "Test error")

                assert result["status"] == "error"
                mock_format.assert_called_once_with(mock_rule, "Test error", "Test description")
