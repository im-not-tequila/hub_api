from fastapi import APIRouter, Depends, Response

from app.api.v1.auth.deps import get_current_user
from app.models.postgres import User as UserModel
from app.services.work_tabel import WorkTabelService

router = APIRouter()

@router.get(
    path="/"
)
async def work_tabel(
        year: int,
        month: int,
        current_user: UserModel = Depends(get_current_user)
):
    return await WorkTabelService().work_tabel(year, month, current_user)

@router.get(
    path="/excel"
)
async def get_table(
        year: int,
        month: int,
        current_user: UserModel = Depends(get_current_user)
):
    tabel_data = await WorkTabelService().work_tabel(year, month, current_user)

    headers = {
        "Content-Disposition": "attachment; filename=tabel.xlsx"
    }

    output = await WorkTabelService().generate_table_html(year, month, tabel_data)

    return Response(content=output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
