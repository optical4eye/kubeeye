#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule loading module - supports GitOps mode
"""

import yaml
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

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
        self.id = rule_data.get('id', '')
        self.name = rule_data.get('name', '')
        self.description = rule_data.get('description', '')
        self.type = rule_data.get('type', '')  # Rule type: node, prometheus, opa
        self.category = rule_data.get('category', '')  # Rule category
        self.severity = rule_data.get('severity', 'warning')  # Severity
        self.enabled = rule_data.get('enabled', True)  # Is enabled
        self.solution = rule_data.get('solution', '')  # Solution
        self.tags = rule_data.get('tags', [])  # Tags
        self.tier = rule_data.get('tier', 'basic')  # Rule tier (basic/standard/extended)

        # GitOps related fields
        self.source = rule_data.get('source', 'local')  # Source: local or git
        self.repository = rule_data.get('repository', '')  # Git repository name
        self.file_path = rule_data.get('file_path', '')  # Path in Git repository

        # Main configuration
        self.config = rule_data.get('config', {})  # Unified configuration object

        # Fields specific to assertions mode
        self.assertions = self.config.get('assertions', [])  # List of assertion configurations
        self.extractors = self.config.get('extractors', [])  # List of extractor configurations

    def to_dict(self) -> Dict:
        """Convert rule to dictionary"""
        # Basic fields
        rule_dict = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'category': self.category,
            'severity': self.severity,
            'enabled': self.enabled,
            'solution': self.solution,
            'tags': self.tags,
            'tier': self.tier,
            'config': self.config
        }

        # Include source information only for Git rules
        if self.source == 'git':
            rule_dict['source'] = self.source
            rule_dict['repository'] = self.repository
            rule_dict['file_path'] = self.file_path

        return rule_dict

    @property
    def execution(self) -> Dict:
        """Get execution configuration"""
        return self.config.get('execution', {})

def load_rules(rule_type: str = None, include_disabled: bool = False, use_gitops: bool = False) -> List[Rule]:
    """
    Load rules of specified type

    Args:
        rule_type: rule type, e.g. node, opa, prometheus, if None, load all rules
        include_disabled: whether to include disabled rules
        use_gitops: whether to use GitOps rules

    Returns:
        List of rules
    """
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
                type_dir = repo_dir / rule_type if rule_type else repo_dir
                if type_dir.exists():
                    search_dirs.append(type_dir)
                else:
                    # If specific type not found, search all subdirectories with rules
                    for sub_dir in repo_dir.iterdir():
                        if sub_dir.is_dir() and sub_dir.name in ['node', 'prometheus', 'opa']:
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
                logger.warning(f"Directory for rule type '{rule_type}' does not exist: {type_dir}")
        else:
            # Search in all rule directories
            for item in base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_') and not item.name == 'examples':
                    search_dirs.append(item)

    logger.info(f"Found directories to search: {[str(d) for d in search_dirs]}")

    # Load rules from each directory
    for rules_dir in search_dirs:
        logger.info(f"Searching for rules in directory: {rules_dir}")

        yaml_files = list(rules_dir.glob('*.yaml'))
        logger.info(f"Found YAML files in {rules_dir}: {len(yaml_files)}")

        for file_path in yaml_files:
            try:
                # Load YAML file
                with open(file_path, 'r', encoding='utf-8') as f:
                    rule_data = yaml.safe_load(f)

                # Ensure rule data is a dictionary
                if not isinstance(rule_data, dict):
                    logger.warning(f"Rule file format {file_path} is invalid, must be YAML dictionary")
                    continue

                # Determine rule type
                if 'type' not in rule_data:
                    # Try to determine type from directory name
                    dir_name = rules_dir.name
                    if dir_name in ['node', 'prometheus', 'opa']:
                        rule_data['type'] = dir_name
                    else:
                        # If this is repository subdirectory, look at parent directory
                        parent_dir = rules_dir.parent.name
                        if parent_dir in ['node', 'prometheus', 'opa']:
                            rule_data['type'] = parent_dir
                        else:
                            rule_data['type'] = 'unknown'

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

                    rule_data['source'] = 'git'
                    rule_data['repository'] = repo_name or 'unknown'
                    rule_data['file_path'] = str(file_path.relative_to(GIT_RULES_DIR))

                    # AUTOMATICALLY ENABLE RULES FROM GITOPS
                    rule_data['enabled'] = True
                    logger.info(f"Rule from GitOps automatically enabled: {rule_data.get('id', 'unknown')}")

                # Create rule object
                rule = Rule(rule_data)

                # Check if should include in result
                if rule.enabled or include_disabled:
                    rules.append(rule)
                    logger.info(f"Loaded rule: {rule.id} (type: {rule.type}, enabled: {rule.enabled})")
                else:
                    logger.info(f"Skipped disabled rule: {rule.id}")

            except Exception as e:
                logger.error(f"Failed to load rule file {file_path}: {str(e)}")

    logger.info(f"Loaded {len(rules)} rules from {'GitOps' if use_gitops else 'local'} directory")
    return rules

def load_rule_from_file(file_path: str) -> Optional[Rule]:
    """
    Load single rule from file

    Args:
        file_path: path to rule file

    Returns:
        Rule object, if loading failed, return None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            rule_data = yaml.safe_load(f)

        if not isinstance(rule_data, dict):
            logger.warning(f"Rule file format {file_path} is invalid, must be YAML dictionary")
            return None

        # If type not specified explicitly, try to infer from file path
        if 'type' not in rule_data:
            # Try to extract rule type from path
            path_parts = Path(file_path).parts
            for part in path_parts:
                if part in ('node', 'opa', 'prometheus'):
                    rule_data['type'] = part
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
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(rule_dict, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Rule {rule.id} successfully saved to file {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save rule {rule.id}: {str(e)}")
        return False