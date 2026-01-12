#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser for secret variables in cluster configuration
Supports ${secret:secret-name} syntax
"""

import re
from typing import Dict, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from infra.security.secret_service import SecretService
from core.logging import get_logger
from core.common.cache_utils import CacheManager

logger = get_logger(__name__)


class SecretVariableParser:
    """Parser for secret variables in configuration strings"""

    # Pattern to match ${secret:secret-name}
    SECRET_PATTERN = re.compile(r"\$\{secret:([^}]+)\}")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.secret_service = SecretService(session)
        self.cache_manager = CacheManager()
        self._cache = self.cache_manager.get_or_create_cache("secret_variables", maxsize=100, ttl=600)  # 10 minutes TTL

    def find_variables(self, text: str) -> List[str]:
        """
        Find all secret variable references in text

        Args:
            text: Text to search for variables

        Returns:
            List of secret names found in variables
        """
        matches = self.SECRET_PATTERN.findall(text)
        return list(set(matches))  # Remove duplicates

    async def replace_variables(self, text: str) -> Tuple[str, List[str]]:
        """
        Replace secret variables with decrypted values

        Args:
            text: Text with secret variables

        Returns:
            Tuple of (text_with_replaced_variables, list_of_errors)
        """
        if not text:
            return text, []

        errors = []

        # Find all secret names in the text
        secret_names = self.find_variables(text)

        if not secret_names:
            return text, []

        # Build replacement map
        replacements = {}

        for secret_name in secret_names:
            # Check cache first
            if secret_name in self._cache:
                replacements[secret_name] = self._cache[secret_name]
                continue

            try:
                # Get secret by name
                secret = await self.secret_service.get_secret_by_name(secret_name)
                if not secret:
                    error_msg = f"Secret '{secret_name}' not found"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    replacements[secret_name] = f"${{secret:{secret_name}}}"  # Keep original
                    continue

                # Decrypt secret
                decrypted_data, _ = await self.secret_service.reveal_secret(secret.id)

                # Cache the result
                self._cache[secret_name] = decrypted_data
                replacements[secret_name] = decrypted_data

            except ValueError as e:
                error_msg = f"Secret '{secret_name}' not found or inactive: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)
                # Keep original variable if secret not found
                replacements[secret_name] = f"${{secret:{secret_name}}}"
            except Exception as e:
                error_msg = f"Failed to decrypt secret '{secret_name}': {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                # Keep original variable if decryption fails
                replacements[secret_name] = f"${{secret:{secret_name}}}"

        # Replace all variables
        result = text
        for secret_name, replacement in replacements.items():
            pattern = f"${{secret:{secret_name}}}"
            result = result.replace(pattern, replacement)

        return result, errors

    async def validate_variables(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate that all secret variables exist and are accessible

        Args:
            text: Text with secret variables

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        secret_names = self.find_variables(text)

        if not secret_names:
            return True, []

        errors = []

        for secret_name in secret_names:
            try:
                secret = await self.secret_service.get_secret_by_name(secret_name)
                if not secret:
                    errors.append(f"Secret '{secret_name}' not found")
                elif not secret.is_active:
                    errors.append(f"Secret '{secret_name}' is not active")
            except Exception as e:
                errors.append(f"Failed to validate secret '{secret_name}': {e}")

        return len(errors) == 0, errors

    def clear_cache(self):
        """Clear the secret cache"""
        self._cache.clear()


async def parse_secret_variables(
    text: str, session: AsyncSession, validate_only: bool = False
) -> Tuple[str, List[str]]:
    """
    Convenience function to parse secret variables

    Args:
        text: Text with secret variables
        session: Database session
        validate_only: If True, only validate without replacing

    Returns:
        Tuple of (result_text, list_of_errors)
    """
    parser = SecretVariableParser(session)

    if validate_only:
        is_valid, errors = await parser.validate_variables(text)
        return text, errors
    else:
        result, errors = await parser.replace_variables(text)
        return result, errors


def extract_secret_names(text: str) -> List[str]:
    """
    Extract secret names from text without database access

    Args:
        text: Text with secret variables

    Returns:
        List of secret names
    """
    return SecretVariableParser.SECRET_PATTERN.findall(text)
