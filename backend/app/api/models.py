import re
from pydantic import BaseModel, Field, field_validator, StringConstraints
from typing import List, Optional, Dict, Any, Annotated


class ClusterCreate(BaseModel):
    """Model for creating a new cluster configuration"""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique name for the cluster"
    )
    nodes: List[Dict[str, Any]] = Field(..., description="List of cluster nodes with connection details")
    prometheus_config: Optional[Dict[str, Any]] = Field(None, description="Prometheus server configuration")
    kubeconfig: Optional[str] = Field(None, description="Base64 encoded kubeconfig content")

    @field_validator("name")
    @classmethod
    def validate_cluster_name(cls, v):
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Cluster name can only contain alphanumeric characters, hyphens, and underscores")
        return v


class TestNodesRequest(BaseModel):
    """Model for testing node connectivity"""

    nodes: List[Dict[str, Any]] = Field(..., description="List of nodes to test connectivity")


class TestKubeconfigRequest(BaseModel):
    """Model for testing kubeconfig validity"""

    kubeconfig: str = Field(..., description="Base64 encoded kubeconfig content to test")


class InspectionRequest(BaseModel):
    """Model for requesting cluster inspection"""

    cluster_name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Name of the cluster to inspect"
    )
    selected_rules: Optional[Dict[str, List[str]]] = Field(
        None, description="Rules to apply by type (node, prometheus, opa)"
    )
    inspection_type: str = Field("immediate", description="Type of inspection: immediate or scheduled")

    @field_validator("cluster_name")
    @classmethod
    def validate_cluster_name(cls, v):
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Cluster name can only contain alphanumeric characters, hyphens, and underscores")
        return v

    @field_validator("inspection_type")
    @classmethod
    def validate_inspection_type(cls, v):
        if v not in ["immediate", "scheduled"]:
            raise ValueError('Inspection type must be either "immediate" or "scheduled"')
        return v


class ScheduledTaskCreate(BaseModel):
    """Model for creating scheduled inspection tasks"""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique name for the scheduled task"
    )
    description: Annotated[str, StringConstraints(min_length=1, max_length=500, strip_whitespace=True)] = Field(
        ..., description="Description of the task"
    )
    cluster: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Target cluster name"
    )
    cron_expr: str = Field(..., description="Cron expression for scheduling")
    rules: Dict[str, Any] = Field(..., description="Rules configuration for the inspection")
    enabled: bool = Field(True, description="Whether the task is enabled")
    task_type: Optional[str] = Field(None, description="Type of scheduled task")
    run_datetime: Optional[str] = Field(None, description="Specific datetime to run (alternative to cron)")

    @field_validator("name")
    @classmethod
    def validate_task_name(cls, v):
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Task name can only contain alphanumeric characters, hyphens, and underscores")
        return v

    @field_validator("cluster")
    @classmethod
    def validate_cluster_name(cls, v):
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Cluster name can only contain alphanumeric characters, hyphens, and underscores")
        return v


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
        if v is not None and v not in ["pending", "running", "completed", "failed"]:
            raise ValueError("Status filter must be one of: pending, running, completed, failed")
        return v


class TaskIdRequest(BaseModel):
    """Model for task ID requests with validation"""

    task_id: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = Field(
        ..., description="Unique identifier for the task"
    )

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v):
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Task ID can only contain alphanumeric characters, hyphens, and underscores")
        return v


# Sanitization utilities
def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input by removing potentially harmful characters"""
    if not isinstance(value, str):
        return str(value)

    # Remove control characters except newlines and tabs
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def sanitize_dict(data: Dict[str, Any], max_key_length: int = 100, max_value_length: int = 1000) -> Dict[str, Any]:
    """Sanitize dictionary keys and values"""
    if not isinstance(data, dict):
        return {}

    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        sanitized_key = sanitize_string(str(key), max_key_length)

        # Sanitize value based on type
        if isinstance(value, str):
            sanitized_value = sanitize_string(value, max_value_length)
        elif isinstance(value, dict):
            sanitized_value = sanitize_dict(value, max_key_length, max_value_length)
        elif isinstance(value, list):
            sanitized_value = [
                sanitize_string(str(item), max_value_length) if isinstance(item, str) else item for item in value
            ]
        else:
            sanitized_value = value

        sanitized[sanitized_key] = sanitized_value

    return sanitized
