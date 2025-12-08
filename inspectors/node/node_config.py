#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Управление конфигурацией параллелизма инспекции узлов
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class NodeInspectorConfig:
    """Конфигурация инспектора узлов"""

    # Управление параллелизмом
    max_workers: int = 5           # Максимальное количество параллельных потоков
    timeout: int = 30              # Время ожидания выполнения команды для одного узла (секунды)

    # Конфигурация подключения
    connection_timeout: int = 10   # Время ожидания подключения SSH (секунды)
    retry_attempts: int = 2        # Количество повторных попыток при неудачном подключении
    retry_delay: int = 1           # Интервал между повторными попытками (секунды)

    # Оптимизация производительности
    enable_connection_pool: bool = True   # Включить пул подключений
    pool_size: int = 10            # Размер пула подключений
    keep_alive: bool = True        # Поддерживать подключение активным

    # Конфигурация логирования
    verbose_logging: bool = False  # Подробное логирование
    log_command_output: bool = False  # Записывать вывод команд

    @classmethod
    def from_env(cls) -> 'NodeInspectorConfig':
        """Создать конфигурацию из переменных среды"""
        return cls(
            max_workers=int(os.getenv('NODE_INSPECTOR_MAX_WORKERS', '5')),
            timeout=int(os.getenv('NODE_INSPECTOR_TIMEOUT', '30')),
            connection_timeout=int(os.getenv('NODE_INSPECTOR_CONNECTION_TIMEOUT', '10')),
            retry_attempts=int(os.getenv('NODE_INSPECTOR_RETRY_ATTEMPTS', '2')),
            retry_delay=int(os.getenv('NODE_INSPECTOR_RETRY_DELAY', '1')),
            enable_connection_pool=os.getenv('NODE_INSPECTOR_CONNECTION_POOL', 'true').lower() == 'true',
            pool_size=int(os.getenv('NODE_INSPECTOR_POOL_SIZE', '10')),
            keep_alive=os.getenv('NODE_INSPECTOR_KEEP_ALIVE', 'true').lower() == 'true',
            verbose_logging=os.getenv('NODE_INSPECTOR_VERBOSE', 'false').lower() == 'true',
            log_command_output=os.getenv('NODE_INSPECTOR_LOG_OUTPUT', 'false').lower() == 'true'
        )

    @classmethod
    def adaptive(cls, node_count: int) -> 'NodeInspectorConfig':
        """Адаптивная конфигурация на основе количества узлов"""
        if node_count <= 3:
            max_workers = node_count
            timeout = 30
        elif node_count <= 10:
            max_workers = min(5, node_count)
            timeout = 25
        elif node_count <= 20:
            max_workers = min(8, node_count)
            timeout = 20
        else:
            max_workers = min(10, node_count)
            timeout = 15

        return cls(
            max_workers=max_workers,
            timeout=timeout,
            connection_timeout=min(10, timeout // 3),
            retry_attempts=2 if node_count <= 10 else 1,
            verbose_logging=node_count <= 5  # Включить подробное логирование при небольшом количестве узлов
        )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        return {
            'max_workers': self.max_workers,
            'timeout': self.timeout,
            'connection_timeout': self.connection_timeout,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'enable_connection_pool': self.enable_connection_pool,
            'pool_size': self.pool_size,
            'keep_alive': self.keep_alive,
            'verbose_logging': self.verbose_logging,
            'log_command_output': self.log_command_output
        }

    def validate(self) -> List[str]:
        """Проверить валидность конфигурации"""
        issues = []

        if self.max_workers < 1:
            issues.append("max_workers должен быть больше 0")
        if self.max_workers > 20:
            issues.append("max_workers не рекомендуется превышать 20, может привести к перегрузке ресурсов")

        if self.timeout < 5:
            issues.append("timeout не рекомендуется меньше 5 секунд")
        if self.timeout > 300:
            issues.append("timeout не рекомендуется превышать 5 минут")

        if self.connection_timeout < 1:
            issues.append("connection_timeout должен быть больше 0")

        if self.retry_attempts < 0:
            issues.append("retry_attempts не может быть меньше 0")
        if self.retry_attempts > 5:
            issues.append("retry_attempts не рекомендуется превышать 5 раз")

        return issues