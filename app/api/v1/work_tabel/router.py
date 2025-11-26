from fastapi import APIRouter, Depends, Response

from app.api.v1.auth.deps import get_current_user
from app.models.postgres import User as UserModel
from app.services.work_tabel import WorkTabelService
from app.db.session import get_nitro_session
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

@router.get(
    path=""
)
async def work_tabel(
        year: int,
        month: int,
        current_user: UserModel = Depends(get_current_user),
        session_nitro: AsyncSession = Depends(get_nitro_session)
):
    return await WorkTabelService(
        session_nitro=session_nitro
    ).work_tabel(
        year,
        month,
        current_user
    )

@router.get(
    path="/excel"
)
async def get_table(
        year: int,
        month: int,
        current_user: UserModel = Depends(get_current_user),
        session_nitro: AsyncSession = Depends(get_nitro_session)
):
    tabel_data = await WorkTabelService(
        session_nitro=session_nitro
    ).work_tabel(
        year,
        month,
        current_user
    )

    headers = {
        "Content-Disposition": "attachment; filename=tabel.xlsx"
    }

    output = await WorkTabelService(
        session_nitro=session_nitro
    ).generate_table_html(
        year,
        month,
        tabel_data
    )

    return Response(content=output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
