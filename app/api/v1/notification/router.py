from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie

from app.db.redis_connection import redis_client
from app.api.v1.auth.deps import get_current_user


router = APIRouter(prefix="/ws", tags=["notifications"])


@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, refresh_token: Optional[str] = Cookie(None)):
    # ✅ токен приходит из cookie
    if not refresh_token:
        await websocket.close(code=1008)
        return

    user = await get_current_user(websocket)

    if not user:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"notifications:{user.id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"notifications:{user.id}")
        await pubsub.close()
