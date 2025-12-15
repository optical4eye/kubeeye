#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node connection management module, used for connecting to cluster nodes via SSH and executing commands
"""

import asyncio
import paramiko
import socket
import logging
from typing import Dict, Tuple, Optional
import os
from .ssh_connection_pool import ssh_pool


class AsyncNodeConnection:
    """Asynchronous SSH connection class to node (using paramiko in thread)"""

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
                - key_path: key path (if auth_type is 'key')
        """
        self.node_info = node_info
        self.client = None
        self.connected = False

    async def connect(self) -> Tuple[bool, str]:
        """
        Connect to node asynchronously (using paramiko in thread)

        Returns:
            On successful connection returns (True, ""), on error — (False, error_message)
        """
        try:
            # Log connection information
            logging.info(
                f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}"
            )

            # Run paramiko connection in thread using asyncio.to_thread
            success, message = await asyncio.to_thread(self._sync_connect)

            self.connected = success
            return success, message
        except asyncio.TimeoutError:
            error_msg = "Connection timeout"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg

    def _sync_connect(self) -> Tuple[bool, str]:
        """Synchronous connection using paramiko"""
        try:
            # Create paramiko client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect
            if self.node_info["auth_type"] == "password":
                self.client.connect(
                    hostname=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    password=self.node_info["password"],
                    timeout=5,
                )
            else:
                # Key authentication
                key_path = self.node_info["key_path"]
                if not os.path.isfile(key_path):
                    return False, f"Key file {key_path} does not exist"

                # Load key (support multiple key types)
                key = self._load_private_key(key_path)
                self.client.connect(
                    hostname=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    pkey=key,
                    timeout=5,
                )

            return True, ""
        except paramiko.AuthenticationException:
            error_msg = "Authentication error (incorrect username, password or SSH key)"
            return False, error_msg
        except paramiko.SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            return False, error_msg
        except socket.timeout:
            error_msg = "Connection timeout"
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            return False, error_msg

    def _load_private_key(self, key_path: str):
        """Load private key supporting multiple types (RSA, DSS, ECDSA, Ed25519)"""
        import paramiko

        # Try different key types in order of preference
        key_types = [
            (paramiko.RSAKey, "RSA"),
            (paramiko.Ed25519Key, "Ed25519"),
            (paramiko.ECDSAKey, "ECDSA"),
        ]

        for key_class, key_name in key_types:
            try:
                key = key_class.from_private_key_file(key_path)
                logging.debug(f"Successfully loaded {key_name} key from {key_path}")
                return key
            except paramiko.SSHException:
                continue  # Try next key type

        # If none worked, raise an error
        raise paramiko.SSHException(
            f"Unable to load private key from {key_path}. Supported types: RSA, Ed25519, ECDSA, DSS"
        )

    def close(self) -> None:
        """Close connection"""
        if self.connected and self.client:
            try:
                self.client.close()
            except Exception as e:
                logging.warning(f"Error closing connection: {str(e)}")
            self.client = None
            self.connected = False


class NodeConnection:
    """Synchronous SSH connection class to node (using paramiko)"""

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
                - key_path: key path (if auth_type is 'key')
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
        Connect to node using paramiko

        Returns:
            On successful connection returns (True, ""), on error — (False, error_message)
        """
        try:
            # Log connection information
            logging.info(
                f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}"
            )

            # Create paramiko client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Get configurable SSH timeout (used for connection, commands, and socket tests)
            ssh_timeout = int(os.getenv('KUBEYE_SSH_CONNECTION_TIMEOUT', '10'))

            # Connect
            if self.node_info["auth_type"] == "password":
                self.client.connect(
                    hostname=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    password=self.node_info["password"],
                    timeout=ssh_timeout,
                )
            else:
                # Key authentication
                key_path = self.node_info["key_path"]
                if not os.path.isfile(key_path):
                    return False, f"Key file {key_path} does not exist"

                # Load key (support multiple key types)
                key = self._load_private_key(key_path)
                self.client.connect(
                    hostname=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    pkey=key,
                    timeout=ssh_timeout,
                )

            self.connected = True
            return True, ""
        except paramiko.AuthenticationException:
            error_msg = (
                "Authentication failed (incorrect username, password or SSH key)"
            )
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except paramiko.SSHException as e:
            error_msg = f"SSH error: {str(e)}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except socket.timeout:
            error_msg = "Connection timeout"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
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
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
                # If there's already a running loop, we need to use it differently
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._execute_command_sync, command)
                    return future.result(timeout=command_timeout + 5)  # command timeout + 5s buffer
            except RuntimeError:
                # No running loop, we can use asyncio.run
                return asyncio.run(self._execute_command_async(command))

        except Exception as e:
            return False, "", f"Command execution error: {str(e)}"

    async def _execute_command_async(self, command: str) -> Tuple[bool, str, str]:
        """Execute command asynchronously"""
        # Get connection from pool
        client = await ssh_pool.get_connection(self.node_info)
        if not client:
            return False, "", "Failed to get connection from pool"

        try:
            # Execute command with configurable timeout (6x base SSH timeout for commands)
            command_timeout = ssh_timeout * 6  # 60s for 10s base
            stdin, stdout, stderr = client.exec_command(command, timeout=command_timeout)
            exit_status = stdout.channel.recv_exit_status()

            # Read output
            stdout_data = stdout.read().decode("utf-8")
            stderr_data = stderr.read().decode("utf-8")

            success = exit_status == 0
            return success, stdout_data, stderr_data
        finally:
            # Return connection to pool
            await ssh_pool.return_connection(self.node_info, client)

    def _execute_command_sync(self, command: str) -> Tuple[bool, str, str]:
        """Execute command synchronously using new event loop"""
        return asyncio.run(self._execute_command_async(command))

    def _load_private_key(self, key_path: str):
        """Load private key supporting multiple types (RSA, DSS, ECDSA, Ed25519)"""
        import paramiko

        # Try different key types in order of preference
        key_types = [
            (paramiko.RSAKey, "RSA"),
            (paramiko.Ed25519Key, "Ed25519"),
            (paramiko.ECDSAKey, "ECDSA"),
        ]

        for key_class, key_name in key_types:
            try:
                key = key_class.from_private_key_file(key_path)
                logging.debug(f"Successfully loaded {key_name} key from {key_path}")
                return key
            except paramiko.SSHException:
                continue  # Try next key type

        # If none worked, raise an error
        raise paramiko.SSHException(
            f"Unable to load private key from {key_path}. Supported types: RSA, Ed25519, ECDSA, DSS"
        )

    def close(self) -> None:
        """Close connection"""
        if self.connected and self.client:
            try:
                self.client.close()
            except Exception as e:
                logging.warning(f"Error closing connection: {str(e)}")
            self.client = None
            self.connected = False


async def async_test_node_connection(node_info: Dict) -> Tuple[bool, str]:
    """
    Test node connection asynchronously

    Args:
        node_info: node configuration information

    Returns:
        Tuple (success, message)
    """
    async_conn = AsyncNodeConnection(node_info)
    success, message = await async_conn.connect()
    if success:
        async_conn.close()
    else:
        message = f"Failed to connect to {node_info['ip']}: {message}"
    return success, message


def test_node_connection(node_info: Dict) -> Tuple[bool, str]:
    """
    Test node connection (synchronous wrapper with 5 second timeout)

    Args:
        node_info: node configuration information

    Returns:
        Tuple (success, message)
    """
    try:
        # Use a simple socket connection test with 5 second timeout
        import socket

        host = node_info["ip"]
        port = int(node_info.get("port", 22))

        # Create socket with timeout based on SSH timeout (0.5x for quick tests)
        socket_timeout = ssh_timeout * 0.5  # 5s for 10s base
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(float(socket_timeout))

        try:
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return True, f"Connection to {host}:{port} successful"
            else:
                return False, f"Connection to {host}:{port} failed (port unreachable)"
        except socket.timeout:
            sock.close()
            return False, f"Connection to {host}:{port} timed out ({socket_timeout}s)"
        except socket.gaierror as e:
            sock.close()
            return False, f"DNS resolution error for {host}: {str(e)}"
        except Exception as e:
            sock.close()
            return False, f"Connection test error: {str(e)}"

    except Exception as e:
        return False, f"Test setup error: {str(e)}"


async def async_validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """
    Validate SSH key file asynchronously (using paramiko in thread)

    Args:
        key_path: key file path

    Returns:
        Tuple (success, message)
    """
    if not os.path.isfile(key_path):
        return False, f"Key file {key_path} does not exist"

    try:
        # Run paramiko key validation in thread using asyncio.to_thread
        return await asyncio.to_thread(_sync_validate_ssh_key, key_path)
    except Exception as e:
        return False, f"Key validation error: {str(e)}"


def _sync_validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """Synchronous SSH key validation using paramiko"""
    try:
        # Try different key types
        key_types = [
            (paramiko.RSAKey, "RSA"),
            (paramiko.Ed25519Key, "Ed25519"),
            (paramiko.ECDSAKey, "ECDSA"),
        ]

        for key_class, key_name in key_types:
            try:
                key_class.from_private_key_file(key_path)
                return True, f"SSH key format is correct ({key_name})"
            except paramiko.SSHException:
                continue

        return False, "Unsupported key format"
    except Exception as e:
        return False, f"Key validation error: {str(e)}"


def validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """
    Validate SSH key file (synchronous wrapper)

    Args:
        key_path: key file path

    Returns:
        Tuple (success, message)
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(async_validate_ssh_key(key_path))
        loop.close()
        return result
    except Exception as e:
        return False, f"Key validation execution error: {str(e)}"
