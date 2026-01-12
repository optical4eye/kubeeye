#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified validation using Pydantic V2
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_core import ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


class ClusterValidationModel(BaseModel):
    """Simplified cluster validation using Pydantic V2"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255, description="Cluster name")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Node configurations")
    kubeconfig: Optional[str] = Field(None, description="Kubernetes configuration")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate cluster name"""
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("Cluster name must contain only alphanumeric characters, underscores, or hyphens")
        return v.lower()

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate node configurations"""
        for i, node in enumerate(v):
            if "ip" not in node:
                raise ValueError(f'Node at index {i} must have an "ip" field')
            if "name" not in node:
                node["name"] = node["ip"]  # Default name to IP
        return v


class InspectionValidationModel(BaseModel):
    """Simplified inspection validation"""

    cluster_name: str = Field(..., min_length=1, description="Cluster name")
    inspection_type: str = Field(default="immediate", description="Inspection type")
    selected_rules: Optional[Dict[str, List[str]]] = Field(None, description="Selected rules")

    @field_validator("inspection_type")
    @classmethod
    def validate_inspection_type(cls, v: str) -> str:
        """Validate inspection type"""
        allowed_types = ["immediate", "scheduled"]
        if v not in allowed_types:
            raise ValueError(f"Inspection type must be one of {allowed_types}")
        return v


class NodeValidationModel(BaseModel):
    """Simplified node validation"""

    ip: str = Field(..., description="Node IP address")
    port: int = Field(default=22, ge=1, le=65535, description="SSH port")
    username: str = Field(..., min_length=1, description="SSH username")
    auth_type: str = Field(default="password", description="Authentication type")
    password: Optional[str] = Field(None, description="SSH password")
    ssh_key: Optional[str] = Field(None, description="SSH private key (use ${secret:secret-name} syntax)")

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate authentication type"""
        allowed_types = ["password", "key"]
        if v not in allowed_types:
            raise ValueError(f"Authentication type must be one of {allowed_types}")
        return v

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address"""
        import ipaddress

        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")
        return v


def validate_cluster(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate cluster data using Pydantic"""
    try:
        validated = ClusterValidationModel(**data)
        return validated.model_dump()
    except ValidationError as e:
        logger.error(f"Cluster validation failed: {e}")
        raise ValueError(f"Invalid cluster data: {e}")


def validate_inspection(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate inspection data using Pydantic"""
    try:
        validated = InspectionValidationModel(**data)
        return validated.model_dump()
    except ValidationError as e:
        logger.error(f"Inspection validation failed: {e}")
        raise ValueError(f"Invalid inspection data: {e}")


def validate_node(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate node data using Pydantic"""
    try:
        validated = NodeValidationModel(**data)
        return validated.model_dump()
    except ValidationError as e:
        logger.error(f"Node validation failed: {e}")
        raise ValueError(f"Invalid node data: {e}")
