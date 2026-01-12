#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps manager for managing rules from Git repositories
"""

import json
import os
import pygit2
import shutil
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
import re

from core.logging import get_logger
from core.config.settings import settings

logger = get_logger(__name__)


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Маскирует чувствительные данные, оставляя только первые visible_chars символов.

    Args:
        data: Строка с чувствительными данными
        mask_char: Символ для маскирования
        visible_chars: Количество видимых символов в начале строки

    Returns:
        Замаскированная строка
    """
    if not data or len(data) <= visible_chars:
        return mask_char * 8  # Возвращаем маску если данных нет или они слишком короткие

    return data[:visible_chars] + mask_char * (len(data) - visible_chars)


def mask_url_with_credentials(url: str) -> str:
    """
    Маскирует учетные данные в URL.

    Args:
        url: URL который может содержать учетные данные

    Returns:
        URL с замаскированными учетными данными
    """
    if not url:
        return url

    # Маскируем учетные данные в URL формата https://username:token@domain.com
    pattern = r"^(https?://)([^:@]+):([^@]+)@(.+)$"
    masked_url = re.sub(
        pattern,
        lambda m: f"{m.group(1)}{mask_sensitive_data(m.group(2))}:{mask_sensitive_data(m.group(3))}@{m.group(4)}",
        url,
    )

    # Маскируем токен в URL формата https://token@domain.com
    pattern = r"^(https?://)([^@]+)@(.+)$"
    masked_url = re.sub(pattern, lambda m: f"{m.group(1)}{mask_sensitive_data(m.group(2))}@{m.group(3)}", masked_url)

    return masked_url


# GitOps configuration
GITOPS_CONFIG_FILE = Path(settings.kubeeye_data_dir) / "gitops_config.json"

# ENV variables for pre-configuring repository
GITOPS_ENV_VARS = {
    "repo_url": "KUBEEYE_GITOPS_REPO_URL",
    "repo_name": "KUBEEYE_GITOPS_REPO_NAME",
    "repo_branch": "KUBEEYE_GITOPS_REPO_BRANCH",
    "repo_username": "KUBEEYE_GITOPS_REPO_USERNAME",
    "repo_token": "KUBEEYE_GITOPS_REPO_TOKEN",
    "repo_description": "KUBEEYE_GITOPS_REPO_DESCRIPTION",
}


class GitOpsRuleManager:
    """GitOps rules manager"""

    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.git_rules_dir = Path(settings.kubeeye_data_dir) / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)

    def has_env_config(self) -> bool:
        """Check if mandatory environment variables for GitOps are set"""
        repo_url = settings.kubeeye_gitops_repo_url
        repo_name = settings.kubeeye_gitops_repo_name
        return bool(repo_url and repo_name)

    def load_config(self) -> Dict:
        """Load GitOps configuration - ENV variables have priority"""
        # First check ENV variables
        env_repo = self._load_repo_from_env()
        if env_repo:
            return {
                "mode": "gitops",
                "repository": env_repo,
                "auto_sync": True,
                "sync_interval": 3600,
                "from_env": True,
            }

        # If no ENV variables, load from file
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "from_env" in config:
                        config.pop("from_env")
                    return config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")

        # Default config
        return {
            "mode": "local",
            "repository": None,
            "auto_sync": False,
            "sync_interval": 3600,
        }

    def _load_repo_from_env(self) -> Optional[Dict]:
        """Load repository configuration from environment variables"""
        repo_url = settings.kubeeye_gitops_repo_url
        repo_name = settings.kubeeye_gitops_repo_name

        # Mandatory fields
        if not repo_url or not repo_name:
            return None

        # Get insecure value from GIT_SSL_NO_VERIFY env var
        # GIT_SSL_NO_VERIFY="1" disables SSL verification (insecure = True)
        repo_insecure = settings.git_ssl_no_verify == "1"

        return {
            "name": repo_name,
            "url": repo_url,
            "branch": settings.kubeeye_gitops_repo_branch,
            "username": settings.kubeeye_gitops_repo_username,
            "token": settings.kubeeye_gitops_repo_token,
            "description": settings.kubeeye_gitops_repo_description,
            "insecure": repo_insecure,
            "from_env": True,
        }

    def save_config(self, config: Dict):
        """Save GitOps configuration"""
        # Do not save configurations from ENV variables
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            logger.info(
                "Configuration is managed via environment variables and cannot be changed through the interface"
            )
            return

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            config_to_save = config.copy()
            if "from_env" in config_to_save:
                config_to_save.pop("from_env")
            if config_to_save.get("repository") and "from_env" in config_to_save["repository"]:
                config_to_save["repository"].pop("from_env")

            json.dump(config_to_save, f, indent=2, ensure_ascii=False)

    def clone_or_update_repo(self, repo_config: Dict) -> Tuple[bool, str]:
        """Clone or update Git repository"""
        repo_name = repo_config["name"]
        repo_url = repo_config["url"]
        branch = repo_config.get("branch", "main")
        username = repo_config.get("username")
        token = repo_config.get("token")
        insecure = repo_config.get("insecure", False)

        repo_path = self.git_rules_dir / repo_name

        try:
            # Prepare credentials
            credentials = None
            if token and token.strip():
                # Use username if provided, otherwise use 'oauth2' for GitHub PAT
                cred_username = username.strip() if username and username.strip() else "oauth2"
                credentials = pygit2.UserPass(cred_username, token)

            # Create callbacks
            # Support both config-based insecure flag and GIT_SSL_NO_VERIFY env var
            use_insecure = insecure or settings.git_ssl_no_verify == "1"
            if use_insecure:

                class InsecureCallbacks(pygit2.RemoteCallbacks):
                    def certificate_check(self, certificate, valid, host):
                        return True  # Accept all certificates

                callbacks = InsecureCallbacks(credentials=credentials)
            else:
                callbacks = pygit2.RemoteCallbacks(credentials=credentials) if credentials else None

            if repo_path.exists():
                # Check if it's a valid git repository
                try:
                    repo = pygit2.Repository(str(repo_path))
                    # If valid, update existing repository
                    origin = repo.remotes["origin"]

                    # Update remote URL if it has changed
                    current_url = origin.url
                    if current_url != repo_url:
                        # Remove old remote and add new one with updated URL
                        repo.remotes.delete("origin")
                        origin = repo.remotes.create("origin", repo_url)
                        logger.debug(
                            f"Updated remote URL from {mask_url_with_credentials(current_url)} to {mask_url_with_credentials(repo_url)}"
                        )

                    # Fetch from remote
                    origin.fetch(callbacks=callbacks)

                    # Force reset to remote branch to handle deleted files
                    remote_ref = repo.lookup_reference(f"refs/remotes/origin/{branch}")
                    repo.reset(remote_ref.target, pygit2.GIT_RESET_HARD)
                    message = f"Repository {repo_name} successfully updated"
                except pygit2.GitError:
                    # If not a valid git repo, remove corrupted directory and clone fresh
                    shutil.rmtree(repo_path)
                    pygit2.clone_repository(repo_url, str(repo_path), checkout_branch=branch, callbacks=callbacks)
                    message = f"Repository {repo_name} successfully cloned (recovered from corrupted state)"
            else:
                # Clone new repository
                pygit2.clone_repository(repo_url, str(repo_path), checkout_branch=branch, callbacks=callbacks)
                message = f"Repository {repo_name} successfully cloned"

            # Clear rules cache after repository update
            try:
                from infra.rules.rule_loader import clear_rules_cache

                clear_rules_cache()
            except Exception as e:
                logger.warning(f"Failed to clear rules cache: {e}")

            return True, message
        except Exception as e:
            return False, f"Operation error: {str(e)}"

    def get_repo_rules(self, repo_name: str):
        """Get rules from Git repository"""
        from infra.rules.rule_loader import Rule

        repo_path = self.git_rules_dir / repo_name
        rules = []

        if not repo_path.exists():
            return rules

        # Traverse rules in repository
        for rule_type in ["node", "opa"]:
            type_dir = repo_path / rule_type
            if type_dir.exists():
                for yaml_file in type_dir.glob("*.yaml"):
                    try:
                        with open(yaml_file, "r", encoding="utf-8") as f:
                            rule_data = yaml.safe_load(f)

                        if isinstance(rule_data, dict):
                            # Mark source as git
                            rule_data["source"] = "git"
                            rule_data["repository"] = repo_name
                            rule_data["file_path"] = str(yaml_file.relative_to(repo_path))

                            # AUTOMATICALLY ENABLE RULES FROM GITOPS
                            rule_data["enabled"] = True

                            rules.append(Rule(rule_data))
                    except Exception as e:
                        logger.error(f"Error loading rule file {yaml_file}: {e}")

        logger.info(f"Loaded {len(rules)} rules from Git repository {repo_name}, all automatically enabled")
        return rules

    def set_repository(self, repo_config: Dict) -> Tuple[bool, str]:
        """Set single repository"""
        config = self.load_config()

        # Check if repository is managed via ENV
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            return (
                False,
                "Repository is managed via environment variables and cannot be changed",
            )

        config["repository"] = repo_config
        config["mode"] = "gitops"
        self.save_config(config)
        return True, "Repository successfully set"

    def remove_repository(self) -> Tuple[bool, str]:
        """Remove repository"""
        config = self.load_config()

        # Check if repository is managed via ENV
        if config.get("from_env") or (config.get("repository") and config["repository"].get("from_env")):
            return (
                False,
                "Repository is managed via environment variables and cannot be deleted",
            )

        repo_name = config["repository"]["name"] if config.get("repository") else None
        config["repository"] = None
        config["mode"] = "local"
        self.save_config(config)

        # Also remove local repository copy
        if repo_name:
            repo_path = self.git_rules_dir / repo_name
            if repo_path.exists():
                shutil.rmtree(repo_path)

        return True, "Repository removed"

    def get_env_config_info(self) -> Dict:
        """Get information about configuration via ENV variables"""
        info = {}
        for key, env_var in GITOPS_ENV_VARS.items():
            value = getattr(settings, f"kubeeye_gitops_{key}")
            if value:
                # Маскируем все чувствительные данные: токены, пароли, имена пользователей
                if any(
                    sensitive_word in key.lower()
                    for sensitive_word in ["token", "password", "username", "secret", "key"]
                ):
                    info[env_var] = mask_sensitive_data(str(value))
                else:
                    info[env_var] = value
            else:
                info[env_var] = "Not set"

        # Add GIT_SSL_NO_VERIFY status
        git_ssl_no_verify = settings.git_ssl_no_verify
        info["GIT_SSL_NO_VERIFY"] = git_ssl_no_verify if git_ssl_no_verify else "Not set"

        return info

    def force_reload_from_env(self):
        """Force reload configuration from ENV variables"""
        if self.config_file.exists():
            # Create backup of old config
            backup_file = self.config_file.with_suffix(".json.backup")
            shutil.copy2(self.config_file, backup_file)

        # Load config from ENV
        env_config = self.load_config()
        return env_config
