#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
        ..., description="Unique name for cluster"
    )
    nodes: List[Dict[str, Any]] = Field(..., description="List of cluster nodes with connection details")
    kubeconfig: Optional[str] = Field(None, description="Base64 encoded kubeconfig content")

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

    nodes: List[Dict[str, Any]] = Field(..., description="List of nodes to test connectivity")

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

    kubeconfig: str = Field(..., description="Base64 encoded kubeconfig content to test")


class GetNodesFromKubeconfigRequest(BaseModel):
    """Model for getting nodes from kubeconfig"""

    kubeconfig: str = Field(..., description="Base64 encoded kubeconfig content")


class InspectionRequest(BaseModel):
    """Model for requesting cluster inspection"""

    cluster_name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Name of cluster to inspect"
    )
    selected_rules: Optional[Dict[str, List[str]]] = Field(None, description="Rules to apply by type (node, opa)")
    inspection_type: str = Field("immediate", description="Type of inspection: immediate or scheduled")

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
        ..., description="Unique name for the scheduled task"
    )
    description: Annotated[str, StringConstraints(min_length=1, max_length=500, strip_whitespace=True)] = Field(
        ..., description="Description of task"
    )
    cluster: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Target cluster name"
    )
    cron_expr: str = Field(..., description="Cron expression for scheduling")
    rules: Dict[str, List[str]] = Field(..., description="Rules configuration for inspection")
    enabled: bool = Field(True, description="Whether task is enabled")
    task_type: Optional[str] = Field(None, description="Type of scheduled task")
    run_datetime: Optional[str] = Field(None, description="Specific datetime to run (alternative to cron)")

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
    repository: Optional[Dict[str, Any]] = None


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


# New models for queue management with validation
class QueueStatusRequest(BaseModel):
    """Model for queue status requests"""

    pass  # No parameters needed for status request


class QueueTasksRequest(BaseModel):
    """Model for queue tasks request with validation"""

    limit: int = Field(default=50, ge=1, le=1000, description="Maximum number of tasks to return (1-1000)")
    status_filter: Optional[str] = Field(
        None, description="Filter tasks by status (pending, running, completed, failed)"
    )

    @field_validator("status_filter")
    @classmethod
    def validate_status_filter(cls, v):
        # Use centralized validation
        return validate_status_filter(v)


class TaskIdRequest(BaseModel):
    """Model for task ID requests with validation"""

    task_id: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique identifier for task"
    )

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v):
        # Use centralized validation
        return validate_task_id(v)
