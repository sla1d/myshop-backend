"""WebSocket эндпоинт для уведомлений и чата поддержки."""
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from app.core.config import settings
from app.core.websocket import manager

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("myshop.ws")


async def authenticate_ws(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id and payload.get("type") == "access":
            return int(user_id)
    except (JWTError, ValueError):
        pass
    return None


# ─── Notifications ────────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
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


# ─── Support Chat ─────────────────────────────────────
chat_connections: dict[str, WebSocket] = {}
admin_chat_connections: dict[str, WebSocket] = {}
chat_messages: dict[str, list[dict]] = defaultdict(list)


@router.websocket("/ws/chat")
async def support_chat(websocket: WebSocket, token: str = Query(...)):
    user_id = await authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    room_id = f"user_{user_id}"
    chat_connections[room_id] = websocket

    for msg in chat_messages[room_id][-50:]:
        await websocket.send_json(msg)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            message = {
                "type": "chat",
                "sender": "user",
                "user_id": user_id,
                "text": msg.get("text", ""),
            }
            chat_messages[room_id].append(message)

            for admin_ws in list(admin_chat_connections.values()):
                try:
                    await admin_ws.send_json({"room_id": room_id, **message})
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        chat_connections.pop(room_id, None)


@router.websocket("/ws/chat/admin")
async def admin_chat(websocket: WebSocket, token: str = Query(...)):
    user_id = await authenticate_ws(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    admin_id = f"admin_{user_id}"
    admin_chat_connections[admin_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            target_room = msg.get("room_id", "")
            if target_room:
                message = {
                    "type": "chat",
                    "sender": "admin",
                    "text": msg.get("text", ""),
                }
                chat_messages[target_room].append(message)
                target_ws = chat_connections.get(target_room)
                if target_ws:
                    try:
                        await target_ws.send_json(message)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        pass
    finally:
        admin_chat_connections.pop(admin_id, None)
