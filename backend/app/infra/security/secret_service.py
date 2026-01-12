#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service for secret management operations and validation
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.secrets import Secret
from db.repositories.secret_repository import SecretRepository, EncryptionKeyRepository
from infra.security.crypto_utils import get_encryption_service
from core.logging import get_logger

logger = get_logger(__name__)


class SecretValidator:
    """Validator for different types of secrets"""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password format

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"

        # No complexity requirements as per task requirements
        # Only check that it's not empty
        return True, None

    @staticmethod
    def validate_ssh_key(ssh_key: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SSH key format using asyncssh

        Args:
            ssh_key: SSH key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ssh_key:
            return False, "SSH key cannot be empty"

        # Remove leading/trailing whitespace
        ssh_key = ssh_key.strip()

        # Use asyncssh for validation (most reliable method)
        try:
            import asyncssh

            key = asyncssh.import_private_key(ssh_key)
            if key:
                key_type = key.algorithm.decode() if isinstance(key.algorithm, bytes) else key.algorithm
                return True, f"SSH key format is correct ({key_type})"
            else:
                return False, "Unsupported key format or failed to load"
        except asyncssh.KeyImportError as e:
            return False, f"Invalid SSH key format: {str(e)}"
        except Exception as e:
            return False, f"Key validation error: {str(e)}"

    @staticmethod
    def validate_kubeconfig(kubeconfig: str) -> Tuple[bool, Optional[str]]:
        """
        Validate kubeconfig format (secret reference)

        This method validates that kubeconfig is a valid secret reference in the format
        ${secret:secret-name}. It does NOT validate the actual YAML content.

        Args:
            kubeconfig: Kubeconfig content to validate (must be a secret reference)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check that kubeconfig is not empty and is a string
        if not kubeconfig or not isinstance(kubeconfig, str):
            return False, "Kubeconfig must be a non-empty string"

        # Security check: kubeconfig must be a secret reference
        if not kubeconfig.startswith("${secret:"):
            return False, "Direct kubeconfig input is not allowed. Use ${secret:secret-name} syntax"

        # Validate secret reference format
        # Format: ${secret:secret-name}
        if len(kubeconfig) < 11:  # Minimum length: ${secret:x}
            return False, "Invalid secret reference format"

        # Extract secret name and validate it's not empty
        secret_name = kubeconfig[10:-1]  # Remove ${secret: and }
        if not secret_name:
            return False, "Secret name cannot be empty"

        # Validate secret name contains only valid characters
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", secret_name):
            return False, "Secret name can only contain alphanumeric characters, hyphens, and underscores"

        return True, None

    @staticmethod
    def validate_kubeconfig_yaml(kubeconfig_yaml: str) -> Tuple[bool, Optional[str]]:
        """
        Validate kubeconfig YAML content

        This method validates the actual YAML content of a kubeconfig file.
        It checks for required fields and valid YAML structure.

        Args:
            kubeconfig_yaml: Kubeconfig YAML content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not kubeconfig_yaml or not isinstance(kubeconfig_yaml, str):
            return False, "Kubeconfig YAML must be a non-empty string"

        try:
            import yaml

            # Try to parse as YAML
            config = yaml.safe_load(kubeconfig_yaml)

            if not isinstance(config, dict):
                return False, "Kubeconfig must be a valid YAML dictionary"

            # Check for required fields
            if "apiVersion" not in config:
                return False, "Kubeconfig missing required field: apiVersion"

            if "kind" not in config or config["kind"] != "Config":
                return False, "Kubeconfig must have kind: Config"

            if "clusters" not in config or not config["clusters"]:
                return False, "Kubeconfig must contain at least one cluster"

            if "users" not in config or not config["users"]:
                return False, "Kubeconfig must contain at least one user"

            if "contexts" not in config or not config["contexts"]:
                return False, "Kubeconfig must contain at least one context"

            return True, None

        except yaml.YAMLError as e:
            return False, f"Invalid YAML format: {str(e)}"
        except Exception as e:
            logger.error(f"Kubeconfig YAML validation error: {e}")
            return False, f"Failed to validate kubeconfig YAML: {str(e)}"

    @staticmethod
    def validate_secret(secret_type: str, data: str) -> Tuple[bool, Optional[str]]:
        """
        Validate secret based on type

        Args:
            secret_type: Type of secret (password, ssh_key, kubeconfig)
            data: Secret data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        validators = {
            "password": SecretValidator.validate_password,
            "ssh_key": SecretValidator.validate_ssh_key,
            "kubeconfig": SecretValidator.validate_kubeconfig_yaml,  # Validate YAML content for secrets
        }

        validator = validators.get(secret_type)
        if not validator:
            return False, f"Unknown secret type: {secret_type}"

        return validator(data)


class SecretService:
    """Service for secret business logic"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = SecretRepository(session)
        self.encryption_key_repository = EncryptionKeyRepository(session)
        self.encryption_service = get_encryption_service(session)

    async def create_secret(
        self,
        name: str,
        secret_type: str,
        data: str,
        description: Optional[str] = None,
        secret_metadata: Optional[Dict[str, Any]] = None,
    ) -> Secret:
        """
        Create a new secret

        Args:
            name: Unique name for the secret
            secret_type: Type of secret (password, ssh_key, kubeconfig)
            data: Secret data (will be encrypted)
            description: Optional description
            secret_metadata: Optional metadata

        Returns:
            Created Secret object

        Raises:
            ValueError: If validation fails
        """
        # Check if name already exists
        if await self.repository.check_name_exists(name):
            raise ValueError(f"Secret with name '{name}' already exists")

        # Validate secret data
        is_valid, error_message = SecretValidator.validate_secret(secret_type, data)
        if not is_valid:
            raise ValueError(f"Invalid {secret_type}: {error_message}")

        # Encrypt data
        encrypted_data = await self.encryption_service.encrypt(data)

        # Create secret
        secret = Secret(
            name=name,
            secret_type=secret_type,
            encrypted_data=encrypted_data,
            description=description,
            secret_metadata=secret_metadata,
            is_active=True,
        )

        self.session.add(secret)
        await self.session.commit()
        await self.session.refresh(secret)

        logger.info(f"Created secret: {name} (type: {secret_type})")
        return secret

    async def get_secret(self, secret_id: int) -> Optional[Secret]:
        """Get secret by ID"""
        return await self.repository.get_by_id(secret_id)

    async def get_secret_by_name(self, name: str) -> Optional[Secret]:
        """Get secret by name"""
        return await self.repository.get_by_name(name)

    async def list_secrets(
        self,
        secret_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Secret], int]:
        """List secrets with filters"""
        return await self.repository.get_filtered(
            secret_type=secret_type, is_active=is_active, search=search, limit=limit, offset=offset
        )

    async def update_secret(
        self,
        secret_id: int,
        name: Optional[str] = None,
        data: Optional[str] = None,
        description: Optional[str] = None,
        secret_metadata: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Secret:
        """
        Update an existing secret

        Args:
            secret_id: ID of secret to update
            name: New name (optional)
            data: New data (optional, will be encrypted)
            description: New description (optional)
            secret_metadata: New metadata (optional)
            is_active: New active status (optional)

        Returns:
            Updated Secret object

        Raises:
            ValueError: If validation fails or secret not found
        """
        secret = await self.repository.get_by_id(secret_id)
        if not secret:
            raise ValueError(f"Secret with ID {secret_id} not found")

        # Update name if provided
        if name is not None:
            if await self.repository.check_name_exists(name, exclude_id=secret_id):
                raise ValueError(f"Secret with name '{name}' already exists")
            secret.name = name

        # Update data if provided
        if data is not None:
            is_valid, error_message = SecretValidator.validate_secret(secret.secret_type, data)
            if not is_valid:
                raise ValueError(f"Invalid {secret.secret_type}: {error_message}")
            secret.encrypted_data = await self.encryption_service.encrypt(data)

        # Update other fields
        if description is not None:
            secret.description = description

        if secret_metadata is not None:
            secret.secret_metadata = secret_metadata

        if is_active is not None:
            secret.is_active = is_active

        secret.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(secret)

        logger.info(f"Updated secret: {secret.name} (ID: {secret_id})")
        return secret

    async def delete_secret(self, secret_id: int) -> bool:
        """
        Delete a secret (hard delete - permanently remove from database)

        Args:
            secret_id: ID of secret to delete

        Returns:
            True if deleted successfully
        """
        return await self.repository.delete(secret_id)

    async def reveal_secret(self, secret_id: int) -> Tuple[str, Secret]:
        """
        Reveal (decrypt) secret data

        Args:
            secret_id: ID of secret to reveal

        Returns:
            Tuple of (decrypted_data, secret_object)

        Raises:
            ValueError: If secret not found or decryption fails
        """
        secret = await self.repository.get_by_id(secret_id)
        if not secret:
            raise ValueError(f"Secret with ID {secret_id} not found")

        if not secret.is_active:
            raise ValueError(f"Secret '{secret.name}' is not active")

        try:
            decrypted_data = await self.encryption_service.decrypt(secret.encrypted_data)

            # Update last_used_at
            await self.repository.update_last_used(secret_id)

            logger.info(f"Revealed secret: {secret.name} (ID: {secret_id})")
            return decrypted_data, secret

        except Exception as e:
            logger.error(f"Failed to reveal secret {secret_id}: {e}")
            raise ValueError(f"Failed to decrypt secret: {e}")

    async def test_secret(self, secret_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Test if secret is valid and can be decrypted

        Args:
            secret_id: ID of secret to test

        Returns:
            Tuple of (success, message, details)
        """
        try:
            secret = await self.repository.get_by_id(secret_id)
            if not secret:
                return False, f"Secret with ID {secret_id} not found", None

            if not secret.is_active:
                return False, f"Secret '{secret.name}' is not active", None

            # Try to decrypt
            decrypted_data = await self.encryption_service.decrypt(secret.encrypted_data)

            # Validate based on type
            is_valid, error_message = SecretValidator.validate_secret(secret.secret_type, decrypted_data)

            if is_valid:
                details = {"secret_type": secret.secret_type, "name": secret.name, "data_length": len(decrypted_data)}
                return True, f"Secret '{secret.name}' is valid", details
            else:
                return False, f"Secret validation failed: {error_message}", None

        except Exception as e:
            logger.error(f"Failed to test secret {secret_id}: {e}")
            return False, f"Failed to test secret: {str(e)}", None

    async def get_secrets_for_cluster_nodes(self, node_configs: List[Dict[str, Any]]) -> Dict[int, str]:
        """
        Get decrypted secrets for cluster nodes

        Args:
            node_configs: List of node configurations with secret_id

        Returns:
            Dictionary mapping secret_id to decrypted data
        """
        secrets_data = {}

        for node in node_configs:
            secret_id = node.get("secret_id")
            if secret_id and secret_id not in secrets_data:
                try:
                    decrypted_data, _ = await self.reveal_secret(secret_id)
                    secrets_data[secret_id] = decrypted_data
                except Exception as e:
                    logger.error(f"Failed to get secret {secret_id} for node: {e}")

        return secrets_data

    async def get_kubeconfig_from_secret(self, secret_id: int) -> Optional[str]:
        """
        Get kubeconfig from secret

        Args:
            secret_id: ID of secret containing kubeconfig

        Returns:
            Decrypted kubeconfig or None if not found
        """
        try:
            secret = await self.repository.get_by_id(secret_id)
            if not secret or secret.secret_type != "kubeconfig":
                return None

            decrypted_data, _ = await self.reveal_secret(secret_id)
            return decrypted_data

        except Exception as e:
            logger.error(f"Failed to get kubeconfig from secret {secret_id}: {e}")
            return None


def validate_secret(secret_type: str, data: str) -> Tuple[bool, Optional[str]]:
    """Validate secret data"""
    return SecretValidator.validate_secret(secret_type, data)
