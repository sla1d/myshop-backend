"""WebSocket менеджер для real-time уведомлений."""
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("myshop.ws")


class ConnectionManager:
    """Управление WebSocket подключениями по user_id."""

    def __init__(self):
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info("WS connected: user=%d (total=%d)", user_id, len(self._connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws != websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WS disconnected: user=%d", user_id)

    async def send(self, user_id: int, message: dict[str, Any]) -> bool:
        """Отправить сообщение конкретному пользователю."""
        connections = self._connections.get(user_id, [])
        if not connections:
            return False
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            connections.remove(ws)
        return True

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Отправить всем подключённым пользователям."""
        sent = 0
        for user_id, connections in list(self._connections.items()):
            dead = []
            for ws in connections:
                try:
                    await ws.send_json(message)
                    sent += 1
                except Exception:
                    dead.append(ws)
            for ws in dead:
                connections.remove(ws)
        return sent

    @property
    def online_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


manager = ConnectionManager()
