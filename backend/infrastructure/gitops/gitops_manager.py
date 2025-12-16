#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitOps manager for managing rules from Git repositories
"""

import json
import os
import git
import shutil
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# GitOps configuration
GITOPS_CONFIG_FILE = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent))) / "gitops_config.json"

# ENV variables for pre-configuring repository
GITOPS_ENV_VARS = {
    "repo_url": "KUBEEYE_GITOPS_REPO_URL",
    "repo_name": "KUBEEYE_GITOPS_REPO_NAME",
    "repo_branch": "KUBEEYE_GITOPS_REPO_BRANCH",
    "repo_username": "KUBEEYE_GITOPS_REPO_USERNAME",
    "repo_token": "KUBEEYE_GITOPS_REPO_TOKEN",
    "repo_description": "KUBEEYE_GITOPS_REPO_DESCRIPTION",
    "repo_insecure": "KUBEEYE_GITOPS_REPO_INSECURE",
}


class GitOpsRuleManager:
    """GitOps rules manager"""

    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.git_rules_dir = Path(os.environ.get("KUBEEYE_DATA_DIR", str(Path(__file__).parent.parent))) / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)

    def has_env_config(self) -> bool:
        """Check if mandatory environment variables for GitOps are set"""
        repo_url = os.getenv(GITOPS_ENV_VARS["repo_url"])
        repo_name = os.getenv(GITOPS_ENV_VARS["repo_name"])
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
        repo_url = os.getenv(GITOPS_ENV_VARS["repo_url"])
        repo_name = os.getenv(GITOPS_ENV_VARS["repo_name"])

        # Mandatory fields
        if not repo_url or not repo_name:
            return None

        # Get insecure value from ENV and correctly convert to boolean
        insecure_env = os.getenv(GITOPS_ENV_VARS["repo_insecure"], "").lower()

        # Fixed logic: "true" -> True (SSL verification disabled), "false" -> False (SSL verification enabled)
        # By default SSL verification is enabled (insecure = False)
        repo_insecure = insecure_env == "true"

        return {
            "name": repo_name,
            "url": repo_url,
            "branch": os.getenv(GITOPS_ENV_VARS["repo_branch"], "main"),
            "username": os.getenv(GITOPS_ENV_VARS["repo_username"]),
            "token": os.getenv(GITOPS_ENV_VARS["repo_token"]),
            "description": os.getenv(GITOPS_ENV_VARS["repo_description"], ""),
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
            # Form URL with authentication
            auth_url = repo_url
            if token and token.strip():
                # Only use authentication if token is not empty
                if username and username.strip():
                    # Use username:token if both are present
                    if repo_url.startswith("https://"):
                        auth_url = repo_url.replace("https://", f"https://{username}:{token}@")
                    elif repo_url.startswith("http://"):
                        auth_url = repo_url.replace("http://", f"http://{username}:{token}@")
                else:
                    # Use token only if username is empty
                    if repo_url.startswith("https://"):
                        auth_url = repo_url.replace("https://", f"https://{token}@")
                    elif repo_url.startswith("http://"):
                        auth_url = repo_url.replace("http://", f"http://{token}@")

            if repo_path.exists():
                # Check if it's a valid git repository
                try:
                    repo = git.Repo(repo_path)
                    # If valid, update existing repository
                    origin = repo.remotes.origin

                    # Update remote URL if it has changed
                    current_url = origin.url
                    if current_url != auth_url:
                        origin.set_url(auth_url)
                        logger.debug(f"Updated remote URL from {current_url} to {auth_url}")

                    # Add options for insecure connection
                    pull_kwargs = {}
                    if insecure:
                        pull_kwargs = {"env": {"GIT_SSL_NO_VERIFY": "1"}}

                    # Force reset to remote branch to handle deleted files
                    origin.fetch()
                    repo.git.reset("--hard", f"origin/{branch}")
                    message = f"Repository {repo_name} successfully updated"
                except git.InvalidGitRepositoryError:
                    # If not a valid git repo, remove corrupted directory and clone fresh
                    shutil.rmtree(repo_path)
                    clone_kwargs = {"branch": branch}
                    if insecure:
                        clone_kwargs["env"] = {"GIT_SSL_NO_VERIFY": "1"}

                    git.Repo.clone_from(auth_url, repo_path, **clone_kwargs)
                    message = f"Repository {repo_name} successfully cloned (recovered from corrupted state)"
            else:
                # Clone new repository
                clone_kwargs = {"branch": branch}
                if insecure:
                    clone_kwargs["env"] = {"GIT_SSL_NO_VERIFY": "1"}

                git.Repo.clone_from(auth_url, repo_path, **clone_kwargs)
                message = f"Repository {repo_name} successfully cloned"

            # Clear rules cache after repository update
            try:
                from infrastructure.rules.rule_loader import clear_rules_cache

                clear_rules_cache()
            except Exception as e:
                logger.warning(f"Failed to clear rules cache: {e}")

            return True, message
        except Exception as e:
            return False, f"Operation error: {str(e)}"

    def get_repo_rules(self, repo_name: str):
        """Get rules from Git repository"""
        from infrastructure.rules.rule_loader import Rule

        repo_path = self.git_rules_dir / repo_name
        rules = []

        if not repo_path.exists():
            return rules

        # Traverse rules in repository
        for rule_type in ["node", "prometheus", "opa"]:
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

    def sync_git_rule_to_local(self, rule, target_type: str) -> bool:
        """Synchronize rule from Git with local storage"""
        try:
            from infrastructure.rules.rule_loader import RULES_DIR

            local_file = RULES_DIR / target_type / f"{rule.id}.yaml"
            local_file.parent.mkdir(parents=True, exist_ok=True)

            rule_data = rule.to_dict()
            # Remove git-specific fields
            rule_data.pop("source", None)
            rule_data.pop("repository", None)
            rule_data.pop("file_path", None)

            with open(local_file, "w", encoding="utf-8") as f:
                yaml.dump(rule_data, f, default_flow_style=False, allow_unicode=True)

            return True
        except Exception as e:
            logger.error(f"Error synchronizing rule: {e}")
            return False

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
            value = os.getenv(env_var)
            if value:
                if "token" in key and len(value) > 4:
                    info[env_var] = value[:4] + "***"
                elif "username" in key and len(value) > 4:
                    info[env_var] = value[:4] + "***"
                else:
                    info[env_var] = value
            else:
                info[env_var] = "Not set"
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
