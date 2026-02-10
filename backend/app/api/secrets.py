#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secret management API routes and models
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, StringConstraints, ConfigDict

from db.database import get_db
from infra.security.secret_service import SecretService
from .unified_middleware import api_error_handler
from api.dependencies import get_current_user
from db.models.user import User
from core.logging import get_logger
from core.rbac import Permission, require_permission

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================


class SecretCreate(BaseModel):
    """Model for creating a new secret"""

    name: Annotated[str, StringConstraints(min_length=3, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique name for the secret"
    )
    secret_type: str = Field(..., description="Type of secret: password, ssh_key, or kubeconfig")
    data: str = Field(..., description="Secret data (will be encrypted)")
    description: Optional[str] = Field(None, description="Description of the secret")
    secret_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")

    @field_validator("secret_type")
    @classmethod
    def validate_secret_type(cls, v):
        valid_types = ["password", "ssh_key", "kubeconfig"]
        if v not in valid_types:
            raise ValueError(f"Secret type must be one of: {valid_types}")
        return v

    @field_validator("data")
    @classmethod
    def validate_data_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Secret data cannot be empty")
        return v


class SecretUpdate(BaseModel):
    """Model for updating an existing secret"""

    name: Optional[Annotated[str, StringConstraints(min_length=3, max_length=100, strip_whitespace=True)]] = Field(
        None, description="New name for the secret"
    )
    data: Optional[str] = Field(None, description="New secret data (will be encrypted)")
    description: Optional[str] = Field(None, description="New description")
    secret_metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")
    is_active: Optional[bool] = Field(None, description="Active status")


class SecretResponse(BaseModel):
    """Model for secret response (without decrypted data)"""

    id: int
    name: str
    secret_type: str
    description: Optional[str]
    secret_metadata: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SecretRevealResponse(BaseModel):
    """Model for secret reveal response (with decrypted data)"""

    id: int
    name: str
    secret_type: str
    data: str  # Decrypted data
    description: Optional[str]
    secret_metadata: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class SecretTestRequest(BaseModel):
    """Model for testing a secret"""

    pass  # No parameters needed


class SecretTestResponse(BaseModel):
    """Model for secret test response"""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class SecretListResponse(BaseModel):
    """Model for secret list response"""

    secrets: list[SecretResponse]
    total: int
    filtered: int


# ============================================================================
# API Routes
# ============================================================================


@router.get("/secrets", response_model=SecretListResponse)
@api_error_handler
@require_permission(Permission.SECRET_READ)
async def list_secrets(
    secret_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List secrets with optional filters

    - **secret_type**: Filter by secret type (password, ssh_key, kubeconfig)
    - **is_active**: Filter by active status
    - **search**: Search in name and description
    - **limit**: Maximum number of results (default: 100)
    - **offset**: Offset for pagination (default: 0)
    """
    service = SecretService(db)
    secrets, total = await service.list_secrets(
        secret_type=secret_type, is_active=is_active, search=search, limit=limit, offset=offset
    )

    return SecretListResponse(
        secrets=[SecretResponse.model_validate(secret) for secret in secrets], total=total, filtered=len(secrets)
    )


@router.get("/secrets/{secret_id}", response_model=SecretResponse)
@api_error_handler
@require_permission(Permission.SECRET_READ)
async def get_secret(
    secret_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get secret details (without decrypted data)

    - **secret_id**: ID of the secret
    """
    service = SecretService(db)
    secret = await service.get_secret(secret_id)

    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret with ID {secret_id} not found")

    return SecretResponse.model_validate(secret)


@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
@api_error_handler
@require_permission(Permission.SECRET_CREATE)
async def create_secret(
    secret_data: SecretCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Create a new secret

    - **name**: Unique name for the secret
    - **secret_type**: Type of secret (password, ssh_key, kubeconfig)
    - **data**: Secret data (will be encrypted)
    - **description**: Optional description
    - **metadata**: Optional metadata as JSON
    """
    service = SecretService(db)

    try:
        secret = await service.create_secret(
            name=secret_data.name,
            secret_type=secret_data.secret_type,
            data=secret_data.data,
            description=secret_data.description,
            secret_metadata=secret_data.secret_metadata,
        )
        return SecretResponse.model_validate(secret)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/secrets/{secret_id}", response_model=SecretResponse)
@api_error_handler
@require_permission(Permission.SECRET_UPDATE)
async def update_secret(
    secret_id: int,
    secret_data: SecretUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing secret

    - **secret_id**: ID of the secret to update
    - **name**: New name (optional)
    - **data**: New data (optional, will be encrypted)
    - **description**: New description (optional)
    - **metadata**: New metadata (optional)
    - **is_active**: New active status (optional)
    """
    service = SecretService(db)

    try:
        secret = await service.update_secret(
            secret_id=secret_id,
            name=secret_data.name,
            data=secret_data.data,
            description=secret_data.description,
            secret_metadata=secret_data.secret_metadata,
            is_active=secret_data.is_active,
        )
        return SecretResponse.model_validate(secret)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/secrets/{secret_id}")
@api_error_handler
@require_permission(Permission.SECRET_DELETE)
async def delete_secret(
    secret_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Delete a secret (hard delete - permanently remove from database)

    - **secret_id**: ID of the secret to delete
    """
    service = SecretService(db)

    success = await service.delete_secret(secret_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret with ID {secret_id} not found")

    return {"message": f"Secret {secret_id} deleted successfully"}


@router.post("/secrets/{secret_id}/reveal", response_model=SecretRevealResponse)
@api_error_handler
@require_permission(Permission.SECRET_READ)
async def reveal_secret(
    secret_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Reveal (decrypt) secret data

    - **secret_id**: ID of the secret to reveal

    **Warning**: This endpoint returns decrypted data. Use with caution.
    """
    service = SecretService(db)

    try:
        decrypted_data, secret = await service.reveal_secret(secret_id)

        return SecretRevealResponse(
            id=secret.id,
            name=secret.name,
            secret_type=secret.secret_type,
            data=decrypted_data,
            description=secret.description,
            secret_metadata=secret.secret_metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/secrets/{secret_id}/test", response_model=SecretTestResponse)
@api_error_handler
@require_permission(Permission.SECRET_READ)
async def test_secret(
    secret_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Test if secret is valid and can be decrypted

    - **secret_id**: ID of the secret to test
    """
    service = SecretService(db)

    success, message, details = await service.test_secret(secret_id)

    return SecretTestResponse(success=success, message=message, details=details)
