from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.calendar.schemas import (
    CalendarEventExtendedProps,
    CalendarEventListItem,
    CalendarEventResponse,
    CreateCalendarEventRequest,
    UpdateCalendarEventRequest,
    EventPlaceItem,
    EventTypeItem,
)
from app.dao.base import PostgresDao
from app.dao.mysql import StructuralSubdivisionDAO
from app.models.mysql.nitro import StructuralSubdivision as StructuralSubdivisionModel
from app.models.postgres import (
    CalendarEventManager,
    CalendarEventPlace,
    CalendarEventType,
    User as UserModel,
)

_LANG = Literal["ru", "kz", "en"]
_TITLE_ATTR = {"ru": "title_ru", "kz": "title_kz", "en": "title_en"}
_DESC_ATTR = {"ru": "description_ru", "kz": "description_kz", "en": "description_en"}
_PLACE_NAME_ATTR = {"ru": "name_ru", "kz": "name_kz", "en": "name_en"}
_TYPE_NAME_ATTR = {"ru": "name_ru", "kz": "name_kz", "en": "name_en"}
_SUBDIVISION_NAME_ATTR = {"ru": "nameru", "kz": "namekz", "en": "nameen"}


class CalendarService:
    def __init__(
        self,
        *,
        session_postgres: AsyncSession,
        session_nitro: AsyncSession | None = None,
    ):
        self.session_postgres = session_postgres
        self.session_nitro = session_nitro

    async def create_event(
        self,
        *,
        body: CreateCalendarEventRequest,
        current_user: UserModel,
    ) -> CalendarEventResponse:
        dao = PostgresDao(self.session_postgres, CalendarEventManager)
        event = await dao.add(
            creator_user_id=current_user.id,
            structural_subdivision_id=body.structural_subdivision_id,
            start_datetime=body.start_datetime,
            end_datetime=body.end_datetime,
            place_id=body.place_id,
            title_ru=body.title_ru,
            title_kz=body.title_kz,
            title_en=body.title_en,
            description_ru=body.description_ru or None,
            description_kz=body.description_kz or None,
            description_en=body.description_en or None,
            needs_media_capture=body.needs_media_capture,
            event_type_id=body.event_type_id,
            contacts=body.contacts,
            needs_tech_support=body.needs_tech_support,
        )
        return CalendarEventResponse.model_validate(event)

    async def list_events(
        self,
        *,
        lang: _LANG,
        current_user: UserModel,
    ) -> list[CalendarEventListItem]:
        stmt = (
            select(CalendarEventManager)
            .where(CalendarEventManager.is_active.is_(True))
            .options(
                selectinload(CalendarEventManager.place),
                selectinload(CalendarEventManager.type),
            )
        )
        result = await self.session_postgres.execute(stmt)
        events = result.scalars().unique().all()

        subdivisions_by_id: dict[int, StructuralSubdivisionModel] = {}
        subdivision_ids = [
            e.structural_subdivision_id
            for e in events
            if e.structural_subdivision_id is not None
        ]
        subdivision_ids = list(dict.fromkeys(subdivision_ids))
        if subdivision_ids:
            if self.session_nitro is None:
                raise RuntimeError("Nitro session is required to list events")
            subdao = StructuralSubdivisionDAO(self.session_nitro)
            subs = await subdao.get_all_filtered(
                filters={StructuralSubdivisionModel.id: subdivision_ids},
                limit=len(subdivision_ids) + 1,
            )
            subdivisions_by_id = {s.id: s for s in subs}

        title_attr = _TITLE_ATTR[lang]
        desc_attr = _DESC_ATTR[lang]
        place_attr = _PLACE_NAME_ATTR[lang]
        type_attr = _TYPE_NAME_ATTR[lang]
        sub_attr = _SUBDIVISION_NAME_ATTR[lang]

        items: list[CalendarEventListItem] = []
        for e in events:
            title = getattr(e, title_attr) or ""
            description = getattr(e, desc_attr)
            place_name = getattr(e.place, place_attr) if e.place else ""
            type_name = getattr(e.type, type_attr) if e.type else ""

            structural_subdivision_name: str | None = None
            if (
                e.structural_subdivision_id
                and e.structural_subdivision_id in subdivisions_by_id
            ):
                structural_subdivision_name = (
                    getattr(subdivisions_by_id[e.structural_subdivision_id], sub_attr)
                    or None
                )

            is_owner = (
                e.creator_user_id is not None and e.creator_user_id == current_user.id
            )

            items.append(
                CalendarEventListItem(
                    id=str(e.id),
                    title=title,
                    start_datetime=e.start_datetime,
                    end_datetime=e.end_datetime,
                    extendedProps=CalendarEventExtendedProps(
                        event_type=type_name,
                        place=place_name,
                        description=description,
                        needs_media=1 if e.needs_media_capture else 0,
                        needs_tech=1 if (e.needs_tech_support is True) else 0,
                        structural_subdivision=structural_subdivision_name,
                        is_owner=is_owner,
                    ),
                )
            )
        return items

    async def get_event(self, *, event_id: int) -> CalendarEventResponse:
        stmt = select(CalendarEventManager).where(
            CalendarEventManager.id == event_id,
            CalendarEventManager.is_active.is_(True),
        )
        result = await self.session_postgres.execute(stmt)
        event = result.scalar_one_or_none()
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return CalendarEventResponse.model_validate(event)

    async def delete_event(self, *, event_id: int, current_user: UserModel) -> None:
        dao = PostgresDao(self.session_postgres, CalendarEventManager)
        event = await dao.get_by_id(event_id)
        if event is None or event.is_active is not True:
            raise HTTPException(status_code=404, detail="Event not found")

        if event.creator_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        event.is_active = False
        await self.session_postgres.commit()

    async def update_event(
        self,
        *,
        event_id: int,
        body: UpdateCalendarEventRequest,
        current_user: UserModel,
    ) -> CalendarEventResponse:
        dao = PostgresDao(self.session_postgres, CalendarEventManager)
        event = await dao.get_by_id(event_id)
        if event is None or event.is_active is not True:
            raise HTTPException(status_code=404, detail="Event not found")

        if event.creator_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        update_data = body.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)

        await self.session_postgres.commit()
        await self.session_postgres.refresh(event)
        return CalendarEventResponse.model_validate(event)

    async def list_places(self, *, lang: _LANG) -> list[EventPlaceItem]:
        stmt = select(CalendarEventPlace).order_by(CalendarEventPlace.id)
        result = await self.session_postgres.execute(stmt)
        places = result.scalars().all()
        name_attr = _PLACE_NAME_ATTR[lang]
        return [
            EventPlaceItem(id=p.id, name=getattr(p, name_attr) or "") for p in places
        ]

    async def list_event_types(self, *, lang: _LANG) -> list[EventTypeItem]:
        stmt = select(CalendarEventType).order_by(CalendarEventType.id)
        result = await self.session_postgres.execute(stmt)
        types = result.scalars().all()
        name_attr = _TYPE_NAME_ATTR[lang]
        return [EventTypeItem(id=t.id, name=getattr(t, name_attr) or "") for t in types]

