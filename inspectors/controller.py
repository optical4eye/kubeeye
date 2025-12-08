#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspection controller, responsible for planning and coordinating different types of inspections
"""

import logging
from typing import Dict, List, Any, Optional

from inspectors.node.node_inspector import NodeInspector
from inspectors.opa.opa_inspector import OpaInspector
from inspectors.prometheus.prometheus_inspector import PrometheusInspector
from utils.inspection_result import InspectionResult

# Logging setup
logger = logging.getLogger(__name__)

class InspectionController:
    """Inspection controller, responsible for coordinating the inspection process"""

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Initialize inspection controller

        Args:
            config: controller configuration
            use_gitops: whether to use GitOps rules
        """
        self.config = config
        self.use_gitops = use_gitops
        self.inspectors = {}
        self._initialize_inspectors()

    def _initialize_inspectors(self):
        """Initialize all inspectors"""
        # Output configuration information for debugging
        logger.info(f"Controller configuration: {list(self.config.keys())}")
        logger.info(f"GitOps mode: {self.use_gitops}")

        # Initialize node inspector
        if 'nodes' in self.config and self.config['nodes']:
            logger.info(f"Node configuration detected, number of nodes: {len(self.config['nodes'])}")
            self.inspectors['node'] = NodeInspector(self.config['nodes'], use_gitops=self.use_gitops)
            logger.info("Node inspector initialized")
        else:
            logger.warning(f"Node configuration not found: nodes={'nodes' in self.config}, count={len(self.config.get('nodes', []))}")

        # Initialize OPA inspector
        if 'opa' in self.config:
            self.inspectors['opa'] = OpaInspector(self.config['opa'], use_gitops=self.use_gitops)
            logger.info("OPA inspector initialized")

        # Initialize Prometheus inspector
        if 'prometheus' in self.config:
            self.inspectors['prometheus'] = PrometheusInspector(self.config['prometheus'], use_gitops=self.use_gitops)
            logger.info("Prometheus inspector initialized")

        logger.info(f"Initialized {len(self.inspectors)} inspectors: {list(self.inspectors.keys())}")

    def get_available_inspectors(self) -> List[str]:
        """
        Get available inspector types

        Returns:
            List of inspector types
        """
        return list(self.inspectors.keys())

    def run_inspection(self, cluster_name: str, inspector_types: List[str] = None,
                      rule_ids: Dict[str, List[str]] = None) -> Dict[str, InspectionResult]:
        """
        Execute inspection

        Args:
            cluster_name: cluster name
            inspector_types: list of inspector types to execute, if None, execute all inspectors
            rule_ids: dictionary of rule IDs for each inspector, format {inspector_type: [rule_id1, rule_id2]}

        Returns:
            Dictionary of inspection results, format {inspector_type: inspection_result}
        """
        results = {}

        # Determine inspectors to execute
        if inspector_types:
            active_inspectors = {k: v for k, v in self.inspectors.items() if k in inspector_types}
        else:
            active_inspectors = self.inspectors

        if not active_inspectors:
            logger.warning("No available inspectors")
            return results

        # Execute inspection
        for inspector_type, inspector in active_inspectors.items():
            try:
                # Get rule IDs for this inspector
                inspector_rule_ids = None
                if rule_ids and inspector_type in rule_ids:
                    inspector_rule_ids = rule_ids[inspector_type]

                logger.info(f"Executing {inspector_type} inspection...")
                result = inspector.run_inspection(cluster_name, inspector_rule_ids)
                results[inspector_type] = result
                logger.info(f"{inspector_type} inspection completed, found {len(result.items)} results")

            except Exception as e:
                logger.exception(f"Error executing {inspector_type} inspection: {str(e)}")

        return results

    def save_inspection_result(self, all_results: Dict[str, InspectionResult],
                             cluster_name: str, inspection_type: str = "immediate") -> str:
        """
        Save inspection results to file

        Args:
            all_results: dictionary of inspection results
            cluster_name: cluster name
            inspection_type: inspection type ('immediate' or 'scheduled')

        Returns:
            Path to saved file
        """
        import os
        import json
        from datetime import datetime
        from pathlib import Path

        # Ensure results directory exists
        from utils.inspection_result import RESULTS_DIR
        results_dir = RESULTS_DIR
        results_dir.mkdir(parents=True, exist_ok=True)

        # Generate result ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_id = f"{inspection_type}_{timestamp}"
        filename = f"inspection_result_{cluster_name}_{timestamp}.json"
        result_path = results_dir / filename

        # Calculate statistics
        total_items = 0
        total_passed = 0
        total_failed = 0
        total_warning = 0
        total_error = 0

        # Serialize inspection results
        serialized_results = {}
        for inspector_type, result in all_results.items():
            if hasattr(result, 'items'):
                items = result.items
            else:
                items = []

            # Calculate statistics - safe access to item properties
            total_items += len(items)
            for item in items:
                # Safe status retrieval
                if hasattr(item, '__dict__'):
                    status = getattr(item, 'status', 'unknown')
                elif isinstance(item, dict):
                    status = item.get('status', 'unknown')
                elif isinstance(item, (tuple, list)) and len(item) > 1:
                    status = str(item[1])
                else:
                    status = 'unknown'

                # Normalize status (as in InspectionResult.add_item)
                if status in ['failed', 'warning', 'error']:
                    status = 'exception'

                # Status statistics - using simplified status system
                if status == 'passed':
                    total_passed += 1
                elif status == 'exception':
                    # Get severity for exception classification
                    severity = 'unknown'
                    if hasattr(item, '__dict__'):
                        severity = getattr(item, 'severity', 'unknown')
                    elif isinstance(item, dict):
                        severity = item.get('severity', 'unknown')

                    if severity == 'critical':
                        total_failed += 1  # critical is considered as failed
                    elif severity == 'warning':
                        total_warning += 1
                    else:
                        total_error += 1  # other severity levels are considered as error
                else:
                    # Unknown status is treated as error
                    total_error += 1

            # Serialize items - ensure all items have dictionary format and normalized status
            serialized_items = []
            for item in items:
                if hasattr(item, '__dict__'):
                    # If it's an object, convert to dictionary
                    item_dict = item.__dict__.copy()
                elif isinstance(item, dict):
                    # If already a dictionary, create a copy
                    item_dict = item.copy()
                elif isinstance(item, (tuple, list)) and len(item) >= 2:
                    # If it's a tuple or list, try to convert to basic dictionary format
                    item_dict = {
                        'name': str(item[0]) if len(item) > 0 else 'Unknown',
                        'status': str(item[1]) if len(item) > 1 else 'unknown',
                        'description': str(item[2]) if len(item) > 2 else '',
                        'severity': 'info',
                        'details': str(item),
                        'solution': ''
                    }
                else:
                    # Other cases, create basic dictionary
                    item_dict = {
                        'name': str(item),
                        'status': 'unknown',
                        'description': f'Converted from {type(item).__name__}',
                        'severity': 'info',
                        'details': str(item),
                        'solution': ''
                    }

                # Normalize status (as in InspectionResult.add_item)
                if item_dict.get('status') in ['failed', 'warning', 'error']:
                    item_dict['status'] = 'exception'

                serialized_items.append(item_dict)

            serialized_results[inspector_type] = {
                "inspector_type": inspector_type,
                "items": serialized_items
            }

        # Build complete result structure
        result_data = {
            "result_id": result_id,
            "cluster_name": cluster_name,
            "timestamp": datetime.now().isoformat(),
            "inspection_type": inspection_type,  # immediate or scheduled
            "execution_info": {
                "triggered_by": "user" if inspection_type == "immediate" else "scheduler",
                "inspectors_used": list(all_results.keys()),
                "execution_duration": "N/A"  # Timer functionality can be added later
            },
            "inspection_results": serialized_results,
            "summary": {
                "total_items": total_items,
                "passed": total_passed,
                "failed": total_failed,
                "warning": total_warning,
                "error": total_error
            },
            # Compatibility with old fields
            "critical": total_failed,  # Display failed as critical for compatibility with existing code
            "warning": total_warning,
            "passed": total_passed
        }

        # Save to file
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        # Caching disabled

        # Start data cleanup - cleanup old reports after creating new one
        try:
            from utils.data_cleanup import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.cleanup_inspection_results()
        except Exception as e:
            logger.warning(f"Error cleaning up old reports: {e}")

        logger.info(f"Inspection results saved to: {result_path}")
        return str(result_path)
