#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket message models for real-time communication
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
from api.version import VERSION

# JSON serialization for WebSocket messages


class WebSocketMessage(BaseModel):
    """Base WebSocket message model"""

    type: str
    payload: Dict[str, Any]
    timestamp: str
    target: Optional[List[str]] = None

    def to_json_bytes(self) -> bytes:
        """Serialize message to JSON bytes."""
        return self.model_dump_json().encode('utf-8')

    @classmethod
    def from_json_bytes(cls, data: bytes) -> 'WebSocketMessage':
        """Deserialize message from JSON bytes."""
        return cls.model_validate_json(data.decode('utf-8'))


class TaskMessage(WebSocketMessage):
    """Message for task-related events"""

    type: str  # Will be set by subclasses
    payload: Dict[str, Any]  # task_id, task_type, etc.


class TaskScheduledMessage(TaskMessage):
    """Message when a task is scheduled"""

    type: str = "task_scheduled"


class TaskStartedMessage(TaskMessage):
    """Message when a task starts"""

    type: str = "task_started"


class TaskCompletedMessage(TaskMessage):
    """Message when a task completes"""

    type: str = "task_completed"


class TaskFailedMessage(TaskMessage):
    """Message when a task fails"""

    type: str = "task_failed"


class InspectionMessage(WebSocketMessage):
    """Message for inspection-related events"""

    type: str  # Will be set by subclasses
    payload: Dict[str, Any]  # cluster_name, config, result, etc.


class InspectionStartedMessage(InspectionMessage):
    """Message when inspection starts"""

    type: str = "inspection_started"


class InspectionCompletedMessage(InspectionMessage):
    """Message when inspection completes"""

    type: str = "inspection_completed"


class InspectionFailedMessage(InspectionMessage):
    """Message when inspection fails"""

    type: str = "inspection_failed"


class SystemStatusMessage(WebSocketMessage):
    """Message for system status updates"""

    type: str = "system_status"
    payload: Dict[str, Any]  # status, queue, clusters_count, version


class PingMessage(WebSocketMessage):
    """Message for ping heartbeat"""

    type: str = "ping"
    payload: Dict[str, Any] = {}


class PongMessage(WebSocketMessage):
    """Message for pong response"""

    type: str = "pong"
    payload: Dict[str, Any] = {}


# Convenience functions for creating messages
def create_task_scheduled_message(task_id: str, task_type: str) -> TaskScheduledMessage:
    """Create a task scheduled message"""
    return TaskScheduledMessage(
        payload={"task_id": task_id, "task_type": task_type}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["tasks"]
    )


def create_task_started_message(task_id: str, task_type: str) -> TaskStartedMessage:
    """Create a task started message"""
    return TaskStartedMessage(
        payload={"task_id": task_id, "task_type": task_type}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["tasks"]
    )


def create_task_completed_message(task_id: str, result: Any) -> TaskCompletedMessage:
    """Create a task completed message"""
    return TaskCompletedMessage(
        payload={"task_id": task_id, "result": result}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["tasks"]
    )


def create_task_failed_message(task_id: str, error: str) -> TaskFailedMessage:
    """Create a task failed message"""
    return TaskFailedMessage(
        payload={"task_id": task_id, "error": error}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["tasks"]
    )


def create_inspection_started_message(cluster_name: str, config: Dict[str, Any]) -> InspectionStartedMessage:
    """Create an inspection started message"""
    return InspectionStartedMessage(
        payload={"cluster_name": cluster_name, "config": config}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["inspections"]
    )


def create_inspection_completed_message(cluster_name: str, result: Dict[str, Any]) -> InspectionCompletedMessage:
    """Create an inspection completed message"""
    return InspectionCompletedMessage(
        payload={"cluster_name": cluster_name, "result": result}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["inspections"]
    )


def create_inspection_failed_message(cluster_name: str, error: str) -> InspectionFailedMessage:
    """Create an inspection failed message"""
    return InspectionFailedMessage(
        payload={"cluster_name": cluster_name, "error": error}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), target=["inspections"]
    )


def create_system_status_message(
    status: str, queue: Dict[str, Any], clusters_count: Optional[int] = None, version: str = VERSION
) -> SystemStatusMessage:
    """Create a system status message"""
    return SystemStatusMessage(
        payload={
            "status": status,
            "queue": queue,
            "clusters_count": clusters_count,
            "version": version,
        },
        timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        target=["system_status"],
    )


def create_ping_message() -> PingMessage:
    """Create a ping message"""
    return PingMessage(payload={}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))


def create_pong_message() -> PongMessage:
    """Create a pong message"""
    return PongMessage(payload={}, timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
