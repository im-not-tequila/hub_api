from starlette import status

from app.services.notification import NotificationService
from typing import Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie, Depends

from app.db.redis_connection import redis_client
from app.api.v1.auth.deps import get_current_user
from app.schemas import NotificationResponse
from app.models.postgres import User as UserModel


router = APIRouter(tags=["notifications"])


@router.websocket("/ws")
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


@router.get(
    path="",
    response_model=List[NotificationResponse]
)
async def notifications(
        is_read: bool = None,
        current_user: UserModel = Depends(get_current_user),
        limit: int = 50
):
    return await NotificationService.notifications(current_user.id, is_read, limit)


@router.post(
    path="/mark-as-read",
    status_code=status.HTTP_204_NO_CONTENT
)
async def mark_as_read(
        notification_ids: List[int],
        current_user: UserModel = Depends(get_current_user)
):
    await NotificationService.mark_as_read(current_user.id, notification_ids)
