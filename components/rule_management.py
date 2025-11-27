#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Современный компонент управления правилами — поддержка режима GitOps
"""
import streamlit as st
import yaml
import json
import pandas as pd
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils.rule_loader import load_rules, Rule, RULES_DIR
from utils.gitops_manager import GitOpsRuleManager
from utils.rule_manager import RuleManager

def render_rule_management_tab():
    """Отобразить вкладку управления правилами"""
    st.markdown("### 🛠️ Центр управления правилами")

    gitops_manager = GitOpsRuleManager()
    config = gitops_manager.load_config()

    # Выбор режима
    render_mode_selector(gitops_manager, config)

    # Отображение интерфейса в зависимости от режима
    if config["mode"] == "local":
        render_local_mode(gitops_manager)
    else:
        render_gitops_mode(gitops_manager, config)


def render_mode_selector(gitops_manager: GitOpsRuleManager, config: Dict):
    """Отобразить селектор режима"""
    st.markdown("#### 🎯 Режим управления правилами")

    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        current_mode = config.get("mode", "local")
        mode_options = {
            "local": "📁 Локальный режим",
            "gitops": "🔄 Режим GitOps"
        }

        # Если репозиторий из ENV, блокируем выбор режима
        if is_env_config or is_env_repo:
            st.selectbox(
                "Выберите режим управления",
                options=["gitops"],
                format_func=lambda x: "🔄 Режим GitOps (управляется через ENV)",
                index=0,
                disabled=True
            )
            st.info("Режим управляется через переменные окружения")
        else:
            # Проверяем, заданы ли ENV переменные
            has_env = gitops_manager.has_env_config()

            if has_env:
                # ENV переменные заданы - можно выбирать режим
                selected_mode = st.selectbox(
                    "Выберите режим управления",
                    options=list(mode_options.keys()),
                    format_func=lambda x: mode_options[x],
                    index=list(mode_options.keys()).index(current_mode)
                )

                if selected_mode != current_mode:
                    config["mode"] = selected_mode
                    gitops_manager.save_config(config)
                    st.success(f"Переключено на {mode_options[selected_mode]}")
                    st.rerun()
            else:
                # ENV переменные не заданы - только локальный режим
                st.selectbox(
                    "Выберите режим управления",
                    options=["local"],
                    format_func=lambda x: "📁 Локальный режим (ENV переменные не заданы)",
                    index=0,
                    disabled=True
                )
                st.info("Для использования GitOps задайте переменные окружения")

    with col2:
        # Показываем количество локальных правил только в локальном режиме
        if config.get("mode") == "local":
            local_rules_count = sum(len(load_rules(rt)) for rt in ["node", "prometheus", "opa"])
            st.metric("Локальные правила", local_rules_count)
        else:
            # В режиме GitOps показываем информацию о GitOps правилах
            current_repo = config.get("repository")
            if current_repo:
                repo_name = current_repo.get("name", "Неизвестно")
                git_rules = gitops_manager.get_repo_rules(repo_name)
                st.metric("Правил GitOps", len(git_rules))
            else:
                st.metric("Правил GitOps", 0)

    with col3:
        if st.button("🔄 Обновить", help="Обновить список правил"):
            st.rerun()


def render_local_mode(gitops_manager: GitOpsRuleManager):
    """Отобразить интерфейс локального режима"""
    st.markdown("#### 📁 Локальные правила")
    render_local_rule_list()


def render_gitops_mode(gitops_manager: GitOpsRuleManager, config: Dict):
    """Отобразить интерфейс режима GitOps"""
    st.markdown("#### 🔄 Управление правилами GitOps")

    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    if is_env_config or is_env_repo:
        st.info("🎯 Конфигурация управляется через переменные окружения")

    tab_manage, tab_browse = st.tabs(["⚙️ Настройка репозитория", "🔍 Просмотр правил"])

    with tab_manage:
        render_repository_management(gitops_manager, config)

    with tab_browse:
        render_git_rule_browser(gitops_manager, config)


def render_local_rule_list():
    """Отобразить список локальных правил"""
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_types = st.multiselect(
            "Выберите типы правил",
            ["node", "prometheus", "opa"],
            default=["node", "prometheus", "opa"],
            format_func=lambda x: {"node": "🖥️ Правила узлов", "prometheus": "📊 Правила мониторинга", "opa": "🔒 Правила безопасности"}[x]
        )

    with col2:
        show_disabled = st.checkbox("Показывать отключённые", value=False)

    all_rules = []
    for rule_type in selected_types:
        rules = load_rules(rule_type, include_disabled=show_disabled)
        all_rules.extend(rules)

    if not all_rules:
        st.info("Правила не найдены, проверьте каталог или создайте новые правила.")
        return

    rule_data = []
    severity_map = {
        "info": "ℹ️ Информация",
        "low": "🟢 Низкая",
        "warning": "⚠️ Предупреждение",
        "medium": "🟡 Средняя",
        "high": "🟠 Высокая",
        "critical": "🚨 Критическая"
    }

    for rule in all_rules:
        rule_data.append({
            "ID": rule.id,
            "Название": rule.name,
            "Тип": {"node": "🖥️ Узел", "prometheus": "📊 Мониторинг", "opa": "🔒 Безопасность"}[rule.type],
            "Статус": "✅ Включено" if rule.enabled else "❌ Отключено",
            "Серьёзность": severity_map.get(rule.severity, f"❓ {rule.severity}"),
            "Описание": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description
        })

    if rule_data:
        df = pd.DataFrame(rule_data)
        st.dataframe(df, use_container_width=True)


def render_repository_management(gitops_manager: GitOpsRuleManager, config: Dict):
    """Управление единственным репозиторием"""
    is_env_config = config.get("from_env", False)
    current_repo = config.get("repository")
    is_env_repo = current_repo.get('from_env', False) if current_repo else False

    if current_repo and not (is_env_config or is_env_repo):
        # Отображение текущего репозитория - только просмотр и удаление
        st.markdown("### 📋 Текущий репозиторий")
        st.info("💡 Репозиторий нельзя изменить. Для смены репозитория необходимо сначала удалить текущий.")

        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**🎯 {current_repo['name']}**")
                st.markdown(f"**URL:** `{current_repo['url']}`")
                st.markdown(f"**Ветка:** `{current_repo.get('branch', 'main')}`")
                if current_repo.get('username'):
                    st.markdown(f"**Имя пользователя:** `{current_repo['username']}`")
                if current_repo.get('token'):
                    st.markdown("🔐 **Доступ: с токеном**")
                insecure_status = "✅ Включено" if current_repo.get('insecure') else "❌ Отключено"
                st.markdown(f"**Проверка SSL:** `{insecure_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Описание:** {current_repo['description']}")

                # Проверяем синхронизацию
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("✅ Репозиторий синхронизирован")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Обнаружено правил:** {rules_count} (все автоматически включены)")
                else:
                    st.warning("⚠️ Репозиторий не синхронизирован")

            with col2:
                if st.button("🔄 Синхронизировать", type="primary", use_container_width=True):
                    sync_repository(gitops_manager, current_repo)

            with col3:
                if st.button("🗑️ Удалить", type="secondary", use_container_width=True):
                    success, message = gitops_manager.remove_repository()
                    if success:
                        st.success(message)
                        st.rerun()

        st.markdown("---")
        st.warning("Для добавления нового репозитория необходимо сначала удалить текущий")

    elif current_repo and (is_env_config or is_env_repo):
        # Репозиторий из ENV переменных - только просмотр
        st.markdown("### 📋 Репозиторий из переменных окружения")
        st.info("🔧 Этот репозиторий настроен через переменные окружения и не может быть изменен через интерфейс.")

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**🎯 {current_repo['name']}**")
                st.markdown(f"**URL:** `{current_repo['url']}`")
                st.markdown(f"**Ветка:** `{current_repo.get('branch', 'main')}`")
                if current_repo.get('username'):
                    st.markdown(f"**Имя пользователя:** `{current_repo['username']}`")
                if current_repo.get('token'):
                    st.markdown("🔐 **Доступ: с токеном**")
                insecure_status = "✅ Включено" if current_repo.get('insecure') else "❌ Отключено"
                st.markdown(f"**Проверка SSL:** `{insecure_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Описание:** {current_repo['description']}")

                # Проверяем синхронизацию
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("✅ Репозиторий синхронизирован")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Обнаружено правил:** {rules_count} (все автоматически включены)")
                else:
                    st.warning("⚠️ Репозиторий не синхронизирован")

            with col2:
                if st.button("🔄 Синхронизировать", type="primary", use_container_width=True):
                    sync_repository(gitops_manager, current_repo)

    else:
        # Форма добавления нового репозитория
        st.markdown("### ➕ Добавление репозитория правил")
        st.info("💡 В режиме GitOps можно использовать только один репозиторий. После добавления его можно будет только удалить, но не изменить.")

        with st.form("add_repo_form"):
            col1, col2 = st.columns(2)

            with col1:
                repo_name = st.text_input("Название репозитория*",
                                        placeholder="Мой репозиторий правил")
                repo_url = st.text_input("URL репозитория*",
                                       placeholder="https://github.com/user/repo.git")
                repo_branch = st.text_input("Ветка",
                                          value="main",
                                          placeholder="main")
                repo_username = st.text_input("Имя пользователя",
                                            placeholder="username (опционально)",
                                            help="Имя пользователя для аутентификации")

            with col2:
                repo_description = st.text_area("Описание",
                                              placeholder="Описание репозитория правил")
                repo_token = st.text_input("Токен доступа", type="password",
                                         placeholder="ghp_... для GitHub, glpat_... для GitLab",
                                         help="Токен для доступа к приватным репозиториям")
                repo_insecure = st.checkbox(
                    "Отключить проверку SSL сертификата",
                    value=False,
                    help="Используйте только для тестирования или внутренних репозиториев с самоподписанными сертификатами"
                )

            submitted = st.form_submit_button("✅ Добавить репозиторий")

            if submitted:
                if not repo_name or not repo_url:
                    st.error("Пожалуйста, заполните обязательные поля (название и URL)")
                else:
                    repo_config = {
                        "name": repo_name,
                        "url": repo_url,
                        "branch": repo_branch or "main",
                        "username": repo_username if repo_username else None,
                        "token": repo_token if repo_token else None,
                        "description": repo_description,
                        "insecure": repo_insecure
                    }

                    success, message = gitops_manager.set_repository(repo_config)
                    if success:
                        st.success(message)
                        sync_repository(gitops_manager, repo_config)
                    else:
                        st.error(message)


def render_git_rule_browser(gitops_manager: GitOpsRuleManager, config: Dict):
    """Просмотр правил из Git"""
    current_repo = config.get("repository")

    if not current_repo:
        st.warning("💡 Сначала добавьте Git репозиторий в разделе 'Настройка репозитория'")
        return

    repo_path = gitops_manager.git_rules_dir / current_repo["name"]
    if not repo_path.exists():
        st.warning(f"⚠️ Репозиторий **{current_repo['name']}** не синхронизирован")
        if st.button("🔄 Синхронизировать сейчас", type="primary"):
            sync_repository(gitops_manager, current_repo)
        return

    git_rules = gitops_manager.get_repo_rules(current_repo["name"])

    if not git_rules:
        st.info("📭 В этом репозитории отсутствуют файлы правил или структура не соответствует ожидаемой")
        st.markdown("""
        **Ожидаемая структура репозитория:**
        ```
        repository-root/
        ├── node/           # Правила для узлов
        │   └── *.yaml
        ├── prometheus/     # Правила мониторинга
        │   └── *.yaml
        └── opa/            # Правила безопасности
            └── *.yaml
        ```
        **Примечание:** Все правила из GitOps автоматически включаются после синхронизации.
        """)
        return

    st.success(f"📚 Репозиторий: **{current_repo['name']}** | Всего правил: **{len(git_rules)}** (все автоматически включены)")

    # Фильтры для правил
    col1, col2 = st.columns([2, 1])
    with col1:
        rule_type_filter = st.multiselect(
            "Фильтр по типу",
            ["node", "prometheus", "opa"],
            default=["node", "prometheus", "opa"],
            format_func=lambda x: {"node": "🖥️ Узлы", "prometheus": "📊 Мониторинг", "opa": "🔒 Безопасность"}[x]
        )

    with col2:
        search_term = st.text_input("Поиск по названию")

    filtered_rules = [
        rule for rule in git_rules
        if rule.type in rule_type_filter and
        (not search_term or search_term.lower() in rule.name.lower() or search_term.lower() in rule.description.lower())
    ]

    if not filtered_rules:
        st.info("Правила не найдены по заданным фильтрам")
        return

    for i, rule in enumerate(filtered_rules):
        with st.expander(f"📋 {rule.name} ({rule.type})", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Описание:** {rule.description}")
                st.markdown(f"**Тип:** {rule.type} | **Cерьёзность:** {rule.severity}")
                st.markdown(f"**Категория:** {rule.category}")
                if rule.tags:
                    st.markdown(f"**Теги:** {', '.join(rule.tags)}")
                status_icon = "✅" if rule.enabled else "❌"
                st.markdown(f"**Статус:** {status_icon} {'Включено (автоматически)' if rule.enabled else 'Отключено'}")
            with col2:
                if st.button(f"📥 Импортировать", key=f"import_{rule.id}_{i}", type="primary"):
                    if gitops_manager.sync_git_rule_to_local(rule, rule.type):
                        st.success("✅ Импортировано локально")
                        st.rerun()
                    else:
                        st.error("❌ Ошибка импорта")


def sync_repository(gitops_manager: GitOpsRuleManager, repo: Dict):
    """Синхронизация репозитория"""
    with st.spinner(f"Синхронизация репозитория {repo['name']}..."):
        success, message = gitops_manager.clone_or_update_repo(repo)

        if success:
            st.success(message)
            rules_count = len(gitops_manager.get_repo_rules(repo["name"]))
            st.info(f"Обнаружено правил: {rules_count} (все автоматически включены)")
        else:
            st.error(message)

        st.rerun()
