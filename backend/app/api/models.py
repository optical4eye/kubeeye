#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, StringConstraints
from typing import List, Optional, Dict, Any, Annotated
from core.common.unified_validation import (
    validate_task_name,
    validate_status_filter,
    validate_inspection_type,
    validate_node_data,
    validate_cluster_name,
    validate_task_id,
)
from infra.security.secret_service import SecretValidator


class ClusterCreate(BaseModel):
    """Model for creating a new cluster configuration"""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique name for cluster", examples=["production-cluster"]
    )
    nodes: List[Dict[str, Any]] = Field(
        ...,
        description="List of cluster nodes with connection details",
        examples=[
            [
                {
                    "ip": "192.168.1.10",
                    "port": 22,
                    "auth": {"type": "password", "username": "kube", "password": "secret123"},
                    "name": "master-node",
                },
                {
                    "ip": "192.168.1.11",
                    "port": 22,
                    "auth": {"type": "key", "username": "kube", "key_path": "/path/to/key"},
                    "name": "worker-node-1",
                },
            ]
        ],
    )
    kubeconfig: Optional[str] = Field(
        None, description="Base64 encoded kubeconfig content", examples=["LS0tLS1CRUdJTi..."]
    )

    @field_validator("name")
    @classmethod
    def validate_cluster_name(cls, v):
        # Use centralized validation
        return validate_cluster_name(v)

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        """Validate all nodes in cluster using centralized validation"""
        if not isinstance(v, list):
            raise ValueError("Nodes must be a list")

        validated_nodes = []
        for i, node in enumerate(v):
            try:
                # Use strict validation for cluster creation (requires auth fields)
                validated_node = validate_node_data(node, strict=True)
                validated_nodes.append(validated_node)
            except ValueError as e:
                raise ValueError(f"Node {i + 1} validation error: {str(e)}")

        return validated_nodes

    @field_validator("kubeconfig")
    @classmethod
    def validate_kubeconfig(cls, v):
        """Validate kubeconfig - must be a secret reference"""
        if v is None:
            return v

        is_valid, error_message = SecretValidator.validate_kubeconfig(v)
        if not is_valid:
            raise ValueError(error_message)

        return v


class NodesTestRequest(BaseModel):
    """Model for testing node connectivity"""

    nodes: List[Dict[str, Any]] = Field(
        ...,
        description="List of nodes to test connectivity",
        examples=[
            [
                {
                    "ip": "192.168.1.10",
                    "port": 22,
                    "auth": {"type": "password", "username": "kube", "password": "secret123"},
                },
                {
                    "ip": "192.168.1.11",
                    "port": 22,
                    "auth": {"type": "key", "username": "kube", "key_path": "/path/to/key"},
                },
            ]
        ],
    )

    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v):
        """Validate all nodes for testing using centralized validation"""
        if not isinstance(v, list):
            raise ValueError("Nodes must be a list")

        validated_nodes = []
        for i, node in enumerate(v):
            try:
                # Use non-strict validation for connectivity testing (only ip and port required)
                validated_node = validate_node_data(node, strict=False)
                validated_nodes.append(validated_node)
            except ValueError as e:
                raise ValueError(f"Node {i + 1} validation error: {str(e)}")

        return validated_nodes


class KubeconfigTestRequest(BaseModel):
    """Model for testing kubeconfig validity"""

    kubeconfig: str = Field(
        ..., description="Base64 encoded kubeconfig content to test", examples=["LS0tLS1CRUdJTi..."]
    )


class GetNodesFromKubeconfigRequest(BaseModel):
    """Model for getting nodes from kubeconfig"""

    kubeconfig: str = Field(..., description="Base64 encoded kubeconfig content", examples=["LS0tLS1CRUdJTi..."])


class InspectionRequest(BaseModel):
    """Model for requesting cluster inspection"""

    cluster_name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Name of cluster to inspect", examples=["production-cluster"]
    )
    selected_rules: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Rules to apply by type (node, opa)",
        examples=[{"node": ["check_kernel_version", "check_disk_space"], "opa": ["check_pod_security"]}],
    )
    selected_tags: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Tags to filter rules by type (node, opa)",
        examples=[{"node": ["security", "performance"], "opa": ["compliance"]}],
    )
    inspection_type: str = Field(
        "immediate", description="Type of inspection: immediate or scheduled", examples=["immediate"]
    )

    @field_validator("cluster_name")
    @classmethod
    def validate_cluster_name(cls, v):
        # Use centralized validation
        return validate_cluster_name(v)

    @field_validator("inspection_type")
    @classmethod
    def validate_inspection_type(cls, v):
        # Use centralized validation
        return validate_inspection_type(v)


class ScheduledTaskCreate(BaseModel):
    """Model for creating scheduled inspection tasks"""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique name for the scheduled task", examples=["daily-security-check"]
    )
    description: Annotated[str, StringConstraints(min_length=1, max_length=500, strip_whitespace=True)] = Field(
        ..., description="Description of task", examples=["Daily security inspection of production cluster"]
    )
    cluster: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Target cluster name", examples=["production-cluster"]
    )
    cron_expr: str = Field(..., description="Cron expression for scheduling", examples=["0 2 * * *"])
    rules: Dict[str, List[str]] = Field(
        ...,
        description="Rules configuration for inspection",
        examples=[{"node": ["check_kernel_version", "check_disk_space"], "opa": ["check_pod_security"]}],
    )
    tags: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Tags to filter rules by type (node, opa)",
        examples=[{"node": ["security"], "opa": ["compliance"]}],
    )
    enabled: bool = Field(True, description="Whether task is enabled", examples=[True])
    task_type: Optional[str] = Field(None, description="Type of scheduled task", examples=["inspection"])
    run_datetime: Optional[str] = Field(
        None, description="Specific datetime to run (alternative to cron)", examples=["2024-01-15T14:30:00Z"]
    )

    @field_validator("name")
    @classmethod
    def validate_task_name(cls, v):
        # Use centralized validation
        return validate_task_name(v)

    @field_validator("cluster")
    @classmethod
    def validate_cluster_name(cls, v):
        # Use centralized validation
        return validate_cluster_name(v)


class GitOpsConfig(BaseModel):
    repository: Optional[Dict[str, Any]] = Field(
        None,
        description="Git repository configuration",
        examples=[
            {
                "url": "https://github.com/user/kubeeye-rules.git",
                "branch": "main",
                "path": "rules",
                "auth": {"type": "token", "token": "ghp_..."},
            }
        ],
    )


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = Field(None, description="Whether the rule is enabled", examples=[True])
    config: Optional[Dict[str, Any]] = Field(
        None, description="Rule configuration parameters", examples=[{"severity": "high", "timeout": 30}]
    )


# New models for queue management with validation
class QueueStatusRequest(BaseModel):
    """Model for queue status requests"""

    pass  # No parameters needed for status request


class QueueTasksRequest(BaseModel):
    """Model for queue tasks request with validation"""

    limit: int = Field(
        default=50, ge=1, le=1000, description="Maximum number of tasks to return (1-1000)", examples=[50]
    )
    status_filter: Optional[str] = Field(
        None, description="Filter tasks by status (pending, running, completed, failed)", examples=["pending"]
    )

    @field_validator("status_filter")
    @classmethod
    def validate_status_filter(cls, v):
        # Use centralized validation
        return validate_status_filter(v)


class TaskIdRequest(BaseModel):
    """Model for task ID requests with validation"""

    task_id: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique identifier for task", examples=["task-12345"]
    )

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v):
        # Use centralized validation
        return validate_task_id(v)


# Authentication models
class LoginRequest(BaseModel):
    """Login request model - local auth only (OAuth is separate)"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    auth_type: Optional[str] = Field(None, description="Authentication type: 'local' only (deprecated)")

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, v):
        if v is not None and v not in ("local",):
            raise ValueError("auth_type must be 'local'")
        return v


class TokenResponse(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """User response model"""

    id: int
    username: str
    email: str
    role: str
    auth_type: str = "local"  # 'local' or 'oauth'
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """User create request model (admin only)"""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: str = Field(default="operator")  # Default role for new users
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        from db.models.user import UserRole

        if not UserRole.is_valid(v):
            raise ValueError(f"Invalid role. Must be one of: {UserRole.all()}")
        return v


class UserUpdateRequest(BaseModel):
    """User update request model (admin only)"""

    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None:
            from db.models.user import UserRole

            if not UserRole.is_valid(v):
                raise ValueError(f"Invalid role. Must be one of: {UserRole.all()}")
        return v
