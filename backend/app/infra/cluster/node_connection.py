#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node connection management module, used for connecting to cluster nodes via SSH and executing commands
"""

import asyncio
import socket
from typing import Dict, Tuple
import os
from infra.dependency_injection.container import get_service
from core.logging import get_logger
from core.config.settings import settings
from infra.security.ssh_service import (
    AuthenticationException,
    SSHException,
)

logger = get_logger(__name__)


class AsyncNodeConnection:
    """Asynchronous SSH connection class to node using SSHService"""

    def __init__(self, node_info: Dict):
        """
        Node connection initialization

        Args:
            node_info: dictionary with node information, contains:
                - ip: node IP address
                - port: SSH port
                - username: SSH username
                - auth_type: authentication type ('password' or 'key')
                - password: password (if auth_type is 'password')
                - ssh_key: SSH key content (if auth_type is 'key')
        """
        self.node_info = node_info
        self.client = None
        self.connected = False

    async def connect(self) -> Tuple[bool, str]:
        """
        Connect to node asynchronously using SSHService

        Returns:
            On successful connection returns (True, ""), on error — (False, error_message)
        """
        from infra.dependency_injection.container import get_service

        try:
            # Log connection information
            logger.info(
                f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}"
            )

            # Use SSHService for connection (use pool for better resource management)
            ssh_service = await get_service("ssh_service")
            self.client = await ssh_service.connect(
                host=self.node_info["ip"],
                port=int(self.node_info["port"]),
                username=self.node_info["username"],
                auth_type=self.node_info["auth_type"],
                password=self.node_info.get("password"),
                key_data=self.node_info.get("ssh_key"),
                timeout=settings.kubeeye_ssh_connection_timeout,
                use_pool=True,  # Use connection pool for better resource management
            )

            self.connected = True
            return True, ""
        except AuthenticationException as e:
            error_msg = "Authentication error (incorrect username, password or SSH key)"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except asyncio.TimeoutError:
            error_msg = "Connection timeout"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg

    async def close_async(self) -> None:
        """Close connection - return to pool if using pool, otherwise close"""
        if not self.connected or not self.client:
            return

        try:
            # Get SSH service to return connection to pool
            ssh_service = await get_service("ssh_service")
            await ssh_service._return_connection_to_pool(
                host=self.node_info["ip"],
                port=int(self.node_info["port"]),
                username=self.node_info["username"],
                client=self.client,
            )
            logger.debug(f"Connection to {self.node_info['ip']} returned to pool")
        except Exception as e:
            # Fallback: close connection if return to pool fails
            try:
                if self.client and not self.client.is_closed():
                    self.client.close()
                    logger.warning(f"Error returning connection to pool, closed directly: {e}")
            except Exception as close_error:
                logger.warning(f"Error closing connection: {close_error}")
        finally:
            self.client = None
            self.connected = False

    def close(self) -> None:
        """Close connection (synchronous wrapper that calls async close)"""
        if not self.connected or not self.client:
            return

        try:
            # Handle both async and sync contexts properly
            try:
                loop = asyncio.get_running_loop()
                # If there's a running loop, schedule close as a task and wait briefly
                if loop.is_running():
                    # Create task and run it to completion
                    task = asyncio.run_coroutine_threadsafe(self.close_async(), loop)
                    # Wait for task with timeout to avoid hanging
                    task.result(timeout=10)
                else:
                    loop.run_until_complete(self.close_async())
            except RuntimeError:
                # No running loop, use asyncio.run
                asyncio.run(self.close_async())
        except Exception as e:
            logger.warning(f"Error closing connection: {str(e)}")


class NodeConnection:
    """Synchronous SSH connection class to node using SSHService"""

    def __init__(self, node_info: Dict):
        """
        Node connection initialization

        Args:
            node_info: dictionary with node information, contains:
                - ip: node IP address
                - port: SSH port
                - username: SSH username
                - auth_type: authentication type ('password' or 'key')
                - password: password (if auth_type is 'password')
                - ssh_key: SSH key content (if auth_type is 'key')
        """
        self.node_info = node_info
        self.client = None
        self.connected = False

    def __enter__(self):
        """Context manager entry, connect to node and return self"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit, close connection"""
        self.close()
        return False  # Pass exception further

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to node using SSHService (synchronous wrapper)

        Returns:
            On successful connection returns (True, ""), on error — (False, error_message)
        """
        try:
            # Log connection information
            logger.info(
                f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}"
            )

            # Get configurable SSH timeout
            ssh_timeout = settings.kubeeye_ssh_connection_timeout

            async def _connect_async():
                ssh_service = await get_service("ssh_service")
                return await ssh_service.connect(
                    host=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    auth_type=self.node_info["auth_type"],
                    password=self.node_info.get("password"),
                    key_data=self.node_info.get("ssh_key"),
                    timeout=ssh_timeout,
                    use_pool=True,  # Use connection pool for better resource management
                )

            # Handle both async and sync contexts properly
            try:
                loop = asyncio.get_running_loop()
                # If there's already a running loop, schedule task properly
                if loop.is_running():
                    # Use threadsafe approach to avoid blocking
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(asyncio.run, _connect_async())
                        self.client = future.result(timeout=ssh_timeout + 10)
                else:
                    self.client = loop.run_until_complete(_connect_async())
            except RuntimeError:
                # No running loop, we can use asyncio.run
                self.client = asyncio.run(_connect_async())

            self.connected = True
            return True, ""
        except AuthenticationException:
            error_msg = "Authentication failed (incorrect username, password or SSH key)"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except asyncio.TimeoutError:
            error_msg = "Connection timeout"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg

    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute command on node using connection pool

        Args:
            command: command to execute

        Returns:
            Tuple (success, stdout, stderr)
        """
        try:
            # Use command timeout from settings directly
            command_timeout = settings.kubeeye_ssh_command_timeout

            # Handle both async and sync contexts properly
            try:
                loop = asyncio.get_running_loop()
                # If there's already a running loop, schedule task properly
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self._execute_command_sync, command)
                        return future.result(timeout=command_timeout + 10)
                else:
                    return loop.run_until_complete(self._execute_command_async(command))
            except RuntimeError:
                # No running loop, we can use asyncio.run
                return asyncio.run(self._execute_command_async(command))

        except Exception as e:
            return False, "", f"Command execution error: {str(e)}"

    async def _execute_command_async(self, command: str) -> Tuple[bool, str, str]:
        """Execute command asynchronously using SSHService with connection pooling"""
        # Get SSH service
        ssh_service = await get_service("ssh_service")

        # Use command timeout from settings directly
        command_timeout = settings.kubeeye_ssh_command_timeout

        # Use SSHService to execute command (it handles connection pooling internally)
        # execute_command expects node_info dict and returns (stdout, stderr)
        stdout, stderr = await ssh_service.execute_command(
            node_info=self.node_info,
            command=command,
            timeout=command_timeout,
            enable_security_check=False,  # Allow all commands for node inspection
        )

        # Determine success: no stderr means success
        success = not bool(stderr)
        return success, stdout, stderr

    def _execute_command_sync(self, command: str) -> Tuple[bool, str, str]:
        """Execute command synchronously using new event loop"""
        return asyncio.run(self._execute_command_async(command))

    def close(self) -> None:
        """Close connection - return to pool or close it"""
        if not self.connected or not self.client:
            return

        try:
            # Handle both async and sync contexts properly
            try:
                loop = asyncio.get_running_loop()
                # If there's a running loop, use threadsafe execution
                if loop.is_running():
                    task = asyncio.run_coroutine_threadsafe(self._close_async(), loop)
                    task.result(timeout=10)
                else:
                    loop.run_until_complete(self._close_async())
            except RuntimeError:
                # No running loop, use asyncio.run
                asyncio.run(self._close_async())
        except Exception as e:
            logger.warning(f"Error closing connection: {str(e)}")
        finally:
            # Reset state regardless of success/failure
            self.client = None
            self.connected = False

    async def _close_async(self) -> None:
        """Return connection to pool or close it"""
        if not self.client:
            return

        try:
            # Get SSH service to return connection to pool
            ssh_service = await get_service("ssh_service")
            await ssh_service._return_connection_to_pool(
                host=self.node_info["ip"],
                port=int(self.node_info["port"]),
                username=self.node_info["username"],
                client=self.client,
            )
            logger.debug(f"Connection to {self.node_info['ip']} returned to pool")
        except Exception as e:
            # Fallback: close connection if return to pool fails
            try:
                if self.client and not self.client.is_closed():
                    self.client.close()
                    logger.warning(f"Error returning connection to pool, closed directly: {e}")
            except Exception as close_error:
                logger.warning(f"Error closing connection: {close_error}")


async def async_test_node_connection(node_info: Dict) -> Tuple[bool, str]:
    """
    Test node connection asynchronously using SSHService

    Args:
        node_info: node configuration information

    Returns:
        Tuple (success, message)
    """
    from infra.dependency_injection.container import get_service

    logger.debug(
        f"Testing connection to node: {node_info.get('ip')}:{node_info.get('port')} user: {node_info.get('username')} auth: {node_info.get('auth_type')}"
    )

    # Use SSHService for connection testing
    ssh_service = await get_service("ssh_service")
    success, message = await ssh_service.test_connection(node_info)

    if success:
        logger.debug(f"Connection test successful for {node_info['ip']}")
    else:
        logger.error(f"Connection test failed for {node_info['ip']}: {message}")
        message = f"Failed to connect to {node_info['ip']}: {message}"

    return success, message


# Note: SSH key validation is now handled by SSHService.validate_key()
# Use: await get_service("ssh_service").validate_key(ssh_key)
