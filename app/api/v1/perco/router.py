from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.deps import get_current_user
from app.db.session import get_perco_session
from app.models.postgres import User as UserModel

from .schemas import StatusItem


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

