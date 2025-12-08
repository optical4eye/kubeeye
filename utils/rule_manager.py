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
    def get_enabled_rules(rule_type: str, use_gitops: bool = False) -> List[Rule]:
        """Получить включённые правила указанного типа"""
        all_rules = load_rules(rule_type, use_gitops=use_gitops)
        enabled_rules = [rule for rule in all_rules if rule.enabled]

        # Отладочная информация
        if use_gitops:
            print(f"GitOps правила для {rule_type}: найдено {len(all_rules)} всего, {len(enabled_rules)} включено")
            for rule in enabled_rules:
                print(f"  - {rule.id}: {rule.name} (включено: {rule.enabled})")

        return enabled_rules

    @staticmethod
    def get_rule_display_names(rules: List[Rule]) -> Dict[str, str]:
        """Получить отображаемые имена правил по их ID"""
        return {rule.id: rule.name for rule in rules}

    @staticmethod
    def get_rule_options(rules: List[Rule]) -> List[str]:
        """Получить список ID правил"""
        return [rule.id for rule in rules]

    @classmethod
    def get_rule_selection_data(cls, rule_type: str, use_gitops: bool = False) -> Tuple[List[Rule], List[str], Dict[str, str]]:
        """Получить данные, необходимые для выбора правил"""
        rules = cls.get_enabled_rules(rule_type, use_gitops)
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
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Источник": " Git" if rule.source == 'git' else " Локальный"
            })
        return pd.DataFrame(data)

    @classmethod
    def create_rule_selection(cls, rule_type: str, key_suffix: str = "", use_gitops: bool = False) -> List[str]:
        """
        Упрощённый вариант: выбор правил через data_editor без дополнительной связки таблицы
        Обновление session_state на основе результатов редактирования data_editor
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type, use_gitops)
        if not rules:
            source_type = "GitOps" if use_gitops else "локальных"
            st.info(f"Не найдено включённых правил для {cls.get_rule_type_display_names()[rule_type]} в {source_type} правилах.")

            # Показать дополнительную отладочную информацию
            all_rules = load_rules(rule_type, include_disabled=True, use_gitops=use_gitops)
            if all_rules:
                st.warning(f"Найдено {len(all_rules)} правил, но все они отключены или имеют проблемы с загрузкой")
                for rule in all_rules:
                    st.write(f"- {rule.id}: {rule.name} (включено: {rule.enabled})")

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
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Источник": " Git" if rule.source == 'git' else " Локальный"
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Выбор": st.column_config.CheckboxColumn("Выбор", help="Выберите правила для выполнения", width="small"),
                "ID": st.column_config.TextColumn("ID правила", width="medium"),
                "Название": st.column_config.TextColumn("Название правила", width="medium"),
                "Категория": st.column_config.TextColumn("Категория", width="small"),
                "Серьезность": st.column_config.TextColumn("Серьезность", width="small"),
                "Описание": st.column_config.TextColumn("Описание", width="large"),
                "Количество утверждений": st.column_config.NumberColumn("Количество утверждений", width="small"),
                "Источник": st.column_config.TextColumn("Источник", width="small"),
            },
            disabled=["ID", "Название", "Категория", "Серьезность", "Описание", "Количество утверждений", "Источник"],
            key=table_key,
            on_change=None
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Выбор"]]

        # Обновить session_state без перезагрузки страницы
        st.session_state[form_key] = selected_rules

        source_type = "GitOps" if use_gitops else "локальных"
        st.caption(f"Выбрано: {len(selected_rules)}/{len(options)} {source_type} правил")
        return selected_rules

    @classmethod
    def create_rule_selection_in_form(cls, rule_type: str, key_suffix: str = "", use_gitops: bool = False) -> List[str]:
        """
        Выбор правил в форме через data_editor с оптимизацией для уменьшения количества обновлений
        """
        rules, options, display_names = cls.get_rule_selection_data(rule_type, use_gitops)
        if not rules:
            source_type = "GitOps" if use_gitops else "локальных"
            st.info(f"Не найдено включённых правил для {cls.get_rule_type_display_names()[rule_type]} в {source_type} правилах.")
            return []

        form_key = f"rule_selection_form_{rule_type}{key_suffix}"
        table_key = f"rule_table_form_{rule_type}{key_suffix}"

        if form_key not in st.session_state:
            st.session_state[form_key] = options.copy()

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
                "Количество утверждений": len(rule.assertions) if hasattr(rule, 'assertions') else 0,
                "Источник": " Git" if rule.source == 'git' else " Локальный"
            })
        rules_df = pd.DataFrame(data)

        edited_df = st.data_editor(
            rules_df,
            width='stretch',
            hide_index=True,
            column_config={
                "Выбор": st.column_config.CheckboxColumn("Выбор", help="Выберите правила для выполнения", width="small"),
                "ID": st.column_config.TextColumn("ID правила", width="medium"),
                "Название": st.column_config.TextColumn("Название правила", width="medium"),
                "Категория": st.column_config.TextColumn("Категория", width="small"),
                "Серьезность": st.column_config.TextColumn("Серьезность", width="small"),
                "Описание": st.column_config.TextColumn("Описание", width="large"),
                "Количество утверждений": st.column_config.NumberColumn("Количество утверждений", width="small"),
                "Источник": st.column_config.TextColumn("Источник", width="small"),
            },
            disabled=["ID", "Название", "Категория", "Серьезность", "Описание", "Количество утверждений", "Источник"],
            key=table_key,
        )

        selected_rules = [row["ID"] for _, row in edited_df.iterrows() if row["Выбор"]]

        if st.session_state[form_key] != selected_rules:
            st.session_state[form_key] = selected_rules

        source_type = "GitOps" if use_gitops else "локальных"
        st.caption(f"Выбрано: {len(selected_rules)}/{len(options)} {source_type} правил")
        return selected_rules

    @classmethod
    def create_rule_selection_tabs(
        cls, node_check: bool, prometheus_check: bool, opa_check: bool, key_suffix: str = "",
        in_form: bool = False, use_gitops: bool = False
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Создание вкладок выбора правил, показывая только доступные типы правил,
        позволяя пользователю выбирать правила в каждой вкладке.
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
                cls.get_rule_selection_data(cfg["type"], use_gitops)

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
                        key_suffix=f"{key_suffix}_{cfg['type']}",
                        use_gitops=use_gitops
                    )
                else:
                    selected_rules = cls.create_rule_selection(
                        cfg["type"],
                        key_suffix=f"{key_suffix}_{cfg['type']}",
                        use_gitops=use_gitops
                    )

                if cfg["result_var"] == "selected_node_rules":
                    selected_node_rules = selected_rules
                elif cfg["result_var"] == "selected_prometheus_rules":
                    selected_prometheus_rules = selected_rules
                elif cfg["result_var"] == "selected_opa_rules":
                    selected_opa_rules = selected_rules

        return selected_node_rules, selected_prometheus_rules, selected_opa_rules

    @classmethod
    def should_use_gitops(cls) -> bool:
        """Определить, следует ли использовать правила GitOps"""
        try:
            from utils.gitops_manager import GitOpsRuleManager
            gitops_manager = GitOpsRuleManager()
            config = gitops_manager.load_config()

            # Если есть конфигурация из ENV переменных, используем GitOps
            if config.get("from_env"):
                return True

            # Если нет ENV переменных, но в конфиге сохранен GitOps режим
            if config.get("mode") == "gitops" and config.get("repository") is not None:
                # Проверяем, заданы ли обязательные ENV переменные
                if not gitops_manager.has_env_config():
                    print("GitOps настроен в конфиге, но ENV переменные не заданы - используем локальный режим")
                    return False
                return True

            return False
        except Exception:
            return False
