#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс инспектора, определяет общие интерфейсы и базовые функции для всех инспекторов
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Any, Optional, Union

from utils.inspection_result import InspectionResult
from utils.rule_loader import Rule, load_rules
from inspectors.rule_processor import RuleProcessor

# Настройка логирования
logger = logging.getLogger(__name__)

class BaseInspector(ABC):
    """Базовый класс инспектора, все типы инспекторов должны наследовать этот класс"""

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Инициализация инспектора

        Args:
            config: конфигурация инспектора
            use_gitops: использовать ли правила GitOps
        """
        self.config = config
        self.use_gitops = use_gitops
        self.rules = []
        self.rule_processor = RuleProcessor()
        self._load_rules()

    @property
    @abstractmethod
    def inspector_type(self) -> str:
        """Возвращает тип инспектора, например 'node', 'opa', 'prometheus'"""
        pass

    def _load_rules(self):
        """Загрузить правила, применимые к этому инспектору"""
        yaml_rules = load_rules(rule_type=self.inspector_type, use_gitops=self.use_gitops)
        self.rules = [rule for rule in yaml_rules if rule.enabled]
        source_type = "GitOps" if self.use_gitops else "локальных"
        logger.info(f"Загружено {len(self.rules)} {source_type} правил {self.inspector_type} проверки")

    @abstractmethod
    def _apply_rule(self, rule: Rule, context: Dict) -> Union[Dict, List[Dict], None]:
        """
        Применить одно правило для проверки

        Args:
            rule: применяемое правило
            context: контекст проверки

        Returns:
            Результат проверки, может быть одним словарем результата, списком результатов или None (означает, что правило неприменимо)
        """
        pass

    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """
        Получить правило по ID

        Args:
            rule_id: ID правила

        Returns:
            Объект правила, если не найден, возвращает None
        """
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def run_inspection(self, cluster_name: str, rule_ids: List[str] = None) -> InspectionResult:
        """
        Выполнить проверку

        Args:
            cluster_name: имя кластера
            rule_ids: список ID правил для выполнения, если None, выполнить все правила

        Returns:
            Объект результата проверки
        """
        source_type = "GitOps" if self.use_gitops else "локальных"
        logger.info(f"BaseInspector.run_inspection начато - тип инспектора: {self.inspector_type}, кластер: {cluster_name}, источник: {source_type}")
        logger.info(f"Доступных правил всего: {len(self.rules)}, указанные ID правил: {rule_ids}")

        result = InspectionResult(cluster_name, self.inspector_type)

        # Определить правила для выполнения
        if rule_ids:
            active_rules = [rule for rule in self.rules if rule.id in rule_ids]
            logger.info(f"Количество правил после фильтрации по указанным ID: {len(active_rules)}")
        else:
            active_rules = self.rules
            logger.info(f"Использование всех доступных правил: {len(active_rules)}")

        if not active_rules:
            logger.warning(f"Нет выполняемых правил, проверка завершена")
            return result

        logger.info(f"Подготовка к выполнению {len(active_rules)} правил:")
        for rule in active_rules:
            logger.info(f"  - {rule.id}: {rule.name}")

        # Выполнение правил
        context = self._prepare_context(cluster_name)
        logger.info(f"Контекст подготовлен: {context}")

        executed_count = 0
        for rule in active_rules:
            try:
                logger.info(f"Начало выполнения правила {rule.id}: {rule.name}")

                # Проверка конфигурации правила
                validation_issues = self._validate_rule_config(rule)
                if validation_issues:
                    logger.error(f"Правило {rule.id} имеет неверную конфигурацию: {validation_issues}")
                    # Конфигурация правила недействительна
                    result.add_item(self._format_invalid_result(
                        rule,
                        "Конфигурация правила недействительна",
                        f"Следующие проблемы конфигурации препятствуют выполнению правила: {', '.join(validation_issues)}"
                    ))
                    continue
                else:
                    logger.info(f"Правило {rule.id} прошло проверку конфигурации")

                # Проверить, применимо ли правило к текущей среде
                should_apply = self._should_apply_rule(rule, context)
                logger.info(f"Правило {rule.id} проверка применимости: {should_apply}")

                if should_apply:
                    logger.info(f"Применение правила {rule.id}")
                    inspection_result = self._apply_rule(rule, context)
                    logger.info(f"Правило {rule.id} применено, тип результата: {type(inspection_result)}")

                    if inspection_result:
                        # Обработка одного результата или списка результатов
                        if isinstance(inspection_result, list):
                            logger.info(f"Правило {rule.id} вернуло список результатов, длина: {len(inspection_result)}")
                            for item in inspection_result:
                                result.add_item(item)
                        else:
                            logger.info(f"Правило {rule.id} вернуло одиночный результат")
                            result.add_item(inspection_result)
                    else:
                        logger.warning(f"Правило {rule.id} вернуло пустой результат")
                else:
                    logger.info(f"Правило {rule.id} не применимо к текущей среде")
                    # Правило не применимо к текущей среде
                    result.add_item(self._format_not_applicable_result(
                        rule,
                        "Правило не применимо к текущей среде"
                    ))

                executed_count += 1
                logger.info(f"Правило {rule.id} выполнено ({executed_count}/{len(active_rules)})")

            except Exception as e:
                logger.exception(f"Ошибка выполнения правила {rule.id}: {str(e)}")
                error_result = self._format_error_result(
                    rule,
                    f"Ошибка выполнения правила: {str(e)}",
                    str(e)
                )
                result.add_item(error_result)

        logger.info(f"BaseInspector.run_inspection завершено - инспектор: {self.inspector_type}, выполнено правил: {executed_count}, результатов: {len(result.items)}")
        return result

    def _prepare_context(self, cluster_name: str) -> Dict:
        """
        Подготовить контекст проверки

        Args:
            cluster_name: имя кластера

        Returns:
            Контекст проверки
        """
        return {'cluster_name': cluster_name}

    def _should_apply_rule(self, rule: Rule, context: Dict) -> bool:
        """
        Определить, следует ли применять правило к текущему контексту

        Args:
            rule: правило
            context: контекст

        Returns:
            Применять ли правило
        """
        # Реализация по умолчанию всегда возвращает True
        # Подклассы могут переопределить этот метод для реализации более сложной фильтрации правил
        return True

    def _validate_rule_config(self, rule: Rule) -> List[str]:
        """
        Проверить, действительна ли конфигурация правила

        Args:
            rule: объект правила

        Returns:
            Список проблем конфигурации, если проблем нет, возвращает пустой список
        """
        # Подклассы должны переопределить этот метод для реализации логики проверки конкретного типа правил
        return []

    def get_rule_config(self, rule: Rule, path: str, default_value: Any = None) -> Any:
        """
        Получить значение конфигурации из правила, поддерживает вложенные пути

        Args:
            rule: объект правила
            path: путь конфигурации, использует точечную нотацию, например "execution.command"
            default_value: значение по умолчанию, возвращаемое, если путь не существует

        Returns:
            Значение конфигурации или значение по умолчанию
        """
        return self.rule_processor.get_rule_config(rule, path, default_value)

    def _format_invalid_result(self, rule: Rule, description: str, details: str) -> Dict:
        """
        Форматировать результат правила с недействительной конфигурацией (делегировано ResultFormatter)

        Args:
            rule: объект правила
            description: краткое описание
            details: подробная информация

        Returns:
            Форматированный словарь результата
        """
        return self.rule_processor.result_formatter.invalid_result(rule, description, details)

    def _format_not_applicable_result(self, rule: Rule, reason: str) -> Dict:
        """
        Форматировать результат неприменимого правила (делегировано ResultFormatter)

        Args:
            rule: объект правила
            reason: причина неприменимости

        Returns:
            Форматированный словарь результата
        """
        return self.rule_processor.result_formatter.not_applicable_result(rule, reason)

    def _format_skipped_result(self, rule: Rule, reason: str) -> Dict:
        """
        Форматировать результат пропущенного правила (делегировано ResultFormatter)

        Args:
            rule: объект правила
            reason: причина пропуска

        Returns:
            Форматированный словарь результата
        """
        return self.rule_processor.result_formatter.skipped_result(rule, reason)

    def _format_error_result(self, rule: Rule, description: str, error: str) -> Dict:
        """
        Форматировать результат правила с ошибкой (делегировано ResultFormatter)

        Args:
            rule: объект правила
            description: описание ошибки
            error: детали ошибки

        Returns:
            Форматированный словарь результата
        """
        return self.rule_processor.result_formatter.error_result(rule, error, description)
