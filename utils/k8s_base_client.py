#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый клиент Kubernetes - предоставление общей логики инициализации и конфигурации
Уменьшение дублирования кода между k8s_client.py и k8s_dynamic_client.py
"""

import tempfile
import os
import logging
from typing import Optional, Tuple
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

class K8sBaseClient:
    """Базовый клиент Kubernetes, предоставляющий общую функциональность инициализации и конфигурации"""

    def __init__(self, kubeconfig_content: str = None):
        """
        Инициализировать базовый клиент

        Args:
            kubeconfig_content: Содержимое файла kubeconfig
        """
        self.kubeconfig_content = kubeconfig_content
        self.temp_config = None
        self.initialized = False

    def init_client_base(self) -> bool:
        """
        Общая логика инициализации клиента

        Returns:
            Возвращает True при успехе, False при неудаче
        """
        try:
            if self.kubeconfig_content:
                # Создать временный файл для хранения kubeconfig
                self.temp_config = tempfile.NamedTemporaryFile(delete=False)
                self.temp_config.write(self.kubeconfig_content.encode())
                self.temp_config.flush()
                config.load_kube_config(self.temp_config.name)
            else:
                # Попробовать загрузить конфигурацию способом по умолчанию
                config.load_kube_config()

            # Настроить проверку SSL сертификатов
            client.Configuration.set_default(self._configure_no_verify_ssl())

            self.initialized = True
            logger.info("Инициализация базового клиента Kubernetes прошла успешно")
            return True

        except Exception as e:
            logger.error(f"Не удалось инициализировать базовый клиент Kubernetes: {e}")
            self.initialized = False
            return False

    def _configure_no_verify_ssl(self):
        """
        Настроить клиент Kubernetes для пропуска проверки SSL сертификатов, для среды с самоподписанными сертификатами

        Returns:
            Настроенная конфигурация клиента
        """
        # Получить текущую конфигурацию клиента
        configuration = client.Configuration.get_default_copy()

        # Отключить проверку SSL сертификатов
        configuration.verify_ssl = False
        configuration.ssl_ca_cert = None

        # Установить предупреждение
        logger.warning("Проверка SSL сертификатов отключена, это может представлять угрозу безопасности")

        return configuration

    def test_connection(self) -> Tuple[bool, str]:
        """
        Тестировать подключение к кластеру Kubernetes

        Returns:
            (Успешно ли, Сообщение)
        """
        try:
            if not self.initialized:
                return False, "Клиент не инициализирован"

            # Попробовать получить информацию о версии кластера
            version_api = client.VersionApi()
            version = version_api.get_code().git_version
            return True, f"Подключение успешно, версия кластера: {version}"

        except ApiException as e:
            logger.error(f"Тест подключения не удался: {e}")
            return False, f"Ошибка API: {e.reason}"
        except Exception as e:
            logger.error(f"Тест подключения не удался: {e}")
            return False, f"Подключение не удалось: {str(e)}"

    def __del__(self):
        """Деструктор, удалить временные файлы"""
        if self.temp_config:
            try:
                self.temp_config.close()
                os.unlink(self.temp_config.name)
            except:
                pass
