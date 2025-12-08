#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для парсинга узлов из текстового формата
"""

import re
from typing import List, Dict, Any, Tuple

# Предварительно скомпилированные регулярные выражения для производительности
IP_PORT_PATTERN = re.compile(r'^([\d\.]+)(?::(\d+))?$')
NODE_PATTERN = re.compile(
    r'^(\d+\.\d+\.\d+\.\d+)(?::(\d+))?\s+(\w+)\s+(password|key)(?:\s+(.+))?$'
)

def parse_nodes_from_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Оптимизированный парсинг текста с узлами с использованием предварительно скомпилированных regex

    Args:
        text: Текст с узлами в формате "IP:Порт Пользователь ТипАутентификации [Пароль/ПутьККлючу]"

    Returns:
        Кортеж (список узлов, список ошибок)
    """
    nodes = []
    errors = []

    lines = text.strip().split('\n')

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Пропускаем пустые строки и комментарии
        if not line or line.startswith('#'):
            continue

        try:
            # Используем предварительно скомпилированный паттерн для полной строки
            match = NODE_PATTERN.match(line)
            if not match:
                errors.append(f"Строка {line_num}: неверный формат")
                continue

            ip, port, username, auth_type, credential = match.groups()
            port = port or "22"

            # Валидация IP
            if not is_valid_ip(ip):
                errors.append(f"Строка {line_num}: неверный IP-адрес")
                continue

            # Валидация порта
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                errors.append(f"Строка {line_num}: неверный порт")
                continue

            auth_type = auth_type.lower()
            node_info = {
                "ip": ip,
                "port": port,
                "username": username,
                "auth_type": auth_type
            }

            # Обработка учетных данных
            if auth_type == 'password':
                if credential:
                    node_info["password"] = credential
                else:
                    errors.append(f"Строка {line_num}: для типа 'password' требуется пароль")
                    continue
            else:  # key
                if credential:
                    node_info["key_path"] = credential
                else:
                    errors.append(f"Строка {line_num}: для типа 'key' требуется путь к ключу")
                    continue

            nodes.append(node_info)

        except Exception as e:
            errors.append(f"Строка {line_num}: ошибка обработки - {str(e)}")

    return nodes, errors

def is_valid_ip(ip: str) -> bool:
    """Проверяет валидность IP-адреса"""
    parts = ip.split('.')
    if len(parts) != 4:
        return False

    for part in parts:
        if not part.isdigit():
            return False
        if not (0 <= int(part) <= 255):
            return False

    return True

def generate_nodes_template() -> str:
    """Генерирует шаблон для массового добавления узлов"""
    return """# Формат для массового добавления узлов
# Каждая строка должна содержать: IP:Порт Пользователь ТипАутентификации [Пароль/ПутьККлючу]

# Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123

# Примечания:
# - Порт можно опустить, будет использован 22
# - Тип аутентификации: password или key
# - Для password укажите пароль, для key - путь к файлу ключа
"""