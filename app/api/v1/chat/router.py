from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, File, Query, UploadFile, WebSocket
from fastapi.responses import FileResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user, get_current_user_ws
from app.services.chat import ChatService
from app.db.session import get_nitro_session, get_postgres_session

from .schemas import (
    ChatUserResponse,
    ChatResponse,
    ChatMessageResponse,
    SendMessageRequest,
    CreateChatRequest,
    MarkAsReadResponse,
    UploadChatAttachmentResponse,
)

router = APIRouter()


def _get_chat_service(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> ChatService:
    return ChatService(session_postgres=session_postgres, session_nitro=session_nitro)


@router.get("/users", response_model=List[ChatUserResponse])
async def get_chat_users(
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.get_chat_users(current_user)


@router.get("/chats", response_model=List[ChatResponse])
async def get_chats(
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.get_chats(current_user)


@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    body: CreateChatRequest,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.create_chat(current_user, body.participant_id)


@router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.get_messages(current_user, chat_id, limit, offset)


@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.send_message(
        current_user=current_user,
        chat_id=chat_id,
        text=body.text,
        attachment_ids=body.attachment_ids,
    )


@router.post(
    "/chats/{chat_id}/attachments",
    response_model=UploadChatAttachmentResponse,
)
async def upload_attachment(
    chat_id: int,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.upload_attachment(
        current_user=current_user,
        chat_id=chat_id,
        file=file,
    )


@router.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    payload = await service.get_attachment_file(current_user, attachment_id)
    return FileResponse(
        path=payload["path"],
        media_type=payload["mime_type"],
        filename=payload["filename"],
    )


@router.put("/chats/{chat_id}/messages/read", response_model=MarkAsReadResponse)
async def mark_messages_as_read(
    chat_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.mark_as_read(current_user, chat_id)


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    refresh_token: Optional[str] = Cookie(None),
    user: UserModel = Depends(get_current_user_ws),
    service: ChatService = Depends(_get_chat_service),
):
    await service.handle_websocket(
        websocket=websocket,
        user=user,
        refresh_token=refresh_token,
    )
