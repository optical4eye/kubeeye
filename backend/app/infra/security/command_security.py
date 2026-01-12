#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command security checker - prevents execution of dangerous commands
"""

import re
from typing import Tuple
from enum import Enum
from core.logging import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """Risk level"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CommandSecurityChecker:
    """
    Command security checker - whitelist-only mode: only explicitly allowed commands

    Important security principles:
    - Inspection tool can only observe, not modify
    - Only commands in the whitelist are allowed, everything else is prohibited
    - No exceptions or risk analysis - strict whitelist enforcement
    """

    def __init__(self):
        """
        Initialize command security checker

        Note: This class uses whitelist-only mode: only explicitly allowed commands
        """
        self._init_security_rules()

    def _init_security_rules(self):
        """Initialize security rules - whitelist-only mode: only explicitly allowed commands"""

        # Safe read-only commands whitelist (explicitly allowed commands)
        self.safe_readonly_patterns = [
            # System information viewing
            r"^\s*cat\s+(/proc/|/sys/|/etc/hostname|/etc/os-release)",  # System file viewing
            r"^\s*less\s+(/var/log/|/proc/|/sys/)",  # Log and system information viewing
            r"^\s*more\s+(/var/log/|/proc/|/sys/)",  # File content viewing
            r"^\s*head\s+(-\d+\s+)?(/var/log/|/proc/|/sys/|/etc/)",  # File beginning viewing
            r"^\s*tail\s+(-\d+\s+)?(/var/log/|/proc/|/sys/)",  # File end viewing
            r"^\s*(grep|awk|sed)\s+.*(/var/log/|/proc/|/sys/)",  # Text processing read-only
            # System state viewing
            r"^\s*(uname|hostname|whoami|id|date|uptime)\s*",  # Basic system information
            r"^\s*(w|who|last|lastlog)\s*",  # User information
            r"^\s*(ps|top|htop|pstree|pgrep)\s+",  # Process information
            r"^\s*(free|vmstat|iostat|sar)\s+",  # System resources
            r"^\s*(df|du|lsblk|lsof|fuser)\s+",  # Disk and file information
            # Network state viewing
            r"^\s*(netstat|ss)\s+",  # Network connection status
            r"^\s*lsof\s+-i",  # Open network files
            r"^\s*iptables\s+-L",  # Firewall rule viewing
            r"^\s*ip\s+(addr|link|route)\s*(show|list)?",  # IP configuration viewing
            r"^\s*ifconfig\s*$",  # Network interface viewing (no parameters)
            # Filesystem viewing
            r"^\s*ls\s+",  # File listing
            r"^\s*find\s+(/[\w/.-]*\s+)?-type\s+f\s+-name\s+[\w*.-]+\s*$",  # File search (safe, no exec/delete)
            r"^\s*locate\s+",  # File location
            r"^\s*which\s+",  # Command path search
            r"^\s*whereis\s+",  # Command-related file search
            # Kubernetes read-only commands
            r"^\s*kubectl\s+(get|describe|logs|explain|api-resources|api-versions|version|cluster-info)\s+",  # K8s viewing commands
            r"^\s*docker\s+(ps|images|version|info|logs)\s+",  # Docker viewing commands
            # Log viewing
            r"^\s*journalctl\s+(-u\s+\w+\s+)?(-f\s+)?(-n\s+\d+\s+)?(-S\s+.*)?$",  # systemd log viewing
            r"^\s*dmesg\s*$",  # Kernel messages
            # Other read-only commands
            r"^\s*history\s*$",  # Command history
            r"^\s*env\s*$",  # Environment variables
            r"^\s*printenv\s*",  # Environment variable printing
            r"^\s*echo\s+\$\w+",  # Variable value printing
            r"^\s*printf\s+",  # Formatted output
            r"^\s*sestatus\s*$",  # Selinux status
            # Additional safe commands
            r"^\s*(awk|wc|tail|head|xargs|grep|sed)\b.*",
            r"^\s*systemctl\s+(is-active|status|show)\b.*",
            r"^\s*service\s+\w+\s+(status)\b.*",
            r"^\s*echo\b.*",  # Allow echo any content
        ]

        # Compile regex patterns for performance
        self.compiled_safe = [re.compile(p, re.IGNORECASE) for p in self.safe_readonly_patterns]

    def check_command_security(self, command: str) -> Tuple[bool, RiskLevel, str]:
        """
        Command security check - whitelist-only mode: only explicitly allowed commands

        Args:
            command: Command to check

        Returns:
            (is safe, risk level, risk description)
        """
        command = command.strip()

        logger.info(f" Security check begins - Command: {command[:100]}{'...' if len(command) > 100 else ''}")

        if not command:
            logger.info("Empty command, considered safe")
            return True, RiskLevel.LOW, "Empty command"

        # Check if command is explicitly safe read-only (whitelist)
        if self._is_safe_readonly_command(command):
            logger.info("Command passed whitelist check")
            return True, RiskLevel.LOW, "Safe read-only command"

        # Whitelist-only mode: reject all non-explicitly allowed commands
        logger.warning(f" Whitelist-only mode: Command not in safe whitelist: {command[:100]}...")
        return (
            False,
            RiskLevel.HIGH,
            "Command not in safe whitelist, inspection tool allows only read-only viewing commands",
        )

    def _is_safe_readonly_command(self, command: str) -> bool:
        """Check if command is safe read-only, supports sudo prefix, pipe/logical combinations, redirection removal"""
        cmd = command.strip()
        sep_pattern = r"(\|\||&&)"

        logger.info(f" Whitelist check - Original command: {cmd}")

        def strip_redirect(s):
            s = re.split(r">+.*", s)[0].strip()
            return s

        sub_cmds = re.split(sep_pattern, cmd)
        logger.info(f"Split subcommands: {sub_cmds}")

        for i, sub in enumerate(sub_cmds):
            sub = sub.strip()
            if not sub or sub in {"|", "||", "&&"}:
                logger.debug(f"Subcommand {i}: '{sub}' (separator, skip)")
                continue

            if sub.startswith("sudo "):
                sub = sub[5:].lstrip()
                logger.info(f"Subcommand {i}: After sudo prefix removal: '{sub}'")

            sub = strip_redirect(sub)
            logger.info(f"Subcommand {i}: After redirection removal: '{sub}'")

            matched = False
            for compiled in self.compiled_safe:
                if compiled.match(sub):
                    logger.info(f"Subcommand {i} matches whitelist pattern")
                    matched = True
                    break

            if not matched:
                logger.warning(f"Subcommand {i} does not match any whitelist pattern: '{sub}'")
                return False

        logger.info("All subcommands passed whitelist check")
        return True
