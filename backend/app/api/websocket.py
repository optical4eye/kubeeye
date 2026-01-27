# WebSocket endpoints for real-time communication

from typing import Optional
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from infra.websocket.websocket_manager import websocket_manager
from infra.websocket.message_models import create_pong_message
from core.logging import get_logger
from .version import VERSION

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    Unified WebSocket endpoint for real-time updates

    Args:
        websocket: WebSocket connection
        client_id: Optional client identifier for tracking connections
    """
    import asyncio

    client_id = client_id or "anonymous"
    await websocket_manager.connect(websocket, client_id)
    logger.info(f"WebSocket connection established. Client: {client_id}")

    heartbeat_task = None
    status_update_task = None
    try:
        # Start heartbeat
        heartbeat_task = asyncio.create_task(websocket_manager.start_heartbeat(websocket))

        update_count = 0
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            logger.debug(f"Received message from client {client_id}: {data}")

            # Parse the message
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "pong":
                    await websocket_manager.handle_pong(websocket)
                    logger.debug(f"Handled pong from client {client_id}")
                elif message_type == "ping":
                    # Respond with pong
                    pong_message = create_pong_message()
                    await websocket_manager.send_personal_message(pong_message.dict(), websocket)
                    logger.debug(f"Responded with pong to ping from client {client_id}")
                elif message_type == "subscribe":
                    targets = message.get("payload", {}).get("targets", [])
                    await websocket_manager.set_connection_targets(websocket, targets)
                    logger.debug(f"Set targets for client {client_id}: {targets}")

                    # If subscribing to system_status, start periodic updates
                    if "system_status" in targets and (status_update_task is None or status_update_task.done()):
                        # Send initial status
                        logger.debug(f"Sending initial status update for client: {client_id}")
                        await send_system_status_update(websocket)
                        # Start periodic updates
                        status_update_task = asyncio.create_task(send_periodic_status_updates(websocket, client_id))
                    elif "system_status" not in targets:
                        # Cancel status updates if no longer subscribed
                        if status_update_task and not status_update_task.done():
                            status_update_task.cancel()
                            try:
                                await status_update_task
                            except asyncio.CancelledError:
                                pass
                            status_update_task = None
                else:
                    # Handle other messages or echo
                    if data.strip():
                        await websocket_manager.send_personal_message(
                            {"type": "echo", "message": f"Received: {data}"}, websocket
                        )
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}: {data}")
                await websocket_manager.send_personal_message({"type": "error", "message": "Invalid JSON"}, websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed. Client: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Cancel tasks
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        if status_update_task and not status_update_task.done():
            status_update_task.cancel()
            try:
                await status_update_task
            except asyncio.CancelledError:
                pass
        await websocket_manager.disconnect(websocket)


async def send_periodic_status_updates(websocket: WebSocket, client_id: str):
    """Send periodic system status updates to the websocket"""
    try:
        update_count = 0
        while True:
            await asyncio.sleep(30.0)  # Send every 30 seconds
            update_count += 1
            logger.debug(f"Sending periodic status update #{update_count} for client: {client_id}")
            await send_system_status_update(websocket)
    except asyncio.CancelledError:
        logger.debug(f"Periodic status updates cancelled for client: {client_id}")
    except Exception as e:
        logger.error(f"Error in periodic status updates for client {client_id}: {e}")


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
