#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенная конфигурация безопасности KubeEye - чтение только основных параметров конфигурации
"""

import os
import yaml
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleSecurityConfig:
    """Упрощенный класс конфигурации безопасности - обработка только настраиваемых параметров"""

    def __init__(self, config_file: str = "config/security.yaml"):
        """
        Инициализировать упрощенную конфигурацию безопасности

        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Загрузить файл конфигурации"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Файл конфигурации не существует: {config_path}，использовать конфигурацию по умолчанию")
                config = {}

            # Установить значения по умолчанию
            return {
                'max_command_length': config.get('max_command_length', 1000),
                'command_timeout': config.get('command_timeout', 30),
                'audit_log_path': config.get('audit_log_path', 'data/logs/security_audit.log'),
                'audit_retention_days': config.get('audit_retention_days', 90),
                'enable_detailed_logging': config.get('enable_detailed_logging', True),
                'allowed_ports': config.get('allowed_ports', [22, 80, 443, 6443, 8080, 9090, 10250]),
                'blocked_ips': config.get('blocked_ips', []),
                'require_key_auth': config.get('require_key_auth', False)
            }
        except Exception as e:
            logger.error(f"Не удалось загрузить конфигурацию безопасности: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Получить конфигурацию по умолчанию"""
        return {
            'max_command_length': 1000,
            'command_timeout': 30,
            'audit_log_path': 'data/logs/security_audit.log',
            'audit_retention_days': 90,
            'enable_detailed_logging': True,
            'allowed_ports': [22, 80, 443, 6443, 8080, 9090, 10250],
            'blocked_ips': [],
            'require_key_auth': False
        }

    def get(self, key: str, default=None):
        """Получить значение конфигурации"""
        return self.config.get(key, default)

    @property
    def max_command_length(self) -> int:
        """Максимальная длина команды"""
        return self.config['max_command_length']

    @property
    def command_timeout(self) -> int:
        """Время ожидания команды"""
        return self.config['command_timeout']

    @property
    def audit_log_path(self) -> str:
        """Путь к журналу аудита"""
        return self.config['audit_log_path']

    @property
    def audit_retention_days(self) -> int:
        """Количество дней хранения журнала аудита"""
        return self.config['audit_retention_days']

    @property
    def enable_detailed_logging(self) -> bool:
        """Включить ли подробное логирование"""
        return self.config['enable_detailed_logging']

    @property
    def allowed_ports(self) -> List[int]:
        """Список разрешенных портов"""
        return self.config['allowed_ports']

    @property
    def blocked_ips(self) -> List[str]:
        """Список заблокированных IP"""
        return self.config['blocked_ips']

    @property
    def require_key_auth(self) -> bool:
        """Требовать ли аутентификацию по ключу"""
        return self.config['require_key_auth']

# Глобальный экземпляр конфигурации
_global_security_config = None

def get_security_config() -> SimpleSecurityConfig:
    """Получить глобальный экземпляр конфигурации безопасности"""
    global _global_security_config
    if _global_security_config is None:
        _global_security_config = SimpleSecurityConfig()
    return _global_security_config
