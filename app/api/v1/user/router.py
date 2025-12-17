import imghdr
import datetime

from fastapi import APIRouter, Depends, Query, Response
from typing import List

from app.models.postgres import User as UserModel

from app.models.mysql.nitro import (
    Tutor as TutorModel,
    StructuralSubdivision as StructuralSubdivisionModel,
    TutorPositions as TutorPositionsModel
)

from app.api.v1.auth.deps import get_current_user
from app.schemas import UserResponse, BarrierResponse, WorkingHoursResponse
from app.dao.mysql import TutorDAO
from app.dao.postgres import UserDAO
from .schemas import TutorWithPosition
from app.services.user import UserService
from app.db.session import get_nitro_session, get_postgres_session, get_perco_session
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session),
):
    """
    Получение информации о текущем пользователе.
    """

    return await UserService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco,
    ).user_data(
        current_user
    )


@router.get(
    path="/all_tutors_with_position",
    response_model=List[TutorWithPosition]
)
async def get_all_tutors_with_position(
    lang: str = Query('ru', description="Язык: ru, kz, en"),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    current_user: UserModel = Depends(get_current_user)
):
    tutor_dao = TutorDAO(session_nitro)

    all_tutors_and_position = await tutor_dao.join_structural_subdivision_and_tutor_positions_deans(
        filters={
            StructuralSubdivisionModel.subdivision_type: [0, 1, 2, 3]
        },
        fields=[
            TutorModel.TutorID,
            TutorModel.lastname,
            TutorModel.firstname,
            TutorModel.patronymic,
            StructuralSubdivisionModel.nameru,
            StructuralSubdivisionModel.namekz,
            StructuralSubdivisionModel.nameen,
            TutorPositionsModel.NameRU,
            TutorPositionsModel.NameKZ,
            TutorPositionsModel.NameEN
        ]
    )

    structural_subdivision_name_field = {
        'ru': 'nameru',
        'kz': 'namekz',
        'en': 'nameen'
    }.get(lang, 'nameru')

    tutor_position_name_field = {
        'ru': 'NameRU',
        'kz': 'NameKZ',
        'en': 'NameEN'
    }.get(lang, 'nameru')

    response = [
        {
            "tutor_id": tutor.TutorID,
            "lastname": tutor.lastname,
            "firstname": tutor.firstname,
            "patronymic": tutor.patronymic,
            "structural_subdivision_name": getattr(subdivision, structural_subdivision_name_field),
            "tutor_position_name": getattr(position, tutor_position_name_field)
        }
        for tutor, subdivision, position in all_tutors_and_position
    ]

    return response


@router.get(
    path="/{user_id}/avatar"
)
async def avatar(
        user_id: int,
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        current_user: UserModel = Depends(get_current_user)
):
    user_dao = UserDAO(session_postgres)
    tutor_dao = TutorDAO(session_nitro)

    user = await user_dao.get_by_id(user_id)

    tutor = await tutor_dao.get_one_or_none(
        fields=[TutorModel.photo],
        filters={
            TutorModel.TutorID: user.platonus_id
        }
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
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session),
):
    return await UserService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco,
    ).visit_history_barrier(
        current_user,
        target_date
    )


@router.get(
    path="/visit-history/working-hours",
    response_model=List[WorkingHoursResponse]
)
async def visit_history_working_hours(
        start_date: datetime.date = Query(..., description="Дата в формате YYYY-MM-DD"),
        finish_date: datetime.date = Query(..., description="Дата в формате YYYY-MM-DD"),
        current_user: UserModel = Depends(get_current_user),
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session),
):
    return await UserService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco,
    ).visit_history_working_hours(
        current_user,
        start_date,
        finish_date
    )


@router.get(
    path="/vices"
)
async def vices(
    structural_subdivision_id: int,
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
    session_perco: AsyncSession = Depends(get_perco_session),
    current_user: UserModel = Depends(get_current_user),
):
    return await UserService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco,
    ).vices(
        structural_subdivision_id
    )
