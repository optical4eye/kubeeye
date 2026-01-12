#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for EventBus
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from core.events.event_bus import (
    EventType,
    Event,
    EventBus,
    event_bus,
    publish_inspection_started,
    publish_inspection_completed,
    publish_inspection_failed,
    publish_task_started,
    publish_task_completed,
    publish_task_failed,
)


class TestEvent:
    """Tests for Event dataclass"""

    def test_event_creation(self):
        """Test creating an event"""
        event = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=123.456)
        assert event.type == EventType.INSPECTION_STARTED
        assert event.data == {"cluster_name": "test"}
        assert event.timestamp == 123.456

    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        event = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=123.456)
        event_dict = event.to_dict()
        assert event_dict["type"] == "inspection_started"
        assert event_dict["data"] == {"cluster_name": "test"}
        assert event_dict["timestamp"] == 123.456


class TestEventBus:
    """Tests for EventBus"""

    @pytest.fixture
    def bus(self):
        """Create a new event bus for each test"""
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        """Test subscribing to and publishing events"""
        handler = AsyncMock()
        await bus.subscribe(EventType.INSPECTION_STARTED, handler)

        event = Event(
            type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=asyncio.get_event_loop().time()
        )
        await bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        """Test multiple subscribers to the same event"""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()

        await bus.subscribe(EventType.INSPECTION_STARTED, handler1)
        await bus.subscribe(EventType.INSPECTION_STARTED, handler2)
        await bus.subscribe(EventType.INSPECTION_STARTED, handler3)

        event = Event(
            type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=asyncio.get_event_loop().time()
        )
        await bus.publish(event)

        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        """Test unsubscribing from events"""
        handler = AsyncMock()
        await bus.subscribe(EventType.INSPECTION_STARTED, handler)

        event = Event(
            type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=asyncio.get_event_loop().time()
        )
        await bus.publish(event)
        assert handler.call_count == 1

        await bus.unsubscribe(EventType.INSPECTION_STARTED, handler)
        await bus.publish(event)
        assert handler.call_count == 1  # Should not be called again

    @pytest.mark.asyncio
    async def test_handler_exception(self, bus):
        """Test that handler exceptions don't stop other handlers"""
        handler1 = AsyncMock(side_effect=Exception("Handler failed"))
        handler2 = AsyncMock()

        await bus.subscribe(EventType.INSPECTION_STARTED, handler1)
        await bus.subscribe(EventType.INSPECTION_STARTED, handler2)

        event = Event(
            type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=asyncio.get_event_loop().time()
        )
        await bus.publish(event)

        handler1.assert_called_once()
        handler2.assert_called_once()  # Should still be called

    @pytest.mark.asyncio
    async def test_no_subscribers(self, bus):
        """Test publishing event with no subscribers"""
        event = Event(
            type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=asyncio.get_event_loop().time()
        )
        # Should not raise an exception
        await bus.publish(event)

    @pytest.mark.asyncio
    async def test_event_history(self, bus):
        """Test event history tracking"""
        event1 = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test1"}, timestamp=1.0)
        event2 = Event(type=EventType.INSPECTION_COMPLETED, data={"cluster_name": "test2"}, timestamp=2.0)

        await bus.publish(event1)
        await bus.publish(event2)

        history = bus.get_history()
        assert len(history) == 2
        assert history[0] == event1
        assert history[1] == event2

    @pytest.mark.asyncio
    async def test_event_history_filter_by_type(self, bus):
        """Test filtering event history by type"""
        event1 = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test1"}, timestamp=1.0)
        event2 = Event(type=EventType.INSPECTION_COMPLETED, data={"cluster_name": "test2"}, timestamp=2.0)
        event3 = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test3"}, timestamp=3.0)

        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event3)

        history = bus.get_history(event_type=EventType.INSPECTION_STARTED)
        assert len(history) == 2
        assert history[0] == event1
        assert history[1] == event3

    @pytest.mark.asyncio
    async def test_event_history_limit(self, bus):
        """Test limiting event history"""
        for i in range(10):
            event = Event(type=EventType.INSPECTION_STARTED, data={"index": i}, timestamp=float(i))
            await bus.publish(event)

        history = bus.get_history(limit=5)
        assert len(history) == 5
        assert history[0].data["index"] == 5
        assert history[4].data["index"] == 9

    @pytest.mark.asyncio
    async def test_clear_history(self, bus):
        """Test clearing event history"""
        event = Event(type=EventType.INSPECTION_STARTED, data={"cluster_name": "test"}, timestamp=1.0)
        await bus.publish(event)

        assert len(bus.get_history()) == 1

        bus.clear_history()

        assert len(bus.get_history()) == 0

    def test_get_subscriber_count(self, bus):
        """Test getting subscriber count"""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        # Use sync version for this test
        asyncio.run(bus.subscribe(EventType.INSPECTION_STARTED, handler1))
        asyncio.run(bus.subscribe(EventType.INSPECTION_STARTED, handler2))

        count = bus.get_subscriber_count(EventType.INSPECTION_STARTED)
        assert count == 2

        count = bus.get_subscriber_count(EventType.INSPECTION_COMPLETED)
        assert count == 0

    def test_get_all_subscriber_counts(self, bus):
        """Test getting all subscriber counts"""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        asyncio.run(bus.subscribe(EventType.INSPECTION_STARTED, handler1))
        asyncio.run(bus.subscribe(EventType.INSPECTION_STARTED, handler2))
        asyncio.run(bus.subscribe(EventType.INSPECTION_COMPLETED, handler1))

        counts = bus.get_all_subscriber_counts()
        assert counts["inspection_started"] == 2
        assert counts["inspection_completed"] == 1

    @pytest.mark.asyncio
    async def test_clear_all_subscribers(self, bus):
        """Test clearing all subscribers"""
        handler = AsyncMock()
        await bus.subscribe(EventType.INSPECTION_STARTED, handler)
        await bus.subscribe(EventType.INSPECTION_COMPLETED, handler)

        assert bus.get_subscriber_count(EventType.INSPECTION_STARTED) == 1
        assert bus.get_subscriber_count(EventType.INSPECTION_COMPLETED) == 1

        await bus.clear_all_subscribers()

        assert bus.get_subscriber_count(EventType.INSPECTION_STARTED) == 0
        assert bus.get_subscriber_count(EventType.INSPECTION_COMPLETED) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    @pytest.mark.asyncio
    async def test_publish_inspection_started(self):
        """Test publish_inspection_started function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.INSPECTION_STARTED, handler)

        await publish_inspection_started("test-cluster", {"key": "value"})

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.INSPECTION_STARTED
        assert event.data["cluster_name"] == "test-cluster"
        assert event.data["config"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_publish_inspection_completed(self):
        """Test publish_inspection_completed function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.INSPECTION_COMPLETED, handler)

        await publish_inspection_completed("test-cluster", {"status": "success"})

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.INSPECTION_COMPLETED
        assert event.data["cluster_name"] == "test-cluster"
        assert event.data["result"] == {"status": "success"}

    @pytest.mark.asyncio
    async def test_publish_inspection_failed(self):
        """Test publish_inspection_failed function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.INSPECTION_FAILED, handler)

        await publish_inspection_failed("test-cluster", "Connection error")

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.INSPECTION_FAILED
        assert event.data["cluster_name"] == "test-cluster"
        assert event.data["error"] == "Connection error"

    @pytest.mark.asyncio
    async def test_publish_task_started(self):
        """Test publish_task_started function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.TASK_STARTED, handler)

        await publish_task_started("task-123", "inspection")

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.TASK_STARTED
        assert event.data["task_id"] == "task-123"
        assert event.data["task_type"] == "inspection"

    @pytest.mark.asyncio
    async def test_publish_task_completed(self):
        """Test publish_task_completed function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.TASK_COMPLETED, handler)

        await publish_task_completed("task-123", {"result": "done"})

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.TASK_COMPLETED
        assert event.data["task_id"] == "task-123"
        assert event.data["result"] == {"result": "done"}

    @pytest.mark.asyncio
    async def test_publish_task_failed(self):
        """Test publish_task_failed function"""
        handler = AsyncMock()
        await event_bus.subscribe(EventType.TASK_FAILED, handler)

        await publish_task_failed("task-123", "Timeout error")

        handler.assert_called_once()
        event = handler.call_args[0][0]
        assert event.type == EventType.TASK_FAILED
        assert event.data["task_id"] == "task-123"
        assert event.data["error"] == "Timeout error"
