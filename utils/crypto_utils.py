#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Password encryption tool for protecting sensitive information
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

# Generate default key file path
KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '.secret_key')

def get_encryption_key():
    """
    Get or generate encryption key

    Returns:
        bytes: encryption key
    """
    try:
        # Try to read existing key
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, 'rb') as f:
                key_data = f.read()
                # Check if need to remove first line comment (// filepath:...)
                if key_data.startswith(b'//'):
                    key_lines = key_data.split(b'\n')
                    if len(key_lines) > 1:
                        key_data = key_lines[1].strip()

                # Try to load key as valid Fernet key
                try:
                    # Check if key is valid
                    Fernet(key_data)
                    logger.info("Encryption key loaded successfully")
                    return key_data
                except Exception as e:
                    logger.error(f"Loaded key has invalid format, new key will be generated: {str(e)}")
                    os.rename(KEY_FILE, f"{KEY_FILE}.backup")

        # If does not exist or invalid, generate new key
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        logger.info("New encryption key generated")
        return key
    except Exception as e:
        logger.error(f"Key management error: {str(e)}", exc_info=True)
        # If error occurred, generate temporary key (do not save)
        return Fernet.generate_key()

def encrypt_password(password: str) -> str:
    """
    Encrypt password

    Args:
        password: password in plain text

    Returns:
        str: encrypted password string
    """
    if not password:
        return ""

    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(password.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Password encryption error: {str(e)}")
        return password  # On encryption failure return original password

def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypt password

    Args:
        encrypted_password: encrypted password string

    Returns:
        str: decrypted password in plain text
    """
    if not encrypted_password:
        return ""

    try:
        key = get_encryption_key()
        f = Fernet(key)

        # Try to decode and clean possible format issues
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_password)
        except Exception as e:
            logger.error(f"Base64 decoding failure: {str(e)}, try to decrypt directly")
            # Possibly password is already decrypted, return directly
            return encrypted_password

        # Decrypt
        try:
            decrypted = f.decrypt(encrypted).decode()
            logger.debug(f"Password decryption successful")
            return decrypted
        except Exception as e:
            logger.error(f"Fernet decryption failure: {str(e)}")
            # Decryption failure, possibly password already decrypted, return directly
            return encrypted_password
    except Exception as e:
        logger.error(f"Error occurred during password decryption process: {str(e)}")
        return encrypted_password  # On decryption failure return original encrypted string
