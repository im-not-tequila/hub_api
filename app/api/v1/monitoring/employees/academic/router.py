from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Path as PathParam, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.monitoring.schemas import (
    TutorAcademicDetailItem,
    TutorAcademicFirstInItem,
    TutorAcademicListItem,
)
from app.db.session import get_nitro_session, get_perco_session, get_postgres_session
from app.services.monitoring import AbsenceLang, MonitoringService

router = APIRouter()


@router.get(path="/list/active", response_model=list[TutorAcademicListItem])
async def list_employees_academic(
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    lang: AbsenceLang = Query("ru", description="Language: ru/kz/en"),
) -> list[TutorAcademicListItem]:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_employees_academic(lang=lang)


@router.get(path="/list/punctuality", response_model=list[TutorAcademicFirstInItem])
async def list_tutors_academic_punctuality(
    date: datetime.date | None = Query(None, description="Date (YYYY-MM-DD), default=today"),
    session_perco: AsyncSession = Depends(get_perco_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
) -> list[TutorAcademicFirstInItem]:
    return await MonitoringService(
        session_perco=session_perco,
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).list_academic_punctuality(
        startdate=date,
        enddate=date,
    )


@router.get(path="/{id}", response_model=TutorAcademicDetailItem)
async def get_employee_academic(
    platonus_id: int = PathParam(..., alias="id", description="TutorID"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    lang: AbsenceLang = Query("ru", description="Language: ru/kz/en"),
) -> TutorAcademicDetailItem:
    return await MonitoringService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
    ).get_employee_academic(
        platonus_id=platonus_id,
        lang=lang,
    )
