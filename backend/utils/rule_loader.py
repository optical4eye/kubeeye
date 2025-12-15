#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule loading module - supports GitOps mode
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

# Log setup
logger = logging.getLogger(__name__)

# Main rules directory
RULES_DIR = Path(__file__).parent.parent / "rules"
# GitOps rules directory
GIT_RULES_DIR = Path(__file__).parent.parent / "data" / "git_rules"


class Rule:
    """Rule class representing a check rule, supports assertions format"""

    def __init__(self, rule_data: Dict):
        """
        Initialize rule object, supports assertions format

        Args:
            rule_data: rule data dictionary
        """
        # Basic metadata
        self.id = rule_data.get("id", "")
        self.name = rule_data.get("name", "")
        self.description = rule_data.get("description", "")
        self.type = rule_data.get("type", "")  # Rule type: node, prometheus, opa
        self.category = rule_data.get("category", "")  # Rule category
        self.severity = rule_data.get("severity", "warning")  # Severity
        self.enabled = rule_data.get("enabled", True)  # Is enabled
        self.solution = rule_data.get("solution", "")  # Solution
        self.tags = rule_data.get("tags", [])  # Tags
        self.tier = rule_data.get(
            "tier", "basic"
        )  # Rule tier (basic/standard/extended)

        # GitOps related fields
        self.source = rule_data.get("source", "local")  # Source: local or git
        self.repository = rule_data.get("repository", "")  # Git repository name
        self.file_path = rule_data.get("file_path", "")  # Path in Git repository

        # Main configuration
        self.config = rule_data.get("config", {})  # Unified configuration object

        # Fields specific to assertions mode
        self.assertions = self.config.get(
            "assertions", []
        )  # List of assertion configurations

        # Handle extractors - convert from execution format if needed
        self.extractors = self.config.get("extractors", [])
        if not self.extractors and "execution" in self.config:
            # Convert execution format to extractors format
            execution = self.config["execution"]
            if "command" in execution:
                self.extractors = [
                    {
                        "name": "default_extractor",
                        "type": "command",
                        "command": execution["command"],
                        "timeout": execution.get("timeout", 30),
                    }
                ]
                logger.info(
                    f"Converted execution format to extractors for rule {self.id}"
                )

    def to_dict(self) -> Dict:
        """Convert rule to dictionary"""
        # Basic fields
        rule_dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "severity": self.severity,
            "enabled": self.enabled,
            "solution": self.solution,
            "tags": self.tags,
            "tier": self.tier,
            "config": self.config,
        }

        # Include source information only for Git rules
        if self.source == "git":
            rule_dict["source"] = self.source
            rule_dict["repository"] = self.repository
            rule_dict["file_path"] = self.file_path

        return rule_dict

    @property
    def execution(self) -> Dict:
        """Get execution configuration"""
        return self.config.get("execution", {})


@lru_cache(maxsize=32)
def _load_rules_cached(
    rule_type: str = None, include_disabled: bool = False, use_gitops: bool = False, cache_key: int = 0
) -> tuple:
    """Cached version of rule loading - returns tuple for hashing"""
    # Implementation moved to _load_rules_impl
    rules = _load_rules_impl(rule_type, include_disabled, use_gitops)
    return tuple(rule.id for rule in rules)


def _load_rules_impl(
    rule_type: str = None, include_disabled: bool = False, use_gitops: bool = False
) -> List[Rule]:
    """Internal implementation of rule loading"""
    rules = []

    # Determine base directory
    if use_gitops:
        base_dir = GIT_RULES_DIR
        # If GitOps directory does not exist, return empty list
        if not base_dir.exists():
            logger.info(f"GitOps rules directory does not exist: {base_dir}")
            return rules
        logger.info(f"Loading GitOps rules from: {base_dir}")

        # For GitOps search in all repository subdirectories
        search_dirs = []
        for repo_dir in base_dir.iterdir():
            if repo_dir.is_dir():
                # First try hierarchical structure: repo_name/rule_type/
                type_dir = repo_dir / rule_type if rule_type else repo_dir
                if type_dir.exists() and type_dir.is_dir():
                    search_dirs.append(type_dir)
                else:
                    # If hierarchical structure not found, try flat structure in repo root
                    # Check if there are rule files directly in repo_dir
                    yaml_files_in_repo = list(repo_dir.glob("*.yaml"))
                    if yaml_files_in_repo:
                        # Use repo_dir as search directory for flat structure
                        search_dirs.append(repo_dir)
                    else:
                        # Fallback: search in subdirectories with rule type names
                        for sub_dir in repo_dir.iterdir():
                            if sub_dir.is_dir() and sub_dir.name in [
                                "node",
                                "prometheus",
                                "opa",
                            ]:
                                if not rule_type or sub_dir.name == rule_type:
                                    search_dirs.append(sub_dir)
    else:
        base_dir = RULES_DIR
        logger.info(f"Loading local rules from: {base_dir}")

        # Determine directories to search
        search_dirs = []
        if rule_type:
            # Search only in specified rule type directory
            type_dir = base_dir / rule_type
            if type_dir.exists():
                search_dirs.append(type_dir)
            else:
                logger.warning(
                    f"Directory for rule type '{rule_type}' does not exist: {type_dir}"
                )
        else:
            # Search in all rule directories
            for item in base_dir.iterdir():
                if (
                    item.is_dir()
                    and not item.name.startswith("_")
                    and not item.name == "examples"
                ):
                    search_dirs.append(item)

    logger.info(f"Found directories to search: {[str(d) for d in search_dirs]}")

    # Load rules from each directory
    for rules_dir in search_dirs:
        logger.info(f"Searching for rules in directory: {rules_dir}")

        yaml_files = list(rules_dir.glob("*.yaml"))
        logger.info(f"Found YAML files in {rules_dir}: {len(yaml_files)}")

        for file_path in yaml_files:
            try:
                # Load YAML file
                with open(file_path, "r", encoding="utf-8") as f:
                    rule_data = yaml.safe_load(f)

                # Skip files that don't contain valid rule data
                if (
                    rule_data is None
                    or not isinstance(rule_data, dict)
                    or not rule_data
                ):
                    logger.info(f"Skipping empty or invalid rule file: {file_path}")
                    continue

                # Determine rule type
                if "type" not in rule_data:
                    # Try to determine type from directory name
                    dir_name = rules_dir.name
                    if dir_name in ["node", "prometheus", "opa"]:
                        rule_data["type"] = dir_name
                    else:
                        # If this is repository subdirectory, look at parent directory
                        parent_dir = rules_dir.parent.name
                        if parent_dir in ["node", "prometheus", "opa"]:
                            rule_data["type"] = parent_dir
                        else:
                            rule_data["type"] = "unknown"

                # For GitOps rules add source information
                if use_gitops:
                    # Find repository name from path
                    repo_name = None
                    try:
                        # Path relative to GIT_RULES_DIR
                        relative_path = file_path.relative_to(GIT_RULES_DIR)
                        if relative_path.parts:
                            repo_name = relative_path.parts[0]
                    except ValueError:
                        pass

                    rule_data["source"] = "git"
                    rule_data["repository"] = repo_name or "unknown"
                    rule_data["file_path"] = str(file_path.relative_to(GIT_RULES_DIR))

                    # AUTOMATICALLY ENABLE RULES FROM GITOPS
                    rule_data["enabled"] = True
                    logger.info(
                        f"Rule from GitOps automatically enabled: {rule_data.get('id', 'unknown')}"
                    )

                # Create rule object
                rule = Rule(rule_data)

                # Check if should include in result
                if rule.enabled or include_disabled:
                    # For GitOps with flat structure, filter by rule_type if specified
                    if (
                        use_gitops
                        and rule_type
                        and rule.type != rule_type
                        and rule.type != "unknown"
                    ):
                        logger.info(
                            f"Skipped rule {rule.id} (type mismatch: expected {rule_type}, got {rule.type})"
                        )
                        continue
                    rules.append(rule)
                    logger.info(
                        f"Loaded rule: {rule.id} (type: {rule.type}, enabled: {rule.enabled})"
                    )
                else:
                    logger.info(f"Skipped disabled rule: {rule.id}")

            except Exception as e:
                logger.error(f"Failed to load rule file {file_path}: {str(e)}")

    logger.info(
        f"Loaded {len(rules)} rules from {'GitOps' if use_gitops else 'local'} directory"
    )
    return rules


def _get_directory_hash(base_dir: Path) -> int:
    """Get hash of directory contents for cache invalidation"""
    if not base_dir.exists():
        return 0

    import hashlib
    hasher = hashlib.md5()

    try:
        # Sort files for consistent hashing
        yaml_files = sorted(base_dir.rglob("*.yaml"))
        for file_path in yaml_files:
            if file_path.is_file():
                # Include file path and modification time
                hasher.update(str(file_path).encode())
                hasher.update(str(file_path.stat().st_mtime).encode())
    except Exception:
        # If hashing fails, return 0 to disable cache
        return 0

    return int(hasher.hexdigest(), 16) % 2**32


def load_rules(
    rule_type: str = None, include_disabled: bool = False, use_gitops: bool = False
) -> List[Rule]:
    """
    Load rules of specified type

    Args:
        rule_type: rule type, e.g. node, opa, prometheus, if None, load all rules
        include_disabled: whether to include disabled rules
        use_gitops: whether to use GitOps rules

    Returns:
        List of rules
    """
    # Generate cache key based on directory contents
    base_dir = GIT_RULES_DIR if use_gitops else RULES_DIR
    cache_key = _get_directory_hash(base_dir)

    # Check cache first
    cached_ids = _load_rules_cached(rule_type, include_disabled, use_gitops, cache_key)
    if cached_ids:
        # If we have cached result, load fresh rules and filter by cached IDs
        all_rules = _load_rules_impl(rule_type, include_disabled, use_gitops)
        # Filter rules by cached IDs to maintain order and ensure consistency
        id_to_rule = {rule.id: rule for rule in all_rules}
        return [id_to_rule[rule_id] for rule_id in cached_ids if rule_id in id_to_rule]

    # If no cache, load normally
    return _load_rules_impl(rule_type, include_disabled, use_gitops)


def load_rule_from_file(file_path: str) -> Optional[Rule]:
    """
    Load single rule from file

    Args:
        file_path: path to rule file

    Returns:
        Rule object, if loading failed, return None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rule_data = yaml.safe_load(f)

        if not isinstance(rule_data, dict):
            logger.warning(
                f"Rule file format {file_path} is invalid, must be YAML dictionary"
            )
            return None

        # If type not specified explicitly, try to infer from file path
        if "type" not in rule_data:
            # Try to extract rule type from path
            path_parts = Path(file_path).parts
            for part in path_parts:
                if part in ("node", "opa", "prometheus"):
                    rule_data["type"] = part
                    break

        return Rule(rule_data)

    except Exception as e:
        logger.error(f"Failed to load rule file {file_path}: {str(e)}")
        return None


def save_rule(rule: Rule) -> bool:
    """
    Save rule to file

    Args:
        rule: rule object to save

    Returns:
        Whether saving was successful
    """
    try:
        # Determine rule type directory
        rule_type_dir = RULES_DIR / rule.type

        # Ensure directory exists
        if not rule_type_dir.exists():
            rule_type_dir.mkdir(parents=True, exist_ok=True)

        # Path to rule file
        file_path = rule_type_dir / f"{rule.id}.yaml"

        # Convert rule to dictionary
        rule_dict = rule.to_dict()

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(rule_dict, f, default_flow_style=False, allow_unicode=True)

        # Clear cache after saving
        _load_rules_cached.cache_clear()

        logger.info(f"Rule {rule.id} successfully saved to file {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save rule {rule.id}: {str(e)}")
        return False


def clear_rules_cache():
    """Clear the rules loading cache"""
    _load_rules_cached.cache_clear()
    logger.info("Rules cache cleared")
