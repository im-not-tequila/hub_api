from typing import Literal

from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.deps import get_current_user
from app.db.session import get_postgres_session, get_nitro_session
from app.models.postgres import User as UserModel
from app.services.calendar import CalendarService

from .schemas import (
    CreateCalendarEventRequest,
    UpdateCalendarEventRequest,
    CalendarEventResponse,
    CalendarEventListItem,
    EventPlaceItem,
    EventTypeItem,
)

router = APIRouter()
_LANG = Literal["ru", "kz", "en"]


@router.post(
    "",
    response_model=CalendarEventResponse,
    status_code=201,
)
async def create_calendar_event(
    body: CreateCalendarEventRequest,
    current_user: UserModel = Depends(get_current_user),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> CalendarEventResponse:
    return await CalendarService(session_postgres=session_postgres).create_event(
        body=body,
        current_user=current_user,
    )


@router.put(
    "/{event_id}",
    response_model=CalendarEventResponse,
)
async def update_calendar_event(
    event_id: int,
    body: UpdateCalendarEventRequest,
    current_user: UserModel = Depends(get_current_user),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> CalendarEventResponse:
    return await CalendarService(session_postgres=session_postgres).update_event(
        event_id=event_id,
        body=body,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[CalendarEventListItem],
)
async def list_calendar_events(
    lang: _LANG = Query("ru", description="Язык: ru, kz, en"),
    current_user: UserModel = Depends(get_current_user),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> list[CalendarEventListItem]:
    return await CalendarService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    ).list_events(
        lang=lang,
        current_user=current_user,
    )


@router.get(
    "/places",
    response_model=list[EventPlaceItem],
)
async def list_event_places(
    lang: _LANG = Query("ru", description="Язык: ru, kz, en"),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[EventPlaceItem]:
    return await CalendarService(session_postgres=session_postgres).list_places(
        lang=lang,
    )


@router.get(
    "/event-types",
    response_model=list[EventTypeItem],
)
async def list_event_types(
    lang: _LANG = Query("ru", description="Язык: ru, kz, en"),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[EventTypeItem]:
    return await CalendarService(session_postgres=session_postgres).list_event_types(
        lang=lang,
    )


@router.get(
    "/{event_id}",
    response_model=CalendarEventResponse,
)
async def get_calendar_event(
    event_id: int,
    current_user: UserModel = Depends(get_current_user),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> CalendarEventResponse:
    _ = current_user
    return await CalendarService(session_postgres=session_postgres).get_event(
        event_id=event_id
    )


@router.delete(
    "/{event_id}",
    status_code=204,
)
async def delete_calendar_event(
    event_id: int,
    current_user: UserModel = Depends(get_current_user),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> None:
    await CalendarService(session_postgres=session_postgres).delete_event(
        event_id=event_id,
        current_user=current_user,
    )
