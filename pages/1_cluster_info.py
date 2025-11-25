#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Страница управления информацией о кластере Kubernetes
"""


# Импорт необходимых библиотек
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import json


# Настройка страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Инфо о кластере - kubeeye",
    page_icon="🔗",
    layout="wide"
)


# Добавление корневой директории проекта в путь Python
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Импорт модулей приложения
from utils.common import initialize_page
from utils.cluster_config import list_clusters, get_cluster, delete_cluster
from utils.node_connection import test_node_connection
from utils.prometheus_client import PrometheusClient
from utils.k8s_client import K8sClient


# Инициализация страницы
initialize_page(
    title="Инфо о кластере",
    icon="🔗",
    page_title="Управление информацией о кластере",
    page_subtitle="Управляйте и настраивайте подключения к вашим кластерам Kubernetes"
)


# Вкладки
tab1, tab2, tab3 = st.tabs(["Список кластеров", "Добавить кластер", "Редактировать кластер"])


# Вкладка списка кластеров
with tab1:
    st.header("Настроенные кластеры")

    # Кнопка обновления списка
    if st.button("Обновить список"):
        st.rerun()

    # Загрузка списка кластеров
    clusters = list_clusters()

    if clusters:
        for cluster_name in clusters:
            with st.expander(f"Кластер: {cluster_name}", expanded=False):
                cluster_config = get_cluster(cluster_name)

                # Отображение информации об узлах
                st.subheader("Информация об узлах")
                nodes = cluster_config.get_nodes()

                if nodes:
                    node_data = []
                    for node in nodes:
                        node_data.append({
                            "IP": node['ip'],
                            "Порт": node['port'],
                            "Имя пользователя": node['username'],
                            "Тип аутентификации": node['auth_type']
                        })
                    st.dataframe(pd.DataFrame(node_data))
                else:
                    st.info("Узлы не настроены")

                # Отображение конфигурации Prometheus
                st.subheader("Конфигурация Prometheus")
                prometheus_config = cluster_config.get_prometheus_config()
                st.json(prometheus_config)

                # Отображение kubeconfig
                st.subheader("Kubeconfig")
                kubeconfig = cluster_config.get_kubeconfig()
                if kubeconfig:
                    st.code(kubeconfig, language="yaml")
                else:
                    st.info("kubeconfig не настроен")

                # Кнопка удаления кластера
                if st.button("Удалить кластер", key=f"delete_{cluster_name}"):
                    delete_cluster(cluster_name)
                    st.success(f"Кластер {cluster_name} удалён")
                    st.rerun()
    else:
        st.info("Кластеры ещё не настроены, перейдите на вкладку «Добавить кластер» для создания.")


# Вкладка добавления кластера
with tab2:
    st.header("Добавить новый кластер")

    with st.form("add_cluster_form"):
        cluster_name = st.text_input("Название кластера", placeholder="production")
        st.caption("Введите уникальное имя для идентификации кластера")

        st.subheader("Информация об узлах")
        st.caption("Добавьте данные узлов для проверки")

        col1, col2 = st.columns(2)
        with col1:
            node_ip = st.text_input("IP узла", placeholder="192.168.1.100")
            node_port = st.text_input("SSH порт", "22")
            node_username = st.text_input("Имя пользователя", "root")

        with col2:
            auth_type = st.selectbox("Тип аутентификации", ["password", "key"])

            if auth_type == "password":
                node_password = st.text_input("Пароль", type="password")
                node_key_path = ""
            else:
                node_password = ""
                node_key_path = st.text_input("Путь к ключу", placeholder="/home/user/.ssh/id_rsa")

        st.subheader("Конфигурация Prometheus")
        st.caption("Настройте Prometheus для мониторинга")

        prometheus_enabled = st.checkbox("Включить Prometheus")

        col1, col2 = st.columns(2)
        with col1:
            prometheus_url = st.text_input("URL Prometheus", placeholder="http://prometheus.example.com:9090")
            prometheus_username = st.text_input("Имя пользователя (необязательно)")

        with col2:
            prometheus_password = st.text_input("Пароль (необязательно)", type="password")
            prometheus_token = st.text_input("Токен (необязательно)", type="password")

        st.subheader("Kubeconfig")
        st.caption("Вставьте содержимое kubeconfig для управления ресурсами")

        kubeconfig_content = st.text_area("Содержимое kubeconfig", height=150)

        submitted = st.form_submit_button("Сохранить кластер")

        if submitted:
            if not cluster_name:
                st.error("Введите название кластера")
            elif not node_ip:
                st.error("Введите IP хотя бы одного узла")
            else:
                # Создание нового кластера
                cluster_config = get_cluster(cluster_name)

                # Добавление данных узла
                node_info = {
                    "ip": node_ip,
                    "port": node_port,
                    "username": node_username,
                    "auth_type": auth_type
                }

                if auth_type == "password":
                    node_info["password"] = node_password
                else:
                    node_info["key_path"] = node_key_path

                # Проверка соединения с узлом
                with st.spinner("Проверка соединения с узлом..."):
                    success, message = test_node_connection(node_info)

                if not success:
                    st.error(f"Ошибка соединения с узлом: {message}")
                else:
                    # Обновление конфигурации узла
                    cluster_config.update_node(node_info)

                    # Обновление конфигурации Prometheus
                    prometheus_config = {
                        "url": prometheus_url,
                        "username": prometheus_username,
                        "password": prometheus_password,
                        "token": prometheus_token,
                        "enabled": prometheus_enabled
                    }
                    cluster_config.update_prometheus(prometheus_config)

                    # Обновление kubeconfig
                    if kubeconfig_content:
                        cluster_config.update_kubeconfig(kubeconfig_content)

                    st.success(f"Кластер {cluster_name} успешно добавлен")
                    st.info("Вы можете добавить дополнительные узлы во вкладке «Редактировать кластер»")


# Вкладка редактирования кластера
with tab3:
    st.header("Редактировать кластер")

    # Загрузка списка кластеров
    clusters = list_clusters()

    if not clusters:
        st.info("Кластеры ещё не настроены, перейдите на вкладку «Добавить кластер» для создания.")
    else:
        selected_cluster = st.selectbox("Выберите кластер для редактирования", clusters)

        if selected_cluster:
            cluster_config = get_cluster(selected_cluster)

            st.subheader(f"Редактировать кластер: {selected_cluster}")

            # Вкладки редактирования
            edit_tab1, edit_tab2, edit_tab3 = st.tabs(["Управление узлами", "Конфигурация Prometheus", "Kubeconfig"])

            # Вкладка управления узлами
            with edit_tab1:
                st.subheader("Управление узлами")

                # Отображение существующих узлов
                nodes = cluster_config.get_nodes()

                if nodes:
                    st.write("Существующие узлы:")

                    for i, node in enumerate(nodes):
                        with st.expander(f"Узел: {node['ip']}", expanded=False):
                            st.json(node)

                            if st.button("Удалить узел", key=f"delete_node_{i}"):
                                cluster_config.remove_node(node['ip'])
                                st.success(f"Узел {node['ip']} удалён")
                                st.rerun()

                # Добавление нового узла
                st.write("Добавить новый узел:")

                with st.form("add_node_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        node_ip = st.text_input("IP узла", placeholder="192.168.1.101", key="edit_node_ip")
                        node_port = st.text_input("SSH порт", "22", key="edit_node_port")
                        node_username = st.text_input("Имя пользователя", "root", key="edit_node_username")

                    with col2:
                        auth_type = st.selectbox("Тип аутентификации", ["password", "key"], key="edit_auth_type")

                        if auth_type == "password":
                            node_password = st.text_input("Пароль", type="password", key="edit_node_password")
                            node_key_path = ""
                        else:
                            node_password = ""
                            node_key_path = st.text_input("Путь к ключу", placeholder="/home/user/.ssh/id_rsa", key="edit_node_key")

                    submitted = st.form_submit_button("Добавить узел")

                    if submitted:
                        if not node_ip:
                            st.error("Введите IP узла")
                        else:
                            # Формирование информации об узле
                            node_info = {
                                "ip": node_ip,
                                "port": node_port,
                                "username": node_username,
                                "auth_type": auth_type
                            }

                            if auth_type == "password":
                                node_info["password"] = node_password
                            else:
                                node_info["key_path"] = node_key_path

                            # Проверка соединения
                            with st.spinner("Проверка соединения с узлом..."):
                                success, message = test_node_connection(node_info)

                            if not success:
                                st.error(f"Ошибка соединения с узлом: {message}")
                            else:
                                # Обновление конфигурации узла
                                cluster_config.update_node(node_info)
                                st.success(f"Узел {node_ip} добавлен")
                                st.rerun()

            # Вкладка настройки Prometheus
            with edit_tab2:
                st.subheader("Конфигурация Prometheus")

                # Получение текущей конфигурации
                prometheus_config = cluster_config.get_prometheus_config()

                with st.form("edit_prometheus_form"):
                    prometheus_enabled = st.checkbox("Включить Prometheus", value=prometheus_config.get('enabled', False))

                    col1, col2 = st.columns(2)
                    with col1:
                        prometheus_url = st.text_input("URL Prometheus", value=prometheus_config.get('url', ''))
                        prometheus_username = st.text_input("Имя пользователя", value=prometheus_config.get('username', ''))

                    with col2:
                        prometheus_password = st.text_input("Пароль", type="password", value=prometheus_config.get('password', ''))
                        prometheus_token = st.text_input("Токен", type="password", value=prometheus_config.get('token', ''))

                    # Кнопка теста соединения
                    test_prom_button = st.form_submit_button("Тест соединения")

                    # Кнопка сохранения конфигурации
                    save_prom_button = st.form_submit_button("Сохранить конфигурацию")

                    if test_prom_button:
                        if not prometheus_url:
                            st.error("Введите URL Prometheus")
                        else:
                            # Формирование временной конфигурации
                            test_config = {
                                "url": prometheus_url,
                                "username": prometheus_username,
                                "password": prometheus_password,
                                "token": prometheus_token,
                                "enabled": True
                            }

                            # Тест соединения
                            with st.spinner("Тест соединения..."):
                                client = PrometheusClient(test_config)
                                result = client.test_connection()

                            if result.get('status') == 'success':
                                st.success("Соединение успешно")
                            else:
                                st.error(f"Ошибка соединения: {result.get('error', 'Неизвестная ошибка')}")

                    if save_prom_button:
                        # Сохранение новой конфигурации
                        new_config = {
                            "url": prometheus_url,
                            "username": prometheus_username,
                            "password": prometheus_password,
                            "token": prometheus_token,
                            "enabled": prometheus_enabled
                        }

                        cluster_config.update_prometheus(new_config)
                        st.success("Конфигурация Prometheus обновлена")

            # Вкладка настройки Kubeconfig
            with edit_tab3:
                st.subheader("Конфигурация Kubeconfig")

                # Получение текущей конфигурации
                current_kubeconfig = cluster_config.get_kubeconfig()

                with st.form("edit_kubeconfig_form"):
                    kubeconfig_content = st.text_area("Содержимое Kubeconfig", value=current_kubeconfig, height=300)

                    # Кнопка теста соединения
                    test_kube_button = st.form_submit_button("Тест соединения")

                    # Кнопка сохранения конфигурации
                    save_kube_button = st.form_submit_button("Сохранить конфигурацию")

                    if test_kube_button:
                        if not kubeconfig_content:
                            st.error("Введите содержимое kubeconfig")
                        else:
                            # Тест соединения
                            with st.spinner("Тест соединения..."):
                                client = K8sClient(kubeconfig_content)
                                success, message = client.test_connection()

                            if success:
                                st.success("Соединение успешно")
                            else:
                                st.error(f"Ошибка соединения: {message}")

                    if save_kube_button:
                        # Обновление конфигурации
                        cluster_config.update_kubeconfig(kubeconfig_content)
                        st.success("Конфигурация kubeconfig обновлена")
