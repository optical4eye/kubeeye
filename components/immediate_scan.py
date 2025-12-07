#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Компонент мгновенной проверки — переработанная версия, с использованием единого движка проверки
"""
import streamlit as st
from utils.cluster_config import list_clusters
from components.ui import display_cluster_info, select_inspectors
from components.ui.inspection_engine import execute_inspection_unified
from utils.rule_manager import RuleManager
from utils.rule_loader import load_rules

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

            # Определить, использовать ли правила GitOps
            use_gitops = RuleManager.should_use_gitops()

            if use_gitops:
                st.success("Используются правила GitOps (все правила автоматически включены)")

                # Показать отладочную информацию о правилах - СВЕРНУТО по умолчанию
                with st.expander("Информация о правилах GitOps", expanded=False):
                    for rule_type in ["node", "prometheus", "opa"]:
                        rules = load_rules(rule_type, use_gitops=True)
                        enabled_rules = [r for r in rules if r.enabled]
                        st.write(f"**{rule_type} правила:** {len(enabled_rules)} включенных из {len(rules)} всего")

                        if enabled_rules:
                            st.write("Доступные правила:")
                            for rule in enabled_rules:
                                st.write(f"- {rule.name} (ID: {rule.id})")
                        else:
                            st.warning(f"Нет включенных правил для типа: {rule_type}")

                            # Показать все правила (включая отключенные) для отладки
                            all_rules = load_rules(rule_type, include_disabled=True, use_gitops=True)
                            if all_rules:
                                st.write("Все правила (включая отключенные):")
                                for rule in all_rules:
                                    status = "включено" if rule.enabled else "отключено"
                                    st.write(f"- {rule.id}: {rule.name} ({status}: {rule.enabled})")
                            else:
                                st.error(f"Не найдено ни одного файла правил для типа {rule_type} в GitOps")

                                # Показать структуру директорий для отладки
                                from pathlib import Path
                                git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
                                if git_rules_dir.exists():
                                    st.write("Содержимое директории GitOps:")
                                    for item in git_rules_dir.rglob("*"):
                                        if item.is_file():
                                            st.write(f"- Файл: {item.relative_to(git_rules_dir)}")
                                        elif item.is_dir():
                                            st.write(f"- Директория: {item.relative_to(git_rules_dir)}/")

            # Использование нового RuleManager для создания области выбора правил
            selected_node_rules, selected_prometheus_rules, selected_opa_rules = RuleManager.create_rule_selection_tabs(
                run_node_check, run_prometheus_check, run_opa_check, key_suffix="_run", use_gitops=use_gitops
            )

            # Показать предупреждение, если нет выбранных правил
            total_selected = len(selected_node_rules) + len(selected_prometheus_rules) + len(selected_opa_rules)
            if total_selected == 0:
                st.warning("Не выбрано ни одного правила для проверки. Пожалуйста, выберите хотя бы одно правило.")

            # Кнопка запуска проверки
            run_inspection = st.button("Начать проверку", type="primary", disabled=total_selected==0)

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
                    show_ui_feedback=True,
                    use_gitops=use_gitops  # Передаем информацию об источнике правил
                )

                if not success:
                    st.error(f"Ошибка проверки: {message}")
