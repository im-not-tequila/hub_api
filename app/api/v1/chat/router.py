from fastapi import APIRouter, Depends, Query
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import User as UserModel
from app.api.v1.auth.deps import get_current_user
from app.dao.mysql import TutorDAO
from app.dao.postgres import UserDAO
from app.services.chat import ChatService
from app.db.session import get_nitro_session, get_postgres_session

from .schemas import (
    ChatUserResponse,
    ChatResponse,
    ChatMessageResponse,
    SendMessageRequest,
    CreateChatRequest,
    MarkAsReadResponse,
)

router = APIRouter()


def _get_chat_service(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> ChatService:
    return ChatService(session_postgres=session_postgres, session_nitro=session_nitro)


@router.get("/users", response_model=List[ChatUserResponse])
async def get_chat_users(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = (
        select(UserModel)
        .where(
            UserModel.platonus_id.isnot(None),
            UserModel.is_student == False,
            UserModel.id != current_user.id,
        )
    )
    result = await session_postgres.execute(stmt)
    pg_users = result.scalars().all()

    if not pg_users:
        return []

    platonus_to_pg = {u.platonus_id: u.id for u in pg_users}
    platonus_ids = list(platonus_to_pg.keys())

    tutor_dao = TutorDAO(session_nitro)
    tutor_rows = await tutor_dao.get_tutors_with_positions_by_ids(platonus_ids)

    result_list = []
    for tutor, position in tutor_rows:
        pg_user_id = platonus_to_pg.get(tutor.TutorID)
        if pg_user_id is None:
            continue

        firstname = (tutor.firstname or "").strip().capitalize()
        lastname = (tutor.lastname or "").strip().capitalize()
        patronymic = (tutor.patronymic or "").strip().capitalize()

        first_initial = f"{firstname[0].upper()}." if firstname else ""
        patronymic_initial = f"{patronymic[0].upper()}." if patronymic else ""
        shortname = f"{lastname} {first_initial}{patronymic_initial}".strip()

        post = position.NameRU if position else None

        result_list.append(ChatUserResponse(
            id=pg_user_id,
            firstname=firstname,
            lastname=lastname,
            shortname=shortname,
            avatar=None,
            is_online=False,
            last_seen=None,
            post=post,
        ))

    return result_list


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
    return await service.send_message(current_user, chat_id, body.text)


@router.put("/chats/{chat_id}/messages/read", response_model=MarkAsReadResponse)
async def mark_messages_as_read(
    chat_id: int,
    current_user: UserModel = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
):
    return await service.mark_as_read(current_user, chat_id)
