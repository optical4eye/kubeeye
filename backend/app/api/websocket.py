#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket endpoints for real-time communication
"""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from infra.websocket.websocket_manager import websocket_manager
from core.logging import get_logger
from .version import VERSION

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/tasks")
async def websocket_tasks_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for task-related real-time updates

    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier for tracking connections
    """
    client_id = client_id or "anonymous"
    await websocket_manager.connect(websocket, client_id)
    logger.info(f"WebSocket connection established for tasks endpoint. Client: {client_id}")

    try:
        while True:
            # Keep the connection alive and wait for any client messages
            # Currently, this endpoint is primarily for server-to-client messages
            # But we can extend it to handle client-to-server messages if needed
            data = await websocket.receive_text()
            logger.debug(f"Received message from client {client_id}: {data}")

            # For now, just echo back or handle simple commands
            # In the future, this could handle subscription filters, etc.
            if data.strip():
                await websocket_manager.send_personal_message(
                    {"type": "echo", "message": f"Received: {data}"}, websocket
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for tasks endpoint. Client: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for tasks endpoint: {e}")
    finally:
        await websocket_manager.disconnect(websocket)


@router.websocket("/ws/system-status")
async def websocket_system_status_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for system status real-time updates

    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier for tracking connections
    """
    from infra.dependency_injection.container import get_service
    import asyncio

    client_id = client_id or "anonymous"
    logger.info(f"WebSocket connection attempt for system-status endpoint. Client: {client_id}")

    try:
        await websocket_manager.connect(websocket, client_id)
        logger.info(f"WebSocket connection established for system-status endpoint. Client: {client_id}")
    except Exception as e:
        logger.error(f"Failed to establish WebSocket connection for system-status endpoint. Client: {client_id}, Error: {e}")
        return

    try:
        # Send initial status
        logger.debug(f"Sending initial status update for client: {client_id}")
        await send_system_status_update(websocket)

        update_count = 0
        # Send periodic updates every 30 seconds
        while True:
            logger.debug(f"Waiting 30 seconds before next update for client: {client_id}")
            await asyncio.sleep(30)
            update_count += 1
            logger.debug(f"Sending periodic status update #{update_count} for client: {client_id}")
            await send_system_status_update(websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for system-status endpoint. Client: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for system-status endpoint. Client: {client_id}, Error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.debug(f"Disconnecting WebSocket for client: {client_id}")
        await websocket_manager.disconnect(websocket)


async def send_system_status_update(websocket: WebSocket):
    """Send current system status to the websocket"""
    try:
        logger.debug("Starting to send system status update")
        from infra.dependency_injection.container import get_service
        from infra.websocket.message_models import create_system_status_message

        # Get task queue status
        try:
            logger.debug("Getting task_queue service")
            task_queue = await get_service("task_queue")
            logger.debug("Got task_queue service, getting status")
            queue_status = await task_queue.get_status()
            logger.debug(f"Got queue status: {queue_status}")
        except Exception as e:
            logger.error(f"Failed to get task queue status: {e}")
            queue_status = {"running": False, "active_workers": 0, "pending_tasks": 0}

        # Get database health
        try:
            logger.debug("Getting database health")
            from db.database import health_check
            db_health = await health_check()
            logger.debug(f"Got database health: {db_health}")
            status = "healthy" if db_health.get("status") == "healthy" else "unhealthy"
        except Exception as e:
            logger.error(f"Failed to get database health: {e}")
            status = "unhealthy"

        # Get clusters count (placeholder)
        clusters_count = 0  # TODO: implement actual count

        try:
            logger.debug("Creating system status message")
            message = create_system_status_message(
                status=status,
                queue={
                    "running": queue_status.get("running", False),
                    "active_workers": queue_status.get("active_workers", 0),
                    "pending_tasks": queue_status.get("pending_tasks", 0),
                },
                clusters_count=clusters_count,
                version=VERSION,
            )
            logger.debug(f"Created message: {message.dict()}")
        except Exception as e:
            logger.error(f"Failed to create system status message: {e}")
            return

        logger.info(f"Sending system status update: status={status}, queue={queue_status}")
        await websocket_manager.send_personal_message(message.dict(), websocket)
        logger.debug("Successfully sent system status update")

    except Exception as e:
        logger.error(f"Failed to send system status update: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
