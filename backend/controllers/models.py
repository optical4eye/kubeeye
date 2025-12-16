from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ClusterCreate(BaseModel):
    """Model for creating a new cluster configuration"""

    name: str = Field(..., description="Unique name for the cluster")
    nodes: List[Dict[str, Any]] = Field(
        ..., description="List of cluster nodes with connection details"
    )
    prometheus_config: Optional[Dict[str, Any]] = Field(
        None, description="Prometheus server configuration"
    )
    kubeconfig: Optional[str] = Field(
        None, description="Base64 encoded kubeconfig content"
    )


class TestNodesRequest(BaseModel):
    """Model for testing node connectivity"""

    nodes: List[Dict[str, Any]] = Field(
        ..., description="List of nodes to test connectivity"
    )


class TestKubeconfigRequest(BaseModel):
    """Model for testing kubeconfig validity"""

    kubeconfig: str = Field(
        ..., description="Base64 encoded kubeconfig content to test"
    )


class InspectionRequest(BaseModel):
    """Model for requesting cluster inspection"""

    cluster_name: str = Field(..., description="Name of the cluster to inspect")
    selected_rules: Dict[str, List[str]] = Field(
        ..., description="Rules to apply by type (node, prometheus, opa)"
    )
    inspection_type: str = Field(
        "immediate", description="Type of inspection: immediate or scheduled"
    )


class ScheduledTaskCreate(BaseModel):
    """Model for creating scheduled inspection tasks"""

    name: str = Field(..., description="Unique name for the scheduled task")
    description: str = Field(..., min_length=1, description="Description of the task")
    cluster: str = Field(..., description="Target cluster name")
    cron_expr: str = Field(..., description="Cron expression for scheduling")
    rules: Dict[str, Any] = Field(
        ..., description="Rules configuration for the inspection"
    )
    enabled: bool = Field(True, description="Whether the task is enabled")
    task_type: Optional[str] = Field(None, description="Type of scheduled task")
    run_datetime: Optional[str] = Field(
        None, description="Specific datetime to run (alternative to cron)"
    )


class GitOpsConfig(BaseModel):
    repository: Optional[Dict[str, Any]] = None


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None