from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.structural_subdivision.schemas import StructuralSubdivisionItem
from app.db.session import get_nitro_session
from app.services.structural_subdivision import StructuralSubdivisionService

router = APIRouter()


@router.get("", response_model=list[StructuralSubdivisionItem])
async def get_all_active_structural_subdivisions(
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
):
    """Список структурных подразделений с deleted=0 и is_closed=0."""
    return await StructuralSubdivisionService(
        session_nitro=session_nitro
    ).get_all_active(lang)


@router.get(path="/{subdivision_id}/subordinates")
async def get_subordinates(
    subdivision_id: int,
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
):
    return await StructuralSubdivisionService(
        session_nitro=session_nitro
    ).get_subordinates(subdivision_id, lang)
