#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base inspector class, defines common interfaces and basic functions for all inspectors
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Any, Optional, Union

from infrastructure.results.inspection_result import InspectionResult
from infrastructure.rules.rule_loader import Rule, load_rules
from services.inspectors.rule_processor import RuleProcessor

# Logging setup
logger = logging.getLogger(__name__)


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
        """Returns inspector type, e.g. 'node', 'opa', 'prometheus'"""
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

    @abstractmethod
    def _apply_rule(self, rule: Rule, context: Dict) -> Union[Dict, List[Dict], None]:
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

    def run_inspection(self, cluster_name: str, rule_ids: List[str] = None) -> InspectionResult:
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
        if rule_ids:
            active_rules = [
                rule for rule in self.rules if rule.id in rule_ids and rule.enabled
            ]  # Only execute enabled rules
            logger.info(f"Number of rules after filtering by specified IDs: {len(active_rules)}")
        else:
            active_rules = [rule for rule in self.rules if rule.enabled]  # Only execute enabled rules
            logger.info(f"Using all enabled rules: {len(active_rules)}")

        if not active_rules:
            logger.warning("No executable rules, inspection completed")
            return result

        logger.info(f"Preparing to execute {len(active_rules)} rules:")
        for rule in active_rules:
            logger.info(f"  - {rule.id}: {rule.name}")

        # Execute rules
        context = self._prepare_context(cluster_name)
        logger.info(f"Context prepared: {context}")

        executed_count = 0
        for rule in active_rules:
            try:
                logger.info(f"Starting execution of rule {rule.id}: {rule.name}")

                # Validate rule configuration
                validation_issues = self._validate_rule_config(rule)
                if validation_issues:
                    logger.error(f"Rule {rule.id} has invalid configuration: {validation_issues}")
                    # Rule configuration is invalid
                    result.add_item(
                        self._format_invalid_result(
                            rule,
                            "Rule configuration is invalid",
                            f"The following configuration issues prevent rule execution: {', '.join(validation_issues)}",
                        )
                    )
                    continue

                else:
                    logger.info(f"Rule {rule.id} passed configuration validation")
                # Check if rule is applicable to current environment
                should_apply = self._should_apply_rule(rule, context)
                logger.info(f"Rule {rule.id} applicability check: {should_apply}")

                if should_apply:
                    logger.info(f"Applying rule {rule.id}")
                    inspection_result = self._apply_rule(rule, context)
                    logger.info(f"Rule {rule.id} applied, result type: {type(inspection_result)}")

                    if inspection_result:
                        # Handle single result or list of results
                        if isinstance(inspection_result, list):
                            logger.info(f"Rule {rule.id} returned list of results, length: {len(inspection_result)}")
                            for item in inspection_result:
                                result.add_item(item)
                        else:
                            logger.info(f"Rule {rule.id} returned single result")
                            result.add_item(inspection_result)
                    else:
                        logger.warning(f"Rule {rule.id} returned empty result")
                else:
                    logger.info(f"Rule {rule.id} is not applicable to current environment")
                    # Rule is not applicable to current environment
                    result.add_item(
                        self._format_not_applicable_result(rule, "Rule is not applicable to current environment")
                    )

                executed_count += 1
                logger.info(f"Rule {rule.id} executed ({executed_count}/{len(active_rules)})")

            except Exception as e:
                logger.exception(f"Error executing rule {rule.id}: {str(e)}")
                error_result = self._format_error_result(rule, f"Rule execution error: {str(e)}", str(e))
                result.add_item(error_result)

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
        # Subclasses should override this method to implement validation logic for specific rule types
        return []

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
        Format result for rule with error (delegated to ResultFormatter)

        Args:
            rule: rule object
            description: error description
            error: error details

        Returns:
            Formatted result dictionary
        """
        return self.rule_processor.result_formatter.error_result(rule, error, description)
