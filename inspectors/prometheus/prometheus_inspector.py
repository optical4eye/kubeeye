#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus инспектор - упрощенная версия, поддерживает "одно правило = один запрос = один элемент проверки"
"""

import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple

from inspectors.base_inspector import BaseInspector
from utils.prometheus_client import PrometheusClient
from utils.rule_loader import Rule

# Настройка логирования
logger = logging.getLogger(__name__)

class PrometheusInspector(BaseInspector):
    """
    Prometheus инспектор правил - упрощенная версия
    """

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Инициализация Prometheus инспектора

        Args:
            config: словарь конфигурации Prometheus, должен содержать следующие поля:
                - url: URL сервера Prometheus
                - username: опциональное имя пользователя
                - password: опциональный пароль
                - token: опциональный токен доступа
                - enabled: включен ли
            use_gitops: использовать ли правила GitOps
        """
        # Убедиться, что конфигурация действительна
        if not isinstance(config, dict):
            raise TypeError("Конфигурация должна быть словарем")

        # Если переданная конфигурация отсутствует необходимые поля, добавить значения по умолчанию
        if 'url' not in config:
            raise ValueError("Конфигурация Prometheus отсутствует поле url")

        # Создать экземпляр PrometheusClient
        self.prometheus_client = PrometheusClient(config)

        # Вызов инициализации родительского класса
        super().__init__(config, use_gitops=use_gitops)

    @property
    def inspector_type(self) -> str:
        return "prometheus"

    def _prepare_context(self, cluster_name: str) -> Dict:
        """
        Подготовить контекст проверки Prometheus

        Args:
            cluster_name: имя кластера

        Returns:
            Подготовленный контекст
        """
        context = super()._prepare_context(cluster_name)
        return context

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """
        Проверить, действительна ли конфигурация правила

        Args:
            rule: объект правила

        Returns:
            Список проблем конфигурации, если проблем нет, возвращает пустой список
        """
        issues = []

        # Проверить необходимую конфигурацию запроса
        query = self.get_rule_config(rule, 'query', '')
        if not query:
            issues.append("Отсутствует необходимый Prometheus запрос (query)")

        # Проверить необходимую конфигурацию утверждений
        assertions = self.get_rule_config(rule, 'assertions', [])
        if not assertions:
            issues.append("Отсутствует необходимая конфигурация утверждений (assertions)")

        return issues

    def _apply_rule(self, rule: Rule, context: Dict) -> Dict:
        """
        Применить правило Prometheus для проверки - упрощенная версия

        Args:
            rule: объект правила
            context: контекст

        Returns:
            Результат проверки
        """
        # Получить конфигурацию запроса и утверждений
        query = self.get_rule_config(rule, 'query', '')
        assertions = self.get_rule_config(rule, 'assertions', [])

        # Выполнить запрос
        try:
            # Выполнить мгновенный запрос (упрощенная версия, больше не поддерживает сложные запросы по диапазону времени)
            result = self.prometheus_client.query(query)

            # Обработать результат
            metrics = self._process_query_result(result)
            if not metrics:
                return self.rule_processor.format_rule_result(
                    rule=rule,
                    status="passed",
                    description=f"{rule.name}: нет данных",
                    severity="info",
                    details="Prometheus запрос не вернул соответствующих данных метрик",
                    solution=""
                )

            # Извлечь данные для оценки утверждений
            variables = self._extract_metrics_variables(metrics)

            # Сгенерировать суффикс имени, содержащий информацию о контексте
            name_suffix = self._generate_context_suffix(metrics, variables)

            # Оценить утверждения
            assertion_result = self.rule_processor.evaluate_assertions(assertions, variables)

            # Вернуть результат проверки на основе результата утверждений
            if assertion_result['passed']:
                # Для пройденных проверок отображать конкретные данные мониторинга в описании
                first_assertion = assertions[0] if assertions else {}
                first_assertion_desc = first_assertion.get('description', '')
                if first_assertion_desc:
                    # Отрендерить шаблон для отображения конкретных значений
                    rendered_desc = self.rule_processor.assertion_manager.render_template(first_assertion_desc, variables)
                    description = f"{rule.name}: {rendered_desc}"
                else:
                    # Отобразить ключевые значения метрик
                    if 'max_value' in variables:
                        description = f"{rule.name}: максимальное значение {variables['max_value']:.2f}"
                    elif 'value' in variables:
                        description = f"{rule.name}: текущее значение {variables['value']:.2f}"
                    else:
                        description = f"{rule.name}: проверка пройдена"

                result = self.rule_processor.format_rule_result(
                    rule=rule,
                    status="passed",
                    description=description,
                    severity="info",
                    details="Метрики мониторинга в норме",
                    solution=""
                )
            else:
                # Удалить префикс "Утверждение не выполнено: ", использовать описание напрямую
                clean_description = assertion_result['description'].replace("Утверждение не выполнено: ", "")

                result = self.rule_processor.format_rule_result(
                    rule=rule,
                    status="failed",
                    description=clean_description,
                    severity=assertion_result['severity'],
                    details=f"Сработало оповещение мониторинга\nЗапрос: {query}\nЗначение результата: {self._format_simple_metrics(metrics)}",
                    solution=rule.solution
                )

            # Добавить информацию о контексте к имени
            if name_suffix:
                result['name'] = f"{rule.name} - {name_suffix}"

            return result

        except Exception as e:
            logger.exception(f"Ошибка выполнения Prometheus запроса: {str(e)}")
            return self._format_error_result(rule,
                "Ошибка выполнения Prometheus запроса", str(e))

    def _process_query_result(self, result: Dict) -> List[Dict]:
        """
        Обработать результат Prometheus запроса - упрощенная версия, поддерживает только vector тип

        Args:
            result: результат Prometheus запроса

        Returns:
            Обработанный список метрик
        """
        metrics = []

        # Проверить формат результата
        if not result or not isinstance(result, dict):
            return metrics

        data = result.get('data', {})
        result_type = data.get('resultType')
        result_data = data.get('result', [])

        if not result_data:
            return metrics

        # Обрабатывать только результаты мгновенных запросов (vector тип)
        if result_type == 'vector':
            for item in result_data:
                metric = {
                    'metric': item.get('metric', {}),
                    'value': float(item.get('value', [0, '0'])[1]) if item.get('value') else 0
                }
                metrics.append(metric)
        else:
            # Больше не поддерживает matrix тип сложных временных рядов
            logger.warning(f"Неподдерживаемый тип результата запроса: {result_type}, используйте мгновенный запрос")

        return metrics

    def _extract_metrics_variables(self, metrics: List[Dict]) -> Dict[str, Any]:
        """
        Извлечь переменные из метрик для оценки утверждений

        Args:
            metrics: список метрик

        Returns:
            Словарь переменных
        """
        variables = {
            # Хранить список всех значений для удобства вычисления среднего, максимума и т.д.
            'values': [m.get('value', 0) for m in metrics],
        }

        # Если только одна метрика, использовать ее значение напрямую
        if len(metrics) == 1:
            variables['value'] = metrics[0].get('value', 0)

            # Добавить метки как переменные
            metric_labels = metrics[0].get('metric', {})
            for label, label_value in metric_labels.items():
                variables[f"label_{label}"] = label_value

        # Добавить агрегированные значения
        if variables['values']:
            variables['max_value'] = max(variables['values'])
            variables['min_value'] = min(variables['values'])
            variables['avg_value'] = sum(variables['values']) / len(variables['values'])

        return variables

    def _generate_context_suffix(self, metrics: List[Dict], variables: Dict[str, Any]) -> str:
        """
        Сгенерировать суффикс имени, содержащий информацию о контексте

        Args:
            metrics: список метрик
            variables: словарь переменных

        Returns:
            Строка суффикса контекста
        """
        if not metrics:
            return ""

        # Если только одна метрика, попытаться извлечь значимые метки
        if len(metrics) == 1:
            metric_labels = metrics[0].get('metric', {})

            # Приоритетно отображать информацию, связанную с узлом
            if 'instance' in metric_labels:
                instance = metric_labels['instance']
                # Очистить формат instance (обычно IP:PORT или hostname:PORT)
                if ':' in instance:
                    instance = instance.split(':')[0]
                return f"Узел {instance}"
            elif 'node' in metric_labels:
                return f"Узел {metric_labels['node']}"
            elif 'job' in metric_labels:
                return f"Задача {metric_labels['job']}"
            elif '__name__' in metric_labels:
                return f"Метрика {metric_labels['__name__']}"

        # Если несколько метрик, отобразить количество метрик
        elif len(metrics) > 1:
            # Попытаться найти общие метки
            first_metric_labels = metrics[0].get('metric', {})
            if 'job' in first_metric_labels:
                job_name = first_metric_labels['job']
                return f"{len(metrics)} экземпляров {job_name}"
            else:
                return f"{len(metrics)} экземпляров"

        return ""

    def _format_simple_metrics(self, metrics: List[Dict]) -> str:
        """
        Упрощенный метод форматирования метрик

        Args:
            metrics: список метрик

        Returns:
            Отформатированная строка метрик
        """
        if not metrics:
            return "Нет данных"

        if len(metrics) == 1:
            metric = metrics[0]
            value = metric.get('value', 'N/A')
            return f"Текущее значение: {value}"
        else:
            values = [m.get('value', 0) for m in metrics]
            max_val = max(values)
            avg_val = sum(values) / len(values)
            return f"Максимальное значение: {max_val:.2f}, Среднее значение: {avg_val:.2f}, Всего {len(metrics)} экземпляров"

    def get_rule_config(self, rule: Rule, key: str, default: Any = None) -> Any:
        """
        Получить значение определенного ключа из конфигурации правила

        Args:
            rule: объект правила
            key: ключ конфигурации
            default: значение по умолчанию, возвращаемое, если ключ не существует

        Returns:
            Значение конфигурации или значение по умолчанию
        """
        if rule.config and key in rule.config:
            return rule.config[key]
        return default

    def _format_skipped_result(self, rule: Rule, reason: str) -> Dict:
        """
        Форматировать результат пропущенного правила (делегировано ResultFormatter)

        Args:
            rule: объект правила
            reason: причина пропуска

        Returns:
            Словарь результата
        """
        return self.rule_processor.result_formatter.skipped_result(rule, reason)

    def _format_error_result(self, rule: Rule, error_type: str, error_msg: str) -> Dict:
        """
        Форматировать результат ошибки (делегировано ResultFormatter)

        Args:
            rule: объект правила
            error_type: тип ошибки
            error_msg: сообщение об ошибке

        Returns:
            Словарь результата
        """
        full_error_msg = f"Тип ошибки: {error_type}\nИнформация об ошибке: {error_msg}\nРекомендация по решению: Проверьте конфигурацию подключения Prometheus и синтаксис запроса"
        return self.rule_processor.result_formatter.error_result(
            rule, full_error_msg, f"{rule.name} ошибка: {error_type}"
        )
