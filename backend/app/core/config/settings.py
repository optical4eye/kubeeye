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

    # SSH configuration (unified for all SSH operations)
    kubeeye_ssh_connection_timeout: int = Field(default=15, description="SSH connection timeout in seconds")
    kubeeye_ssh_max_concurrent_checks: int = Field(default=50, description="Max concurrent SSH checks (supports up to 50 hosts)")
    kubeeye_ssh_command_timeout: int = Field(default=60, description="SSH command execution timeout in seconds")

    # SSH retry configuration
    kubeeye_ssh_retry_attempts: int = Field(default=2, description="Number of SSH retry attempts")
    kubeeye_ssh_retry_delay: int = Field(default=2, description="Delay between SSH retry attempts in seconds")

    # SSH connection pool configuration
    kubeeye_ssh_pool_enabled: bool = Field(default=True, description="Enable SSH connection pool")
    kubeeye_ssh_pool_size: int = Field(default=50, description="SSH connection pool size (supports up to 50 hosts)")
    kubeeye_ssh_pool_connection_timeout: int = Field(
        default=300, description="SSH connection pool timeout in seconds (5 minutes)"
    )
    kubeeye_ssh_pool_keepalive_interval: int = Field(
        default=60, description="SSH connection pool keepalive interval in seconds (1 minute)"
    )
    kubeeye_ssh_keep_alive: bool = Field(default=True, description="Keep SSH connections alive")

    # SSH logging configuration
    kubeeye_ssh_verbose: bool = Field(default=False, description="Enable verbose SSH logging")
    kubeeye_ssh_log_output: bool = Field(default=False, description="Log SSH command output")

    # Popeye configuration
    kubeeye_popeye_path: str = Field(default="/usr/local/bin/popeye", description="Path to Popeye binary")
    kubeeye_popeye_timeout: int = Field(default=300, description="Popeye execution timeout")
    kubeeye_popeye_default_format: str = Field(default="html", description="Default Popeye output format")

    # GitOps configuration
    kubeeye_gitops_repo_url: Optional[str] = Field(default=None, description="GitOps repository URL")
    kubeeye_gitops_repo_name: Optional[str] = Field(default=None, description="GitOps repository name")
    kubeeye_gitops_repo_branch: str = Field(default="main", description="GitOps repository branch")
    kubeeye_gitops_repo_username: Optional[str] = Field(default=None, description="GitOps repository username")
    kubeeye_gitops_repo_token: Optional[str] = Field(default=None, description="GitOps repository token")
    kubeeye_gitops_repo_description: str = Field(default="", description="GitOps repository description")
    kubeeye_gitops_sync_interval: int = Field(
        default=300, description="GitOps sync interval in seconds (default: 5 minutes)"
    )
    git_ssl_no_verify: Optional[str] = Field(default=None, description="Disable SSL verification for Git operations")

    # JWT Configuration
    kubeeye_jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production", description="JWT secret key for token signing"
    )
    kubeeye_jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    kubeeye_jwt_access_token_expire_hours: int = Field(
        default=24, description="JWT access token expiration time in hours"
    )

    # Admin user initialization
    kubeeye_admin_username: str = Field(default="admin", description="Admin username")
    kubeeye_admin_email: str = Field(default="admin@kubeeye.local", description="Admin email")
    kubeeye_admin_password: str = Field(default="admin123", description="Admin password (change in production)")

    # Security settings
    kubeeye_max_failed_login_attempts: int = Field(default=5, description="Max failed login attempts before lock")
    kubeeye_account_lock_duration_minutes: int = Field(default=30, description="Account lock duration in minutes")

    # Audit configuration
    kubeeye_audit_enabled: bool = Field(default=True, description="Enable/disable audit logging")
    kubeeye_audit_retention_days: int = Field(default=14, description="Number of days to retain audit logs")

    # LDAP configuration
    kubeeye_ldap_enabled: bool = Field(default=False, description="Enable LDAP authentication")
    kubeeye_ldap_server_url: str = Field(default="ldap://localhost:389", description="LDAP server URL")
    kubeeye_ldap_use_ssl: bool = Field(default=False, description="Use SSL for LDAP connection")
    kubeeye_ldap_start_tls: bool = Field(default=False, description="Use StartTLS for LDAP connection")
    kubeeye_ldap_insecure_skip_verify: bool = Field(default=False, description="Skip TLS certificate verification")
    kubeeye_ldap_bind_dn: str = Field(default="", description="DN for binding to LDAP server")
    kubeeye_ldap_bind_password: str = Field(default="", description="Password for LDAP bind")
    kubeeye_ldap_base_dn: str = Field(default="", description="Base DN for user search")
    kubeeye_ldap_group_base_dn: str = Field(default="", description="Base DN for group search")
    kubeeye_ldap_admin_group: str = Field(default="", description="LDAP group for admin role")
    kubeeye_ldap_operator_group: str = Field(default="", description="LDAP group for operator role")
    kubeeye_ldap_user_filter: str = Field(default="(uid={username})", description="LDAP user search filter")
    kubeeye_ldap_type: str = Field(default="openldap", description="LDAP server type: openldap or ad")
    kubeeye_ldap_ad_domain: Optional[str] = Field(default=None, description="Active Directory domain")


# Global settings instance
settings = Settings()
