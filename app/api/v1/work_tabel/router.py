from fastapi import APIRouter, Depends, Response

from app.api.v1.auth.deps import get_current_user
from app.models.postgres import User as UserModel
from app.services.work_tabel import WorkTabelService
from app.db.session import get_nitro_session, get_postgres_session, get_perco_session
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

@router.get(
    path=""
)
async def work_tabel(
    subdivision_id: int,
    year: int,
    month: int,
    current_user: UserModel = Depends(get_current_user),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_perco: AsyncSession = Depends(get_perco_session),
):
    return await WorkTabelService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
        session_perco=session_perco,
        ).work_tabel(
            subdivision_id=subdivision_id,
            year=year,
            month=month,
            current_user=current_user
        )

@router.get(
    path="/excel"
)
async def get_table(
        subdivision_id: int,
        year: int,
        month: int,
        current_user: UserModel = Depends(get_current_user),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_perco: AsyncSession = Depends(get_perco_session),
):
    service = WorkTabelService(
        session_nitro=session_nitro,
        session_postgres=session_postgres,
        session_perco=session_perco,
    )

    tabel_data = await service.work_tabel(
        subdivision_id=subdivision_id,
        year=year,
        month=month,
        current_user=current_user,
    )

    headers = {
        "Content-Disposition": "attachment; filename=tabel.xlsx"
    }

    output = await service.generate_table_html(
        year,
        month,
        tabel_data,
    )

    return Response(content=output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
