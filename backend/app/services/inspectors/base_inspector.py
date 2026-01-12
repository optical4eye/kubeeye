#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base inspector class, defines common interfaces and basic functions for all inspectors
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Dict, List, Any, Optional, Union

from infra.results.inspection_result import InspectionResult
from infra.rules.rule_loader import Rule, load_rules
from services.inspectors.rule_processor import RuleProcessor
from core.common.unified_validation import ValidationManager
from core.common.unified_error_handler import ErrorHandler
from core.logging import get_logger

# Logging setup
logger = get_logger(__name__)


class BaseInspector(ABC):
    """Base inspector class, all inspector types must inherit from this class"""

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Inspector initialization

        Args:
            config: inspector configuration
            use_gitops: whether to use GitOps rules
        """
        self.config = config
        self.use_gitops = use_gitops
        self.rules = []
        self.rule_processor = RuleProcessor()
        self._load_rules()

    @property
    @abstractmethod
    def inspector_type(self) -> str:
        """Returns inspector type, e.g. 'node', 'opa'"""
        pass

    def _load_rules(self):
        """Load rules applicable to this inspector"""
        yaml_rules = load_rules(
            rule_type=self.inspector_type,
            use_gitops=self.use_gitops,
            include_disabled=True,
        )
        self.rules = yaml_rules  # Include all rules, enabled and disabled
        source_type = "GitOps" if self.use_gitops else "local"
        logger.info(f"Loaded {len(self.rules)} {source_type} rules for {self.inspector_type} inspection")

        # Log rule details for debugging
        enabled_rules = [rule for rule in self.rules if rule.enabled]
        disabled_rules = [rule for rule in self.rules if not rule.enabled]
        logger.info(f"Rules breakdown: {len(enabled_rules)} enabled, {len(disabled_rules)} disabled")
        if enabled_rules:
            logger.info("Enabled rules:")
            for rule in enabled_rules:
                logger.info(f"  - {rule.id}: {rule.name}")
        if disabled_rules:
            logger.info("Disabled rules:")
            for rule in disabled_rules:
                logger.info(f"  - {rule.id}: {rule.name}")

    @abstractmethod
    async def _apply_rule(self, rule: Rule, context: Dict) -> Union[Dict, List[Dict], None]:
        """
        Apply a single rule for inspection

        Args:
            rule: rule to apply
            context: inspection context

        Returns:
            Inspection result, can be a single result dict, list of results, or None (means rule is not applicable)
        """
        pass

    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """
        Get rule by ID

        Args:
            rule_id: rule ID

        Returns:
            Rule object, returns None if not found
        """
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def _filter_active_rules(self, rule_ids: Optional[List[str]] = None) -> List[Rule]:
        """
        Filter and return active (enabled) rules to execute

        Args:
            rule_ids: list of rule IDs to execute, if None, execute all rules

        Returns:
            List of active rules to execute
        """
        if rule_ids:
            active_rules = [rule for rule in self.rules if rule.id in rule_ids and rule.enabled]
            logger.info(f"Number of rules after filtering by specified IDs: {len(active_rules)}")
        else:
            active_rules = [rule for rule in self.rules if rule.enabled]
            logger.info(f"Using all enabled rules: {len(active_rules)}")

        if active_rules:
            logger.info(f"Preparing to execute {len(active_rules)} rules:")
            for rule in active_rules:
                logger.info(f"  - {rule.id}: {rule.name}")

        return active_rules

    async def _execute_single_rule(self, rule: Rule, context: Dict) -> Optional[Dict]:
        """
        Execute a single rule with proper error handling

        Args:
            rule: rule to execute
            context: inspection context

        Returns:
            Formatted result dict or None if rule should be skipped
        """
        try:
            logger.info(f"Starting execution of rule {rule.id}: {rule.name}")

            # Validate rule configuration
            validation_issues = self._validate_rule_config(rule)
            if validation_issues:
                logger.error(f"Rule {rule.id} has invalid configuration: {validation_issues}")
                return self._format_invalid_result(
                    rule,
                    "Rule configuration is invalid",
                    f"The following configuration issues prevent rule execution: {', '.join(validation_issues)}",
                )

            logger.info(f"Rule {rule.id} passed configuration validation")

            # Check if rule is applicable to current environment
            should_apply = self._should_apply_rule(rule, context)
            logger.info(f"Rule {rule.id} applicability check: {should_apply}")

            if not should_apply:
                logger.info(f"Rule {rule.id} is not applicable to current environment")
                return self._format_not_applicable_result(rule, "Rule is not applicable to current environment")

            # Apply the rule
            logger.info(f"Applying rule {rule.id}")
            inspection_result = await self._apply_rule(rule, context)

            # Ensure inspection_result is not a coroutine
            if asyncio.iscoroutine(inspection_result):
                inspection_result = await inspection_result

            if inspection_result:
                return await self._process_rule_result(rule, inspection_result)
            else:
                logger.info(f"Rule {rule.id} returned None or empty result, skipping")
                return None

        except Exception as e:
            logger.exception(f"Error executing rule {rule.id}: {str(e)}")
            return self._format_error_result(rule, f"Rule execution error: {str(e)}", str(e))

    async def _process_rule_result(self, rule: Rule, inspection_result: Any) -> Optional[Union[Dict, List[Dict]]]:
        """
        Process the result returned by a rule application

        Args:
            rule: rule that was executed
            inspection_result: result returned by _apply_rule

        Returns:
            Processed result dict, list of results, or None
        """
        logger.debug(
            "Rule %s applied, result type: %s, is coroutine: %s",
            rule.id,
            type(inspection_result),
            asyncio.iscoroutine(inspection_result),
        )

        # Handle single result or list of results
        if isinstance(inspection_result, list):
            logger.debug(f"Rule {rule.id} returned list of results, length: {len(inspection_result)}")
            # For node inspector, return all results from the list
            # For other inspectors, return first item as before for backward compatibility
            if inspection_result:
                if self.inspector_type == "node":
                    # For node inspector, return all results
                    processed_results = []
                    for item in inspection_result:
                        if asyncio.iscoroutine(item):
                            item = await item
                        if item:  # Only add non-None results
                            processed_results.append(item)
                    return processed_results if processed_results else None
                else:
                    # For other inspectors, return first item as before
                    item = inspection_result[0]
                    if asyncio.iscoroutine(item):
                        item = await item
                    return item
        else:
            logger.debug(
                "Rule %s returned single result, type: %s, is coroutine: %s",
                rule.id,
                type(inspection_result),
                asyncio.iscoroutine(inspection_result),
            )

            if isinstance(inspection_result, dict):
                if "items" in inspection_result:
                    logger.debug(f"inspection_result is dict with 'items', type: {type(inspection_result)}")
                    # Return first item from items list
                    return inspection_result["items"][0] if inspection_result["items"] else None
                elif "results" in inspection_result:
                    logger.debug(f"inspection_result is dict with 'results', type: {type(inspection_result)}")
                    # For node inspector, return all results from the results list
                    results_list = inspection_result["results"]
                    if self.inspector_type == "node":
                        # For node inspector, return all results
                        processed_results = []
                        for item in results_list:
                            if asyncio.iscoroutine(item):
                                item = await item
                            if item:  # Only add non-None results
                                processed_results.append(item)
                        return processed_results if processed_results else None
                    else:
                        # For other inspectors, return first item as before
                        return results_list[0] if results_list else None
                else:
                    return inspection_result
            else:
                return inspection_result

        return None

    async def run_inspection(self, cluster_name: str, rule_ids: Optional[List[str]] = None) -> InspectionResult:
        """
        Run inspection

        Args:
            cluster_name: cluster name
            rule_ids: list of rule IDs to execute, if None, execute all rules

        Returns:
            Inspection result object
        """
        source_type = "GitOps" if self.use_gitops else "local"
        logger.info(
            f"BaseInspector.run_inspection started - inspector type: {self.inspector_type}, cluster: {cluster_name}, source: {source_type}"
        )
        logger.info(f"Total available rules: {len(self.rules)}, specified rule IDs: {rule_ids}")

        result = InspectionResult(cluster_name, self.inspector_type)

        # Determine rules to execute
        active_rules = self._filter_active_rules(rule_ids)

        if not active_rules:
            logger.warning("No executable rules, inspection completed")
            return result

        # Prepare context
        context = self._prepare_context(cluster_name)
        logger.info(f"Context prepared: {context}")

        # Execute rules
        executed_count = 0
        for rule in active_rules:
            rule_result = await self._execute_single_rule(rule, context)
            if rule_result:
                # Handle both single results and lists of results
                if isinstance(rule_result, list):
                    for item in rule_result:
                        result.add_item(item)
                    logger.info(f"Rule {rule.id} added {len(rule_result)} results")
                else:
                    result.add_item(rule_result)
                    logger.info(f"Rule {rule.id} added 1 result")

            executed_count += 1
            logger.info(f"Rule {rule.id} executed ({executed_count}/{len(active_rules)})")

        logger.info(
            f"BaseInspector.run_inspection completed - inspector: {self.inspector_type}, rules executed: {executed_count}, results: {len(result.items)}"
        )
        return result

    def _prepare_context(self, cluster_name: str) -> Dict:
        """
        Prepare inspection context

        Args:
            cluster_name: cluster name

        Returns:
            Inspection context
        """
        return {"cluster_name": cluster_name}

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """
        Determine if rule should be applied to current context

        Args:
            rule: rule
            context: context

        Returns:
            Whether to apply the rule
        """
        # Default implementation always returns True
        # Subclasses can override this method to implement more complex rule filtering
        return True

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """
        Check if rule configuration is valid

        Args:
            rule: rule object

        Returns:
            List of configuration issues, returns empty list if no issues
        """
        # Use ValidationManager for centralized validation
        return ValidationManager.validate_rule_config(self.inspector_type, rule.config)

    def get_rule_config(self, rule: Rule, path: str, default_value: Any = None) -> Any:
        """
        Get configuration value from rule, supports nested paths

        Args:
            rule: rule object
            path: configuration path, uses dot notation, e.g. "execution.command"
            default_value: default value returned if path doesn't exist

        Returns:
            Configuration value or default value
        """
        return self.rule_processor.get_rule_config(rule, path, default_value)

    def _format_invalid_result(self, rule: Rule, description: str, details: str) -> Dict:
        """
        Format result for rule with invalid configuration (delegated to ResultFormatter)

        Args:
            rule: rule object
            description: brief description
            details: detailed information

        Returns:
            Formatted result dictionary
        """
        return self.rule_processor.result_formatter.invalid_result(rule, description, details)

    def _format_not_applicable_result(self, rule: Rule, reason: str) -> Dict:
        """
        Format result for inapplicable rule (delegated to ResultFormatter)

        Args:
            rule: rule object
            reason: reason for inapplicability

        Returns:
            Formatted result dictionary
        """
        return self.rule_processor.result_formatter.not_applicable_result(rule, reason)

    def _format_skipped_result(self, rule: Rule, reason: str) -> Dict:
        """
        Format result for skipped rule (delegated to ResultFormatter)

        Args:
            rule: rule object
            reason: reason for skipping

        Returns:
            Formatted result dictionary
        """
        return self.rule_processor.result_formatter.skipped_result(rule, reason)

    def _format_error_result(self, rule: Rule, description: str, error: str) -> Dict:
        """
        Format result for rule with error (using ErrorHandler)

        Args:
            rule: rule object
            description: error description
            error: error details

        Returns:
            Formatted result dictionary
        """
        return ErrorHandler.create_error_result(rule, error, description)
