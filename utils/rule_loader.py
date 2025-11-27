#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль загрузки правил - поддерживает режим GitOps
"""

import yaml
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Настройка логов
logger = logging.getLogger(__name__)

# Основная директория правил
RULES_DIR = Path(__file__).parent.parent / "rules"
# Директория GitOps правил
GIT_RULES_DIR = Path(__file__).parent.parent / "data" / "git_rules"

class Rule:
    """Класс правила, представляющий правило проверки, поддерживает формат утверждений"""

    def __init__(self, rule_data: Dict):
        """
        Инициализировать объект правила, поддерживает формат утверждений

        Args:
            rule_data: словарь данных правила
        """
        # Основные метаданные
        self.id = rule_data.get('id', '')
        self.name = rule_data.get('name', '')
        self.description = rule_data.get('description', '')
        self.type = rule_data.get('type', '')  # Тип правила: node, prometheus, opa
        self.category = rule_data.get('category', '')  # Категория правила
        self.severity = rule_data.get('severity', 'warning')  # Серьезность
        self.enabled = rule_data.get('enabled', True)  # Включено ли
        self.solution = rule_data.get('solution', '')  # Решение
        self.tags = rule_data.get('tags', [])  # Теги
        self.tier = rule_data.get('tier', 'basic')  # Уровень правила (basic/standard/extended)

        # Поля, связанные с GitOps
        self.source = rule_data.get('source', 'local')  # Источник: local или git
        self.repository = rule_data.get('repository', '')  # Имя Git репозитория
        self.file_path = rule_data.get('file_path', '')  # Путь в Git репозитории

        # Основная конфигурация
        self.config = rule_data.get('config', {})  # Единый объект конфигурации

        # Специфичные поля для режима утверждений
        self.assertions = self.config.get('assertions', [])  # Список конфигураций утверждений
        self.extractors = self.config.get('extractors', [])  # Список конфигураций экстракторов

    def to_dict(self) -> Dict:
        """Преобразовать правило в словарь"""
        # Базовые поля
        rule_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'category': self.category,
            'severity': self.severity,
            'enabled': self.enabled,
            'solution': self.solution,
            'tags': self.tags,
            'tier': self.tier,
            'config': self.config
        }

        # Включать информацию об источнике только для Git правил
        if self.source == 'git':
            rule_dict['source'] = self.source
            rule_dict['repository'] = self.repository
            rule_dict['file_path'] = self.file_path

        return rule_dict

    @property
    def execution(self) -> Dict:
        """Получить конфигурацию выполнения"""
        return self.config.get('execution', {})

def load_rules(rule_type: str = None, include_disabled: bool = False, use_gitops: bool = False) -> List[Rule]:
    """
    Загрузить правила указанного типа

    Args:
        rule_type: тип правила, например node, opa, prometheus, если None, загрузить все правила
        include_disabled: включать ли отключенные правила
        use_gitops: использовать ли правила GitOps

    Returns:
        Список правил
    """
    rules = []

    # Определить базовую директорию
    if use_gitops:
        base_dir = GIT_RULES_DIR
        # Если директория GitOps не существует, вернуть пустой список
        if not base_dir.exists():
            logger.info(f"Директория GitOps правил не существует: {base_dir}")
            return rules
        logger.info(f"Загрузка GitOps правил из: {base_dir}")

        # Для GitOps ищем во всех поддиректориях репозиториев
        search_dirs = []
        for repo_dir in base_dir.iterdir():
            if repo_dir.is_dir():
                type_dir = repo_dir / rule_type if rule_type else repo_dir
                if type_dir.exists():
                    search_dirs.append(type_dir)
                else:
                    # Если конкретный тип не найден, ищем все поддиректории с правилами
                    for sub_dir in repo_dir.iterdir():
                        if sub_dir.is_dir() and sub_dir.name in ['node', 'prometheus', 'opa']:
                            if not rule_type or sub_dir.name == rule_type:
                                search_dirs.append(sub_dir)
    else:
        base_dir = RULES_DIR
        logger.info(f"Загрузка локальных правил из: {base_dir}")

        # Определить директории для поиска
        search_dirs = []
        if rule_type:
            # Искать только в директории указанного типа правил
            type_dir = base_dir / rule_type
            if type_dir.exists():
                search_dirs.append(type_dir)
            else:
                logger.warning(f"Директория для типа правил '{rule_type}' не существует: {type_dir}")
        else:
            # Искать во всех директориях правил
            for item in base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_') and not item.name == 'examples':
                    search_dirs.append(item)

    logger.info(f"Найдено директорий для поиска: {[str(d) for d in search_dirs]}")

    # Загрузить правила из каждой директории
    for rules_dir in search_dirs:
        logger.info(f"Поиск правил в директории: {rules_dir}")

        yaml_files = list(rules_dir.glob('*.yaml'))
        logger.info(f"Найдено YAML файлов в {rules_dir}: {len(yaml_files)}")

        for file_path in yaml_files:
            try:
                # Загрузить YAML файл
                with open(file_path, 'r', encoding='utf-8') as f:
                    rule_data = yaml.safe_load(f)

                # Убедиться, что данные правила являются словарем
                if not isinstance(rule_data, dict):
                    logger.warning(f"Формат файла правила {file_path} неверен, должен быть YAML словарь")
                    continue

                # Определить тип правила
                if 'type' not in rule_data:
                    # Попробовать определить тип из имени директории
                    dir_name = rules_dir.name
                    if dir_name in ['node', 'prometheus', 'opa']:
                        rule_data['type'] = dir_name
                    else:
                        # Если это поддиректория репозитория, посмотреть на родительскую директорию
                        parent_dir = rules_dir.parent.name
                        if parent_dir in ['node', 'prometheus', 'opa']:
                            rule_data['type'] = parent_dir
                        else:
                            rule_data['type'] = 'unknown'

                # Для правил GitOps добавить информацию об источнике
                if use_gitops:
                    # Найти имя репозитория из пути
                    repo_name = None
                    try:
                        # Путь относительно GIT_RULES_DIR
                        relative_path = file_path.relative_to(GIT_RULES_DIR)
                        if relative_path.parts:
                            repo_name = relative_path.parts[0]
                    except ValueError:
                        pass

                    rule_data['source'] = 'git'
                    rule_data['repository'] = repo_name or 'unknown'
                    rule_data['file_path'] = str(file_path.relative_to(GIT_RULES_DIR))

                    # АВТОМАТИЧЕСКИ ВКЛЮЧАЕМ ПРАВИЛА ИЗ GITOPS
                    rule_data['enabled'] = True
                    logger.info(f"Правило из GitOps автоматически включено: {rule_data.get('id', 'unknown')}")

                # Создать объект правила
                rule = Rule(rule_data)

                # Проверить, следует ли включать в результат
                if rule.enabled or include_disabled:
                    rules.append(rule)
                    logger.info(f"Загружено правило: {rule.id} (тип: {rule.type}, включено: {rule.enabled})")
                else:
                    logger.info(f"Пропущено отключенное правило: {rule.id}")

            except Exception as e:
                logger.error(f"Не удалось загрузить файл правила {file_path}: {str(e)}")

    logger.info(f"Загружено {len(rules)} правил из {'GitOps' if use_gitops else 'локальной'} директории")
    return rules

def load_rule_from_file(file_path: str) -> Optional[Rule]:
    """
    Загрузить одно правило из файла

    Args:
        file_path: путь к файлу правила

    Returns:
        Объект правила, если загрузка не удалась, вернуть None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            rule_data = yaml.safe_load(f)

        if not isinstance(rule_data, dict):
            logger.warning(f"Формат файла правила {file_path} неверен, должен быть YAML словарь")
            return None

        # Если тип не указан явно, попытаться вывести из пути к файлу
        if 'type' not in rule_data:
            # Попытаться извлечь тип правила из пути
            path_parts = Path(file_path).parts
            for part in path_parts:
                if part in ('node', 'opa', 'prometheus'):
                    rule_data['type'] = part
                    break

        return Rule(rule_data)

    except Exception as e:
        logger.error(f"Не удалось загрузить файл правила {file_path}: {str(e)}")
        return None

def save_rule(rule: Rule) -> bool:
    """
    Сохранить правило в файл

    Args:
        rule: объект правила для сохранения

    Returns:
        Успешно ли сохранение
    """
    try:
        # Определить директорию типа правила
        rule_type_dir = RULES_DIR / rule.type

        # Убедиться, что директория существует
        if not rule_type_dir.exists():
            rule_type_dir.mkdir(parents=True, exist_ok=True)

        # Путь к файлу правила
        file_path = rule_type_dir / f"{rule.id}.yaml"

        # Преобразовать правило в словарь
        rule_dict = rule.to_dict()

        # Сохранить в файл
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(rule_dict, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Правило {rule.id} успешно сохранено в файл {file_path}")
        return True

    except Exception as e:
        logger.error(f"Не удалось сохранить правило {rule.id}: {str(e)}")
        return False