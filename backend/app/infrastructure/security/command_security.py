#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command security checker - prevents execution of dangerous commands
"""

import re
import logging
from typing import Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CommandSecurityChecker:
    """
    Command security checker - forced whitelist mode, allows only read operations

    Important security principles:
    - Inspection tool can only observe, not modify
    - All high-risk commands are strictly prohibited, no exceptions
    - Does not provide any options to reduce security level
    """

    def __init__(self):
        """
        Initialize command security checker

        Note: This class forcibly uses the strictest security mode, accepts no parameters
        """
        # Security principles of inspection tool: read-only, observation only, no modification
        self.strict_mode = True  # Forced strict mode, cannot be changed
        self.whitelist_only = True  # Forced whitelist mode, cannot be changed
        self._init_security_rules()

    def _init_security_rules(self):
        """Initialize security rules - focus on whitelist of read-only commands"""

        # Absolutely prohibited commands (CRITICAL level) - any modification operations
        self.critical_commands = [
            # File and directory deletion/movement/modification
            r"\brm\s+",  # Any rm command
            r"\bmv\s+",  # Any mv command
            r"\bcp\s+.*>\s*/",  # Copying with overwriting system files
            r"\bmkdir\s+",  # Directory creation
            r"\brmdir\s+",  # Directory deletion
            r"\btouch\s+",  # File creation/modification timestamp
            # Permission and ownership changes
            r"\bchmod\s+",  # Any permission change
            r"\bchown\s+",  # Ownership change
            r"\bchgrp\s+",  # Group change
            # System service management (only modification operations prohibited, read-only like is-active/status/show allowed)
            r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask|kill|reset-failed)\b",  # Service management
            r"\bservice\s+\w+\s+(start|stop|restart|reload)\b",  # service command
            r"\binit\s+[0-6]",  # System runlevel change
            r"\bshutdown\s+",  # System shutdown
            r"\breboot\s*",  # System reboot
            r"\bhalt\s*",  # System halt
            # Process management
            r"\bkill\s+(-[0-9]+|\w+)",  # Process killing
            r"\bkillall\s+",  # Mass process killing
            r"\bpkill\s+",  # Process killing by pattern
            # Dangerous system commands
            r"\bdd\s+.*of=",  # dd write operation
            r"\bmkfs\.",  # Filesystem formatting
            r"\bmount\s+",  # Mount operation
            r"\bumount\s+",  # Unmount operation
            r"\bfsck\s+",  # Filesystem check and repair
            # Package management
            r"\bapt\s+(install|remove|purge|upgrade)",  # Debian package management
            r"\bapt-get\s+(install|remove|purge|upgrade)",  # apt-get operations
            r"\byum\s+(install|remove|erase|update)",  # RedHat package management
            r"\bdnf\s+(install|remove|erase|update)",  # Fedora package management
            r"\bpip\s+install",  # Python package installation
            r"\bnpm\s+install",  # Node.js package installation
            # Network configuration changes
            r"\bifconfig\s+\w+\s+(up|down)",  # Network interface enable/disable
            r"\bip\s+(addr|link|route)\s+(add|del|set)",  # IP configuration changes
            r"\biptables\s+(-A|-D|-I|-R|-F|-X)",  # Firewall rule changes
            r"\bnetplan\s+apply",  # Network configuration application
            # Scheduled task management
            r"\bcrontab\s+(-e|-r)",  # Cron editing/deletion
            r"\bat\s+",  # Scheduled task
            # File redirection and pipes (may modify files)
            r">\s*[^/]*/",  # Redirection to file
            r">>\s*[^/]*/",  # Append redirection to file
            # Remote execution and download
            r"(wget|curl).*\|\s*(sh|bash|python|perl)",  # Download and execute
            r"(wget|curl).*\|.*sh",  # Download and execute (simplified version)
            r"\bscp\s+.*:",  # Remote copying
            r"\brsync\s+.*:",  # Remote synchronization
            # Compilation and building
            r"\bmake\s+(install|clean)",  # Compilation and installation
            r"\b\./configure\s+",  # Configuration script
            # Kernel and system parameter changes
            r"\bsysctl\s+-w",  # Kernel parameter changes
            r"\becho\s+.*>\s*/proc/",  # proc parameter changes
            r"\bmodprobe\s+",  # Kernel module loading
            r"\brmmod\s+",  # Kernel module unloading
        ]

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
            r"^\s*find\s+.*-type\s+f.*-name",  # File search
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
        ]
        self.safe_readonly_patterns.extend(
            [
                r"^\s*(awk|wc|tail|head|xargs|grep|sed)\b.*",
                r"^\s*systemctl\s+(is-active|status|show)\b.*",
                r"^\s*service\s+\w+\s+(status)\b.*",
                r"^\s*echo\b.*",  # Allow echo any content
            ]
        )

    def check_command_security(self, command: str) -> Tuple[bool, RiskLevel, str]:
        """
        Command security check - whitelist priority mode

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

        # Step one: Check if command is explicitly safe read-only (whitelist)
        if self._is_safe_readonly_command(command):
            logger.info("Command passed whitelist check")
            return True, RiskLevel.LOW, "Safe read-only command"

        # Step two: Check if command contains absolutely prohibited operations (blacklist)
        if self._contains_critical_operations(command):
            risk_level, risk_desc = self._analyze_command_risk(command)
            logger.error(f"Prohibited modification operation detected: {command[:100]}... Risk: {risk_desc}")
            return False, risk_level, risk_desc

        # Step three: If whitelist-only mode is enabled, reject all non-explicitly allowed commands
        if self.whitelist_only:
            logger.warning(f" Whitelist-only mode: Command not in safe whitelist: {command[:100]}...")
            return (
                False,
                RiskLevel.HIGH,
                "Command not in safe whitelist, inspection tool allows only read-only viewing commands",
            )

        # Step four: Traditional risk analysis (for compatibility mode)
        risk_level, risk_desc = self._analyze_command_risk(command)

        if risk_level == RiskLevel.CRITICAL:
            logger.error(f"Critical risk command detected: {command[:100]}... Risk: {risk_desc}")
            return False, risk_level, risk_desc

        if self.strict_mode and risk_level == RiskLevel.HIGH:
            logger.warning(f"High risk command rejected in strict mode: {command[:100]}... Risk: {risk_desc}")
            return False, risk_level, risk_desc

        if risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
            logger.warning(
                f"Risky command detected: {command[:100]}... Risk level: {risk_level.value}, Description: {risk_desc}"
            )
            return not self.strict_mode, risk_level, risk_desc

        return True, RiskLevel.LOW, "Command passed security check"

    def _contains_critical_operations(self, command: str) -> bool:
        """Check if command contains absolutely prohibited modification operations (split each subcommand for judgment, avoid misjudging read-only combinations)"""
        cmd = command.strip()
        sep_pattern = r"(\|\||&&)"

        def strip_redirect(s):
            s = re.split(r">+.*", s)[0].strip()
            return s

        sub_cmds = re.split(sep_pattern, cmd)
        for sub in sub_cmds:
            sub = sub.strip()
            if not sub or sub in {"|", "||", "&&"}:
                continue
            if sub.startswith("sudo "):
                sub = sub[5:].lstrip()
            sub = strip_redirect(sub)
            for pattern in self.critical_commands:
                if re.search(pattern, sub, re.IGNORECASE):
                    return True
        return False

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
            for pattern in self.safe_readonly_patterns:
                if re.match(pattern, sub, re.IGNORECASE):
                    logger.info(f"Subcommand {i} matches whitelist pattern: {pattern}")
                    matched = True
                    break

            if not matched:
                logger.warning(f"Subcommand {i} does not match any whitelist pattern: '{sub}'")
                return False

        logger.info("All subcommands passed whitelist check")
        return True

    def _analyze_command_risk(self, command: str) -> Tuple[RiskLevel, str]:
        """
        Command risk analysis - identification of risky patterns and levels in command

        Args:
            command: Command to analyze

        Returns:
            (risk level, risk description)
        """
        command = command.strip()

        if not command:
            return RiskLevel.LOW, "Empty command"

        risk_level = RiskLevel.LOW
        risk_desc = "Low risk command"

        # Check risk of each subcommand
        sep_pattern = r"(\|\||&&)"
        sub_cmds = re.split(sep_pattern, command)
        for sub in sub_cmds:
            sub = sub.strip()
            if not sub or sub in {"|", "||", "&&"}:
                continue
            if sub.startswith("sudo "):
                sub = sub[5:].lstrip()
            sub_risk_level, sub_risk_desc = self._analyze_single_command_risk(sub)

            # Merge risk levels
            if sub_risk_level.value > risk_level.value:
                risk_level = sub_risk_level
                risk_desc = sub_risk_desc

        return risk_level, risk_desc

    def _analyze_single_command_risk(self, command: str) -> Tuple[RiskLevel, str]:
        """
        Single command risk analysis - identification of risky patterns and levels in single command

        Args:
            command: Command to analyze

        Returns:
            (risk level, risk description)
        """
        command = command.strip()

        if not command:
            return RiskLevel.LOW, "Empty command"

        # Check if command is absolutely prohibited
        for pattern in self.critical_commands:
            if re.search(pattern, command, re.IGNORECASE):
                return (
                    RiskLevel.CRITICAL,
                    "Contains absolutely prohibited modification operations",
                )

        # Check if command is high risk
        high_risk_patterns = [
            r"\b(dd|mkfs|mount|umount|chmod|chown|chgrp|systemctl|service|kill|killall|pkill|reboot|shutdown|halt|apt-get|yum|dnf|pip|npm)\b",
            r"\b(find|locate|grep|awk|sed|xargs|wc|sort|uniq|tee|cut|tr|head|tail)\s+.*[|&]",  # Pipe/logical combinations
        ]
        for pattern in high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.HIGH, "Contains high-risk commands or operations"

        # Check if command is medium risk
        medium_risk_patterns = [
            r"\b(less|more|cat|echo|printf|env|printenv|history|journalctl|dmesg)\b",  # Only for some parameters
            r"\b(systemctl|service)\s+\w+\s+(status|show|is-active)\b",  # Read-only state viewing
        ]
        for pattern in medium_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return RiskLevel.MEDIUM, "Contains medium-risk commands or operations"

        return RiskLevel.LOW, "Low risk command"
