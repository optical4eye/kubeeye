#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified SSH Service
Centralized service for all SSH operations: connection, testing, validation, and command execution
With integrated connection pooling for performance optimization
"""

import asyncio
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import asyncssh

from core.logging import get_logger
from core.config.settings import settings
from infra.security.command_security import CommandSecurityChecker
from infra.security.interfaces import ISSHService
from infra.dependency_injection.container import injectable

logger = get_logger(__name__)


@dataclass
class ConnectionInfo:
    """Connection information for pool"""

    client: asyncssh.SSHClientConnection
    last_used: float
    created_at: float


# SSH Exceptions (moved from async_ssh_base.py)
class SSHException(Exception):
    """Base SSH exception"""

    pass


class AuthenticationException(SSHException):
    """Authentication failed"""

    pass


class BadHostKeyException(SSHException):
    """Bad host key"""

    pass


def map_asyncssh_exception(e: Exception) -> Exception:
    """
    Map asyncssh exceptions to paramiko-like exceptions for compatibility

    Args:
        e: Original asyncssh exception

    Returns:
        Mapped exception
    """
    if isinstance(e, asyncssh.PermissionDenied):
        return AuthenticationException(str(e))
    elif isinstance(e, asyncssh.DisconnectError):
        return SSHException(f"SSH disconnect: {str(e)}")
    elif isinstance(e, asyncssh.KeyImportError):
        return SSHException(f"Key import error: {str(e)}")
    elif isinstance(e, asyncssh.ChannelOpenError):
        return SSHException(f"Channel error: {str(e)}")
    else:
        return SSHException(str(e))


def load_private_key(key_data: str) -> Optional[asyncssh.SSHKey]:
    """
    Load private key from data supporting multiple types (RSA, Ed25519, ECDSA)

    Args:
        key_data: Private key data as string

    Returns:
        Loaded SSH key or None if failed
    """
    try:
        logger.debug(f"Loading private key, data length: {len(key_data)}")
        key = asyncssh.import_private_key(key_data)
        logger.debug(f"Successfully loaded key from data, algorithm: {key.algorithm}")
        return key
    except asyncssh.KeyImportError as e:
        logger.error(f"Failed to load key from data: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading key from data: {e}")
        return None


@injectable(name="ssh_service")
class SSHService(ISSHService):
    """
    Unified SSH service for all SSH operations
    Provides centralized connection management, testing, validation, and command execution
    With integrated connection pooling for performance optimization
    """

    # Timeout constants
    DEFAULT_CONNECTION_TIMEOUT = 10
    DEFAULT_COMMAND_TIMEOUT = 60
    COMMAND_TIMEOUT_MULTIPLIER = 6  # Command timeout = connection_timeout * 6

    # Pool configuration (now using settings)
    @property
    def DEFAULT_POOL_SIZE(self) -> int:
        return settings.kubeeye_ssh_pool_size

    @property
    def DEFAULT_CONNECTION_TIMEOUT_POOL(self) -> int:
        return settings.kubeeye_ssh_pool_connection_timeout

    @property
    def DEFAULT_KEEPALIVE_INTERVAL(self) -> int:
        return settings.kubeeye_ssh_pool_keepalive_interval

    def __init__(self):
        self.security_checker = CommandSecurityChecker()
        # Connection pool
        self.pools: Dict[str, list] = {}  # node_key -> list of ConnectionInfo
        self._locks: Dict[str, asyncio.Lock] = {}  # node_key -> asyncio.Lock for thread safety
        self._keepalive_task: Optional[asyncio.Task] = None
        self._pool_stats = {
            "total_connections": 0,
            "reused_connections": 0,
            "new_connections": 0,
            "failed_connections": 0,
            "closed_connections": 0,
        }

    def _get_node_key(self, host: str, port: int, username: str) -> str:
        """Generate unique key for node"""
        return f"{host}:{port}:{username}"

    async def _get_connection_from_pool(
        self, host: str, port: int, username: str
    ) -> Optional[asyncssh.SSHClientConnection]:
        """
        Get connection from pool or create new one

        Args:
            host: Target host
            port: SSH port
            username: SSH username

        Returns:
            SSH client or None if failed
        """
        node_key = self._get_node_key(host, port, username)

        # Get or create lock for this node
        if node_key not in self._locks:
            self._locks[node_key] = asyncio.Lock()

        lock = self._locks[node_key]
        async with lock:
            # Clean expired connections
            await self._clean_expired_connections(node_key)

            # Try to get existing connection
            if node_key in self.pools and self.pools[node_key]:
                conn_info = self.pools[node_key].pop()
                if await self._is_connection_alive(conn_info.client):
                    conn_info.last_used = time.time()
                    self._pool_stats["reused_connections"] += 1
                    logger.debug(f"Reusing connection for {node_key}")
                    return conn_info.client
                else:
                    # Connection is dead, close it
                    try:
                        conn_info.client.close()
                        self._pool_stats["closed_connections"] += 1
                    except Exception:
                        pass

        return None

    async def _return_connection_to_pool(
        self, host: str, port: int, username: str, client: asyncssh.SSHClientConnection
    ):
        """
        Return connection to pool

        Args:
            host: Target host
            port: SSH port
            username: SSH username
            client: SSH client to return
        """
        node_key = self._get_node_key(host, port, username)

        # Get or create lock for this node
        if node_key not in self._locks:
            self._locks[node_key] = asyncio.Lock()

        lock = self._locks[node_key]
        async with lock:
            # Clean expired connections
            await self._clean_expired_connections(node_key)

            # Check pool size limit
            if node_key not in self.pools:
                self.pools[node_key] = []

            if len(self.pools[node_key]) < self.DEFAULT_POOL_SIZE:
                conn_info = ConnectionInfo(client=client, last_used=time.time(), created_at=time.time())
                self.pools[node_key].append(conn_info)
                logger.debug(f"Returned connection to pool for {node_key}")
            else:
                # Pool is full, close connection
                try:
                    client.close()
                except Exception:
                    pass
                logger.debug(f"Closed connection (pool full) for {node_key}")

    async def _is_connection_alive(self, client: asyncssh.SSHClientConnection) -> bool:
        """Check if connection is alive"""
        try:
            # Check if connection is closed
            if client.is_closed():
                return False
            # Try to execute a simple command
            result = await client.run("echo 1", timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    async def _clean_expired_connections(self, node_key: str):
        """Clean expired connections for node"""
        if node_key not in self.pools:
            return

        current_time = time.time()
        active_connections = []

        for conn_info in self.pools[node_key]:
            if current_time - conn_info.last_used < self.DEFAULT_CONNECTION_TIMEOUT_POOL:
                active_connections.append(conn_info)
            else:
                # Close expired connection
                try:
                    conn_info.client.close()
                except Exception:
                    pass
                logger.debug(f"Closed expired connection for {node_key}")

        self.pools[node_key] = active_connections

    async def start_keepalive(self):
        """Start keepalive task for all connections"""

        async def keepalive():
            while True:
                await asyncio.sleep(self.DEFAULT_KEEPALIVE_INTERVAL)
                for node_key, connections in list(self.pools.items()):
                    for conn_info in list(connections):
                        if not await self._is_connection_alive(conn_info.client):
                            logger.warning(f"Connection {node_key} is dead, removing from pool")
                            try:
                                conn_info.client.close()
                                self._pool_stats["closed_connections"] += 1
                            except Exception:
                                pass
                            connections.remove(conn_info)

        self._keepalive_task = asyncio.create_task(keepalive())
        logger.info("Started SSH keepalive task")

    async def stop_keepalive(self):
        """Stop keepalive task"""
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
            logger.info("Stopped SSH keepalive task")

    def get_pool_stats(self) -> dict:
        """Get pool statistics"""
        total_pooled = sum(len(conns) for conns in self.pools.values())
        return {
            **self._pool_stats,
            "total_pooled_connections": total_pooled,
            "max_connections": self.DEFAULT_POOL_SIZE,
            "keepalive_interval": self.DEFAULT_KEEPALIVE_INTERVAL,
            "connection_timeout": self.DEFAULT_CONNECTION_TIMEOUT_POOL,
        }

    async def close_all_connections(self):
        """Close all connections in pool"""
        # Close all connections
        for node_key, connections in self.pools.items():
            for conn_info in connections:
                try:
                    conn_info.client.close()
                except Exception:
                    pass
        self.pools.clear()
        # Clear all locks
        self._locks.clear()
        # Stop keepalive task
        await self.stop_keepalive()

        logger.info("Closed all connections in pool")

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
        Create SSH connection (with optional connection pooling)

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
        try:
            # Try to get connection from pool first
            if use_pool:
                client = await self._get_connection_from_pool(host, port, username)
                if client:
                    logger.debug(f"Using pooled connection for {host}:{port}")
                    return client

            # Create new connection
            # Use provided timeout or default from settings
            if timeout is None:
                timeout = settings.kubeeye_ssh_connection_timeout

            logger.debug(f"Creating new SSH connection to {host}:{port} with auth_type: {auth_type}")

            if auth_type == "password":
                logger.debug("Using password authentication")
                conn = await asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=None,  # Disable host key checking
                    connect_timeout=timeout,
                )
            elif auth_type == "key":
                logger.debug("Using key authentication")
                if not key_data:
                    raise ValueError("key_data required for key authentication")

                logger.debug(f"Key data length: {len(key_data)}")
                key = load_private_key(key_data)
                if not key:
                    raise SSHException("Failed to load key from provided data")

                conn = await asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    client_keys=[key],
                    known_hosts=None,  # Disable host key checking
                    connect_timeout=timeout,
                )
            else:
                raise ValueError(f"Unsupported auth_type: {auth_type}")

            self._pool_stats["new_connections"] += 1
            self._pool_stats["total_connections"] += 1
            logger.debug(f"SSH connection to {host}:{port} established successfully")
            return conn

        except Exception as e:
            logger.error(f"Failed to create SSH connection to {host}:{port}: {e}")
            self._pool_stats["failed_connections"] += 1
            raise map_asyncssh_exception(e)

    async def test_connection(self, node_info: Dict) -> Tuple[bool, str]:
        """
        Test SSH connection to node

        Args:
            node_info: Node configuration with ip, port, username, auth_type, password/ssh_key

        Returns:
            Tuple (success, message)
        """
        try:
            logger.debug(
                f"Testing connection to node: {node_info.get('ip')}:{node_info.get('port')} "
                f"user: {node_info.get('username')} auth: {node_info.get('auth_type')}"
            )

            # Prepare connection parameters
            host = node_info["ip"]
            port = int(node_info.get("port", 22))
            username = node_info["username"]
            auth_type = node_info["auth_type"]
            password = node_info.get("password")
            ssh_key = node_info.get("ssh_key")

            # Use shorter timeout for testing (half of default)
            test_timeout = int(settings.kubeeye_ssh_connection_timeout * 0.5)

            # Try to connect (don't use pool for testing)
            client = await self.connect(
                host=host,
                port=port,
                username=username,
                auth_type=auth_type,
                password=password,
                key_data=ssh_key,
                timeout=test_timeout,
                use_pool=False,  # Don't use pool for testing
            )

            if client:
                # Close connection after successful test
                try:
                    client.close()
                except Exception as e:
                    logger.warning(f"Error closing test connection: {e}")

                logger.debug(f"Connection test successful for {host}")
                return True, f"Connection to {host}:{port} successful"
            else:
                return False, f"Failed to establish connection to {host}:{port}"

        except AuthenticationException:
            error_msg = "Authentication failed (incorrect username, password or SSH key)"
            logger.error(f"Node {node_info.get('ip')}: {error_msg}")
            return False, error_msg
        except SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            logger.error(f"Node {node_info.get('ip')}: {error_msg}")
            return False, error_msg
        except asyncio.TimeoutError:
            error_msg = "Connection timeout"
            logger.error(f"Node {node_info.get('ip')}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(f"Node {node_info.get('ip')}: {error_msg}")
            return False, error_msg

    async def validate_key(self, ssh_key: str) -> Tuple[bool, str]:
        """
        Validate SSH private key

        Args:
            ssh_key: SSH private key data as string

        Returns:
            Tuple (success, message)
        """
        try:
            key = load_private_key(ssh_key)
            if key:
                key_type = key.algorithm
                return True, f"SSH key format is correct ({key_type})"
            else:
                return False, "Unsupported key format or failed to load"
        except Exception as e:
            return False, f"Key validation error: {str(e)}"

    async def execute_command(
        self,
        node_info: Dict,
        command: str,
        timeout: Optional[int] = None,
        enable_security_check: bool = True,
    ) -> Tuple[str, str]:
        """
        Execute command on node (with connection pooling)

        Args:
            node_info: Node configuration
            command: Command to execute
            timeout: Command timeout in seconds (uses default if None)
            enable_security_check: Enable command security check

        Returns:
            Tuple (stdout, stderr)
        """
        node_name = node_info.get("name", node_info["ip"])
        host = node_info["ip"]
        port = int(node_info["port"])
        username = node_info["username"]

        # Security check
        if enable_security_check and command:
            is_safe, risk_level, risk_desc = self.security_checker.check_command_security(command)
            if not is_safe:
                error_msg = f"Command blocked by security: {risk_desc}"
                logger.error(f"Node {node_name}: {error_msg}")
                return "", error_msg

        client = None
        try:
            # Get connection from pool
            client = await self.connect(
                host=host,
                port=port,
                username=username,
                auth_type=node_info["auth_type"],
                password=node_info.get("password"),
                key_data=node_info.get("ssh_key"),
                use_pool=True,
            )

            if not client:
                error_msg = "Failed to get SSH connection"
                logger.error(f"Node {node_name}: {error_msg}")
                return "", error_msg

            try:
                # Calculate timeout
                if timeout is None:
                    timeout = settings.kubeeye_ssh_connection_timeout * self.COMMAND_TIMEOUT_MULTIPLIER

                # Execute command
                result = await asyncio.wait_for(client.run(command, timeout=timeout), timeout=timeout)

                # Get output
                stdout_data = result.stdout
                stderr_data = result.stderr
                exit_status = result.returncode

                if exit_status == 0:
                    logger.info(f"Command executed successfully on node {node_name}")
                    # Return connection to pool on success
                    await self._return_connection_to_pool(host, port, username, client)
                    return stdout_data, ""
                else:
                    logger.warning(f"Command failed on node {node_name} with exit code {exit_status}")
                    # Return connection to pool even on failure (connection is still valid)
                    await self._return_connection_to_pool(host, port, username, client)
                    return stdout_data, stderr_data

            except Exception as e:
                # On error, close connection instead of returning to pool
                try:
                    client.close()
                except Exception:
                    pass
                raise

        except asyncio.TimeoutError:
            error_msg = f"Command execution timeout for node {node_name}"
            logger.error(error_msg)
            return "", error_msg
        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            logger.error(f"Node {node_name}: {error_msg}")
            return "", error_msg

    def is_ssh_connection_error(self, error_msg: str) -> bool:
        """
        Check if error is related to SSH connection

        Args:
            error_msg: Error message to check

        Returns:
            True if SSH-related error, False otherwise
        """
        ssh_keywords = [
            "connection",
            "connect",
            "ssh",
            "timeout",
            "refused",
            "authentication",
            "auth",
            "handshake",
            "socket",
            "network",
            "unreachable",
            "closed",
            "reset",
        ]
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in ssh_keywords)
