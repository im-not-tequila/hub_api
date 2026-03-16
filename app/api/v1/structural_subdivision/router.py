from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_nitro_session
from app.services.structural_subdivision import StructuralSubdivisionService

router = APIRouter()


@router.get(path="/{subdivision_id}/subordinates")
async def get_subordinates(
    subdivision_id: int,
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await StructuralSubdivisionService(
        session_nitro=session_nitro
    ).get_subordinates(subdivision_id, lang)
