#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер GitOps для управления правилами из Git репозиториев
"""

import json
import os
import git
import shutil
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    "repo_insecure": "KUBEEYE_GITOPS_REPO_INSECURE"
}

class GitOpsRuleManager:
    """Менеджер правил GitOps"""

    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)

    def has_env_config(self) -> bool:
        """Проверить, заданы ли обязательные переменные окружения для GitOps"""
        repo_url = os.getenv(GITOPS_ENV_VARS["repo_url"])
        repo_name = os.getenv(GITOPS_ENV_VARS["repo_name"])
        return bool(repo_url and repo_name)

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
                "from_env": True
            }

        # Если ENV переменных нет, загружаем из файла
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "from_env" in config:
                        config.pop("from_env")
                    return config
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")

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

        # Получаем значение insecure из ENV и правильно преобразуем в булево
        insecure_env = os.getenv(GITOPS_ENV_VARS["repo_insecure"], "").lower()

        # Исправленная логика: "true" -> True (SSL проверка отключена), "false" -> False (SSL проверка включена)
        # По умолчанию SSL проверка включена (insecure = False)
        repo_insecure = insecure_env == "true"

        return {
            "name": repo_name,
            "url": repo_url,
            "branch": os.getenv(GITOPS_ENV_VARS["repo_branch"], "main"),
            "username": os.getenv(GITOPS_ENV_VARS["repo_username"]),
            "token": os.getenv(GITOPS_ENV_VARS["repo_token"]),
            "description": os.getenv(GITOPS_ENV_VARS["repo_description"], ""),
            "insecure": repo_insecure,
            "from_env": True
        }

    def save_config(self, config: Dict):
        """Сохранить конфигурацию GitOps"""
        # Не сохраняем конфигурации из ENV переменных
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            print("Конфигурация управляется через переменные окружения и не может быть изменена через интерфейс")
            return

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
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
        insecure = repo_config.get("insecure", False)

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

    def get_repo_rules(self, repo_name: str):
        """Получить правила из Git репозитория"""
        from utils.rule_loader import Rule
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

                            # АВТОМАТИЧЕСКИ ВКЛЮЧАЕМ ПРАВИЛА ИЗ GITOPS
                            rule_data['enabled'] = True

                            rules.append(Rule(rule_data))
                    except Exception as e:
                        print(f"Ошибка загрузки файла правила {yaml_file}: {e}")

        print(f"Загружено {len(rules)} правил из Git репозитория {repo_name}, все автоматически включены")
        return rules

    def sync_git_rule_to_local(self, rule, target_type: str) -> bool:
        """Синхронизировать правило из Git с локальным хранилищем"""
        try:
            from utils.rule_loader import RULES_DIR
            local_file = RULES_DIR / target_type / f"{rule.id}.yaml"
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
            print(f"Ошибка синхронизации правила: {e}")
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
