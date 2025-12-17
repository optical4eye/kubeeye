#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified KubeEye security configuration - reading only basic configuration parameters
"""

import yaml
import logging
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleSecurityConfig:
    """Simplified security configuration class - processing only configurable parameters"""

    def __init__(self, config_file: str = "config/security.yaml"):
        """
        Initialize simplified security configuration

        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration file"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Configuration file does not exist: {config_path}, using default configuration")
                config = {}

            # Set default values
            return {
                "max_command_length": config.get("max_command_length", 1000),
                "command_timeout": config.get("command_timeout", 30),
                "audit_log_path": config.get("audit_log_path", "data/logs/security_audit.log"),
                "audit_retention_days": config.get("audit_retention_days", 90),
                "enable_detailed_logging": config.get("enable_detailed_logging", True),
                "allowed_ports": config.get("allowed_ports", [22, 80, 443, 6443, 8080, 9090, 10250]),
                "blocked_ips": config.get("blocked_ips", []),
                "require_key_auth": config.get("require_key_auth", False),
            }
        except Exception as e:
            logger.error(f"Failed to load security configuration: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "max_command_length": 1000,
            "command_timeout": 30,
            "audit_log_path": "data/logs/security_audit.log",
            "audit_retention_days": 90,
            "enable_detailed_logging": True,
            "allowed_ports": [22, 80, 443, 6443, 8080, 9090, 10250],
            "blocked_ips": [],
            "require_key_auth": False,
        }

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    @property
    def max_command_length(self) -> int:
        """Maximum command length"""
        return self.config["max_command_length"]

    @property
    def command_timeout(self) -> int:
        """Command timeout"""
        return self.config["command_timeout"]

    @property
    def audit_log_path(self) -> str:
        """Path to audit log"""
        return self.config["audit_log_path"]

    @property
    def audit_retention_days(self) -> int:
        """Number of days to retain audit log"""
        return self.config["audit_retention_days"]

    @property
    def enable_detailed_logging(self) -> bool:
        """Whether to enable detailed logging"""
        return self.config["enable_detailed_logging"]

    @property
    def allowed_ports(self) -> List[int]:
        """List of allowed ports"""
        return self.config["allowed_ports"]

    @property
    def blocked_ips(self) -> List[str]:
        """List of blocked IPs"""
        return self.config["blocked_ips"]

    @property
    def require_key_auth(self) -> bool:
        """Whether to require key authentication"""
        return self.config["require_key_auth"]


# Global configuration instance
_global_security_config = None


def get_security_config() -> SimpleSecurityConfig:
    """Get global security configuration instance"""
    global _global_security_config
    if _global_security_config is None:
        _global_security_config = SimpleSecurityConfig()
    return _global_security_config
