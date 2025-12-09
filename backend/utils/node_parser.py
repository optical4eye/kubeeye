#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility for parsing nodes from text format
"""

import re
from typing import List, Dict, Any, Tuple

# Pre-compiled regular expressions for performance
IP_PORT_PATTERN = re.compile(r"^([\d\.]+)(?::(\d+))?$")
NODE_PATTERN = re.compile(
    r"^(\d+\.\d+\.\d+\.\d+)(?::(\d+))?\s+(\w+)\s+(password|key)(?:\s+(.+))?$"
)


def parse_nodes_from_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Optimized parsing of text with nodes using pre-compiled regex

    Args:
        text: Text with nodes in format "IP:Port User AuthType [Password/KeyPath]"

    Returns:
        Tuple (list of nodes, list of errors)
    """
    nodes = []
    errors = []

    lines = text.strip().split("\n")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        try:
            # Use pre-compiled pattern for full line
            match = NODE_PATTERN.match(line)
            if not match:
                errors.append(f"Line {line_num}: invalid format")
                continue

            ip, port, username, auth_type, credential = match.groups()
            port = port or "22"

            # IP validation
            if not is_valid_ip(ip):
                errors.append(f"Line {line_num}: invalid IP address")
                continue

            # Port validation
            if not port.isdigit() or not (1 <= int(port) <= 65535):
                errors.append(f"Line {line_num}: invalid port")
                continue

            auth_type = auth_type.lower()
            node_info = {
                "ip": ip,
                "port": port,
                "username": username,
                "auth_type": auth_type,
            }

            # Credential processing
            if auth_type == "password":
                if credential:
                    node_info["password"] = credential
                else:
                    errors.append(
                        f"Line {line_num}: password required for 'password' type"
                    )
                    continue
            else:  # key
                if credential:
                    node_info["key_path"] = credential
                else:
                    errors.append(f"Line {line_num}: key path required for 'key' type")
                    continue

            nodes.append(node_info)

        except Exception as e:
            errors.append(f"Line {line_num}: processing error - {str(e)}")

    return nodes, errors


def is_valid_ip(ip: str) -> bool:
    """Checks IP address validity"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False

    for part in parts:
        if not part.isdigit():
            return False
        if not (0 <= int(part) <= 255):
            return False

    return True


def generate_nodes_template() -> str:
    """Generates template for bulk node addition"""
    return """# Format for bulk node addition
# Each line should contain: IP:Port User AuthType [Password/KeyPath]

# Examples:
192.168.1.100:22 root password mypassword123
192.168.1.101:22 admin key /home/user/.ssh/id_rsa
10.0.1.50:2222 ubuntu password ubuntu123

# Notes:
# - Port can be omitted, 22 will be used
# - Auth type: password or key
# - For password specify password, for key - path to key file
"""
