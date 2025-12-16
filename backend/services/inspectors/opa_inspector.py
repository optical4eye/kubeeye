#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPA rules inspector - simplified version
Focused on core functions, removed redundant code and excessive logging
"""

import logging
import os
import tempfile
import json
import subprocess
import datetime
from typing import Dict, List, Any, Optional

from services.inspectors.base_inspector import BaseInspector
from infrastructure.cluster.k8s_dynamic_client import K8sDynamicClient
from infrastructure.rules.rule_loader import Rule

logger = logging.getLogger(__name__)


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

    def validate_rule(self, rule: Rule) -> List[str]:
        """Validate rule configuration"""
        issues = []

        # Check Rego rules
        if not (
            self.get_rule_config(rule, "rego.inline")
            or self.get_rule_config(rule, "rego.file")
        ):
            issues.append("Missing Rego rules configuration")

        # Check resource configuration
        if not self.get_rule_config(rule, "resources", []):
            issues.append("Missing resource configuration")

        # Check assertions configuration
        if not self.get_rule_config(rule, "assertions", []):
            issues.append("Missing assertions configuration")

        return issues

    def _prepare_context(self, cluster_name: str) -> Dict:
        """Prepare inspection context"""
        return super()._prepare_context(cluster_name)

    def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """Execute OPA rule validation"""
        logger.info(f"Executing rule: {rule.id}")

        try:
            # Get Rego rules content
            rego_content = self._get_rego_content(rule)
            if not rego_content:
                return self._error_result(rule, "Failed to get Rego rules content")

            # Get cluster resources
            resources = self._get_cluster_resources(rule)
            if not resources:
                return self._pass_result(rule, "No matching resources")

            # Execute OPA evaluation
            violations = self._evaluate_opa(rego_content, resources)

            # Evaluate assertions
            return self._evaluate_assertions(rule, violations, len(resources))

        except Exception as e:
            logger.error(f"Rule {rule.id} execution failed: {e}")
            return self._error_result(rule, f"Execution failed: {str(e)}")

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
                resources_dict = self.k8s_client.list_resources_from_config_optimized(
                    rule.config
                )
            else:
                resources_dict = self.k8s_client.list_resources_from_config(rule.config)

            # Flatten resource list
            all_resources = []
            for resource_list in resources_dict.values():
                all_resources.extend(resource_list)

            logger.info(f"Retrieved {len(all_resources)} resources")
            return all_resources

        except Exception as e:
            logger.error(f"Failed to get cluster resources: {e}")
            return []

    def _evaluate_opa(self, rego_content: str, resources: List[Dict]) -> List[Dict]:
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

            input_data = {"resources": resources}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
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

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True,
            )

            # Parse results
            if result.stdout:
                output = json.loads(result.stdout.strip())

                # Get actual violation data from result[0].expressions[0].value
                try:
                    if "result" in output and len(output["result"]) > 0:
                        result_item = output["result"][0]
                        if (
                            "expressions" in result_item
                            and len(result_item["expressions"]) > 0
                        ):
                            violations = result_item["expressions"][0].get("value", [])
                            logger.info(f"Found {len(violations)} violations")
                            return violations if isinstance(violations, list) else []
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error parsing OPA results: {e}")
                    # Try old parsing method as fallback
                    violations = output.get("result", [])
                    return violations if isinstance(violations, list) else []

            return []

        except subprocess.CalledProcessError as e:
            logger.error(
                f"OPA execution failed: returncode={e.returncode}, stderr={e.stderr}, stdout={e.stdout}"
            )
            raise Exception(f"OPA execution failed: {e.stderr}")
        except OSError as e:
            logger.error(f"OS error executing OPA: {e}, errno={e.errno}")
            if e.errno == 8:  # Exec format error
                logger.error(
                    f"Exec format error for OPA at {self.opa_path}. Check architecture and file integrity."
                )
                # Try to get file info
                try:
                    import os

                    stat_info = os.stat(self.opa_path)
                    logger.error(f"OPA file permissions: {oct(stat_info.st_mode)}")
                    # Try to run file command if available
                    try:
                        file_result = subprocess.run(
                            ["file", self.opa_path], capture_output=True, text=True
                        )
                        logger.error(f"File info: {file_result.stdout}")
                    except:
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

    def _evaluate_assertions(
        self, rule: Rule, violations: List[Dict], resource_count: int
    ) -> Dict:
        """Evaluate assertions and return result (using unified AssertionManager)"""
        try:
            # Ensure violations is a list
            if not isinstance(violations, list):
                logger.warning(
                    f"Violation result is not a list type: {type(violations)}"
                )
                violations = [] if violations is None else [violations]

            assertion_vars = {
                "violation_count": len(violations),
                "violations": violations,
                "resource_count": resource_count,
            }

            assertions = self.get_rule_config(rule, "assertions", [])
            assertion_result = (
                self.rule_processor.assertion_manager.evaluate_assertions(
                    assertions, assertion_vars, mode="simple"
                )
            )

            if assertion_result["passed"]:
                description = assertion_result.get(
                    "pass_description", f"{rule.name}: Check passed"
                )
                return self._pass_result(
                    rule, description, f"Checked {resource_count} resources"
                )
            else:
                description = assertion_result.get(
                    "fail_description", f"{rule.name}: Check failed"
                )
                details = self._format_violations(violations)
                return self._fail_result(
                    rule,
                    description,
                    details,
                    assertion_result.get("severity", "warning"),
                    violations,
                )
        except Exception as e:
            logger.error(f"Error evaluating assertions: {e}")
            return self._error_result(rule, f"Assertion evaluation failed: {str(e)}")

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
                logger.error(
                    f"Error formatting violation {i}: {e}, violation type: {type(violation)}"
                )
                details.append(
                    f"- Violation element with formatting error: {str(violation)[:100]}"
                )

        return "\n".join(details)

    def _pass_result(self, rule: Rule, description: str, details: str = "") -> Dict:
        """Generate "Passed" result (delegated to ResultFormatter)"""
        return self.rule_processor.result_formatter.pass_result(
            rule, description, details
        )

    def _fail_result(
        self,
        rule: Rule,
        description: str,
        details: str,
        severity: str = "warning",
        violations: List[Dict] = None,
    ) -> Dict:
        """Generate "Failed" result (delegated to ResultFormatter)"""
        return self.rule_processor.result_formatter.fail_result(
            rule, description, details, severity, violations
        )

    def _error_result(self, rule: Rule, error_msg: str) -> Dict:
        """Generate "Error" result (delegated to ResultFormatter)"""
        return self.rule_processor.result_formatter.error_result(rule, error_msg)
