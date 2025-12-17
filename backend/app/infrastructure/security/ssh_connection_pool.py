#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH connection pool for reusing connections to nodes
"""

import asyncio
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
import paramiko

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Connection information"""

    client: paramiko.SSHClient
    last_used: float
    created_at: float


class SSHConnectionPool:
    """SSH connection pool for reusing connections"""

    def __init__(self, max_connections: int = 10, connection_timeout: int = 300):
        """
        Initialize connection pool

        Args:
            max_connections: maximum number of connections per node
            connection_timeout: connection idle timeout in seconds
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.pools: Dict[str, list] = {}  # node_key -> list of ConnectionInfo
        self._lock = asyncio.Lock()

    def _get_node_key(self, node_info: Dict) -> str:
        """Generate unique key for node"""
        return f"{node_info['ip']}:{node_info['port']}:{node_info['username']}"

    async def get_connection(self, node_info: Dict) -> Optional[paramiko.SSHClient]:
        """
        Get connection from pool or create new one

        Args:
            node_info: node connection information

        Returns:
            SSH client or None if failed
        """
        node_key = self._get_node_key(node_info)

        async with self._lock:
            # Clean expired connections
            await self._clean_expired_connections(node_key)

            # Try to get existing connection
            if node_key in self.pools and self.pools[node_key]:
                conn_info = self.pools[node_key].pop()
                if self._is_connection_alive(conn_info.client):
                    conn_info.last_used = time.time()
                    logger.debug(f"Reusing connection for {node_key}")
                    return conn_info.client
                else:
                    # Connection is dead, close it
                    try:
                        conn_info.client.close()
                    except Exception:
                        pass

            # Create new connection
            client = await self._create_connection(node_info)
            if client:
                conn_info = ConnectionInfo(client=client, last_used=time.time(), created_at=time.time())
                logger.debug(f"Created new connection for {node_key}")
                return client

        return None

    async def return_connection(self, node_info: Dict, client: paramiko.SSHClient):
        """
        Return connection to pool

        Args:
            node_info: node connection information
            client: SSH client to return
        """
        node_key = self._get_node_key(node_info)

        async with self._lock:
            # Clean expired connections
            await self._clean_expired_connections(node_key)

            # Check pool size limit
            if node_key not in self.pools:
                self.pools[node_key] = []

            if len(self.pools[node_key]) < self.max_connections:
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

    async def _create_connection(self, node_info: Dict) -> Optional[paramiko.SSHClient]:
        """Create new SSH connection"""
        import os

        # Get configurable SSH connection timeout
        ssh_connection_timeout = int(os.getenv("KUBEYE_SSH_CONNECTION_TIMEOUT", "10"))

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if node_info["auth_type"] == "password":
                client.connect(
                    hostname=node_info["ip"],
                    port=int(node_info["port"]),
                    username=node_info["username"],
                    password=node_info["password"],
                    timeout=ssh_connection_timeout,
                )
            else:
                # Key authentication
                key_path = node_info["key_path"]
                key = self._load_private_key(key_path)
                client.connect(
                    hostname=node_info["ip"],
                    port=int(node_info["port"]),
                    username=node_info["username"],
                    pkey=key,
                    timeout=ssh_connection_timeout,
                )

            return client

        except Exception as e:
            logger.error(f"Failed to create connection for {node_info['ip']}: {e}")
            return None

    def _load_private_key(self, key_path: str):
        """Load private key"""
        key_types = [
            (paramiko.RSAKey, "RSA"),
            (paramiko.Ed25519Key, "Ed25519"),
            (paramiko.ECDSAKey, "ECDSA"),
        ]

        for key_class, key_name in key_types:
            try:
                return key_class.from_private_key_file(key_path)
            except paramiko.SSHException:
                continue

        raise paramiko.SSHException(f"Unable to load private key from {key_path}")

    def _is_connection_alive(self, client: paramiko.SSHClient) -> bool:
        """Check if connection is alive"""
        try:
            # Try to execute a simple command
            stdin, stdout, stderr = client.exec_command("echo 1", timeout=5)
            return stdout.channel.recv_exit_status() == 0
        except Exception:
            return False

    async def _clean_expired_connections(self, node_key: str):
        """Clean expired connections for node"""
        if node_key not in self.pools:
            return

        current_time = time.time()
        active_connections = []

        for conn_info in self.pools[node_key]:
            if current_time - conn_info.last_used < self.connection_timeout:
                active_connections.append(conn_info)
            else:
                # Close expired connection
                try:
                    conn_info.client.close()
                except Exception:
                    pass
                logger.debug(f"Closed expired connection for {node_key}")

        self.pools[node_key] = active_connections

    async def close_all(self):
        """Close all connections in pool"""
        async with self._lock:
            for node_key, connections in self.pools.items():
                for conn_info in connections:
                    try:
                        conn_info.client.close()
                    except Exception:
                        pass
            self.pools.clear()
            logger.info("Closed all connections in pool")


# SSH connection pool is now managed by DI container
# Use: from infrastructure.dependency_injection.container import get_service
# ssh_pool = await get_service("ssh_pool")
