from __future__ import annotations

import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.deps import get_current_user
from app.db.session import get_perco_session
from app.models.postgres import User as UserModel

from .schemas import ControlItem, PersonControlItem, StatusItem


router = APIRouter()


@router.get("/status", response_model=list[StatusItem])
async def list_status(
    session_perco: AsyncSession = Depends(get_perco_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[StatusItem]:
    rows = (
        await session_perco.execute(
            text("SELECT id, name FROM status ORDER BY id")
        )
    ).mappings().all()
    return [StatusItem(**dict(r)) for r in rows]


@router.get("/controls", response_model=list[ControlItem])
async def list_controls(
    session_perco: AsyncSession = Depends(get_perco_session),
    # current_user: UserModel = Depends(get_current_user),
) -> list[ControlItem]:
    rows = (
        await session_perco.execute(
            text(
                """
                SELECT
                    turniketid AS turniket_id,
                    name,
                    address,
                    lat,
                    lng
                FROM controls
                ORDER BY turniketid
                """
            )
        )
    ).mappings().all()
    return [ControlItem(**dict(r)) for r in rows]


@router.get("/person-controls", response_model=list[PersonControlItem])
async def list_person_controls(
    turniket_id: int,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    event_type: Literal["in", "out"],
    session_perco: AsyncSession = Depends(get_perco_session),
    # current_user: UserModel = Depends(get_current_user),
) -> list[PersonControlItem]:
    rows = (
        await session_perco.execute(
            text(
                """
                SELECT
                    pc.controlid AS control_id,
                    pc.personid AS person_id,
                    pc.createdate AS create_date,
                    pc.turniketid AS turniket_id,
                    pc.inoutdata AS event_type,
                    pc.role AS role,
                    pc.type AS type,

                    c.name AS control_name,
                    c.address AS control_address,
                    c.lat AS control_lat,
                    c.lng AS control_lng
                FROM personcontrols pc
                LEFT JOIN controls c ON c.turniketid = pc.turniketid
                WHERE pc.turniketid = :turniket_id
                  AND pc.createdate >= :start_date
                  AND pc.createdate <= :end_date
                  AND pc.inoutdata = :event_type
                ORDER BY pc.createdate
                """
            ),
            {
                "turniket_id": turniket_id,
                "start_date": start_date,
                "end_date": end_date,
                "event_type": event_type,
            },
        )
    ).mappings().all()
    return [PersonControlItem(**dict(r)) for r in rows]

