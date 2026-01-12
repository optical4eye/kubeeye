#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPA rules inspector - simplified version
Focused on core functions, removed redundant code and excessive logging
"""

import asyncio
import os
import tempfile
import json
import subprocess
import datetime
from typing import Dict, List, Any, Optional

from services.inspectors.base_inspector import BaseInspector
from infra.cluster.k8s_dynamic_client import K8sDynamicClient
from infra.rules.rule_loader import Rule
from core.logging import get_logger

logger = get_logger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime types"""

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        return super().default(obj)


class OpaInspector(BaseInspector):
    """OPA rules inspector - simplified version"""

    def __init__(self, opa_config: Dict[str, Any], use_gitops: bool = False):
        self.k8s_client = K8sDynamicClient(opa_config.get("kubeconfig"))
        self.opa_path = opa_config.get("opa_path", "/usr/local/bin/opa")
        super().__init__(opa_config, use_gitops=use_gitops)

    @property
    def inspector_type(self) -> str:
        return "opa"

    def _prepare_context(self, cluster_name: str) -> Dict:
        """Prepare inspection context"""
        return super()._prepare_context(cluster_name)

    async def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """Execute OPA rule validation"""
        import time

        rule_start_time = time.time()

        logger.info(f"Executing rule: {rule.id}")

        try:
            # Get Rego rules content
            rego_content = self._get_rego_content(rule)
            if not rego_content:
                return self.rule_processor.result_formatter.error_result(rule, "Failed to get Rego rules content")

            # Get cluster resources
            resources = self._get_cluster_resources(rule)
            if not resources:
                return self.rule_processor.result_formatter.pass_result(rule, "No matching resources")

            # Execute OPA evaluation
            violations = await self._evaluate_opa(rego_content, resources)

            # Evaluate assertions
            result = self._evaluate_assertions(rule, violations, len(resources))

            rule_duration = time.time() - rule_start_time
            logger.info(
                f"Rule {rule.id} completed in {rule_duration:.2f}s, checked {len(resources)} resources, found {len(violations)} violations"
            )

            return result

        except Exception as e:
            rule_duration = time.time() - rule_start_time
            logger.error(f"Rule {rule.id} execution failed after {rule_duration:.2f}s: {e}", exc_info=True)
            return self.rule_processor.result_formatter.error_result(rule, f"Execution failed: {str(e)}")

    def _get_rego_content(self, rule: Rule) -> Optional[str]:
        """Get Rego rules content"""
        # Try to get from inline configuration
        rego_content = self.get_rule_config(rule, "rego.inline")
        if rego_content:
            return rego_content

        # Try to get from file
        rego_file = self.get_rule_config(rule, "rego.file")
        if rego_file and os.path.exists(rego_file):
            try:
                with open(rego_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read Rego file: {e}")

        return None

    def _get_cluster_resources(self, rule: Rule) -> List[Dict]:
        """Get cluster resources"""
        try:
            # Prefer optimized version
            if hasattr(self.k8s_client, "list_resources_from_config_optimized"):
                resources_dict = self.k8s_client.list_resources_from_config_optimized(rule.config)
            else:
                resources_dict = self.k8s_client.list_resources_from_config(rule.config)

            # Flatten resource list
            all_resources = []
            try:
                if isinstance(resources_dict, dict):
                    try:
                        for resource_list in resources_dict.values():
                            if isinstance(resource_list, list):
                                all_resources.extend(resource_list)
                            else:
                                logger.warning(f"Skipping non-list resource_list: {type(resource_list)}")
                    except Exception as e:
                        logger.error(f"Error iterating resources_dict.values(): {e}", exc_info=True)
                        return []
                else:
                    logger.warning(f"resources_dict is not dict: {type(resources_dict)}")
            except Exception as e:
                logger.error(f"Error flattening resources: {e}", exc_info=True)
                return []

            logger.info(f"Retrieved {len(all_resources)} resources")
            return all_resources

        except Exception as e:
            logger.error(f"Failed to get cluster resources: {e}", exc_info=True)
            return []

    async def _evaluate_opa(self, rego_content: str, resources: List[Dict]) -> List[Dict]:
        """Execute OPA evaluation"""
        if not resources:
            return []

        rego_path = None
        input_path = None

        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".rego", delete=False) as f:
                f.write(rego_content.encode("utf-8"))
                rego_path = f.name

            # Filter out callable objects from resources
            def filter_callable(data):
                if isinstance(data, dict):
                    return {k: filter_callable(v) for k, v in data.items() if not callable(v)}
                elif isinstance(data, list):
                    return [filter_callable(item) for item in data if not callable(item)]
                else:
                    return data if not callable(data) else None

            filtered_resources = filter_callable(resources)
            input_data = {"resources": filtered_resources}
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(input_data, f, cls=DateTimeEncoder)
                input_path = f.name

            # Execute OPA command
            cmd = [
                self.opa_path,
                "eval",
                f"--data={rego_path}",
                f"--input={input_path}",
                "data.kubernetes.violations",
            ]

            logger.info(f"Executing OPA command: {' '.join(cmd)}")

            # Check if OPA binary exists and is executable
            import os

            if not os.path.exists(self.opa_path):
                raise Exception(f"OPA binary not found at {self.opa_path}")

            if not os.access(self.opa_path, os.X_OK):
                raise Exception(f"OPA binary at {self.opa_path} is not executable")

            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True,
            )

            # Parse results
            if result.stdout:
                try:
                    output = json.loads(result.stdout.strip())
                except json.JSONDecodeError as e:
                    logger.error(f"OPA output is not valid JSON: {e}, stdout: {result.stdout[:500]}")
                    return []
                except Exception as e:
                    logger.error(f"Error parsing OPA output: {e}")
                    return []

                # Get actual violation data from result[0].expressions[0].value
                try:
                    if "result" in output and len(output["result"]) > 0:
                        result_item = output["result"][0]
                        if "expressions" in result_item and len(result_item["expressions"]) > 0:
                            violations = result_item["expressions"][0].get("value", [])
                            logger.info(f"Found {len(violations)} violations")
                            return violations if isinstance(violations, list) else []
                except Exception as e:
                    logger.error(f"Error parsing OPA results: {e}", exc_info=True)
                    return []

            return []

        except subprocess.CalledProcessError as e:
            logger.error(f"OPA execution failed: returncode={e.returncode}, stderr={e.stderr}, stdout={e.stdout}")
            raise Exception(f"OPA execution failed: {e.stderr}")
        except OSError as e:
            logger.error(f"OS error executing OPA: {e}, errno={e.errno}")
            if e.errno == 8:  # Exec format error
                logger.error(f"Exec format error for OPA at {self.opa_path}. Check architecture and file integrity.")
                # Try to get file info
                try:
                    import os

                    stat_info = os.stat(self.opa_path)
                    logger.error(f"OPA file permissions: {oct(stat_info.st_mode)}")
                    # Try to run file command if available
                    try:
                        file_result = subprocess.run(["file", self.opa_path], capture_output=True, text=True)
                        logger.error(f"File info: {file_result.stdout}")
                    except Exception:
                        pass
                except Exception as stat_e:
                    logger.error(f"Could not get file info: {stat_e}")
            raise Exception(f"OS error executing OPA: {e}")
        except Exception as e:
            logger.error(f"OPA evaluation error: {e}")
            raise
        finally:
            # Clean up temporary files
            for path in [rego_path, input_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    def _evaluate_assertions(self, rule: Rule, violations: List[Dict], resource_count: int) -> Dict:
        """Evaluate assertions and return result (using unified AssertionManager)"""
        try:
            # Ensure violations is a list
            if not isinstance(violations, list):
                logger.warning(f"Violation result is not a list type: {type(violations)}")
                violations = [] if violations is None else [violations]

            assertion_vars = {
                "violation_count": len(violations),
                "violations": violations,
                "resource_count": resource_count,
            }

            assertions = rule.assertions
            if not isinstance(assertions, list):
                logger.warning(f"Assertions is not list: {type(assertions)}, setting to []")
                assertions = []
            assertion_result = self.rule_processor.assertion_manager.evaluate_assertions(
                assertions, assertion_vars, mode="simple"
            )

            if assertion_result["passed"]:
                description = assertion_result.get("pass_description", f"{rule.name}: Check passed")
                return self.rule_processor.result_formatter.pass_result(
                    rule, description, f"Checked {resource_count} resources"
                )
            else:
                description = assertion_result.get("fail_description", f"{rule.name}: Check failed")
                details = self._format_violations(violations)
                return self.rule_processor.result_formatter.fail_result(
                    rule,
                    description,
                    details,
                    assertion_result.get("severity", "warning"),
                    violations,
                )
        except Exception as e:
            logger.error(f"Error evaluating assertions: {e}")
            return self.rule_processor.result_formatter.error_result(rule, f"Assertion evaluation failed: {str(e)}")

    def _format_violations(self, violations: List[Dict]) -> str:
        """Format violation information"""
        if not violations:
            return "No resources with violations"

        details = []
        for i, violation in enumerate(violations):
            try:
                if isinstance(violation, dict):
                    kind = violation.get("kind", "Unknown")
                    name = violation.get("name", "unnamed")
                    namespace = violation.get("namespace")
                    message = violation.get("message", "Unknown violation")

                    if namespace and namespace not in ["-", "", "null", None]:
                        detail = f"- {kind}/{name} (namespace: {namespace}): {message}"
                    else:
                        detail = f"- {kind}/{name}: {message}"
                elif isinstance(violation, str):
                    detail = f"- {violation}"
                else:
                    # Handle other types of violation data
                    detail = f"- {str(violation)}"

                details.append(detail)
            except Exception as e:
                logger.error(f"Error formatting violation {i}: {e}, violation type: {type(violation)}")
                details.append(f"- Violation element with formatting error: {str(violation)[:100]}")

        return "\n".join(details)
