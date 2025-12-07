#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт инициализации KubeEye
Для инициализационной работы при запуске Docker-контейнера
"""

import os
import sys
from pathlib import Path

def ensure_data_directories():
    """Обеспечить существование каталогов данных"""
    data_dir = Path(os.environ.get('KUBEEYE_DATA_DIR', '/app/data'))

    # Создать необходимые каталоги
    directories = [
        data_dir / 'clusters',
        data_dir / 'results',
        data_dir / 'logs',
        data_dir / 'schedules',
        data_dir / 'git_rules'
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Обеспечить существование каталога: {directory}")

def validate_environment():
    """Проверить конфигурацию среды"""
    required_env_vars = [
        'PYTHONPATH',
        'KUBEEYE_DATA_DIR'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Отсутствуют переменные среды: {', '.join(missing_vars)}")
        return False

    print("Проверка переменных среды пройдена")
    return True

def main():
    """Главная функция инициализации"""
    print("Инициализация KubeEye начата...")

    try:
        # Проверить среду
        if not validate_environment():
            sys.exit(1)

        # Обеспечить каталоги данных
        ensure_data_directories()

        print("Инициализация KubeEye завершена!")

    except Exception as e:
        print(f"Инициализация не удалась: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
