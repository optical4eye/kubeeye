#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event bus for decoupled communication between components
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from core.logging import get_logger
from infra.websocket.websocket_manager import websocket_manager
from infra.websocket.message_models import (
    create_task_scheduled_message,
    create_task_started_message,
    create_task_completed_message,
    create_task_failed_message,
    create_inspection_started_message,
    create_inspection_completed_message,
    create_inspection_failed_message,
    create_system_status_message,
)
from api.version import VERSION

logger = get_logger(__name__)


class EventType(Enum):
    """Event types"""

    INSPECTION_STARTED = "inspection_started"
    INSPECTION_COMPLETED = "inspection_completed"
    INSPECTION_FAILED = "inspection_failed"
    NODE_CHECK_STARTED = "node_check_started"
    NODE_CHECK_COMPLETED = "node_check_completed"
    OPA_CHECK_STARTED = "opa_check_started"
    OPA_CHECK_COMPLETED = "opa_check_completed"
    POPEYE_CHECK_STARTED = "popeye_check_started"
    POPEYE_CHECK_COMPLETED = "popeye_check_completed"
    DATABASE_CONNECTION_CREATED = "database_connection_created"
    DATABASE_CONNECTION_CLOSED = "database_connection_closed"
    SSH_CONNECTION_CREATED = "ssh_connection_created"
    SSH_CONNECTION_CLOSED = "ssh_connection_closed"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    TASK_SCHEDULED = "task_scheduled"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_STATUS = "system_status"


@dataclass
class Event:
    """Event data structure"""

    type: EventType
    data: Dict[str, Any]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {"type": self.type.value, "data": self.data, "timestamp": self.timestamp}


class EventBus:
    """Simple event bus for decoupled communication"""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._event_history: List[Event] = []
        self._max_history_size = 1000

    async def subscribe(self, event_type: EventType, handler: Callable):
        """
        Subscribe to event type

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed to {event_type.value}")

    async def publish(self, event: Event):
        """
        Publish event to all subscribers

        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event: {event.type.value}")

        # Add to history
        self._add_to_history(event)

        # Get handlers for this event type
        handlers = self._subscribers.get(event.type, [])

        if not handlers:
            logger.debug(f"No subscribers for event: {event.type.value}")
            return

        # Execute all handlers asynchronously
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any handler errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {i} for event {event.type.value} failed: {result}")

    async def unsubscribe(self, event_type: EventType, handler: Callable):
        """
        Unsubscribe from event type

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        async with self._lock:
            if event_type in self._subscribers:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    logger.debug(f"Unsubscribed from {event_type.value}")

    def _add_to_history(self, event: Event):
        """
        Add event to history

        Args:
            event: Event to add
        """
        self._event_history.append(event)

        # Keep history size limited
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """
        Get event history

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        if event_type:
            filtered = [e for e in self._event_history if e.type == event_type]
            return filtered[-limit:] if limit else filtered
        else:
            return self._event_history[-limit:] if limit else self._event_history

    def clear_history(self):
        """Clear event history"""
        self._event_history.clear()
        logger.debug("Event history cleared")

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get number of subscribers for event type

        Args:
            event_type: Type of event

        Returns:
            Number of subscribers
        """
        return len(self._subscribers.get(event_type, []))

    def get_all_subscriber_counts(self) -> Dict[str, int]:
        """
        Get subscriber counts for all event types

        Returns:
            Dictionary mapping event type names to subscriber counts
        """
        return {event_type.value: len(handlers) for event_type, handlers in self._subscribers.items()}

    async def clear_all_subscribers(self):
        """Clear all subscribers"""
        async with self._lock:
            self._subscribers.clear()
            logger.info("All subscribers cleared")


# WebSocket event handlers
async def handle_task_scheduled(event: Event):
    """Handle task scheduled event and broadcast via WebSocket"""
    task_id = event.data.get("task_id")
    task_type = event.data.get("task_type")
    if isinstance(task_id, str) and isinstance(task_type, str):
        message = create_task_scheduled_message(task_id=task_id, task_type=task_type)
        await websocket_manager.broadcast(message.dict())


async def handle_task_started(event: Event):
    """Handle task started event and broadcast via WebSocket"""
    task_id = event.data.get("task_id")
    task_type = event.data.get("task_type")
    if isinstance(task_id, str) and isinstance(task_type, str):
        message = create_task_started_message(task_id=task_id, task_type=task_type)
        await websocket_manager.broadcast(message.dict())


async def handle_task_completed(event: Event):
    """Handle task completed event and broadcast via WebSocket"""
    task_id = event.data.get("task_id")
    result = event.data.get("result")
    if isinstance(task_id, str):
        message = create_task_completed_message(task_id=task_id, result=result)
        await websocket_manager.broadcast(message.dict())


async def handle_task_failed(event: Event):
    """Handle task failed event and broadcast via WebSocket"""
    task_id = event.data.get("task_id")
    error = event.data.get("error")
    if isinstance(task_id, str) and isinstance(error, str):
        message = create_task_failed_message(task_id=task_id, error=error)
        await websocket_manager.broadcast(message.dict())


async def handle_inspection_started(event: Event):
    """Handle inspection started event and broadcast via WebSocket"""
    cluster_name = event.data.get("cluster_name")
    config = event.data.get("config")
    if isinstance(cluster_name, str) and isinstance(config, dict):
        message = create_inspection_started_message(cluster_name=cluster_name, config=config)
        await websocket_manager.broadcast(message.dict())


async def handle_inspection_completed(event: Event):
    """Handle inspection completed event and broadcast via WebSocket"""
    cluster_name = event.data.get("cluster_name")
    result = event.data.get("result")
    if isinstance(cluster_name, str) and isinstance(result, dict):
        message = create_inspection_completed_message(cluster_name=cluster_name, result=result)
        await websocket_manager.broadcast(message.dict())


async def handle_inspection_failed(event: Event):
    """Handle inspection failed event and broadcast via WebSocket"""
    cluster_name = event.data.get("cluster_name")
    error = event.data.get("error")
    if isinstance(cluster_name, str) and isinstance(error, str):
        message = create_inspection_failed_message(cluster_name=cluster_name, error=error)
        await websocket_manager.broadcast(message.dict())


async def handle_system_status(event: Event):
    """Handle system status event and broadcast via WebSocket"""
    status = event.data.get("status")
    queue = event.data.get("queue")
    clusters_count = event.data.get("clusters_count")
    version = event.data.get("version", VERSION)
    if isinstance(status, str) and isinstance(queue, dict):
        message = create_system_status_message(
            status=status, queue=queue, clusters_count=clusters_count, version=version
        )
        await websocket_manager.broadcast(message.dict())


# Global event bus instance
event_bus = EventBus()


# Initialize WebSocket subscriptions
async def init_websocket_subscriptions():
    """Initialize WebSocket event subscriptions"""
    await event_bus.subscribe(EventType.TASK_SCHEDULED, handle_task_scheduled)
    await event_bus.subscribe(EventType.TASK_STARTED, handle_task_started)
    await event_bus.subscribe(EventType.TASK_COMPLETED, handle_task_completed)
    await event_bus.subscribe(EventType.TASK_FAILED, handle_task_failed)
    await event_bus.subscribe(EventType.INSPECTION_STARTED, handle_inspection_started)
    await event_bus.subscribe(EventType.INSPECTION_COMPLETED, handle_inspection_completed)
    await event_bus.subscribe(EventType.INSPECTION_FAILED, handle_inspection_failed)
    await event_bus.subscribe(EventType.SYSTEM_STATUS, handle_system_status)
    logger.info("WebSocket event subscriptions initialized")


# Convenience functions for common event operations
async def publish_inspection_started(cluster_name: str, config: Dict[str, Any]):
    """Publish inspection started event"""
    event = Event(
        type=EventType.INSPECTION_STARTED,
        data={"cluster_name": cluster_name, "config": config},
        timestamp=asyncio.get_event_loop().time(),
    )
    await event_bus.publish(event)


async def publish_inspection_completed(cluster_name: str, result: Dict[str, Any]):
    """Publish inspection completed event"""
    event = Event(
        type=EventType.INSPECTION_COMPLETED,
        data={"cluster_name": cluster_name, "result": result},
        timestamp=asyncio.get_event_loop().time(),
    )
    await event_bus.publish(event)


async def publish_inspection_failed(cluster_name: str, error: str):
    """Publish inspection failed event"""
    event = Event(
        type=EventType.INSPECTION_FAILED,
        data={"cluster_name": cluster_name, "error": error},
        timestamp=asyncio.get_event_loop().time(),
    )
    await event_bus.publish(event)


async def publish_task_started(task_id: str, task_type: str):
    """Publish task started event"""
    event = Event(
        type=EventType.TASK_STARTED,
        data={"task_id": task_id, "task_type": task_type},
        timestamp=asyncio.get_event_loop().time(),
    )
    await event_bus.publish(event)


async def publish_task_completed(task_id: str, result: Any):
    """Publish task completed event"""
    event = Event(
        type=EventType.TASK_COMPLETED,
        data={"task_id": task_id, "result": result},
        timestamp=asyncio.get_event_loop().time(),
    )
    await event_bus.publish(event)


async def publish_task_failed(task_id: str, error: str):
    """Publish task failed event"""
    event = Event(
        type=EventType.TASK_FAILED, data={"task_id": task_id, "error": error}, timestamp=asyncio.get_event_loop().time()
    )
    await event_bus.publish(event)
