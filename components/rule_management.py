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

# ENV переменные для предварительной настройки репозитория
GITOPS_ENV_VARS = {
    "repo_url": "KUBEEYE_GITOPS_REPO_URL",
    "repo_name": "KUBEEYE_GITOPS_REPO_NAME",
    "repo_branch": "KUBEEYE_GITOPS_REPO_BRANCH",
    "repo_username": "KUBEEYE_GITOPS_REPO_USERNAME",
    "repo_token": "KUBEEYE_GITOPS_REPO_TOKEN",
    "repo_description": "KUBEEYE_GITOPS_REPO_DESCRIPTION",
    "repo_insecure": "KUBEEYE_GITOPS_REPO_INSECURE"  # Новая переменная для отключения проверки SSL
}

class GitOpsRuleManager:
    """Менеджер правил GitOps"""

    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.local_rules_dir = RULES_DIR
        self.git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict:
        """Загрузить конфигурацию GitOps - ENV переменные имеют приоритет"""
        # Сначала проверяем ENV переменные
        env_repo = self._load_repo_from_env()
        if env_repo:
            return {
                "mode": "gitops",
                "repository": env_repo,
                "auto_sync": True,
                "sync_interval": 3600,
                "from_env": True  # Помечаем, что конфиг из ENV
            }

        # Если ENV переменных нет, загружаем из файла
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Убедимся, что у старых конфигов нет флага from_env
                    if "from_env" in config:
                        config.pop("from_env")
                    return config
            except Exception as e:
                st.error(f"Ошибка загрузки конфигурации: {e}")

        # Конфиг по умолчанию
        return {
            "mode": "local",
            "repository": None,
            "auto_sync": False,
            "sync_interval": 3600
        }

    def _load_repo_from_env(self) -> Optional[Dict]:
        """Загрузить конфигурацию репозитория из переменных окружения"""
        repo_url = os.getenv(GITOPS_ENV_VARS["repo_url"])
        repo_name = os.getenv(GITOPS_ENV_VARS["repo_name"])

        # Обязательные поля
        if not repo_url or not repo_name:
            return None

        # Получаем значение insecure из ENV (по умолчанию False)
        repo_insecure = os.getenv(GITOPS_ENV_VARS["repo_insecure"], "").lower() == "true"

        return {
            "name": repo_name,
            "url": repo_url,
            "branch": os.getenv(GITOPS_ENV_VARS["repo_branch"], "main"),
            "username": os.getenv(GITOPS_ENV_VARS["repo_username"]),
            "token": os.getenv(GITOPS_ENV_VARS["repo_token"]),
            "description": os.getenv(GITOPS_ENV_VARS["repo_description"], ""),
            "insecure": repo_insecure,  # Добавляем флаг insecure
            "from_env": True
        }

    def save_config(self, config: Dict):
        """Сохранить конфигурацию GitOps"""
        # Не сохраняем конфигурации из ENV переменных
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            st.warning("Конфигурация управляется через переменные окружения и не может быть изменена через интерфейс")
            return

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            # Убедимся, что не сохраняем флаг from_env
            config_to_save = config.copy()
            if "from_env" in config_to_save:
                config_to_save.pop("from_env")
            if config_to_save.get("repository") and "from_env" in config_to_save["repository"]:
                config_to_save["repository"].pop("from_env")

            json.dump(config_to_save, f, indent=2, ensure_ascii=False)

    def clone_or_update_repo(self, repo_config: Dict) -> Tuple[bool, str]:
        """Клонировать или обновить Git репозиторий"""
        repo_name = repo_config["name"]
        repo_url = repo_config["url"]
        branch = repo_config.get("branch", "main")
        username = repo_config.get("username")
        token = repo_config.get("token")
        insecure = repo_config.get("insecure", False)  # Получаем флаг insecure

        repo_path = self.git_rules_dir / repo_name

        try:
            # Формируем URL с аутентификацией
            auth_url = repo_url
            if username and token:
                if repo_url.startswith("https://"):
                    auth_url = repo_url.replace("https://", f"https://{username}:{token}@")
                elif repo_url.startswith("http://"):
                    auth_url = repo_url.replace("http://", f"http://{username}:{token}@")
            elif token:
                if repo_url.startswith("https://"):
                    auth_url = repo_url.replace("https://", f"https://{token}@")
                elif repo_url.startswith("http://"):
                    auth_url = repo_url.replace("http://", f"http://{token}@")

            if repo_path.exists():
                # Обновить существующий репозиторий
                repo = git.Repo(repo_path)
                origin = repo.remotes.origin

                # Добавляем опции для insecure подключения
                pull_kwargs = {}
                if insecure:
                    pull_kwargs = {'env': {'GIT_SSL_NO_VERIFY': '1'}}

                origin.pull(branch, **pull_kwargs)
                message = f"Репозиторий {repo_name} успешно обновлён"
            else:
                # Клонировать новый репозиторий
                clone_kwargs = {'branch': branch}
                if insecure:
                    clone_kwargs['env'] = {'GIT_SSL_NO_VERIFY': '1'}

                git.Repo.clone_from(auth_url, repo_path, **clone_kwargs)
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

    def set_repository(self, repo_config: Dict) -> Tuple[bool, str]:
        """Установить единственный репозиторий"""
        config = self.load_config()

        # Проверяем, не управляется ли репозиторий через ENV
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            return False, "Репозиторий управляется через переменные окружения и не может быть изменен"

        config["repository"] = repo_config
        config["mode"] = "gitops"
        self.save_config(config)
        return True, "Репозиторий успешно установлен"

    def remove_repository(self) -> Tuple[bool, str]:
        """Удалить репозиторий"""
        config = self.load_config()

        # Проверяем, не управляется ли репозиторий через ENV
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            return False, "Репозиторий управляется через переменные окружения и не может быть удален"

        repo_name = config["repository"]["name"] if config.get("repository") else None
        config["repository"] = None
        config["mode"] = "local"
        self.save_config(config)

        # Также удаляем локальную копию репозитория
        if repo_name:
            repo_path = self.git_rules_dir / repo_name
            if repo_path.exists():
                shutil.rmtree(repo_path)

        return True, "Репозиторий удалён"

    def get_env_config_info(self) -> Dict:
        """Получить информацию о конфигурации через ENV переменные"""
        info = {}
        for key, env_var in GITOPS_ENV_VARS.items():
            value = os.getenv(env_var)
            if value:
                if "token" in key and len(value) > 4:
                    info[env_var] = value[:4] + "***"
                elif "username" in key and len(value) > 4:
                    info[env_var] = value[:4] + "***"
                else:
                    info[env_var] = value
            else:
                info[env_var] = "Не установлена"
        return info

    def force_reload_from_env(self):
        """Принудительно перезагрузить конфигурацию из ENV переменных"""
        if self.config_file.exists():
            # Создаем резервную копию старого конфига
            backup_file = self.config_file.with_suffix('.json.backup')
            shutil.copy2(self.config_file, backup_file)

        # Загружаем конфиг из ENV
        env_config = self.load_config()
        return env_config


def render_rule_management_tab():
    """Отобразить вкладку управления правилами"""
    st.markdown("### 🛠️ Центр управления правилами")

    gitops_manager = GitOpsRuleManager()
    config = gitops_manager.load_config()

    # Показать информацию о ENV переменных
    render_env_info(gitops_manager, config)

    # Выбор режима
    render_mode_selector(gitops_manager, config)

    # Отображение интерфейса в зависимости от режима
    if config["mode"] == "local":
        render_local_mode(gitops_manager)
    else:
        render_gitops_mode(gitops_manager, config)


def render_env_info(gitops_manager: GitOpsRuleManager, config: Dict):
    """Отобразить информацию о ENV переменных"""
    with st.expander("🔧 Конфигурация через переменные окружения", expanded=False):
        st.markdown("""
        **Для предварительной настройки GitOps репозитория используйте следующие переменные окружения:**

        | Переменная | Обязательность | Описание |
        |------------|----------------|----------|
        | `KUBEEYE_GITOPS_REPO_URL` | ✅ Обязательно | URL Git репозитория с правилами |
        | `KUBEEYE_GITOPS_REPO_NAME` | ✅ Обязательно | Имя репозитория |
        | `KUBEEYE_GITOPS_REPO_BRANCH` | ❌ Опционально | Ветка (по умолчанию: main) |
        | `KUBEEYE_GITOPS_REPO_USERNAME` | ❌ Опционально | Имя пользователя для аутентификации |
        | `KUBEEYE_GITOPS_REPO_TOKEN` | ❌ Опционально | Токен для приватных репозиториев |
        | `KUBEEYE_GITOPS_REPO_DESCRIPTION` | ❌ Опционально | Описание репозитория |
        | `KUBEEYE_GITOPS_REPO_INSECURE` | ❌ Опционально | Отключить проверку SSL сертификата (true/false) |

        **Примеры использования:**

        **GitHub с токеном:**
        ```dockerfile
        ENV KUBEEYE_GITOPS_REPO_URL=https://github.com/your-org/kubeeye-rules.git
        ENV KUBEEYE_GITOPS_REPO_NAME=production-rules
        ENV KUBEEYE_GITOPS_REPO_TOKEN=ghp_xxx
        ```

        **GitLab с именем пользователя и токеном:**
        ```dockerfile
        ENV KUBEEYE_GITOPS_REPO_URL=https://gitlab.com/your-org/kubeeye-rules.git
        ENV KUBEEYE_GITOPS_REPO_NAME=production-rules
        ENV KUBEEYE_GITOPS_REPO_USERNAME=gitlab-user
        ENV KUBEEYE_GITOPS_REPO_TOKEN=glpat-xxx
        ```

        **Bitbucket с именем пользователя и токеном:**
        ```dockerfile
        ENV KUBEEYE_GITOPS_REPO_URL=https://bitbucket.org/your-org/kubeeye-rules.git
        ENV KUBEEYE_GITOPS_REPO_NAME=production-rules
        ENV KUBEEYE_GITOPS_REPO_USERNAME=bitbucket-user
        ENV KUBEEYE_GITOPS_REPO_TOKEN=app-password
        ```

        **С отключенной проверкой SSL:**
        ```dockerfile
        ENV KUBEEYE_GITOPS_REPO_URL=https://self-signed-cert.example.com/rules.git
        ENV KUBEEYE_GITOPS_REPO_NAME=internal-rules
        ENV KUBEEYE_GITOPS_REPO_INSECURE=true
        ```

        **Примечание:**
        - Репозиторий, настроенный через ENV переменные, нельзя изменить или удалить через интерфейс
        - Для GitHub обычно достаточно токена без имени пользователя
        - Для GitLab и Bitbucket рекомендуется указать и имя пользователя и токен
        - Опция `KUBEEYE_GITOPS_REPO_INSECURE=true` отключает проверку SSL сертификатов (используйте только для тестирования или внутренних репозиториев с самоподписанными сертификатами)
        """)

        # Показать текущие значения ENV переменных
        env_info = gitops_manager.get_env_config_info()
        st.markdown("**Текущие значения ENV переменных:**")
        for env_var, value in env_info.items():
            st.text(f"{env_var}: {value}")

        # Показать статус конфигурации из ENV
        is_env_config = config.get("from_env", False)
        current_repo = config.get("repository")

        if is_env_config:
            st.success("✅ Конфигурация загружена из переменных окружения")
        elif current_repo and current_repo.get("from_env"):
            st.success("✅ Репозиторий загружен из переменных окружения")
        else:
            # Проверим, есть ли ENV переменные, но они не загружены
            env_repo = gitops_manager._load_repo_from_env()
            if env_repo:
                st.warning("⚠️ ENV переменные установлены, но не загружены. Конфигурация была сохранена ранее.")
                if st.button("🔄 Принудительно загрузить из ENV переменных"):
                    new_config = gitops_manager.force_reload_from_env()
                    st.success("✅ Конфигурация перезагружена из ENV переменных")
                    st.rerun()
            else:
                missing = []
                if env_info[GITOPS_ENV_VARS["repo_url"]] == "Не установлена":
                    missing.append(GITOPS_ENV_VARS["repo_url"])
                if env_info[GITOPS_ENV_VARS["repo_name"]] == "Не установлена":
                    missing.append(GITOPS_ENV_VARS["repo_name"])

                if missing:
                    st.error(f"❌ Не хватает обязательных переменных: {', '.join(missing)}")


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
                # Показываем статус insecure
                insecure_status = "✅ Включено" if current_repo.get('insecure') else "❌ Отключено"
                st.markdown(f"**Проверка SSL:** `{insecure_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Описание:** {current_repo['description']}")

                # Проверяем синхронизацию
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("✅ Репозиторий синхронизирован")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Обнаружено правил:** {rules_count}")
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

        # Не показываем форму для изменения репозитория
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
                # Показываем статус insecure
                insecure_status = "✅ Включено" if current_repo.get('insecure') else "❌ Отключено"
                st.markdown(f"**Проверка SSL:** `{insecure_status}`")
                if current_repo.get('description'):
                    st.markdown(f"**Описание:** {current_repo['description']}")

                # Проверяем синхронизацию
                repo_path = gitops_manager.git_rules_dir / current_repo["name"]
                if repo_path.exists():
                    st.success("✅ Репозиторий синхронизирован")
                    rules_count = len(gitops_manager.get_repo_rules(current_repo["name"]))
                    st.markdown(f"**Обнаружено правил:** {rules_count}")
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
                # Добавляем чекбокс для insecure
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
                        "insecure": repo_insecure  # Добавляем флаг insecure
                    }

                    success, message = gitops_manager.set_repository(repo_config)
                    if success:
                        st.success(message)
                        # Автоматически синхронизируем после установки
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
        """)
        return

    st.success(f"📚 Репозиторий: **{current_repo['name']}** | Всего правил: **{len(git_rules)}**")

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

    # Применяем фильтры
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
            st.info(f"Обнаружено правил: {rules_count}")
        else:
            st.error(message)

        st.rerun()
