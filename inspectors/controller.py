#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Контроллер проверки, отвечает за планирование и координацию различных типов проверок
"""

import logging
from typing import Dict, List, Any, Optional

from inspectors.node.node_inspector import NodeInspector
from inspectors.opa.opa_inspector import OpaInspector
from inspectors.prometheus.prometheus_inspector import PrometheusInspector
from utils.inspection_result import InspectionResult

# Настройка логирования
logger = logging.getLogger(__name__)

class InspectionController:
    """Контроллер проверки, отвечает за координацию процесса проверки"""

    def __init__(self, config: Dict[str, Any], use_gitops: bool = False):
        """
        Инициализация контроллера проверки

        Args:
            config: конфигурация контроллера
            use_gitops: использовать ли правила GitOps
        """
        self.config = config
        self.use_gitops = use_gitops
        self.inspectors = {}
        self._initialize_inspectors()

    def _initialize_inspectors(self):
        """Инициализация всех инспекторов"""
        # Вывод информации о конфигурации для отладки
        logger.info(f"Конфигурация контроллера: {list(self.config.keys())}")
        logger.info(f"Режим GitOps: {self.use_gitops}")

        # Инициализация инспектора узлов
        if 'nodes' in self.config and self.config['nodes']:
            logger.info(f"Обнаружена конфигурация узлов, количество узлов: {len(self.config['nodes'])}")
            self.inspectors['node'] = NodeInspector(self.config['nodes'], use_gitops=self.use_gitops)
            logger.info("Инициализирован инспектор узлов")
        else:
            logger.warning(f"Конфигурация узлов не найдена: nodes={'nodes' in self.config}, count={len(self.config.get('nodes', []))}")

        # Инициализация OPA инспектора
        if 'opa' in self.config:
            self.inspectors['opa'] = OpaInspector(self.config['opa'], use_gitops=self.use_gitops)
            logger.info("Инициализирован OPA инспектор")

        # Инициализация Prometheus инспектора
        if 'prometheus' in self.config:
            self.inspectors['prometheus'] = PrometheusInspector(self.config['prometheus'], use_gitops=self.use_gitops)
            logger.info("Инициализирован Prometheus инспектор")

        logger.info(f"Инициализировано {len(self.inspectors)} инспекторов: {list(self.inspectors.keys())}")

    def get_available_inspectors(self) -> List[str]:
        """
        Получить доступные типы инспекторов

        Returns:
            Список типов инспекторов
        """
        return list(self.inspectors.keys())

    def run_inspection(self, cluster_name: str, inspector_types: List[str] = None,
                      rule_ids: Dict[str, List[str]] = None) -> Dict[str, InspectionResult]:
        """
        Выполнить проверку

        Args:
            cluster_name: имя кластера
            inspector_types: список типов инспекторов для выполнения, если None, выполнить все инспекторы
            rule_ids: словарь ID правил для каждого инспектора, формат {inspector_type: [rule_id1, rule_id2]}

        Returns:
            Словарь результатов проверки, формат {inspector_type: inspection_result}
        """
        results = {}

        # Определить инспекторы для выполнения
        if inspector_types:
            active_inspectors = {k: v for k, v in self.inspectors.items() if k in inspector_types}
        else:
            active_inspectors = self.inspectors

        if not active_inspectors:
            logger.warning("Нет доступных инспекторов")
            return results

        # Выполнение проверки
        for inspector_type, inspector in active_inspectors.items():
            try:
                # Получить ID правил для этого инспектора
                inspector_rule_ids = None
                if rule_ids and inspector_type in rule_ids:
                    inspector_rule_ids = rule_ids[inspector_type]

                logger.info(f"Выполнение {inspector_type} проверки...")
                result = inspector.run_inspection(cluster_name, inspector_rule_ids)
                results[inspector_type] = result
                logger.info(f"{inspector_type} проверка завершена, найдено {len(result.items)} результатов")

            except Exception as e:
                logger.exception(f"Ошибка выполнения {inspector_type} проверки: {str(e)}")

        return results

    def save_inspection_result(self, all_results: Dict[str, InspectionResult],
                             cluster_name: str, inspection_type: str = "immediate") -> str:
        """
        Сохранить результаты проверки в файл

        Args:
            all_results: словарь результатов проверки
            cluster_name: имя кластера
            inspection_type: тип проверки ('immediate' или 'scheduled')

        Returns:
            Путь к сохраненному файлу
        """
        import os
        import json
        from datetime import datetime
        from pathlib import Path

        # Убедиться, что каталог results существует
        results_dir = Path("data/results")
        results_dir.mkdir(parents=True, exist_ok=True)

        # Генерация ID результата и имени файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_id = f"{inspection_type}_{timestamp}"
        filename = f"inspection_result_{cluster_name}_{timestamp}.json"
        result_path = results_dir / filename

        # Вычисление статистики
        total_items = 0
        total_passed = 0
        total_failed = 0
        total_warning = 0
        total_error = 0

        # Сериализация результатов проверки
        serialized_results = {}
        for inspector_type, result in all_results.items():
            if hasattr(result, 'items'):
                items = result.items
            else:
                items = []

            # Вычисление статистики - безопасный доступ к свойствам элемента
            total_items += len(items)
            for item in items:
                # Безопасное получение статуса
                if hasattr(item, '__dict__'):
                    status = getattr(item, 'status', 'unknown')
                elif isinstance(item, dict):
                    status = item.get('status', 'unknown')
                elif isinstance(item, (tuple, list)) and len(item) > 1:
                    status = str(item[1])
                else:
                    status = 'unknown'

                # Статистика по статусам - использование упрощенной системы статусов
                if status == 'passed':
                    total_passed += 1
                else:
                    # Все непройденные статусы считаются исключениями
                    # Обработка совместимости со старыми статусами
                    if status in ['failed', 'error']:
                        total_failed += 1
                    elif status == 'warning':
                        total_warning += 1
                    else:
                        # Неизвестный статус обрабатывается как ошибка
                        total_error += 1

            # Сериализация items - обеспечение, что все items имеют формат словаря
            serialized_items = []
            for item in items:
                if hasattr(item, '__dict__'):
                    # Если это объект, преобразовать в словарь
                    serialized_items.append(item.__dict__)
                elif isinstance(item, dict):
                    # Если уже словарь, использовать напрямую
                    serialized_items.append(item)
                elif isinstance(item, (tuple, list)) and len(item) >= 2:
                    # Если это кортеж или список, попытаться преобразовать в базовый формат словаря
                    serialized_items.append({
                        'name': str(item[0]) if len(item) > 0 else 'Unknown',
                        'status': str(item[1]) if len(item) > 1 else 'unknown',
                        'description': str(item[2]) if len(item) > 2 else '',
                        'severity': 'info',
                        'details': str(item),
                        'solution': ''
                    })
                else:
                    # Другие случаи, создать базовый словарь
                    serialized_items.append({
                        'name': str(item),
                        'status': 'unknown',
                        'description': f'Преобразовано из {type(item).__name__}',
                        'severity': 'info',
                        'details': str(item),
                        'solution': ''
                    })

            serialized_results[inspector_type] = {
                "inspector_type": inspector_type,
                "items": serialized_items
            }

        # Построение полной структуры результата
        result_data = {
            "result_id": result_id,
            "cluster_name": cluster_name,
            "timestamp": datetime.now().isoformat(),
            "inspection_type": inspection_type,  # immediate или scheduled
            "execution_info": {
                "triggered_by": "user" if inspection_type == "immediate" else "scheduler",
                "inspectors_used": list(all_results.keys()),
                "execution_duration": "N/A"  # Можно добавить функциональность таймера позже
            },
            "inspection_results": serialized_results,
            "summary": {
                "total_items": total_items,
                "passed": total_passed,
                "failed": total_failed,
                "warning": total_warning,
                "error": total_error
            },
            # Совместимость со старыми полями
            "critical": total_failed,  # Отображение failed как critical для совместимости с существующим кодом
            "warning": total_warning,
            "passed": total_passed
        }

        # Сохранение в файл
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        # Запуск очистки данных - очистка старых отчетов после создания нового
        try:
            from utils.data_cleanup import get_cleanup_manager
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.cleanup_inspection_results()
        except Exception as e:
            logger.warning(f"Ошибка очистки старых отчетов: {e}")

        logger.info(f"Результаты проверки сохранены в: {result_path}")
        return str(result_path)
