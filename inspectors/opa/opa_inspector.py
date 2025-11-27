#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инспектор правил OPA - упрощенная версия
Сфокусирован на основных функциях, убраны избыточный код и чрезмерное логирование
"""

import logging
import os
import tempfile
import json
import subprocess
import datetime
from typing import Dict, List, Any, Optional

from inspectors.base_inspector import BaseInspector
from utils.k8s_dynamic_client import K8sDynamicClient
from utils.rule_loader import Rule

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Пользовательский JSON кодировщик, обрабатывающий типы datetime"""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        return super().default(obj)

class OpaInspector(BaseInspector):
    """Инспектор правил OPA - упрощенная версия"""

    def __init__(self, opa_config: Dict[str, Any], use_gitops: bool = False):
        self.k8s_client = K8sDynamicClient(opa_config.get('kubeconfig'))
        self.opa_path = opa_config.get('opa_path', '/usr/local/bin/opa')
        super().__init__(opa_config, use_gitops=use_gitops)

    @property
    def inspector_type(self) -> str:
        return "opa"

    def validate_rule(self, rule: Rule) -> List[str]:
        """Проверка конфигурации правила"""
        issues = []

        # Проверка правил Rego
        if not (self.get_rule_config(rule, 'rego.inline') or
                self.get_rule_config(rule, 'rego.file')):
            issues.append("Отсутствует конфигурация правил Rego")

        # Проверка конфигурации ресурсов
        if not self.get_rule_config(rule, 'resources', []):
            issues.append("Отсутствует конфигурация ресурсов")

        # Проверка конфигурации утверждений
        if not self.get_rule_config(rule, 'assertions', []):
            issues.append("Отсутствует конфигурация утверждений")

        return issues

    def _prepare_context(self, cluster_name: str) -> Dict:
        """Подготовка контекста проверки"""
        return super()._prepare_context(cluster_name)

    def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """Выполнение проверки правил OPA"""
        logger.info(f"Выполнение правила: {rule.id}")

        try:
            # Получение содержимого правил Rego
            rego_content = self._get_rego_content(rule)
            if not rego_content:
                return self._error_result(rule, "Не удалось получить содержимое правил Rego")

            # Получение ресурсов кластера
            resources = self._get_cluster_resources(rule)
            if not resources:
                return self._pass_result(rule, "Нет соответствующих ресурсов")

            # Выполнение оценки OPA
            violations = self._evaluate_opa(rego_content, resources)

            # Оценка утверждений
            return self._evaluate_assertions(rule, violations, len(resources))

        except Exception as e:
            logger.error(f"Правило {rule.id} выполнение не удалось: {e}")
            return self._error_result(rule, f"Выполнение не удалось: {str(e)}")

    def _get_rego_content(self, rule: Rule) -> Optional[str]:
        """Получение содержимого правил Rego"""
        # Попытка получить из inline конфигурации
        rego_content = self.get_rule_config(rule, 'rego.inline')
        if rego_content:
            return rego_content

        # Попытка получить из файла
        rego_file = self.get_rule_config(rule, 'rego.file')
        if rego_file and os.path.exists(rego_file):
            try:
                with open(rego_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Чтение файла Rego не удалось: {e}")

        return None

    def _get_cluster_resources(self, rule: Rule) -> List[Dict]:
        """Получение ресурсов кластера"""
        try:
            # Приоритетное использование оптимизированной версии
            if hasattr(self.k8s_client, 'list_resources_from_config_optimized'):
                resources_dict = self.k8s_client.list_resources_from_config_optimized(rule.config)
            else:
                resources_dict = self.k8s_client.list_resources_from_config(rule.config)

            # Выравнивание списка ресурсов
            all_resources = []
            for resource_list in resources_dict.values():
                all_resources.extend(resource_list)

            logger.info(f"Получено {len(all_resources)} ресурсов")
            return all_resources

        except Exception as e:
            logger.error(f"Получение ресурсов кластера не удалось: {e}")
            return []

    def _evaluate_opa(self, rego_content: str, resources: List[Dict]) -> List[Dict]:
        """Выполнение оценки OPA"""
        if not resources:
            return []

        rego_path = None
        input_path = None

        try:
            # Создание временных файлов
            with tempfile.NamedTemporaryFile(suffix='.rego', delete=False) as f:
                f.write(rego_content.encode('utf-8'))
                rego_path = f.name

            input_data = {"resources": resources}
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(input_data, f, cls=DateTimeEncoder)
                input_path = f.name

            # Выполнение команды OPA
            cmd = [
                self.opa_path, "eval",
                f"--data={rego_path}",
                f"--input={input_path}",
                "data.kubernetes.violations"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True
            )

            # Разбор результатов
            if result.stdout:
                output = json.loads(result.stdout.strip())

                # Получение фактических данных о нарушениях из result[0].expressions[0].value
                try:
                    if 'result' in output and len(output['result']) > 0:
                        result_item = output['result'][0]
                        if 'expressions' in result_item and len(result_item['expressions']) > 0:
                            violations = result_item['expressions'][0].get('value', [])
                            logger.info(f"Обнаружено {len(violations)} нарушений")
                            return violations if isinstance(violations, list) else []
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Ошибка при разборе результатов OPA: {e}")
                    # Попытка старого способа разбора в качестве запасного варианта
                    violations = output.get('result', [])
                    return violations if isinstance(violations, list) else []

            return []

        except subprocess.CalledProcessError as e:
            logger.error(f"Выполнение OPA не удалось: {e.stderr}")
            raise Exception(f"Выполнение OPA не удалось: {e.stderr}")
        except Exception as e:
            logger.error(f"Ошибка оценки OPA: {e}")
            raise
        finally:
            # Очистка временных файлов
            for path in [rego_path, input_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    def _evaluate_assertions(self, rule: Rule, violations: List[Dict], resource_count: int) -> Dict:
        """Оценка утверждений и возврат результата (с использованием унифицированного AssertionManager)"""
        try:
            # Гарантия что violations является списком
            if not isinstance(violations, list):
                logger.warning(f"Результат нарушений не является типом список: {type(violations)}")
                violations = [] if violations is None else [violations]

            assertion_vars = {
                'violation_count': len(violations),
                'violations': violations,
                'resource_count': resource_count
            }

            assertions = self.get_rule_config(rule, 'assertions', [])
            assertion_result = self.rule_processor.assertion_manager.evaluate_assertions(
                assertions, assertion_vars, mode="simple"
            )

            if assertion_result['passed']:
                description = assertion_result.get('pass_description', f"{rule.name}: Проверка пройдена")
                return self._pass_result(rule, description, f"Проверено {resource_count} ресурсов")
            else:
                description = assertion_result.get('fail_description', f"{rule.name}: Проверка не пройдена")
                details = self._format_violations(violations)
                return self._fail_result(
                    rule,
                    description,
                    details,
                    assertion_result.get('severity', 'warning'),
                    violations
                )
        except Exception as e:
            logger.error(f"Ошибка при оценке утверждений: {e}")
            return self._error_result(rule, f"Оценка утверждений не удалась: {str(e)}")

    def _format_violations(self, violations: List[Dict]) -> str:
        """Форматирование информации о нарушениях"""
        if not violations:
            return "Нет ресурсов с нарушениями"

        details = []
        for i, violation in enumerate(violations):
            try:
                if isinstance(violation, dict):
                    kind = violation.get('kind', 'Unknown')
                    name = violation.get('name', 'unnamed')
                    namespace = violation.get('namespace')
                    message = violation.get('message', 'Неизвестное нарушение')

                    if namespace and namespace not in ['-', '', 'null', None]:
                        detail = f"- {kind}/{name} (пространство имен: {namespace}): {message}"
                    else:
                        detail = f"- {kind}/{name}: {message}"
                elif isinstance(violation, str):
                    detail = f"- {violation}"
                else:
                    # Обработка данных о нарушениях других типов
                    detail = f"- {str(violation)}"

                details.append(detail)
            except Exception as e:
                logger.error(f"Ошибка при форматировании {i}-го нарушения: {e}, тип нарушения: {type(violation)}")
                details.append(f"- Элемент нарушения с ошибкой форматирования: {str(violation)[:100]}")

        return "\n".join(details)

    def _pass_result(self, rule: Rule, description: str, details: str = "") -> Dict:
        """Генерация результата "Пройдено" (делегировано ResultFormatter)"""
        return self.rule_processor.result_formatter.pass_result(rule, description, details)

    def _fail_result(self, rule: Rule, description: str, details: str,
                     severity: str = "warning", violations: List[Dict] = None) -> Dict:
        """Генерация результата "Не пройдено" (делегировано ResultFormatter)"""
        return self.rule_processor.result_formatter.fail_result(
            rule, description, details, severity, violations
        )

    def _error_result(self, rule: Rule, error_msg: str) -> Dict:
        """Генерация результата "Ошибка" (делегировано ResultFormatter)"""
        return self.rule_processor.result_formatter.error_result(rule, error_msg)
