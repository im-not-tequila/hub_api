from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, File, Path, Query, UploadFile, WebSocket
from fastapi.responses import FileResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user, get_current_user_ws
from app.services.chat import ChatService
from app.db.session import get_nitro_session, get_postgres_session

from .schemas import (
    ChatUserResponse,
    ChatResponse,
    ChatParticipantResponse,
    ChatMessageResponse,
    SendMessageRequest,
    ForwardMessageRequest,
    CreateChatRequest,
    CreateGroupChatRequest,
    UpdateGroupChatRequest,
    AddChatParticipantsRequest,
    UpdateChatParticipantRequest,
    DeleteMessageRequest,
    DeleteMessageResponse,
    DeleteChatResponse,
    LeaveChatResponse,
    MarkAsReadResponse,
    UploadChatAttachmentResponse,
)

router = APIRouter()


def _get_chat_service(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> ChatService:
    return ChatService(session_postgres=session_postgres, session_nitro=session_nitro)


# ------------------------------------------------------------------ #
#  Пользователи
# ------------------------------------------------------------------ #

@router.get(
    "/users",
    response_model=List[ChatUserResponse],
    summary="Список пользователей для чата",
)
async def get_chat_users(
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Возвращает пользователей, доступных для переписки: коллеги с должностью,
    онлайн-статусом и временем последней активности.
    """
    return await service.get_chat_users(current_user)


# ------------------------------------------------------------------ #
#  Чаты
# ------------------------------------------------------------------ #

@router.get(
    "/chats",
    response_model=List[ChatResponse],
    summary="Список чатов текущего пользователя",
)
async def get_chats(
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Возвращает личные и групповые чаты с последним сообщением,
    количеством непрочитанных и ролью текущего пользователя.
    """
    return await service.get_chats(current_user)


@router.post(
    "/chats",
    response_model=ChatResponse,
    summary="Создать личный чат",
)
async def create_chat(
    body: CreateChatRequest,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Создаёт или возвращает существующий личный чат с указанным участником.
    Нельзя создать чат с самим собой.
    """
    return await service.create_chat(current_user, body.participant_id)


@router.post(
    "/chats/groups",
    response_model=ChatResponse,
    summary="Создать групповой чат",
)
async def create_group_chat(
    body: CreateGroupChatRequest,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Создаёт групповой чат с названием, аватаром и списком участников.
    Создатель автоматически получает роль администратора.
    """
    return await service.create_group_chat(
        current_user=current_user,
        title=body.title,
        participant_ids=body.participant_ids,
        avatar_url=body.avatar_url,
    )


@router.patch(
    "/chats/{chat_id}",
    response_model=ChatResponse,
    summary="Обновить групповой чат",
)
async def update_group_chat(
    chat_id: int = Path(..., description="ID группового чата"),
    body: UpdateGroupChatRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Изменяет название и/или аватар группового чата.
    Доступно только администратору группы.
    """
    return await service.update_group_chat(
        current_user=current_user,
        chat_id=chat_id,
        title=body.title,
        avatar_url=body.avatar_url,
    )


@router.delete(
    "/chats/{chat_id}",
    response_model=DeleteChatResponse,
    summary="Удалить чат",
)
async def delete_chat(
    chat_id: int = Path(..., description="ID чата"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Скрывает чат для текущего пользователя (мягкое удаление из списка).
    Сообщения и участники в базе сохраняются.
    """
    return await service.delete_chat(current_user=current_user, chat_id=chat_id)


# ------------------------------------------------------------------ #
#  Участники
# ------------------------------------------------------------------ #

@router.get(
    "/chats/{chat_id}/participants",
    response_model=List[ChatParticipantResponse],
    summary="Список участников чата",
)
async def get_chat_participants(
    chat_id: int = Path(..., description="ID чата"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """Возвращает активных участников чата с ролями и профилями."""
    return await service.get_chat_participants(current_user, chat_id)


@router.post(
    "/chats/{chat_id}/participants",
    response_model=List[ChatParticipantResponse],
    summary="Добавить участников в групповой чат",
)
async def add_chat_participants(
    chat_id: int = Path(..., description="ID группового чата"),
    body: AddChatParticipantsRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Добавляет одного или нескольких пользователей в групповой чат.
    Доступно только администратору группы.
    """
    return await service.add_chat_participants(
        current_user=current_user,
        chat_id=chat_id,
        user_ids=body.user_ids,
        role=body.role,
    )


@router.patch(
    "/chats/{chat_id}/participants/{user_id}",
    response_model=ChatParticipantResponse,
    summary="Изменить роль участника",
)
async def update_chat_participant_role(
    chat_id: int = Path(..., description="ID группового чата"),
    user_id: int = Path(..., description="ID пользователя"),
    body: UpdateChatParticipantRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Назначает участнику роль `admin` или `member`.
    Доступно только администратору группы.
    """
    return await service.update_chat_participant_role(
        current_user=current_user,
        chat_id=chat_id,
        user_id=user_id,
        role=body.role,
    )


@router.delete(
    "/chats/{chat_id}/participants/me",
    response_model=LeaveChatResponse,
    summary="Выйти из группового чата",
)
async def leave_chat(
    chat_id: int = Path(..., description="ID группового чата"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Текущий пользователь покидает групповой чат.
    Последний администратор не может выйти, пока не назначит другого.
    """
    return await service.leave_chat(current_user=current_user, chat_id=chat_id)


@router.delete(
    "/chats/{chat_id}/participants/{user_id}",
    summary="Удалить участника из группового чата",
)
async def remove_chat_participant(
    chat_id: int = Path(..., description="ID группового чата"),
    user_id: int = Path(..., description="ID удаляемого пользователя"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Исключает участника из группового чата.
    Доступно только администратору. Администратор не может удалить себя.
    """
    return await service.remove_chat_participant(
        current_user=current_user,
        chat_id=chat_id,
        user_id=user_id,
    )


# ------------------------------------------------------------------ #
#  Сообщения
# ------------------------------------------------------------------ #

@router.get(
    "/chats/{chat_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="История сообщений чата",
)
async def get_messages(
    chat_id: int = Path(..., description="ID чата"),
    limit: int = Query(50, ge=1, le=200, description="Количество сообщений (1–200)"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Возвращает сообщения чата в обратном хронологическом порядке
    с вложениями и признаками прочтения.
    """
    return await service.get_messages(current_user, chat_id, limit, offset)


@router.post(
    "/chats/{chat_id}/messages",
    response_model=ChatMessageResponse,
    summary="Отправить сообщение",
)
async def send_message(
    chat_id: int = Path(..., description="ID чата"),
    body: SendMessageRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Отправляет текстовое сообщение и/или прикрепляет ранее загруженные вложения
    (через `POST /chats/{chat_id}/attachments`). Участникам рассылается событие
    через WebSocket.
    """
    return await service.send_message(
        current_user=current_user,
        chat_id=chat_id,
        text=body.text,
        attachment_ids=body.attachment_ids,
    )


@router.get(
    "/messages/incoming",
    response_model=List[ChatMessageResponse],
    summary="Входящие сообщения",
)
async def get_incoming_messages(
    limit: int = Query(50, ge=1, le=200, description="Количество сообщений (1–200)"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """Возвращает входящие сообщения текущего пользователя из всех чатов."""
    return await service.get_incoming_messages(current_user, limit, offset)


@router.get(
    "/messages/outgoing",
    response_model=List[ChatMessageResponse],
    summary="Исходящие сообщения",
)
async def get_outgoing_messages(
    limit: int = Query(50, ge=1, le=200, description="Количество сообщений (1–200)"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """Возвращает исходящие сообщения текущего пользователя из всех чатов."""
    return await service.get_outgoing_messages(current_user, limit, offset)


@router.post(
    "/messages/{message_id}/forward",
    response_model=ChatMessageResponse,
    summary="Переслать сообщение",
)
async def forward_message(
    message_id: int = Path(..., description="ID пересылаемого сообщения"),
    body: ForwardMessageRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Пересылает сообщение в другой чат (`target_chat_id`) или создаёт личный чат
    с получателем (`recipient_id`). Нужно указать ровно один из этих параметров.
    """
    return await service.forward_message(
        current_user=current_user,
        message_id=message_id,
        target_chat_id=body.target_chat_id,
        recipient_id=body.recipient_id,
    )


@router.delete(
    "/messages/{message_id}",
    response_model=DeleteMessageResponse,
    summary="Удалить сообщение",
)
async def delete_message(
    message_id: int = Path(..., description="ID сообщения"),
    body: DeleteMessageRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Удаляет сообщение для себя (`scope=me`) или для всех участников
    (`scope=everyone`). Удаление для всех доступно только отправителю.
    """
    return await service.delete_message(
        current_user=current_user,
        message_id=message_id,
        scope=body.scope,
    )


@router.put(
    "/chats/{chat_id}/messages/read",
    response_model=MarkAsReadResponse,
    summary="Отметить сообщения прочитанными",
)
async def mark_messages_as_read(
    chat_id: int = Path(..., description="ID чата"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Помечает все непрочитанные входящие сообщения в чате как прочитанные.
    Участникам отправляется событие `messages_read` через WebSocket.
    """
    return await service.mark_as_read(current_user, chat_id)


# ------------------------------------------------------------------ #
#  Вложения
# ------------------------------------------------------------------ #

@router.post(
    "/chats/{chat_id}/attachments",
    response_model=UploadChatAttachmentResponse,
    summary="Загрузить вложение",
)
async def upload_attachment(
    chat_id: int = Path(..., description="ID чата"),
    file: UploadFile = File(..., description="Файл или изображение для отправки в чат"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Загружает файл во временное хранилище чата. Возвращает `attachment_id`,
    который нужно передать в `POST /chats/{chat_id}/messages`.
    """
    return await service.upload_attachment(
        current_user=current_user,
        chat_id=chat_id,
        file=file,
    )


@router.get(
    "/attachments/{attachment_id}",
    summary="Скачать вложение",
)
async def get_attachment(
    attachment_id: int = Path(..., description="ID вложения"),
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    """Возвращает файл вложения, если у пользователя есть доступ к чату."""
    payload = await service.get_attachment_file(current_user, attachment_id)
    return FileResponse(
        path=payload["path"],
        media_type=payload["mime_type"],
        filename=payload["filename"],
    )


# ------------------------------------------------------------------ #
#  WebSocket
# ------------------------------------------------------------------ #

@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    refresh_token: Optional[str] = Cookie(None, description="Refresh-токен из cookie для авторизации"),
    user: UserModel = Depends(get_current_user_ws),
    service: ChatService = Depends(_get_chat_service),
):
    """
    Постоянное соединение для получения событий в реальном времени:
    новые сообщения, прочтение, онлайн-статус участников.

    Авторизация через cookie `refresh_token`. При отсутствии токена
    соединение закрывается с кодом 1008.
    """
    await service.handle_websocket(
        websocket=websocket,
        user=user,
        refresh_token=refresh_token,
    )
