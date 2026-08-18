"""
WebSocket connection manager and route for the BBAC Simulator.
Handles real-time bidirectional communication between the FastAPI backend
and the React frontend dashboard.

Exposes:
    manager   — ConnectionManager singleton, imported by main.py to wire
                engine.set_broadcast_callback(manager.broadcast)
    router    — APIRouter containing the /ws/stream endpoint, registered
                in main.py via app.include_router(websocket.router)
"""

import asyncio
import json
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages active WebSocket connections and broadcasts messages to all
    connected dashboard clients.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts a new WebSocket connection and registers it."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            "Client connected. Total connections: %d", len(self.active_connections)
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Removes a WebSocket connection from the active list, if present."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(
            "Client disconnected. Total connections: %d", len(self.active_connections)
        )

    def get_connection_count(self) -> int:
        """Returns the number of currently connected dashboard clients."""
        return len(self.active_connections)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Sends a string message to one specific client."""
        try:
            await websocket.send_text(message)
        except Exception:
            logger.exception("Error sending personal message — disconnecting client.")
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcasts a JSON-serialisable dictionary to all connected clients.
        Connections that fail to receive the message are removed afterward.

        Args:
            message: Dict payload — e.g. the "risk_event" payload built by
                     modules/analytics/engine.py.
        """
        if not self.active_connections:
            return

        # default=str: fallback for any unconverted datetime/UUID/etc, so a
        # serialization edge case fails gracefully instead of dropping the
        # broadcast for every client.
        message_str = json.dumps(message, default=str)

        dead_connections: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_str)
            except Exception:
                logger.exception("Error broadcasting to a client — marking for removal.")
                dead_connections.append(connection)

        for dead in dead_connections:
            await self.disconnect(dead)


# ---------------------------------------------------------------------------
# Global singleton — imported by main.py to wire the analytics engine's
# broadcast callback: engine.set_broadcast_callback(manager.broadcast)
# ---------------------------------------------------------------------------
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket route
# Frontend connects to: ws://localhost:8000/ws/stream
# ---------------------------------------------------------------------------
@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    Real-time stream endpoint for the security dashboard.
    Pushes risk_event payloads (new logs + scores + decisions) to every
    connected client as they are produced by the analytics engine.

    The receive loop below is required by FastAPI/Starlette to detect when
    a client disconnects — without actively reading from the socket, a
    closed browser tab is never noticed until the next failed broadcast.
    The frontend does not need to send anything meaningful; this loop just
    needs to stay alive and catch WebSocketDisconnect.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Block until the client sends something or disconnects.
            # The dashboard frontend does not need to send data — this call
            # exists purely so Starlette can detect a closed connection.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        logger.exception("Unexpected WebSocket error — disconnecting client.")
        await manager.disconnect(websocket)