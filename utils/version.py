#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль информации о версии, для управления информацией о версии проекта
"""

# Основной номер версии
VERSION_MAJOR = 2
# Второстепенный номер версии
VERSION_MINOR = 0
# Номер исправления
VERSION_PATCH = 0
# Метка версии (например 'alpha', 'beta', 'rc1', оставить пустым для официальной версии)
VERSION_TAG = 'alpha'

# Полный номер версии
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
if VERSION_TAG:
    VERSION = f"{VERSION}-{VERSION_TAG}"

# Название приложения
APP_NAME = "kubeeye"
# Описание приложения
APP_DESCRIPTION = "Инструмент инспекции кластера Kubernetes"
# Автор приложения
APP_AUTHOR = "pixiake"
# Домашняя страница приложения
APP_URL = "https://github.com/kubesphere/kubeeye"

# Дата выпуска версии
RELEASE_DATE = "2025-06-25"

def get_version():
    """Получить текущий номер версии"""
    return VERSION

# Словарь информации о версии
VERSION_INFO = {
    'name': APP_NAME,
    'version': VERSION,
    'description': APP_DESCRIPTION,
    'author': APP_AUTHOR,
    'url': APP_URL,
    'release_date': RELEASE_DATE
}

def get_version_info():
    """Получить словарь информации о версии"""
    return VERSION_INFO

def get_version_string():
    """Получить строку версии"""
    return f"{APP_NAME} v{VERSION}"

if __name__ == "__main__":
    print(get_version_string())
