#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль экстрактора результатов, для извлечения переменных из вывода команд
"""

import re
import logging
from typing import Dict, List, Any

# Настроить логирование
logger = logging.getLogger(__name__)

class ResultExtractor:
    """Извлечение переменных из вывода команд"""

    def extract(self, output: str, extractors: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        Извлечение переменных из вывода на основе конфигурации экстракторов

        Args:
            output: Текст вывода команды
            extractors: Список конфигураций экстракторов
            context: Существующие контекстные переменные

        Returns:
            Словарь извлеченных переменных
        """
        result = context.copy() if context else {}

        for extractor in extractors:
            name = extractor.get("name")
            if not name:
                logger.warning("У экстрактора отсутствует поле name")
                continue

            pattern = extractor.get("pattern")
            value_type = extractor.get("type", "str")

            if pattern:
                # Использовать регулярные выражения для извлечения
                try:
                    match = re.search(pattern, output)
                    if match:
                        # Проверить, есть ли группы захвата
                        if match.groups():
                            # Есть группы захвата, использовать первую группу захвата
                            value = match.group(1)
                        else:
                            # Нет групп захвата, использовать все совпадение
                            value = match.group(0)
                        result[name] = self._convert_value(value, value_type)
                    else:
                        logger.warning(f"Паттерн экстрактора '{name}' '{pattern}' не нашел совпадений")
                        result[name] = None
                except (re.error, IndexError) as e:
                    logger.error(f"Ошибка регулярного выражения экстрактора '{name}': {str(e)}")
                    result[name] = None

        return result

    def _convert_value(self, value: str, value_type: str) -> Any:
        """
        Преобразовать тип значения

        Args:
            value: Строковое значение
            value_type: Целевой тип

        Returns:
            Преобразованное значение
        """
        try:
            if value_type == "int":
                return int(value)
            elif value_type == "float":
                return float(value)
            elif value_type == "bool":
                return value.lower() in ("true", "yes", "1", "on")
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.error(f"Не удалось преобразовать тип: {str(e)}, вернуть исходное значение")
            return value
