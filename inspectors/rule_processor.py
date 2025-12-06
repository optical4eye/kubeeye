#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль обработчика правил, предоставляющий функциональность обработки правил на основе утверждений
"""

import logging
from typing import Dict, List, Any, Optional

from utils.rule_loader import Rule
from utils.assertion_manager import AssertionManager
from utils.result_formatter import ResultFormatter
from utils.result_extractor import ResultExtractor

# 设置日志
logger = logging.getLogger(__name__)

class RuleProcessor:
    """
    Обработчик правил, предоставляющий общую функциональность обработки правил
    """

    def __init__(self):
        """Инициализировать обработчик правил"""
        self.assertion_manager = AssertionManager()
        self.result_formatter = ResultFormatter()
        self.result_extractor = ResultExtractor()

        # Для обратной совместимости сохранить старые имена атрибутов
        self.assertion_evaluator = self.assertion_manager

    @staticmethod
    def get_rule_config(rule: Rule, path: str, default_value: Any = None) -> Any:
        """
        Безопасно получить значение из конфигурации правила, поддерживает пути с точечной нотацией

        Args:
            rule: Объект правила
            path: Путь конфигурации, используя точечную нотацию, например "execution.command"
            default_value: Значение по умолчанию, если путь не существует

        Returns:
            Значение, на которое указывает путь, или значение по умолчанию, если путь не существует
        """
        parts = path.split('.')
        current = getattr(rule, 'config', {})

        # Обработать случай без config, напрямую получить атрибут верхнего уровня из rule
        if not current and hasattr(rule, parts[0]):
            if len(parts) == 1:
                return getattr(rule, parts[0])
            else:
                # Если значение атрибута является словарем, продолжить обработку подпути
                current = getattr(rule, parts[0])
                if not isinstance(current, dict):
                    return default_value
                parts = parts[1:]

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default_value

        return current

    def format_rule_result(self, rule: Rule, status: str, description: str, severity: str,
                          details: str, solution: Optional[str] = None,
                          violations: Optional[List[Dict]] = None, **kwargs) -> Dict:
        """
        Форматировать результат проверки правила (делегировано ResultFormatter)

        Args:
            rule: Объект правила
            status: Статус (passed, failed, error, warning, skipped, unknown)
            description: Краткое описание результата
            severity: Уровень серьезности
            details: Подробная информация
            solution: Опциональное решение
            violations: Опциональный список нарушений
            **kwargs: Другие дополнительные поля

        Returns:
            Форматированный словарь результата
        """
        return self.result_formatter.format_result(
            rule=rule,
            status=status,
            description=description,
            severity=severity,
            details=details,
            solution=solution,
            violations=violations,
            **kwargs
        )

    @staticmethod
    def get_severity_order(severity: str) -> int:
        """
        Получить порядковое значение уровня серьезности для сортировки

        Args:
            severity: Название уровня серьезности

        Returns:
            Целое порядковое значение уровня серьезности
        """
        severity_order = {
            'critical': 4,
            'high': 3,
            'warning': 2,
            'info': 1,
            'unknown': 0
        }

        return severity_order.get(severity.lower(), 0)

    @staticmethod
    def get_highest_severity(severities: List[str]) -> str:
        """
        Получить самый высокий уровень серьезности

        Args:
            severities: Список уровней серьезности

        Returns:
            Самый высокий уровень серьезности
        """
        if not severities:
            return 'unknown'

        highest = 'unknown'
        highest_order = 0

        for severity in severities:
            order = RuleProcessor.get_severity_order(severity)
            if order > highest_order:
                highest = severity
                highest_order = order

        return highest

    def evaluate_assertions(self, assertions: List[Dict], context: Dict[str, Any]) -> Dict:
        """
        Оценить набор утверждений (делегировано AssertionManager)

        Args:
            assertions: Список утверждений
            context: Словарь контекстных переменных

        Returns:
            Словарь результатов оценки, содержащий пройденные, неудачные утверждения и т.д.
        """
        return self.assertion_manager.evaluate_assertions(assertions, context, mode="detailed")

    def extract_variables(self, output: str, extractors: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        Извлечь переменные из вывода

        Args:
            output: Вывод команды
            extractors: Список конфигураций экстракторов
            context: Контекстные переменные

        Returns:
            Словарь извлеченных переменных
        """
        return self.result_extractor.extract(output, extractors, context)
