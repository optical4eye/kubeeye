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
        import concurrent.futures

        try:
            # Log connection information
            logging.info(
                f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}"
            )

            # Run paramiko connection in thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._sync_connect)
                success, message = future.result(timeout=30)

            self.connected = success
            return success, message
        except concurrent.futures.TimeoutError:
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

                # Load key
                key = paramiko.RSAKey.from_private_key_file(key_path)
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

                # Load key
                key = paramiko.RSAKey.from_private_key_file(key_path)
                self.client.connect(
                    hostname=self.node_info["ip"],
                    port=int(self.node_info["port"]),
                    username=self.node_info["username"],
                    pkey=key,
                    timeout=5,
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
        Execute command on node using paramiko

        Args:
            command: command to execute

        Returns:
            Tuple (success, stdout, stderr)
        """
        if not self.connected:
            success, message = self.connect()
            if not success:
                return False, "", message

        try:
            # Execute command
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
            exit_status = stdout.channel.recv_exit_status()

            # Read output
            stdout_data = stdout.read().decode("utf-8")
            stderr_data = stderr.read().decode("utf-8")

            success = exit_status == 0
            return success, stdout_data, stderr_data
        except Exception as e:
            return False, "", f"Command execution error: {str(e)}"

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

        # Create socket with 5 second timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout

        try:
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return True, f"Connection to {host}:{port} successful"
            else:
                return False, f"Connection to {host}:{port} failed (port unreachable)"
        except socket.timeout:
            sock.close()
            return False, f"Connection to {host}:{port} timed out (5s)"
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
    import concurrent.futures

    if not os.path.isfile(key_path):
        return False, f"Key file {key_path} does not exist"

    try:
        # Run paramiko key validation in thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_sync_validate_ssh_key, key_path)
            return future.result(timeout=10)
    except concurrent.futures.TimeoutError:
        return False, "Key validation timeout"
    except Exception as e:
        return False, f"Key validation error: {str(e)}"


def _sync_validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """Synchronous SSH key validation using paramiko"""
    try:
        paramiko.RSAKey.from_private_key_file(key_path)
        return True, "SSH key format is correct"
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
