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
from core.common.metrics import metrics
from .message_models import create_ping_message, create_error_message

logger = get_logger(__name__)


class WebSocketManager:
    """Manager for WebSocket connections and message broadcasting"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_lock = asyncio.Lock()
        self.max_connections = 1000  # Configurable limit
        # Heartbeat tracking: websocket -> {"last_pong": timestamp, "ping_sent": timestamp, "awaiting_pong": bool, "failed_attempts": int}
        self.heartbeat_states: Dict[WebSocket, Dict[str, Any]] = {}
        self.heartbeat_lock = asyncio.Lock()
        # Target subscriptions: websocket -> list of targets
        self.connection_targets: Dict[WebSocket, List[str]] = {}
        self.targets_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """
        Accept a new WebSocket connection

        Args:
            websocket: WebSocket connection to accept
            client_id: Optional client identifier
        """
        async with self.connection_lock:
            logger.debug(
                f"Attempting to accept WebSocket connection. Current connections: {len(self.active_connections)}"
            )
            if len(self.active_connections) >= self.max_connections:
                logger.warning(f"Connection rejected: max connections ({self.max_connections}) reached")
                await websocket.close(code=1008)  # Policy violation
                return

            try:
                await websocket.accept()
                self.active_connections.append(websocket)
                # Initialize heartbeat state
                async with self.heartbeat_lock:
                    self.heartbeat_states[websocket] = {
                        "last_pong": asyncio.get_event_loop().time(),
                        "ping_sent": None,
                        "awaiting_pong": False,
                        "failed_attempts": 0,
                    }
                logger.info(
                    f"WebSocket connection established. Client: {client_id}, Total connections: {len(self.active_connections)}"
                )
            except Exception as e:
                logger.error(f"Failed to accept WebSocket connection: {e}")
                raise

    async def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection

        Args:
            websocket: WebSocket connection to remove
        """
        async with self.connection_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                # Clean up heartbeat state
                async with self.heartbeat_lock:
                    self.heartbeat_states.pop(websocket, None)
                # Clean up targets
                async with self.targets_lock:
                    self.connection_targets.pop(websocket, None)
                logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def set_connection_targets(self, websocket: WebSocket, targets: List[str]):
        """
        Set subscription targets for a WebSocket connection

        Args:
            websocket: WebSocket connection
            targets: List of target strings to subscribe to
        """
        async with self.targets_lock:
            self.connection_targets[websocket] = targets
            logger.debug(f"Set targets for websocket: {targets}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            logger.debug(f"Sending personal message to websocket: {type(message)}")
            json_message = json.dumps(message)
            logger.debug(f"JSON message length: {len(json_message)}")
            await websocket.send_text(json_message)
            logger.debug("Successfully sent personal message")
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            import traceback

            logger.error(f"Send message traceback: {traceback.format_exc()}")
            # Try to send error message before disconnecting
            try:
                error_msg = create_error_message("Failed to send message", {"error": str(e)})
                json_error = json.dumps(error_msg.dict())
                await websocket.send_text(json_error)
            except Exception:
                pass
            # Remove broken connection
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """
        Broadcast a message to active connections, filtered by target if specified

        Args:
            message: Message dictionary to broadcast (may contain 'target' field)
            exclude: Optional WebSocket to exclude from broadcast
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        targets = message.get('target')
        disconnected = []
        message_json = await asyncio.to_thread(json.dumps, message)

        for connection in self.active_connections:
            if connection == exclude:
                continue

            # Check if connection is subscribed to the message's targets
            if targets is not None:
                async with self.targets_lock:
                    connection_targets = self.connection_targets.get(connection, [])
                # If connection has no targets or no overlap with message targets, skip
                if not connection_targets or not any(t in connection_targets for t in targets):
                    continue

            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to broadcast to connection: {e}")
                # Try to send error message before disconnecting
                try:
                    error_msg = create_error_message("Failed to broadcast message", {"error": str(e)})
                    json_error = json.dumps(error_msg.dict())
                    await connection.send_text(json_error)
                except Exception:
                    pass
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

    async def handle_pong(self, websocket: WebSocket):
        """
        Handle pong response from client

        Args:
            websocket: WebSocket connection that sent pong
        """
        async with self.heartbeat_lock:
            if websocket in self.heartbeat_states:
                state = self.heartbeat_states[websocket]
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - state["ping_sent"] if state["ping_sent"] else 0
                state["last_pong"] = current_time
                state["awaiting_pong"] = False
                state["ping_sent"] = None
                state["failed_attempts"] = 0  # Reset failed attempts on successful pong
                logger.debug(f"Pong received from websocket: {websocket}, elapsed: {elapsed:.2f}s")

    async def start_heartbeat(self, websocket: WebSocket):
        """
        Start heartbeat monitoring for a WebSocket connection

        Args:
            websocket: WebSocket connection to monitor
        """
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(30)  # Send ping every 30 seconds

                async with self.heartbeat_lock:
                    if websocket not in self.heartbeat_states:
                        break
                    state = self.heartbeat_states[websocket]

                    # Check if previous ping timed out
                    if state["awaiting_pong"] and state["ping_sent"]:
                        current_time = asyncio.get_event_loop().time()
                        elapsed = current_time - state["ping_sent"]
                        logger.debug(f"Checking heartbeat timeout for websocket: {websocket}, elapsed: {elapsed:.2f}s, awaiting_pong: {state['awaiting_pong']}")
                        if elapsed > 10:  # 10 second timeout
                            state["failed_attempts"] += 1
                            if state["failed_attempts"] >= 3:
                                logger.warning(f"Heartbeat timeout after {state['failed_attempts']} attempts for websocket: {websocket}, closing connection")
                                try:
                                    error_msg = create_error_message("Heartbeat timeout", {"attempts": state["failed_attempts"]})
                                    await self.send_personal_message(error_msg.dict(), websocket)
                                except Exception:
                                    pass
                                await self._close_connection(websocket, code=1008, reason="Heartbeat timeout")
                                break
                            else:
                                logger.warning(f"Heartbeat timeout attempt {state['failed_attempts']} for websocket: {websocket}")

                    # Send ping
                    try:
                        ping_message = create_ping_message()
                        await self.send_personal_message(ping_message.dict(), websocket)
                        state["ping_sent"] = asyncio.get_event_loop().time()
                        state["awaiting_pong"] = True
                        logger.debug(f"Ping sent to websocket: {websocket}")
                    except Exception as e:
                        logger.error(f"Failed to send ping to websocket: {e}")
                        try:
                            error_msg = create_error_message("Failed to send ping", {"error": str(e)})
                            await self.send_personal_message(error_msg.dict(), websocket)
                        except Exception:
                            pass
                        await self._close_connection(websocket, code=1008, reason="Ping send failed")
                        break

        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for websocket: {websocket}")
        except Exception as e:
            logger.error(f"Heartbeat error for websocket: {e}")

    async def _close_connection(self, websocket: WebSocket, code: int = 1000, reason: str = ""):
        """
        Close a WebSocket connection safely

        Args:
            websocket: WebSocket to close
            code: Close code
            reason: Close reason
        """
        try:
            await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.error(f"Error closing websocket: {e}")
        finally:
            await self.disconnect(websocket)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
