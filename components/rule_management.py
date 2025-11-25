#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Современный компонент управления правилами — поддержка режима GitOps
"""
import streamlit as st
import yaml
import json
import pandas as pd
import git
import os
import requests
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from utils.rule_loader import load_rules, save_rule, Rule, RULES_DIR
from utils.rule_manager import RuleManager

# Конфигурация GitOps
GITOPS_CONFIG_FILE = Path(__file__).parent.parent / "data" / "gitops_config.json"
DEFAULT_RULE_REPOS = [
    {
        "name": "Официальный репозиторий правил KubeEye",
        "url": "https://github.com/kubesphere/kubeeye",
        "branch": "rules",
        "description": "Официально поддерживаемый репозиторий правил KubeEye, содержит проверенные правила проверки Kubernetes и рекомендации по лучшим практикам"
    }
]

class GitOpsRuleManager:
    """Менеджер правил GitOps"""

    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.local_rules_dir = RULES_DIR
        self.git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict:
        """Загрузить конфигурацию GitOps"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "mode": "local",  # local или gitops
            "current_repository": None,  # Текущий активный репозиторий
            "auto_sync": False,
            "sync_interval": 3600  # в секундах
        }

    def save_config(self, config: Dict):
        """Сохранить конфигурацию GitOps"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def clone_or_update_repo(self, repo_url: str, repo_name: str, branch: str = "main") -> Tuple[bool, str]:
        """Клонировать или обновить Git репозиторий"""
        repo_path = self.git_rules_dir / repo_name

        try:
            if repo_path.exists():
                # Обновить существующий репозиторий
                repo = git.Repo(repo_path)
                origin = repo.remotes.origin
                origin.pull(branch)
                message = f"Репозиторий {repo_name} успешно обновлён"
            else:
                # Клонировать новый репозиторий
                git.Repo.clone_from(repo_url, repo_path, branch=branch)
                message = f"Репозиторий {repo_name} успешно клонирован"

            return True, message
        except Exception as e:
            return False, f"Ошибка операции: {str(e)}"

    def get_repo_rules(self, repo_name: str) -> List[Rule]:
        """Получить правила из Git репозитория"""
        repo_path = self.git_rules_dir / repo_name
        rules = []

        if not repo_path.exists():
            return rules

        # Обойти правила в репозитории
        for rule_type in ["node", "prometheus", "opa"]:
            type_dir = repo_path / rule_type
            if type_dir.exists():
                for yaml_file in type_dir.glob("*.yaml"):
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            rule_data = yaml.safe_load(f)

                        if isinstance(rule_data, dict):
                            # Отметить источник как git
                            rule_data['source'] = 'git'
                            rule_data['repository'] = repo_name
                            rule_data['file_path'] = str(yaml_file.relative_to(repo_path))
                            rules.append(Rule(rule_data))
                    except Exception as e:
                        st.warning(f"Ошибка загрузки файла правила {yaml_file}: {e}")

        return rules

    def sync_git_rule_to_local(self, rule: Rule, target_type: str) -> bool:
        """Синхронизировать правило из Git с локальным хранилищем"""
        try:
            local_file = self.local_rules_dir / target_type / f"{rule.id}.yaml"
            local_file.parent.mkdir(parents=True, exist_ok=True)

            rule_data = rule.to_dict()
            # Удаляем git-специфичные поля
            rule_data.pop('source', None)
            rule_data.pop('repository', None)
            rule_data.pop('file_path', None)

            with open(local_file, 'w', encoding='utf-8') as f:
                yaml.dump(rule_data, f, default_flow_style=False, allow_unicode=True)

            return True
        except Exception as e:
            st.error(f"Ошибка синхронизации правила: {e}")
            return False


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

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        current_mode = config.get("mode", "local")
        mode_options = {
            "local": "📁 Локальный режим",
            "gitops": "🔄 Режим GitOps"
        }

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

    with col2:
        local_rules_count = sum(len(load_rules(rt)) for rt in ["node", "prometheus", "opa"])
        st.metric("Локальные правила", local_rules_count)

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

    tab_manage, tab_browse = st.tabs(["📚 Управление репозиториями", "🔍 Просмотр правил"])

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
    """Управление репозиториями"""
    current_repo = config.get("current_repository", None)

    if current_repo:
        st.markdown("### 📋 Текущий репозиторий")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Название:** {current_repo['name']}")
            st.markdown(f"**URL:** `{current_repo['url']}`")
            st.markdown(f"**Ветка:** `{current_repo['branch']}`")
            if current_repo.get('description'):
                st.markdown(f"**Описание:** {current_repo['description']}")
        with col2:
            if st.button("🔄 Синхронизировать репозиторий", type="primary"):
                sync_repository(gitops_manager, current_repo)
            if st.button("❌ Сменить репозиторий"):
                config["current_repository"] = None
                gitops_manager.save_config(config)
                st.success("Текущий репозиторий очищен, выберите новый")
                st.rerun()
    else:
        st.markdown("### 🌟 Выбор Git репозитория правил")
        official_repo = DEFAULT_RULE_REPOS[0]
        st.markdown("#### 🏆 Официально рекомендованный")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{official_repo['name']}**")
            st.markdown(f"Адрес: `{official_repo['url']}`")
            st.markdown(f"Описание: {official_repo['description']}")
        with col2:
            if st.button("🚀 Включить официальный репозиторий", type="primary"):
                config["current_repository"] = official_repo.copy()
                gitops_manager.save_config(config)
                st.success("✅ Официальный репозиторий включён")
                st.rerun()

def render_git_rule_browser(gitops_manager: GitOpsRuleManager, config: Dict):
    """Просмотр правил из Git"""
    current_repo = config.get("current_repository", None)

    if not current_repo:
        st.warning("💡 Сначала включите Git репозиторий в 'Управлении репозиториями'")
        return

    repo_path = gitops_manager.git_rules_dir / current_repo["name"]
    if not repo_path.exists():
        st.warning(f"⚠️ Репозиторий **{current_repo['name']}** не синхронизирован")
        if st.button("🔄 Синхронизировать сейчас", type="primary"):
            sync_repository(gitops_manager, current_repo)
        return

    git_rules = gitops_manager.get_repo_rules(current_repo["name"])

    if not git_rules:
        st.info("📭 В этом репозитории отсутствуют файлы правил")
        return

    st.success(f"📚 Репозиторий: **{current_repo['name']}** | Всего правил: **{len(git_rules)}**")

    for i, rule in enumerate(git_rules):
        with st.expander(f"📋 {rule.name} ({rule.type})", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Описание:** {rule.description}")
                st.markdown(f"**Тип:** {rule.type} | **Cерьёзность:** {rule.severity}")
            with col2:
                if st.button(f"📥 Импортировать", key=f"import_{rule.id}_{i}", type="primary"):
                    if gitops_manager.sync_git_rule_to_local(rule, rule.type):
                        st.success("✅ Импортировано локально")
                        st.rerun()
                    else:
                        st.error("❌ Ошибка импорта")

def sync_repository(gitops_manager: GitOpsRuleManager, repo: Dict):
    """Синхронизация одного репозитория"""
    with st.spinner(f"Синхронизация репозитория {repo['name']}..."):
        success, message = gitops_manager.clone_or_update_repo(
            repo["url"],
            repo["name"],
            repo.get("branch", "main")
        )

        if success:
            st.success(message)
            rules_count = len(gitops_manager.get_repo_rules(repo["name"]))
            st.info(f"Обнаружено правил: {rules_count}")
        else:
            st.error(message)

        st.rerun()
