#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task execution module for scheduled inspections
"""

import logging
from typing import Tuple, Optional, Dict, Any

from services.components.inspection_engine import execute_inspection_unified
from infrastructure.rules.rule_manager import RuleManager

logger = logging.getLogger(__name__)


def execute_inspection_task(
    task, show_progress: bool = False
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute inspection task for scheduled tasks

    Args:
        task: ScheduleTask object
        show_progress: whether to show progress

    Returns:
        (success, message, results)
    """
    try:
        cluster_name = task.cluster
        rules = task.rules

        # Convert rules format if needed
        selected_rules = {}
        if rules:
            for rule_type, rule_config in rules.items():
                if isinstance(rule_config, dict) and rule_config.get("enabled", False):
                    selected_rules[rule_type] = rule_config.get("rules", [])
                elif isinstance(rule_config, list):
                    selected_rules[rule_type] = rule_config

        # Determine whether to use GitOps rules
        use_gitops = RuleManager.should_use_gitops()

        logger.info(
            f"Executing scheduled task: {task.name} for cluster: {cluster_name}"
        )
        logger.info(f"Selected rules: {selected_rules}")
        logger.info(f"GitOps mode: {use_gitops}")

        success, message, results = execute_inspection_unified(
            cluster_name=cluster_name,
            selected_rules=selected_rules,
            inspection_type="scheduled",
            show_progress=show_progress,
            show_ui_feedback=False,
            use_gitops=use_gitops,
        )

        if success:
            logger.info(f"Task {task.name} completed successfully")
        else:
            logger.error(f"Task {task.name} failed: {message}")

        return success, message, results

    except Exception as e:
        error_msg = f"Task execution error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None
