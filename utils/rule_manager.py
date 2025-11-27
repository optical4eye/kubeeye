#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления правилами - предоставляет единый интерфейс для обработки правил для различных компонентов
Обновленная версия, поддерживает систему утверждений и отображение правил в виде таблицы
"""
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import pandas as pd
import yaml
from utils.rule_loader import load_rules, Rule


class RuleManager:
    """Класс управления правилами, предоставляющий единый интерфейс для операций с правилами"""

    @staticmethod
    def get_rule_type_display_names() -> Dict[str, str]:
        """Получить отображаемые имена типов правил"""
        return {
            'node': 'Правила проверки состояния узлов',
            'prometheus': 'Правила метрик Prometheus',
            'opa': 'Правила проверки соответствия OPA'
        }

    @staticmethod
    def get_enabled_rules(rule_type: str) -> List[Rule]:
        """Получить включённые правила указанного типа"""
        return [rule for rule in load_rules(rule_type) if rule.enabled]

    @staticmethod
    def get_rule_display_names(rules: List[Rule]) -> Dict[str, str]:
        """Получить отображаемые имена правил по их ID"""
        return {rule.id: rule.name for rule in rules}

    @staticmethod
    def get_rule_options(rules: List[Rule]) -> List[str]:
        """Получить список ID правил"""
        return [rule.id for rule in rules]

    @classmethod
    def get_rule_selection_data(cls, rule_type: str) -> Tuple[List[Rule], List[str], Dict[str, str]]:
        """Получить данные, необходимые для выбора правил"""
        rules = cls.get_enabled_rules(rule_type)
        options = cls.get_rule_options(rules)
        display_names = cls.get_rule_display_names(rules)
        return rules, options, display_names

    @classmethod
    def rule_to_dataframe(cls, rules: List[Rule]) -> pd.DataFrame:
        """Преобразовать список правил в DataFrame для отображения в таблице"""
        if not rules:
            return pd.DataFrame()

        data = []
        for rule in rules:
            data.append({
                "ID": rule.id,
                "Название": rule.name,
                "Категория": rule.category,
                "Серьезность": rule.severity,
                "Описание": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0
            })
        return pd.DataFrame(data)

    @classmethod
    def create_rule_selection(cls, rule_type: str, key_suffix: str = "") -> List[str]:
        """
        Упрощённый вариант: выбор правил через data_editor без дополнительной связки таблицы
        Обновление session_state на основе результатов редактирования data_editor
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type)
        if not rules:
            st.info(f"Не найдено включённых правил для {cls.get_rule_type_display_names()[rule_type]}. Пожалуйста, добавьте включённые правила в управлении правилами.")
            return []

        form_key = f"rule_selection_{rule_type}{key_suffix}"
        table_key = f"rule_table_{rule_type}{key_suffix}"

        # Инициализация session state, если ещё не инициализирован
        if form_key not in st.session_state:
            st.session_state[form_key] = options.copy()  # По умолчанию все выбраны

        data = []
        for rule in rules:
            selected = rule.id in st.session_state[form_key]
            data.append({
                "Выбор": selected,
                "ID": rule.id,
                "Название": rule.name,
                "Категория": rule.category,
                "Серьезность": rule.severity,
                "Описание": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Выбор": st.column_config.CheckboxColumn("Выбор", help="Выберите правила для выполнения", width="small"),
                "ID": st.column_config.TextColumn("ID правила", width="medium"),
                "Название": st.column_config.TextColumn("Название правила", width="medium"),
                "Категория": st.column_config.TextColumn("Категория", width="small"),
                "Серьезность": st.column_config.TextColumn("Серьезность", width="small"),
                "Описание": st.column_config.TextColumn("Описание", width="large"),
                "Количество утверждений": st.column_config.NumberColumn("Количество утверждений", width="small"),
            },
            disabled=["ID", "Название", "Категория", "Серьезность", "Описание", "Количество утверждений"],
            key=table_key,
            on_change=None  # Не использовать on_change, чтобы избежать перезагрузки
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Выбор"]]

        # Обновить session_state без перезагрузки страницы
        st.session_state[form_key] = selected_rules

        st.caption(f"Выбрано: {len(selected_rules)}/{len(options)} правил")
        return selected_rules

    @classmethod
    def create_rule_selection_in_form(cls, rule_type: str, key_suffix: str = "") -> List[str]:
        """
        Выбор правил в форме через data_editor с оптимизацией для уменьшения количества обновлений
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type)
        if not rules:
            st.info(f"Не найдено включённых правил для {cls.get_rule_type_display_names()[rule_type]}. Пожалуйста, добавьте включённые правила в управлении правилами.")
            return []

        form_key = f"rule_selection_form_{rule_type}{key_suffix}"
        table_key = f"rule_table_form_{rule_type}{key_suffix}"

        if form_key not in st.session_state:
            st.session_state[form_key] = options.copy()  # По умолчанию все выбраны

        data = []
        for rule in rules:
            selected = rule.id in st.session_state[form_key]
            data.append({
                "Выбор": selected,
                "ID": rule.id,
                "Название": rule.name,
                "Категория": rule.category,
                "Серьезность": rule.severity,
                "Описание": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Выбор": st.column_config.CheckboxColumn("Выбор", help="Выберите правила для выполнения", width="small"),
                "ID": st.column_config.TextColumn("ID правила", width="medium"),
                "Название": st.column_config.TextColumn("Название правила", width="medium"),
                "Категория": st.column_config.TextColumn("Категория", width="small"),
                "Серьезность": st.column_config.TextColumn("Серьезность", width="small"),
                "Описание": st.column_config.TextColumn("Описание", width="large"),
                "Количество утверждений": st.column_config.NumberColumn("Количество утверждений", width="small"),
            },
            disabled=["ID", "Название", "Категория", "Серьезность", "Описание", "Количество утверждений"],
            key=table_key,
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Выбор"]]

        if st.session_state[form_key] != selected_rules:
            st.session_state[form_key] = selected_rules

        st.caption(f"Выбрано: {len(selected_rules)}/{len(options)} правил")
        return selected_rules

    @classmethod
    def create_rule_selection_tabs(
        cls, node_check: bool, prometheus_check: bool, opa_check: bool, key_suffix: str = "",
        in_form: bool = False
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Создание вкладок выбора правил, показывая только доступные типы правил,
        позволяя пользователю выбирать правила в каждой вкладке.

        Аргументы:
        node_check (bool): включена ли проверка узлов
        prometheus_check (bool): включена ли проверка Prometheus
        opa_check (bool): включена ли проверка OPA
        key_suffix (str): суффикс ключа для различения вызовов
        in_form (bool): используется ли внутри формы

        Возвращает:
        Кортеж выбранных правил для node, prometheus и opa
        """
        selected_node_rules = []
        selected_prometheus_rules = []
        selected_opa_rules = []

        rule_configs = [
            {
                "available": node_check,
                "type": "node",
                "tab_label": "Правила проверки узлов",
                "result_var": "selected_node_rules"
            },
            {
                "available": prometheus_check,
                "type": "prometheus",
                "tab_label": "Правила проверки Prometheus",
                "result_var": "selected_prometheus_rules"
            },
            {
                "available": opa_check,
                "type": "opa",
                "tab_label": "Правила проверки OPA",
                "result_var": "selected_opa_rules"
            }
        ]

        available_configs = [cfg for cfg in rule_configs if cfg["available"]]

        if not available_configs:
            st.warning("Нет доступных типов проверок, пожалуйста, проверьте конфигурацию кластера.")
            return selected_node_rules, selected_prometheus_rules, selected_opa_rules

        for cfg in available_configs:
            key_suffix_type = f"{key_suffix}_{cfg['type']}"
            selection_key = f"rule_selection_{cfg['type']}{key_suffix_type}"
            if selection_key not in st.session_state:
                cls.get_rule_selection_data(cfg["type"])

        tab_labels = [cfg["tab_label"] for cfg in available_configs]

        tab_key = f"rule_tabs{key_suffix}"

        if tab_key not in st.session_state or st.session_state[tab_key] >= len(tab_labels):
            st.session_state[tab_key] = 0

        rule_tabs = st.tabs(tab_labels)

        for i, cfg in enumerate(available_configs):
            with rule_tabs[i]:
                if in_form:
                    selected_rules = cls.create_rule_selection_in_form(
                        cfg["type"],
                        key_suffix=f"{key_suffix}_{cfg['type']}"
                    )
                else:
                    selected_rules = cls.create_rule_selection(
                        cfg["type"],
                        key_suffix=f"{key_suffix}_{cfg['type']}"
                    )

                if cfg["result_var"] == "selected_node_rules":
                    selected_node_rules = selected_rules
                elif cfg["result_var"] == "selected_prometheus_rules":
                    selected_prometheus_rules = selected_rules
                elif cfg["result_var"] == "selected_opa_rules":
                    selected_opa_rules = selected_rules

        return selected_node_rules, selected_prometheus_rules, selected_opa_rules