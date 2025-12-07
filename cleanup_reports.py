#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматической очистки старых отчётов KubeEye
Может выполняться по расписанию через cron
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Добавление корневой директории в путь
ROOT_DIR = Path(__file__).parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Функции очистки (скопированы для автономности)
import json
from pathlib import Path
from datetime import datetime, timedelta

CONFIG_FILE = Path(__file__).parent / "data" / "cleanup_config.json"
DEFAULT_RETENTION_DAYS = 14
DEFAULT_AUTO_CLEANUP = False

# Environment variable for retention days
ENV_RETENTION_DAYS = "KUBEYE_REPORT_RETENTION_DAYS"

def load_cleanup_config() -> dict:
    """Загрузить конфигурацию очистки"""
    # Check environment variable first
    env_retention = os.getenv(ENV_RETENTION_DAYS)
    if env_retention:
        try:
            retention_days = int(env_retention)
            if retention_days > 0:
                return {
                    'retention_days': retention_days,
                    'source': 'env'
                }
        except ValueError:
            pass

    # Fall back to config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config['source'] = 'file'
                return config
        except Exception:
            pass

    return {
        'retention_days': DEFAULT_RETENTION_DAYS,
        'source': 'default'
    }

def save_cleanup_config(config: dict):
    """Сохранить конфигурацию очистки"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def cleanup_old_reports(retention_days: int) -> tuple[int, int]:
    """Очистить старые отчёты старше retention_days дней

    Returns:
        tuple: (удалено_файлов, освобождено_места_в_байтах)
    """
    if retention_days <= 0:
        return 0, 0

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    results_dir = Path(__file__).parent / "data" / "results"

    if not results_dir.exists():
        return 0, 0

    deleted_count = 0
    freed_space = 0

    for file_path in results_dir.glob("*.json"):
        try:
            # Проверяем дату изменения файла
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_date:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_space += file_size
        except Exception:
            continue

    return deleted_count, freed_space


def run_cleanup():
    """Выполнить очистку отчётов согласно настройкам"""
    print("🧹 Запуск очистки отчётов KubeEye...")

    try:
        # Загрузить конфигурацию
        config = load_cleanup_config()
        retention_days = config.get('retention_days', DEFAULT_RETENTION_DAYS)
        print(f"📅 Период хранения: {retention_days} дней")

        # Выполнить очистку
        deleted_count, freed_space = cleanup_old_reports(retention_days)

        # Вывести результаты
        if deleted_count > 0:
            freed_mb = freed_space / (1024 * 1024)
            print(f"✅ Удалено {deleted_count} файлов, освобождено {freed_mb:.1f} MB")
        else:
            print("ℹ️ Не найдено файлов для удаления")

    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        sys.exit(1)


def main():
    """Основная функция для запуска из командной строки"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
KubeEye - очистка старых отчётов

Использование:
    python3 cleanup_reports.py          # Запустить очистку
    python3 cleanup_reports.py --help    # Показать эту справку

Пример:
    cd /path/to/kubeeye
    python3 cleanup_reports.py
            """)
            return

    run_cleanup()


if __name__ == "__main__":
    main()