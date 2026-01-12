#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database models for secrets management
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from db.models.base import BaseModel


class EncryptionKey(BaseModel):
    """Database model for storing encryption keys"""

    __tablename__ = "encryption_keys"

    # Identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    key_name = Column(String(255), unique=True, nullable=False, index=True)

    # Encryption key (stored directly, not encrypted)
    encryption_key = Column(Text, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Audit timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_encryption_keys_name_active", "key_name", "is_active"),
        Index("idx_encryption_keys_created_at", "created_at"),
    )

    @staticmethod
    def validate_data(data: dict) -> dict:
        """Validate encryption key data before creation/update"""
        if "key_name" in data and not data.get("key_name"):
            raise ValueError("Key name is required")

        if "key_name" in data and (not isinstance(data["key_name"], str) or len(data["key_name"]) > 255):
            raise ValueError("Key name must be a string with max length 255")

        if "encryption_key" in data and not isinstance(data["encryption_key"], str):
            raise ValueError("Encryption key must be a string")

        return data

    def __repr__(self):
        return f"<EncryptionKey(id={self.id}, name='{self.key_name}', active={self.is_active})>"


class Secret(BaseModel):
    """Database model for storing encrypted secrets"""

    __tablename__ = "secrets"

    # Identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Secret type
    secret_type = Column(String(50), nullable=False, index=True)  # 'password', 'ssh_key', 'kubeconfig'

    # Encrypted data
    encrypted_data = Column(Text, nullable=False)

    # Metadata (JSON)
    secret_metadata = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Audit timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_secrets_name_type", "name", "secret_type"),
        Index("idx_secrets_type_active", "secret_type", "is_active"),
        Index("idx_secrets_created_at", "created_at"),
        Index("idx_secrets_last_used", "last_used_at"),
    )

    @staticmethod
    def validate_data(data: dict) -> dict:
        """Validate secret data before creation/update"""
        if "name" in data and not data.get("name"):
            raise ValueError("Secret name is required")

        if "name" in data and (not isinstance(data["name"], str) or len(data["name"]) > 255):
            raise ValueError("Secret name must be a string with max length 255")

        if "secret_type" in data:
            valid_types = ["password", "ssh_key", "kubeconfig"]
            if data["secret_type"] not in valid_types:
                raise ValueError(f"Secret type must be one of: {valid_types}")

        if "encrypted_data" in data and not isinstance(data["encrypted_data"], str):
            raise ValueError("Encrypted data must be a string")

        return data

    def __repr__(self):
        return f"<Secret(id={self.id}, name='{self.name}', type='{self.secret_type}', active={self.is_active})>"
