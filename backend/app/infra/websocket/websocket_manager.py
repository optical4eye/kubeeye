#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket manager for handling real-time connections and message broadcasting
"""

from typing import List, Dict, Any, Optional
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manager for WebSocket connections and message broadcasting"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_lock = asyncio.Lock()
        self.max_connections = 1000  # Configurable limit

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """
        Accept a new WebSocket connection

        Args:
            websocket: WebSocket connection to accept
            client_id: Optional client identifier
        """
        async with self.connection_lock:
            if len(self.active_connections) >= self.max_connections:
                await websocket.close(code=1008)  # Policy violation
                logger.warning(f"Connection rejected: max connections ({self.max_connections}) reached")
                return

            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection

        Args:
            websocket: WebSocket connection to remove
        """
        async with self.connection_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            # Remove broken connection
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """
        Broadcast a message to all active connections

        Args:
            message: Message dictionary to broadcast
            exclude: Optional WebSocket to exclude from broadcast
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        disconnected = []
        message_json = json.dumps(message)

        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to broadcast to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            await self.disconnect(conn)

        logger.debug(f"Broadcasted message to {len(self.active_connections) - len(disconnected)} connections")

    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """
        Broadcast a message to connections in a specific room
        Note: This is a placeholder for future room-based broadcasting

        Args:
            room: Room identifier
            message: Message to broadcast
        """
        # For now, broadcast to all
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()