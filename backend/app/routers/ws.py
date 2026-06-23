"""WebSocket эндпоинт для уведомлений."""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from app.core.config import settings
from app.core.websocket import manager

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("myshop.ws")


async def authenticate_ws(token: str) -> int | None:
    """Валидация JWT токена для WebSocket."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id and payload.get("type") == "access":
            return int(user_id)
    except (JWTError, ValueError):
        pass
    return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket для real-time уведомлений.

    Подключение: ws://host/ws?token=<access_token>

    Сообщения (JSON):
    - {"type": "order_created", "order_id": 1, "total": 5000}
    - {"type": "order_status", "order_id": 1, "status": "shipped"}
    - {"type": "notification", "message": "Ваш заказ отправлен"}
    """
    user_id = await authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            logger.info("WS message from user %d: %s", user_id, msg)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user_id)
