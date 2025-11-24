#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль унифицированного форматирования результатов
Предоставляет унифицированные функции форматирования результатов, устраняя дублирование методов _pass_result, _fail_result, _error_result в различных инспекторах
"""

import logging
from typing import Dict, List, Optional, Any
from utils.rule_loader import Rule

# Настройка логирования
logger = logging.getLogger(__name__)

class ResultFormatter:
    """
    Унифицированный форматировщик результатов
    Объединяет дублирующиеся методы форматирования результатов из различных инспекторов
    """

    @staticmethod
    def format_result(rule: Rule, status: str, description: str, severity: str,
                     details: str, solution: Optional[str] = None,
                     violations: Optional[List[Dict]] = None,
                     **kwargs) -> Dict:
        """
        Форматирование результата проверки (унифицированная версия)

        Args:
            rule: объект правила
            status: статус (passed, failed, error, warning, skipped и др.)
            description: краткое описание результата
            severity: уровень серьезности
            details: детальная информация
            solution: опциональное решение проблемы
            violations: опциональный список нарушений
            **kwargs: другие дополнительные поля (например node, variables, assertions и др.)

        Returns:
            отформатированный словарь результата
        """
        if solution is None:
            solution = rule.solution if hasattr(rule, 'solution') else ""

        result = {
            'name': rule.name,
            'status': status,
            'description': description,
            'severity': severity,
            'details': details,
            'solution': solution,
            'rule_id': rule.id
        }

        # Если есть violations, добавляем в результат
        if violations is not None:
            result['violations'] = violations

        # Добавление других дополнительных полей
        result.update(kwargs)

        return result

    @staticmethod
    def pass_result(rule: Rule, description: str, details: str = "", **kwargs) -> Dict:
        """
        Генерация результата "Пройдено"

        Args:
            rule: объект правила
            description: информация описания
            details: детальная информация
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Пройдено"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="passed",
            description=description,
            severity="info",
            details=details,
            solution="",
            **kwargs
        )

    @staticmethod
    def fail_result(rule: Rule, description: str, details: str,
                   severity: str = "warning", violations: List[Dict] = None,
                   **kwargs) -> Dict:
        """
        Генерация результата "Не пройдено"

        Args:
            rule: объект правила
            description: информация описания
            details: детальная информация
            severity: уровень серьезности
            violations: список нарушений
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Не пройдено"
        """
        solution = rule.solution if hasattr(rule, 'solution') else ""
        return ResultFormatter.format_result(
            rule=rule,
            status="failed",
            description=description,
            severity=severity,
            details=details,
            solution=solution,
            violations=violations or [],
            **kwargs
        )

    @staticmethod
    def error_result(rule: Rule, error_msg: str, description: str = None, **kwargs) -> Dict:
        """
        Генерация результата "Ошибка"

        Args:
            rule: объект правила
            error_msg: сообщение об ошибке
            description: пользовательское описание, по умолчанию "Выполнение правила не удалось"
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Ошибка"
        """
        if description is None:
            description = "Выполнение правила не удалось"

        return ResultFormatter.format_result(
            rule=rule,
            status="error",
            description=description,
            severity="error",
            details=error_msg,
            solution="",
            **kwargs
        )

    @staticmethod
    def warning_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Генерация результата "Предупреждение"

        Args:
            rule: объект правила
            description: информация описания
            details: детальная информация
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Предупреждение"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="warning",
            description=description,
            severity="warning",
            details=details,
            solution=rule.solution if hasattr(rule, 'solution') else "",
            **kwargs
        )

    @staticmethod
    def skipped_result(rule: Rule, reason: str, **kwargs) -> Dict:
        """
        Генерация результата "Пропущено"

        Args:
            rule: объект правила
            reason: причина пропуска
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Пропущено"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="skipped",
            description=f"{rule.name} пропущено: {reason}",
            severity="info",
            details=reason,
            solution="",
            **kwargs
        )

    @staticmethod
    def not_applicable_result(rule: Rule, reason: str, **kwargs) -> Dict:
        """
        Генерация результата "Не применимо"

        Args:
            rule: объект правила
            reason: причина неприменимости
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Не применимо"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="not_applicable",
            description=f"Правило не применимо: {reason}",
            severity="info",
            details=f"Правило {rule.name} не применимо к текущему окружению: {reason}",
            solution="",
            **kwargs
        )

    @staticmethod
    def invalid_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Генерация результата "Конфигурация недействительна"

        Args:
            rule: объект правила
            description: краткое описание
            details: детальная информация
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Конфигурация недействительна"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="invalid",
            description=description,
            severity="warning",
            details=details,
            solution="Пожалуйста, проверьте конфигурацию правила и исправьте проблемы",
            **kwargs
        )

    @staticmethod
    def critical_result(rule: Rule, description: str, details: str, **kwargs) -> Dict:
        """
        Генерация результата "Критическая проблема"

        Args:
            rule: объект правила
            description: информация описания
            details: детальная информация
            **kwargs: другие дополнительные поля

        Returns:
            отформатированный результат "Критическая проблема"
        """
        return ResultFormatter.format_result(
            rule=rule,
            status="failed",
            description=description,
            severity="critical",
            details=details,
            solution=rule.solution if hasattr(rule, 'solution') else "",
            **kwargs
        )