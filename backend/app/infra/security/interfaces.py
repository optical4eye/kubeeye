#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Service Interface for Dependency Injection
"""

from typing import Protocol, Tuple, Optional, Dict
import asyncssh


class ISSHService(Protocol):
    """
    Interface for SSH service
    Provides unified SSH operations for connection, testing, validation, and command execution
    """

    async def connect(
        self,
        host: str,
        port: int,
        username: str,
        auth_type: str,
        password: Optional[str] = None,
        key_data: Optional[str] = None,
        timeout: Optional[int] = None,
        use_pool: bool = True,
    ) -> Optional[asyncssh.SSHClientConnection]:
        """
        Create SSH connection

        Args:
            host: Target host
            port: SSH port
            username: SSH username
            auth_type: 'password' or 'key'
            password: Password for password auth
            key_data: Private key data as string for key auth
            timeout: Connection timeout (uses default if None)
            use_pool: Use connection pool (default: True)

        Returns:
            SSH connection or None if failed
        """
        ...

    async def test_connection(self, node_info: Dict) -> Tuple[bool, str]:
        """
        Test SSH connection to node

        Args:
            node_info: Node configuration with ip, port, username, auth_type, password/ssh_key

        Returns:
            Tuple (success, message)
        """
        ...

    async def validate_key(self, ssh_key: str) -> Tuple[bool, str]:
        """
        Validate SSH private key

        Args:
            ssh_key: SSH private key data as string

        Returns:
            Tuple (success, message)
        """
        ...

    async def execute_command(
        self,
        node_info: Dict,
        command: str,
        timeout: Optional[int] = None,
        enable_security_check: bool = True,
    ) -> Tuple[str, str]:
        """
        Execute command on node

        Args:
            node_info: Node configuration
            command: Command to execute
            timeout: Command timeout in seconds (uses default if None)
            enable_security_check: Enable command security check

        Returns:
            Tuple (stdout, stderr)
        """
        ...

    def is_ssh_connection_error(self, error_msg: str) -> bool:
        """
        Check if error is related to SSH connection

        Args:
            error_msg: Error message to check

        Returns:
            True if SSH-related error, False otherwise
        """
        ...
