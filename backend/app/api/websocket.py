#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket endpoints for real-time communication
"""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from infra.websocket.websocket_manager import websocket_manager
from core.logging import get_logger

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
