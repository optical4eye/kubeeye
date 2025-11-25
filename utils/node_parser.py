#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для парсинга узлов из текстового формата
"""

import re
from typing import List, Dict, Any, Tuple

def parse_nodes_from_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Парсит текст с узлами и возвращает список узлов и список ошибок

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
            parts = line.split()
            if len(parts) < 3:
                errors.append(f"Строка {line_num}: недостаточно параметров")
                continue

            # Парсинг IP и порта
            ip_port_match = re.match(r'^([\d\.]+)(?::(\d+))?$', parts[0])
            if not ip_port_match:
                errors.append(f"Строка {line_num}: неверный формат IP:порта")
                continue

            ip = ip_port_match.group(1)
            port = ip_port_match.group(2) or "22"

            # Валидация IP
            if not is_valid_ip(ip):
                errors.append(f"Строка {line_num}: неверный IP-адрес")
                continue

            # Валидация порта
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                errors.append(f"Строка {line_num}: неверный порт")
                continue

            username = parts[1]
            auth_type = parts[2].lower()

            if auth_type not in ['password', 'key']:
                errors.append(f"Строка {line_num}: неверный тип аутентификации (должен быть 'password' или 'key')")
                continue

            node_info = {
                "ip": ip,
                "port": port,
                "username": username,
                "auth_type": auth_type
            }

            # Обработка пароля или ключа
            if auth_type == 'password':
                if len(parts) > 3:
                    node_info["password"] = parts[3]
                else:
                    errors.append(f"Строка {line_num}: для типа 'password' требуется пароль")
                    continue
            else:  # key
                if len(parts) > 3:
                    node_info["key_path"] = parts[3]
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