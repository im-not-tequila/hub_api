import imghdr
import datetime

from fastapi import APIRouter, Depends, Query, Response
from typing import List

from app.models.postgres import User as UserModel
from app.models.mysql.nitro import Tutor as TutorModel, StructuralSubdivision as StructuralSubdivisionModel, Student as StudentModel
from app.api.v1.auth.deps import get_current_user
from app.schemas import UserResponse, BarrierResponse, WorkingHoursResponse
from app.dao.mysql import StudentDAO, TutorDAO
from app.dao.postgres import UserInfoDAO, UserDAO
from app.db.session import get_mysql_session, get_postgres_session
from .schemas import TutorWithPosition
from app.services.user import UserService


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе.
    """

    return await UserService().user_data(current_user)


@router.get(
    path="/all_tutors_with_position",
    response_model=List[TutorWithPosition]
)
async def get_all_tutors_with_position(
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    current_user: UserModel = Depends(get_current_user)
):
    async with get_mysql_session() as mysql_session:
        all_tutors_and_position = await TutorDAO(mysql_session).get_tutors_and_position(
            filters={
                StructuralSubdivisionModel.subdivision_type: [0, 1, 2, 3]
            }
        )

        name_field = {
            'ru': 'nameru',
            'kz': 'namekz',
            'en': 'nameen'
        }.get(lang, 'nameru')

        response = [
            {
                "tutor_id": tutor.TutorID,
                "lastname": tutor.lastname,
                "firstname": tutor.firstname,
                "patronymic": tutor.patronymic,
                "position_name": getattr(subdivision, name_field)
            }
            for tutor, subdivision in all_tutors_and_position
        ]

        return response


@router.get(
    path="/{user_id}/avatar"
)
async def avatar(
    user_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    async with get_postgres_session() as postgres_session:
        user = await UserDAO(postgres_session).get_by_id(user_id)

    async with get_mysql_session() as mysql_session:
        tutor = await TutorDAO(mysql_session).get_one_or_none(
            fields=[TutorModel.photo],
            TutorID=user.platonus_id
        )

    if not tutor.photo or tutor.photo == b"0":
        return Response(status_code=204)

    image_type = imghdr.what(None, h=tutor.photo)

    if image_type not in {"jpeg", "png", "gif", "bmp", "webp"}:
        return Response(status_code=400, content="Invalid image data")

    return Response(content=tutor.photo, media_type=f"image/{image_type}")


@router.get(
    path="/visit-history/barrier",
    response_model=List[BarrierResponse]
)
async def visit_history_barrier(
    target_date: datetime.date = Query(..., description="Дата в формате YYYY-MM-DD"),
    current_user: UserModel = Depends(get_current_user)
):
    return await UserService().visit_history_barrier(current_user, target_date)


@router.get(
    path="/visit-history/working-hours",
    response_model=List[WorkingHoursResponse]
)
async def visit_history_working_hours(
    start_date: datetime.date = Query(..., description="Дата в формате YYYY-MM-DD"),
    finish_date: datetime.date = Query(..., description="Дата в формате YYYY-MM-DD"),
    current_user: UserModel = Depends(get_current_user)
):
    return await UserService().visit_history_working_hours(current_user, start_date, finish_date)
