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
from utils.node_connection import test_node_connection, validate_ssh_key
from utils.prometheus_client import PrometheusClient
from utils.k8s_client import K8sClient
from utils.node_parser import parse_nodes_from_text, generate_nodes_template


# Инициализация страницы
initialize_page(
    title="Инфо о кластере",
    icon="🔗",
    page_title="Управление информацией о кластере",
    page_subtitle="Управляйте и настраивайте подключения к вашим кластерам Kubernetes"
)


# Инициализация состояния сессии для управления списком узлов
if 'temp_nodes' not in st.session_state:
    st.session_state.temp_nodes = []


# Инициализация состояния для скрытия паролей
if 'show_passwords' not in st.session_state:
    st.session_state.show_passwords = {}


# Функция для проверки и валидации ключей
def validate_key_files(nodes):
    """
    Проверяет SSH ключи для списка узлов

    Args:
        nodes: список узлов

    Returns:
        список валидных узлов, список ошибок
    """
    valid_nodes = []
    key_errors = []

    for node_info in nodes:
        if node_info['auth_type'] == 'key':
            key_valid, key_message = validate_ssh_key(node_info['key_path'])
            if not key_valid:
                key_errors.append(f"Узел {node_info['ip']}: {key_message}")
                continue
        valid_nodes.append(node_info)

    return valid_nodes, key_errors


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
        # Основная информация о кластере
        st.subheader("💾 Основная информация")
        cluster_name = st.text_input("Название кластера", placeholder="production")

        # Добавление узлов
        st.subheader("📋 Узлы кластера")
        bulk_nodes_input = st.text_area(
            "Список узлов",
            placeholder="""Добавьте SSH узлы для проверки в формате: IP:Порт Пользователь ТипАутентификации [Пароль/ПутьКключу]
Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123""",
            height=200,
            help="Каждая строка должна содержать: IP:Порт Пользователь ТипАутентификации [Пароль/ПутьКключу]"
        )

        # Кнопка предварительной проверки узлов
        check_nodes = st.form_submit_button("🔍 Проверить узлы")

        if check_nodes:
            if bulk_nodes_input:
                nodes, errors = parse_nodes_from_text(bulk_nodes_input)

                if errors:
                    for error in errors:
                        st.error(error)

                # Проверка ключей перед тестированием соединения
                valid_nodes, key_errors = validate_key_files(nodes)

                if key_errors:
                    st.warning("Обнаружены проблемы с SSH ключами:")
                    for error in key_errors:
                        st.error(error)

                    st.info("""
                    **Рекомендации по исправлению:**
                    - Убедитесь, что путь к ключу корректен
                    - Проверьте формат ключа: `ssh-keygen -l -f /путь/к/ключу`
                    - При необходимости конвертируйте ключ: `ssh-keygen -p -m PEM -f /путь/к/ключу -N ""`
                    """)

                checked_count = 0
                success_count = 0

                for node_info in valid_nodes:
                    checked_count += 1
                    # Проверка соединения
                    with st.spinner(f"Проверка соединения с {node_info['ip']}..."):
                        success, message = test_node_connection(node_info)

                    if success:
                        st.success(f"✅ Узел {node_info['ip']} доступен")
                        success_count += 1
                    else:
                        st.error(f"❌ Ошибка соединения с {node_info['ip']}: {message}")

                st.info(f"Проверка завершена: {success_count}/{checked_count} узлов доступно")

                if key_errors:
                    st.warning(f"⚠️ {len(key_errors)} узлов не проверены из-за проблем с ключами")
            else:
                st.warning("Введите данные узлов для проверки")

        # Конфигурация Prometheus (свернута по умолчанию)
        with st.expander("📊 Конфигурация Prometheus", expanded=False):
            st.caption("Настройте Prometheus для мониторинга")

            prometheus_enabled = st.checkbox("Включить Prometheus")

            col1, col2 = st.columns(2)
            with col1:
                prometheus_url = st.text_input("URL Prometheus", placeholder="http://prometheus.example.com:9090")
                prometheus_username = st.text_input("Имя пользователя (необязательно)")

            with col2:
                prometheus_password = st.text_input("Пароль (необязательно)", type="password")
                prometheus_token = st.text_input("Токен (необязательно)", type="password")

        # Kubeconfig
        st.subheader("⚙️ Kubeconfig")

        # Инициализация состояния для kubeconfig
        if 'kubeconfig_content' not in st.session_state:
            st.session_state.kubeconfig_content = ""

        # Поле для ручного ввода/редактирования kubeconfig
        kubeconfig_content = st.text_area(
            "Содержимое kubeconfig",
            value=st.session_state.kubeconfig_content,
            height=150,
            placeholder="Вставьте содержимое kubeconfig здесь...",
            help="Вставьте содержимое kubeconfig файла вручную"
        )

        # Обновление состояния при ручном редактировании
        if kubeconfig_content != st.session_state.kubeconfig_content:
            st.session_state.kubeconfig_content = kubeconfig_content

        # Постоянная кнопка проверки подключения к Kubernetes
        test_k8s = st.form_submit_button("🔍 Проверить подключение к Kubernetes")
        if test_k8s:
            if not st.session_state.kubeconfig_content:
                st.error("❌ Введите содержимое kubeconfig для проверки подключения")
            else:
                with st.spinner("Проверка подключения к Kubernetes..."):
                    k8s_client = K8sClient(st.session_state.kubeconfig_content)
                    success, message = k8s_client.test_connection()

                if success:
                    st.success("✅ Подключение к Kubernetes успешно")
                else:
                    st.error(f"❌ Ошибка подключения к Kubernetes: {message}")

        # Кнопка сохранения кластера
        submitted = st.form_submit_button("💾 Сохранить кластер")

        if submitted:
            if not cluster_name:
                st.error("Введите название кластера")
            elif not bulk_nodes_input:
                st.error("Добавьте хотя бы один узел")
            else:
                # Парсинг и проверка узлов
                nodes, errors = parse_nodes_from_text(bulk_nodes_input)

                if errors:
                    for error in errors:
                        st.error(error)
                    st.error("Исправьте ошибки в формате узлов перед сохранением")
                elif not nodes:
                    st.error("Не удалось распознать ни одного узла")
                else:
                    # Проверка ключей перед тестированием соединения
                    valid_nodes_for_check, key_errors = validate_key_files(nodes)

                    if key_errors:
                        st.warning("Обнаружены проблемы с SSH ключами:")
                        for error in key_errors:
                            st.error(error)

                    # Проверка соединения для всех узлов
                    valid_nodes = []
                    failed_nodes = []

                    for node_info in valid_nodes_for_check:
                        with st.spinner(f"Проверка соединения с {node_info['ip']}..."):
                            success, message = test_node_connection(node_info)

                        if success:
                            valid_nodes.append(node_info)
                        else:
                            failed_nodes.append((node_info['ip'], message))

                    # Проверка подключения к Kubernetes (если предоставлен kubeconfig)
                    k8s_connection_ok = True
                    k8s_error_message = ""

                    if st.session_state.kubeconfig_content:
                        with st.spinner("Проверка подключения к Kubernetes..."):
                            k8s_client = K8sClient(st.session_state.kubeconfig_content)
                            k8s_success, k8s_message = k8s_client.test_connection()

                        if not k8s_success:
                            k8s_connection_ok = False
                            k8s_error_message = k8s_message

                    # Проверка подключения к Prometheus (если включен)
                    prometheus_connection_ok = True
                    prometheus_error_message = ""

                    if prometheus_enabled and prometheus_url:
                        with st.spinner("Проверка подключения к Prometheus..."):
                            prometheus_config = {
                                "url": prometheus_url,
                                "username": prometheus_username,
                                "password": prometheus_password,
                                "token": prometheus_token,
                                "enabled": True
                            }
                            prometheus_client = PrometheusClient(prometheus_config)
                            prometheus_result = prometheus_client.test_connection()

                        if prometheus_result.get('status') != 'success':
                            prometheus_connection_ok = False
                            prometheus_error_message = prometheus_result.get('error', 'Неизвестная ошибка')

                    # Показать результаты проверок
                    st.subheader("🔍 Результаты проверок:")

                    # Узлы
                    if failed_nodes:
                        st.error(f"❌ Недоступные узлы ({len(failed_nodes)}):")
                        for ip, message in failed_nodes:
                            st.error(f"  - {ip}: {message}")
                    else:
                        st.success(f"✅ Все узлы доступны ({len(valid_nodes)})")

                    # Проблемы с ключами
                    if key_errors:
                        st.error(f"❌ Проблемы с ключами ({len(key_errors)}):")
                        for error in key_errors:
                            st.error(f"  - {error}")

                    # Kubernetes
                    if st.session_state.kubeconfig_content:
                        if k8s_connection_ok:
                            st.success("✅ Подключение к Kubernetes успешно")
                        else:
                            st.error(f"❌ Ошибка подключения к Kubernetes: {k8s_error_message}")
                    else:
                        st.info("ℹ️ Kubeconfig не предоставлен")

                    # Prometheus
                    if prometheus_enabled:
                        if prometheus_connection_ok:
                            st.success("✅ Подключение к Prometheus успешно")
                        else:
                            st.error(f"❌ Ошибка подключения к Prometheus: {prometheus_error_message}")
                    else:
                        st.info("ℹ️ Prometheus отключен")

                    # Решение о сохранении
                    if not valid_nodes:
                        st.error("❌ Нет доступных узлов. Исправьте конфигурацию узлов и попробуйте снова.")
                    else:
                        # Спросить подтверждение, если есть проблемы
                        should_save = True
                        warning_message = ""

                        if failed_nodes:
                            warning_message += f"Только {len(valid_nodes)} из {len(nodes)} узлов доступны. "

                        if key_errors:
                            warning_message += f"{len(key_errors)} узлов имеют проблемы с ключами. "

                        if st.session_state.kubeconfig_content and not k8s_connection_ok:
                            warning_message += "Kubernetes недоступен. "

                        if prometheus_enabled and not prometheus_connection_ok:
                            warning_message += "Prometheus недоступен. "

                        if warning_message:
                            st.warning(f"⚠️ {warning_message}Вы уверены, что хотите сохранить кластер?")
                            # В реальном приложении здесь можно добавить подтверждение
                            # Для простоты продолжаем сохранение, но предупреждаем пользователя

                        # Создание нового кластера
                        cluster_config = get_cluster(cluster_name)

                        # Добавление доступных узлов
                        for node_info in valid_nodes:
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
                        if st.session_state.kubeconfig_content:
                            cluster_config.update_kubeconfig(st.session_state.kubeconfig_content)

                        st.success(f"✅ Кластер {cluster_name} успешно добавлен")

                        # Очистка kubeconfig после успешного сохранения
                        st.session_state.kubeconfig_content = ""

                        # Показать сводку
                        st.info(f"""
                        **Сводка конфигурации:**
                        - Узлы: {len(valid_nodes)} доступно ({len(failed_nodes)} недоступно, {len(key_errors)} с ошибками ключей)
                        - Kubernetes: {'✅ Доступен' if k8s_connection_ok else '❌ Недоступен'}
                        - Prometheus: {'✅ Доступен' if prometheus_connection_ok else ('❌ Недоступен' if prometheus_enabled else '⚪ Отключен')}
                        """)


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
                    st.subheader("Текущие узлы кластера:")

                    # Создаем DataFrame для отображения с чекбоксами
                    node_data = []
                    for node in nodes:
                        node_info = {
                            "Выбрать для удаления": False,
                            "IP адрес": node['ip'],
                            "Порт": node['port'],
                            "Пользователь": node['username'],
                            "Тип аутентификации": node['auth_type'],
                            "Пароль/Ключ": node['password'] if node['auth_type'] == 'password' else node.get('key_path', node.get('password', ''))
                        }
                        node_data.append(node_info)

                    # Создаем интерактивную таблицу с чекбоксами
                    df = pd.DataFrame(node_data)

                    # Отображаем таблицу с возможностью выбора строк
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Выбрать для удаления": st.column_config.CheckboxColumn(
                                "Выбрать",
                                help="Выберите узлы для удаления",
                                default=False,
                            )
                        },
                        disabled=["IP адрес", "Порт", "Пользователь", "Тип аутентификации", "Пароль/Ключ"],
                        hide_index=True,
                        use_container_width=True
                    )

                    # Обработка выбранных узлов для удаления
                    nodes_to_delete = []
                    for idx, row in edited_df.iterrows():
                        if row['Выбрать для удаления']:
                            nodes_to_delete.append(row['IP адрес'])

                    # Кнопка для удаления выбранных узлов
                    if nodes_to_delete:
                        st.warning(f"Выбрано для удаления: {', '.join(nodes_to_delete)}")

                        if st.button("🗑️ Удалить выбранные узлы", type="secondary"):
                            for node_ip in nodes_to_delete:
                                cluster_config.remove_node(node_ip)
                            st.success(f"Удалено {len(nodes_to_delete)} узлов")
                            st.rerun()
                    else:
                        st.info("Выберите узлы для удаления, установив флажки в столбце 'Выбрать для удаления'")

                    # Массовые действия с узлами
                    st.write("**Массовые действия с узлами:**")

                    if st.button("🔄 Проверить все узлы", key="check_all_nodes"):
                        success_count = 0
                        for node in nodes:
                            # Сначала проверяем ключи для узлов с аутентификацией по ключу
                            if node['auth_type'] == 'key':
                                key_path = node.get('key_path', node.get('password', ''))
                                key_valid, key_message = validate_ssh_key(key_path)
                                if not key_valid:
                                    st.error(f"❌ Ошибка ключа для {node['ip']}: {key_message}")
                                    continue

                            with st.spinner(f"Проверка узла {node['ip']}..."):
                                success, message = test_node_connection(node)
                            if success:
                                st.success(f"✅ Узел {node['ip']} доступен")
                                success_count += 1
                            else:
                                st.error(f"❌ Узел {node['ip']}: {message}")

                        st.info(f"Проверка завершена: {success_count}/{len(nodes)} узлов доступно")

                else:
                    st.info("В этом кластере нет узлов.")

                # Раздел для добавления новых узлов
                st.subheader("Добавить новые узлы")

                with st.form("add_nodes_form"):
                    new_nodes_input = st.text_area(
                        "Новые узлы для добавления",
                        placeholder="""Добавьте SSH узлы в формате: IP:Порт Пользователь ТипАутентификации [Пароль/ПутьКключу]
Примеры:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123""",
                        height=150,
                        help="Каждая строка должна содержать: IP:Порт Пользователь ТипАутентификации [Пароль/ПутьКключу]"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        test_new_nodes = st.form_submit_button("🔍 Проверить новые узлы")

                    with col2:
                        add_new_nodes = st.form_submit_button("➕ Добавить новые узлы")

                    if test_new_nodes:
                        if new_nodes_input:
                            new_nodes, errors = parse_nodes_from_text(new_nodes_input)

                            if errors:
                                for error in errors:
                                    st.error(error)

                            # Проверка ключей перед тестированием соединения
                            valid_nodes, key_errors = validate_key_files(new_nodes)

                            if key_errors:
                                st.warning("Обнаружены проблемы с SSH ключами:")
                                for error in key_errors:
                                    st.error(error)

                            checked_count = 0
                            success_count = 0

                            for node_info in valid_nodes:
                                checked_count += 1
                                with st.spinner(f"Проверка соединения с {node_info['ip']}..."):
                                    success, message = test_node_connection(node_info)

                                if success:
                                    st.success(f"✅ Узел {node_info['ip']} доступен")
                                    success_count += 1
                                else:
                                    st.error(f"❌ Ошибка соединения с {node_info['ip']}: {message}")

                            st.info(f"Проверка завершена: {success_count}/{checked_count} узлов доступно")

                            if key_errors:
                                st.warning(f"⚠️ {len(key_errors)} узлов не проверены из-за проблем с ключами")
                        else:
                            st.warning("Введите данные узлов для проверки")

                    if add_new_nodes:
                        if new_nodes_input:
                            new_nodes, errors = parse_nodes_from_text(new_nodes_input)

                            if errors:
                                for error in errors:
                                    st.error(error)
                                st.error("Исправьте ошибки в формате узлов перед добавлением")
                            elif not new_nodes:
                                st.error("Не удалось распознать ни одного узла")
                            else:
                                # Проверка ключей перед добавлением
                                valid_nodes, key_errors = validate_key_files(new_nodes)

                                if key_errors:
                                    st.warning("Обнаружены проблемы с SSH ключами:")
                                    for error in key_errors:
                                        st.error(error)

                                # Проверка соединения и добавление только доступных узлов
                                added_count = 0
                                failed_count = 0

                                for node_info in valid_nodes:
                                    with st.spinner(f"Проверка и добавление узла {node_info['ip']}..."):
                                        success, message = test_node_connection(node_info)

                                    if success:
                                        # Проверяем, не существует ли уже узел с таким IP
                                        existing_nodes = cluster_config.get_nodes()
                                        node_exists = any(node['ip'] == node_info['ip'] for node in existing_nodes)

                                        if node_exists:
                                            st.warning(f"Узел {node_info['ip']} уже существует, обновляем конфигурацию")

                                        cluster_config.update_node(node_info)
                                        added_count += 1
                                        st.success(f"✅ Узел {node_info['ip']} добавлен")
                                    else:
                                        failed_count += 1
                                        st.error(f"❌ Не удалось добавить узел {node_info['ip']}: {message}")

                                st.success(f"Добавлено {added_count} новых узлов")
                                if failed_count > 0:
                                    st.error(f"Не удалось добавить {failed_count} узлов")

                                if key_errors:
                                    st.warning(f"⚠️ {len(key_errors)} узлов не добавлены из-за проблем с ключами")

                                st.rerun()
                        else:
                            st.error("Введите данные узлов для добавления")

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
                    save_prom_button = st.form_submit_button("Сохранить конфигурации")

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

                # Инициализация состояния для редактирования kubeconfig
                if 'edit_kubeconfig_content' not in st.session_state:
                    st.session_state.edit_kubeconfig_content = current_kubeconfig or ""

                with st.form("edit_kubeconfig_form"):
                    st.caption("Отредактируйте содержимое kubeconfig вручную")

                    # Поле для редактирования kubeconfig
                    edit_kubeconfig_content = st.text_area(
                        "Содержимое Kubeconfig",
                        value=st.session_state.edit_kubeconfig_content,
                        height=300,
                        placeholder="Вставьте содержимое kubeconfig здесь..."
                    )

                    # Обновление состояния при редактировании
                    if edit_kubeconfig_content != st.session_state.edit_kubeconfig_content:
                        st.session_state.edit_kubeconfig_content = edit_kubeconfig_content

                    # Постоянная кнопка проверки подключения к Kubernetes
                    test_kube_button = st.form_submit_button("🔍 Проверить подключение к Kubernetes")

                    # Кнопка сохранения конфигурации
                    save_kube_button = st.form_submit_button("Сохранить конфигурацию")

                    if test_kube_button:
                        if not st.session_state.edit_kubeconfig_content:
                            st.error("❌ Введите содержимое kubeconfig для проверки подключения")
                        else:
                            # Тест соединения
                            with st.spinner("Тест соединения..."):
                                client = K8sClient(st.session_state.edit_kubeconfig_content)
                                success, message = client.test_connection()

                            if success:
                                st.success("✅ Подключение к Kubernetes успешно")
                            else:
                                st.error(f"❌ Ошибка подключения: {message}")

                    if save_kube_button:
                        # Обновление конфигурации
                        cluster_config.update_kubeconfig(st.session_state.edit_kubeconfig_content)
                        st.success("Конфигурация kubeconfig обновлена")
