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


# Global event bus instance
event_bus = EventBus()


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
