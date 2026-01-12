#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized configuration management using Pydantic BaseSettings
"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application paths
    kubeeye_data_dir: str = Field(
        default=str(Path(__file__).parent.parent.parent),
        description="Base directory for KubeEye data",
    )

    # Logging
    kubeeye_log_level: str = Field(default="INFO", description="Logging level", validation_alias="KUBEEYE_LOG_LEVEL")

    # Database configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_port: str = Field(default="5432", description="Database port")
    db_user: str = Field(default="kubeeye", description="Database username")
    db_pass: str = Field(default="kubeeye", description="Database password")
    db_name: str = Field(default="kubeeye", description="Database name")
    sql_debug: bool = Field(default=False, description="Enable SQL debug logging")

    # Report cleanup
    kubeeye_report_retention_days: int = Field(default=7, description="Number of days to retain reports")

    # SSH configuration
    kubeeye_ssh_connection_timeout: int = Field(default=10, description="SSH connection timeout in seconds")
    kubeeye_ssh_max_concurrent_checks: int = Field(default=20, description="Max concurrent SSH checks")

    # SSH connection pool configuration
    kubeeye_ssh_pool_size: int = Field(default=10, description="SSH connection pool size")
    kubeeye_ssh_pool_connection_timeout: int = Field(
        default=300, description="SSH connection pool timeout in seconds (5 minutes)"
    )
    kubeeye_ssh_pool_keepalive_interval: int = Field(
        default=60, description="SSH connection pool keepalive interval in seconds (1 minute)"
    )

    # Popeye configuration
    kubeeye_popeye_path: str = Field(default="/usr/local/bin/popeye", description="Path to Popeye binary")
    kubeeye_popeye_timeout: int = Field(default=300, description="Popeye execution timeout")
    kubeeye_popeye_default_format: str = Field(default="html", description="Default Popeye output format")

    # Node inspector configuration
    node_inspector_max_workers: int = Field(default=5, description="Max workers for node inspector")
    node_inspector_timeout: int = Field(default=30, description="Timeout for node inspector")
    node_inspector_connection_timeout: int = Field(default=10, description="Connection timeout for node inspector")
    node_inspector_retry_attempts: int = Field(default=2, description="Retry attempts for node inspector")
    node_inspector_retry_delay: int = Field(default=1, description="Retry delay for node inspector")
    node_inspector_connection_pool: bool = Field(default=True, description="Enable connection pool for node inspector")
    node_inspector_pool_size: int = Field(default=10, description="Pool size for node inspector")
    node_inspector_keep_alive: bool = Field(default=True, description="Keep alive for node inspector")
    node_inspector_verbose: bool = Field(default=False, description="Verbose logging for node inspector")
    node_inspector_log_output: bool = Field(default=False, description="Log command output for node inspector")

    # GitOps configuration
    kubeeye_gitops_repo_url: Optional[str] = Field(default=None, description="GitOps repository URL")
    kubeeye_gitops_repo_name: Optional[str] = Field(default=None, description="GitOps repository name")
    kubeeye_gitops_repo_branch: str = Field(default="main", description="GitOps repository branch")
    kubeeye_gitops_repo_username: Optional[str] = Field(default=None, description="GitOps repository username")
    kubeeye_gitops_repo_token: Optional[str] = Field(default=None, description="GitOps repository token")
    kubeeye_gitops_repo_description: str = Field(default="", description="GitOps repository description")
    git_ssl_no_verify: Optional[str] = Field(default=None, description="Disable SSL verification for Git operations")


# Global settings instance
settings = Settings()
