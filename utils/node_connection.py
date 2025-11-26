#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления подключениями к узлам, используется для подключения к узлам кластера через SSH и выполнения команд
"""


import paramiko
import socket
import logging
from typing import Dict, List, Tuple, Optional
import os
from pathlib import Path


class NodeConnection:
    """Класс SSH-подключения к узлу"""


    def __init__(self, node_info: Dict):
        """
        Инициализация подключения к узлу


        Args:
            node_info: словарь с информацией об узле, содержит:
                - ip: IP-адрес узла
                - port: SSH-порт
                - username: SSH имя пользователя
                - auth_type: тип аутентификации ('password' или 'key')
                - password: пароль (если auth_type равен 'password')
                - key_path: путь до ключа (если auth_type равен 'key')
        """
        self.node_info = node_info
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connected = False


    def __enter__(self):
        """Вход контекстного менеджера, подключение к узлу и возврат себя"""
        self.connect()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера, закрытие подключения"""
        self.close()
        return False  # Передать исключение дальше


    def connect(self) -> Tuple[bool, str]:
        """
        Подключение к узлу


        Returns:
            При успешном подключении возвращает (True, ""), при ошибке — (False, сообщение_об_ошибке)
        """
        try:
            # Логируем информацию о подключении
            logging.info(f"Подключение к узлу: {self.node_info['ip']}:{self.node_info['port']} пользователь: {self.node_info['username']}")


            # Гарантируем, что не будет запроса на ввод пароля интерактивно
            # look_for_keys=False предотвращает попытки Paramiko использовать SSH-агент или искать файлы ключей
            # allow_agent=False предотвращает использование SSH-агента
            if self.node_info['auth_type'] == 'password':
                self.client.connect(
                    hostname=self.node_info['ip'],
                    port=int(self.node_info['port']),
                    username=self.node_info['username'],
                    password=self.node_info['password'],
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
                )
            else:  # аутентификация по ключу
                key_path = self.node_info['key_path']
                if not os.path.isfile(key_path):
                    return False, f"Файл ключа {key_path} не существует"


                # Проверяем права доступа к файлу ключа
                self._check_key_permissions(key_path)


                # Пытаемся загрузить SSH ключ разными методами
                key = self._load_ssh_key(key_path)
                if not key:
                    return False, "Не удалось загрузить SSH ключ. Проверьте формат ключа."


                self.client.connect(
                    hostname=self.node_info['ip'],
                    port=int(self.node_info['port']),
                    username=self.node_info['username'],
                    pkey=key,
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
                )


            self.connected = True
            return True, ""
        except socket.timeout:
            error_msg = f"Превышено время ожидания подключения (порт {self.node_info['port']})"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except socket.gaierror as e:
            error_msg = f"Ошибка DNS разрешения: {str(e)}"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except ConnectionRefusedError:
            error_msg = f"Подключение отклонено (возможно SSH-сервис на порту {self.node_info['port']} не открыт)"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except paramiko.AuthenticationException:
            error_msg = "Ошибка аутентификации (неверное имя пользователя, пароль или SSH ключ)"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except paramiko.SSHException as e:
            # Обработка ошибки "[Errno None] Unable to connect to port"
            error_str = str(e)
            if "Unable to connect to port" in error_str:
                error_msg = f"Невозможно подключиться к порту {self.node_info['port']} (возможно хост недоступен или соединение блокирует фаервол)"
            else:
                error_msg = f"SSH ошибка: {error_str}"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Ошибка подключения: {str(e)}"
            logging.error(f"Узел {self.node_info['ip']}: {error_msg}")
            return False, error_msg


    def _check_key_permissions(self, key_path: str) -> None:
        """Проверка прав доступа к файлу ключа"""
        try:
            stat_info = os.stat(key_path)
            permissions = stat_info.st_mode & 0o777
            if permissions != 0o600:
                logging.warning(f"Права доступа к файлу ключа {oct(permissions)} небезопасны, рекомендуется 600")
                # Только предупреждение, выполнение не блокируется
        except Exception as e:
            logging.warning(f"Не удалось проверить права доступа к файлу ключа: {str(e)}")


    def _load_ssh_key(self, key_path: str) -> Optional[paramiko.PKey]:
        """
        Пытается загрузить SSH ключ разными способами


        Args:
            key_path: путь к файлу ключа


        Returns:
            Загруженный объект ключа или None
        """
        # Сначала пытаемся автообнаружение
        try:
            key = paramiko.PKey.from_private_key_file(key_path)
            logging.info("SSH ключ автоматически обнаружен")
            return key
        except Exception as e:
            logging.info(f"Автовыявление ключа не удалось: {str(e)}")


        # Пытаемся загрузить ключи определенных типов
        key_methods = [
            ("RSA", paramiko.RSAKey.from_private_key_file),
            ("ECDSA", paramiko.ECDSAKey.from_private_key_file),
            ("Ed25519", paramiko.Ed25519Key.from_private_key_file),
        ]


        for key_type, key_loader in key_methods:
            try:
                key = key_loader(key_path)
                logging.info(f"Успешно загружен ключ типа {key_type}")
                return key
            except paramiko.SSHException as e:
                logging.info(f"Ключ {key_type} не подходит: {str(e)}")
                continue
            except Exception as e:
                logging.warning(f"Ошибка при загрузке ключа {key_type}: {str(e)}")
                continue


        # В конце пытаемся загрузить RSA ключ без пароля (для зашифрованных ключей)
        try:
            key = paramiko.RSAKey.from_private_key_file(key_path, password=None)
            logging.info("Успешно загружен RSA ключ (без пароля)")
            return key
        except:
            pass


        logging.error("Все способы загрузки ключа завершились неудачей")
        return None


    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Выполнение команды на узле


        Args:
            command: команда для выполнения


        Returns:
            Кортеж (успех, stdout, stderr)
        """
        if not self.connected:
            success, message = self.connect()
            if not success:
                return False, "", message


        try:
            # Выполняем команду и ожидаем завершения
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)


            # Закрываем стандартный ввод
            stdin.close()


            # Читаем стандартный вывод и стандартный поток ошибок
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')


            # Ожидаем завершения команды и получаем код возврата
            exit_status = stdout.channel.recv_exit_status()


            # Закрываем все каналы
            stdout.close()
            stderr.close()


            success = exit_status == 0
            return success, stdout_data, stderr_data
        except Exception as e:
            return False, "", str(e)


    def close(self) -> None:
        """Закрыть подключение"""
        if self.connected:
            self.client.close()
            self.connected = False



def test_node_connection(node_info: Dict) -> Tuple[bool, str]:
    """
    Тест подключения к узлу


    Args:
        node_info: конфигурационная информация узла


    Returns:
        Кортеж (успех, сообщение)
    """
    conn = NodeConnection(node_info)
    success, message = conn.connect()
    if success:
        conn.close()
    return success, message



def validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """
    Проверка файла SSH ключа


    Args:
        key_path: путь к файлу ключа


    Returns:
        Кортеж (успех, сообщение)
    """
    if not os.path.isfile(key_path):
        return False, f"Файл ключа {key_path} не существует"


    try:
        # Создаем временный объект подключения для теста загрузки ключа
        temp_node_info = {
            'ip': '127.0.0.1',  # фиктивный IP, только для проверки ключа
            'port': 22,
            'username': 'test',
            'auth_type': 'key',
            'key_path': key_path
        }


        conn = NodeConnection(temp_node_info)
        key = conn._load_ssh_key(key_path)
        if key:
            return True, "Формат SSH ключа корректен"
        else:
            return False, "Не удалось загрузить SSH ключ. Проверьте формат ключа."


    except Exception as e:
        return False, f"Ошибка проверки ключа: {str(e)}"
