#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент мгновенной проверки — переработанная версия, с использованием единого движка проверки
"""
import streamlit as st
from utils.cluster_config import list_clusters
from components.ui import display_cluster_info, select_inspectors
from components.ui.inspection_engine import execute_inspection_unified

def render_immediate_scan_tab():
    """Отобразить вкладку мгновенной проверки — с использованием единого движка"""
    # Загрузка списка кластеров
    clusters = list_clusters()

    if not clusters:
        st.warning("Пока не настроены никакие кластеры. Перейдите на страницу «Информация о кластере» для добавления.")
        if st.button("Перейти к странице информации о кластере", key="goto_cluster_info_btn1"):
            st.switch_page("pages/1_cluster_info.py")
    else:
        # Выбор кластера
        selected_cluster = st.selectbox("Выберите кластер для проверки", clusters)

        if selected_cluster:
            # Отобразить информацию о кластере и получить его настройки
            cluster_config, nodes, prometheus_config = display_cluster_info(selected_cluster)
            if not cluster_config:
                return

            # Получить kubeconfig
            kubeconfig = cluster_config.get_kubeconfig()

            # Определение доступных типов проверки
            run_node_check, run_prometheus_check, run_opa_check = select_inspectors(nodes, prometheus_config, kubeconfig)

            # Использование нового RuleManager для создания области выбора правил
            from utils.rule_manager import RuleManager
            selected_node_rules, selected_prometheus_rules, selected_opa_rules = RuleManager.create_rule_selection_tabs(
                run_node_check, run_prometheus_check, run_opa_check, key_suffix="_run"
            )

            # Кнопка запуска проверки
            run_inspection = st.button("Начать проверку", type="primary")

            if run_inspection:
                # Формируем словарь выбранных правил
                selected_rules = {}
                if run_node_check and selected_node_rules:
                    selected_rules["node"] = selected_node_rules
                if run_prometheus_check and selected_prometheus_rules:
                    selected_rules["prometheus"] = selected_prometheus_rules
                if run_opa_check and selected_opa_rules:
                    selected_rules["opa"] = selected_opa_rules

                # Выполнение проверки с помощью единого движка
                success, message, results = execute_inspection_unified(
                    cluster_name=selected_cluster,
                    selected_rules=selected_rules,
                    inspection_type="immediate",
                    show_progress=True,
                    show_ui_feedback=True
                )

                if not success:
                    st.error(f"Ошибка проверки: {message}")
