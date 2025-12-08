#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node connection management module, used for connecting to cluster nodes via SSH and executing commands
"""


import paramiko
import socket
import logging
from typing import Dict, Tuple, Optional
import os


class NodeConnection:
    """SSH connection class to node"""


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
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
        Connect to node


        Returns:
            On successful connection returns (True, ""), on error — (False, error_message)
        """
        try:
            # Log connection information
            logging.info(f"Connecting to node: {self.node_info['ip']}:{self.node_info['port']} user: {self.node_info['username']}")


            # Ensure no interactive password prompt
            # look_for_keys=False prevents Paramiko from trying to use SSH agent or search for key files
            # allow_agent=False prevents SSH agent usage
            if self.node_info['auth_type'] == 'password':
                self.client.connect(
                    hostname=self.node_info['ip'],
                    port=int(self.node_info['port']),
                    username=self.node_info['username'],
                    password=self.node_info['password'],
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
                )
            else:  # key authentication
                key_path = self.node_info['key_path']
                if not os.path.isfile(key_path):
                    return False, f"Key file {key_path} does not exist"


                # Check key file permissions
                self._check_key_permissions(key_path)


                # Try to load SSH key in different ways
                key = self._load_ssh_key(key_path)
                if not key:
                    return False, "Failed to load SSH key. Check key format."


                self.client.connect(
                    hostname=self.node_info['ip'],
                    port=int(self.node_info['port']),
                    username=self.node_info['username'],
                    pkey=key,
                    timeout=10,
                    look_for_keys=False,
                    allow_agent=False
                )


            self.connected = True
            return True, ""
        except socket.timeout:
            error_msg = f"Connection timeout exceeded (port {self.node_info['port']})"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except socket.gaierror as e:
            error_msg = f"DNS resolution error: {str(e)}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except ConnectionRefusedError:
            error_msg = f"Connection refused (possibly SSH service on port {self.node_info['port']} is not open)"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except paramiko.AuthenticationException:
            error_msg = "Authentication error (incorrect username, password or SSH key)"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except paramiko.SSHException as e:
            # Handle "[Errno None] Unable to connect to port" error
            error_str = str(e)
            if "Unable to connect to port" in error_str:
                error_msg = f"Unable to connect to port {self.node_info['port']} (possibly host unreachable or connection blocked by firewall)"
            else:
                error_msg = f"SSH error: {error_str}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logging.error(f"Node {self.node_info['ip']}: {error_msg}")
            return False, error_msg


    def _check_key_permissions(self, key_path: str) -> None:
        """Check key file permissions"""
        try:
            stat_info = os.stat(key_path)
            permissions = stat_info.st_mode & 0o777
            if permissions != 0o600:
                logging.warning(f"Key file permissions {oct(permissions)} are insecure, 600 recommended")
                # Only warning, execution not blocked
        except Exception as e:
            logging.warning(f"Failed to check key file permissions: {str(e)}")


    def _load_ssh_key(self, key_path: str) -> Optional[paramiko.PKey]:
        """
        Tries to load SSH key in different ways


        Args:
            key_path: key file path


        Returns:
            Loaded key object or None
        """
        # First try auto-detection
        try:
            key = paramiko.PKey.from_private_key_file(key_path)
            logging.info("SSH key auto-detected")
            return key
        except Exception as e:
            logging.info(f"Key auto-detection failed: {str(e)}")


        # Try to load specific key types
        key_methods = [
            ("RSA", paramiko.RSAKey.from_private_key_file),
            ("ECDSA", paramiko.ECDSAKey.from_private_key_file),
            ("Ed25519", paramiko.Ed25519Key.from_private_key_file),
        ]


        for key_type, key_loader in key_methods:
            try:
                key = key_loader(key_path)
                logging.info(f"Successfully loaded {key_type} key")
                return key
            except paramiko.SSHException as e:
                logging.info(f"{key_type} key does not fit: {str(e)}")
                continue
            except Exception as e:
                logging.warning(f"Error loading {key_type} key: {str(e)}")
                continue


        # Finally try to load RSA key without password (for encrypted keys)
        try:
            key = paramiko.RSAKey.from_private_key_file(key_path, password=None)
            logging.info("Successfully loaded RSA key (without password)")
            return key
        except:
            pass


        logging.error("All key loading methods failed")
        return None


    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute command on node


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
            # Execute command and wait for completion
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)


            # Close standard input
            stdin.close()


            # Read standard output and standard error stream
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')


            # Wait for command completion and get exit code
            exit_status = stdout.channel.recv_exit_status()


            # Close all channels
            stdout.close()
            stderr.close()


            success = exit_status == 0
            return success, stdout_data, stderr_data
        except Exception as e:
            return False, "", str(e)


    def close(self) -> None:
        """Close connection"""
        if self.connected:
            self.client.close()
            self.connected = False



def test_node_connection(node_info: Dict) -> Tuple[bool, str]:
    """
    Test node connection


    Args:
        node_info: node configuration information


    Returns:
        Tuple (success, message)
    """
    conn = NodeConnection(node_info)
    success, message = conn.connect()
    if success:
        conn.close()
    return success, message



def validate_ssh_key(key_path: str) -> Tuple[bool, str]:
    """
    Validate SSH key file


    Args:
        key_path: key file path


    Returns:
        Tuple (success, message)
    """
    if not os.path.isfile(key_path):
        return False, f"Key file {key_path} does not exist"


    try:
        # Create temporary connection object to test key loading
        temp_node_info = {
            'ip': '127.0.0.1',  # dummy IP, only for key validation
            'port': 22,
            'username': 'test',
            'auth_type': 'key',
            'key_path': key_path
        }


        conn = NodeConnection(temp_node_info)
        key = conn._load_ssh_key(key_path)
        if key:
            return True, "SSH key format is correct"
        else:
            return False, "Failed to load SSH key. Check key format."


    except Exception as e:
        return False, f"Key validation error: {str(e)}"
